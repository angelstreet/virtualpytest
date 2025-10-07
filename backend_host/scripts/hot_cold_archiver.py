#!/usr/bin/env python3
"""
HOT/COLD STORAGE ARCHIVER - Safety Cleanup + Progressive Grouping
==================================================================

Responsibilities:
1. SAFETY CLEANUP: Enforce hot storage limits on ALL file types (prevent RAM exhaustion)
2. Progressive MP4 merging: HOT TS → 1min → 10min MP4 saved to COLD /segments/{hour}/
3. Progressive metadata grouping: HOT JSONs → 1min → 10min chunks saved to COLD /metadata/{hour}/
4. Audio extraction: 10min MP4 → MP3 saved directly to COLD /audio/{hour}/
5. 98% disk write reduction through progressive grouping

Safety cleanup runs FIRST and independently to guarantee hot storage never exceeds
limits even when merging/archiving pipelines fail or get backlogged.

What goes to COLD storage:
- Segments (as 10min MP4 chunks in /segments/{hour}/)
- Metadata (as 10min JSON chunks in /metadata/{hour}/)
- Audio (as 10min MP3 chunks in /audio/{hour}/)
- Transcripts (saved directly by transcript_accumulator.py in /transcript/{hour}/)

What stays HOT-only (deleted):
- Captures (uploaded to R2 cloud when needed)
- Thumbnails (local freeze detection only)
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_base_directories, is_ram_mode
from shared.src.lib.utils.video_utils import merge_progressive_batch

# Configure logging (systemd handles file output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [HOT_COLD_ARCHIVER] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
# Note: This script doesn't use active_captures.conf - it discovers devices via get_capture_base_directories()
# which reads the file from the centralized location (/var/www/html/stream/active_captures.conf)
RAM_RUN_INTERVAL = 60   # 1min for RAM mode (faster cleanup for video content)
SD_RUN_INTERVAL = 60    # 1min (same for consistency)

# Hot storage limits
# LIFECYCLE:
# - Segments: HOT TS (FFmpeg auto-deletes @ 150, safety cleanup @ 200 if needed) → grouped as MP4 to COLD
# - Captures: HOT only → deleted (uploaded to R2 cloud when needed)
# - Thumbnails: HOT only → deleted (local freeze detection only)
# - Metadata: HOT individual JSONs → grouped & saved to COLD /metadata/{hour}/
# - Transcripts: Saved directly to COLD /transcript/{hour}/ (by transcript_accumulator.py)
# - Audio: Extracted directly to COLD /audio/{hour}/ (from 10min MP4 chunks)
#
# RAM Usage (HIGH QUALITY CAPTURES - Video content worst case):
# - Segments: 150 × 38KB = 6MB (FFmpeg auto-deletes, 200 limit = safety net)
# - Captures: 300 × 245KB = 74MB (60s buffer → deleted, R2 when needed)
# - Thumbnails: 100 × 28KB = 3MB (freeze detection → deleted)
# - Metadata: 750 × 1KB = 0.75MB (150s buffer → grouped to cold)
# - Transcripts: N/A (saved directly to cold by transcript_accumulator)
# - Audio: N/A (extracted directly to COLD /audio/{hour}/)
# Total: ~84MB per device (42% of 200MB budget - safe margin for RAM)
#
HOT_LIMITS = {
    'segments': 200,      # Safety limit > FFmpeg's 150 (only cleanup if FFmpeg fails)
    'captures': 300,      # 60s buffer → deleted (R2 cloud when needed)
    'thumbnails': 100,    # For freeze detection → deleted
    'metadata': 750,      # 150s buffer → grouped to 10min chunks in cold
}

# REMOVED: RETENTION_HOURS config
# 
# WHY: Natural 24h rolling buffer through time-based sequential filenames
# All files naturally overwrite after 24h - no retention configuration needed!
# 
# How it works:
# - Files get time-based names based on seconds since midnight
# - After 24h, same time → same filename → automatic overwrite
# - Result: All hour folders maintain 24h of data automatically

# File patterns for archive_hot_files() function (moves files from hot to cold hour folders)
# Note: Metadata uses merge_metadata_batch() instead (groups then saves to cold)
# Note: Transcripts saved directly to cold by transcript_accumulator.py
# Note: Audio extracted directly to cold /audio/{hour}/ (no hot storage needed)
FILE_PATTERNS = {
    'segments': 'segment_*.ts',     # Archived to cold (will be grouped as MP4)
}
# NOT archived (HOT-only with deletion): captures, thumbnails

def get_file_hour(filepath: str) -> int:
    """Get hour (0-23) from file modification time"""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).hour
    except Exception as e:
        logger.error(f"Error getting file hour for {filepath}: {e}")
        return datetime.now().hour


def calculate_time_based_name(filepath: str, file_type: str, fps: int = 5) -> str:
    """
    Calculate time-based sequential filename for 24h rolling buffer
    
    Uses file mtime to calculate position in 24h cycle:
    - Segments (1s): 0-86399 (24h × 3600s)
    - Images (5fps): 0-431999 (86400s × 5fps)
    - Images (2fps): 0-172799 (86400s × 2fps)
    - Transcripts: Keep original name (transcript_hourX.json)
    
    Args:
        filepath: Original file path
        file_type: 'segments', 'captures', 'metadata', 'transcripts'
        fps: Frames per second (for images only)
    
    Returns:
        New filename with time-based sequential number or original name for transcripts
    """
    try:
        # Special case: transcripts keep their original name (transcript_hour13.json)
        if file_type == 'transcripts':
            return os.path.basename(filepath)
        
        mtime = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mtime)
        
        # Calculate seconds since midnight
        seconds_today = (dt.hour * 3600) + (dt.minute * 60) + dt.second
        
        if file_type == 'segments':
            # 1 segment per second: 0-86399
            sequence_num = seconds_today
            new_name = f"segment_{sequence_num:06d}.ts"
        elif file_type in ['captures', 'metadata']:
            # Images at FPS rate
            sequence_num = seconds_today * fps
            
            # Get original filename to extract extension and type
            original_name = os.path.basename(filepath)
            
            if file_type == 'metadata':
                new_name = f"capture_{sequence_num:06d}.json"
            else:  # captures
                new_name = f"capture_{sequence_num:06d}.jpg"
        else:
            # Unknown type, keep original name
            return os.path.basename(filepath)
        
        return new_name
        
    except Exception as e:
        logger.error(f"Error calculating time-based name for {filepath}: {e}")
        return os.path.basename(filepath)


def archive_hot_files(capture_dir: str, file_type: str) -> int:
    """
    Archive hot files to hour folders when exceeding limit
    
    **RAM MODE:** Reads from /hot/captures/, archives to /captures/X/
    **SD MODE:** Reads from /captures/, archives to /captures/X/
    
    GUARANTEES:
    - Always keeps the NEWEST hot_limit files in hot storage
    - Never archives files less than 60 seconds old (safety buffer)
    - Verifies correct file count after archiving
    
    Returns: Number of files archived
    """
    ram_mode = is_ram_mode(capture_dir)
    
    # Determine hot and cold paths based on mode
    if ram_mode:
        # RAM mode: hot storage in /hot/ subdirectory
        hot_dir = os.path.join(capture_dir, 'hot', file_type)
        cold_dir = os.path.join(capture_dir, file_type)
    else:
        # SD mode: hot storage in root, cold in hour subfolders
        hot_dir = os.path.join(capture_dir, file_type)
        cold_dir = hot_dir  # Same directory, hour folders are subdirs
    
    if not os.path.isdir(hot_dir):
        return 0
    
    pattern = FILE_PATTERNS[file_type]
    hot_limit = HOT_LIMITS[file_type]
    
    # Get files in hot storage (root only, not subdirs)
    try:
        files = []
        current_time = time.time()
        
        for item in Path(hot_dir).glob(pattern):
            if item.is_file() and item.parent == Path(hot_dir):
                files.append(item)
        
        file_count = len(files)
        
        if file_count < hot_limit:
            logger.debug(f"{file_type}: {file_count} files (within limit {hot_limit})")
            return 0
        
        # Calculate how many to archive
        to_archive = file_count - hot_limit
        
        # Sort by modification time (oldest first) - CRITICAL for keeping newest files
        files.sort(key=lambda f: f.stat().st_mtime)
        
        # Safety check: Never archive files less than 30 seconds old
        # This protects restart video operations from race conditions
        MIN_AGE_SECONDS = 30
        files_to_archive = []
        files_too_recent = []
        
        for filepath in files[:to_archive]:
            file_age = current_time - filepath.stat().st_mtime
            if file_age >= MIN_AGE_SECONDS:
                files_to_archive.append(filepath)
            else:
                files_too_recent.append(filepath)
        
        if files_too_recent:
            logger.warning(f"{file_type}: {len(files_too_recent)} files too recent to archive (< {MIN_AGE_SECONDS}s old) - keeping in hot storage for safety")
        
        if not files_to_archive:
            logger.info(f"{file_type}: {file_count} files, but all recent files (< {MIN_AGE_SECONDS}s old) - skipping archival for safety")
            return 0
        
        # Log what we're about to do
        oldest_file_age = current_time - files_to_archive[0].stat().st_mtime
        newest_kept_age = current_time - files[-1].stat().st_mtime
        logger.info(f"{file_type}: Archiving {len(files_to_archive)} old files ({file_count} → {hot_limit + len(files_too_recent)}, oldest={oldest_file_age:.1f}s, newest_kept={newest_kept_age:.1f}s)")
        
        archived_count = 0
        for filepath in files_to_archive:
            try:
                # Get hour from file mtime
                file_hour = get_file_hour(str(filepath))
                hour_folder = os.path.join(cold_dir, str(file_hour))
                
                # Ensure hour folder exists
                os.makedirs(hour_folder, exist_ok=True)
                
                # Calculate time-based sequential name for 24h rolling buffer
                # FPS detection: segments=1fps, captures/metadata=5fps default
                fps = 5 if file_type in ['captures', 'metadata'] else 1
                new_filename = calculate_time_based_name(str(filepath), file_type, fps)
                
                # Move file to hour folder with time-based name (RAM → SD or SD root → SD hour)
                dest_path = os.path.join(hour_folder, new_filename)
                
                # If file exists (24h rollover), overwrite it (natural rolling buffer behavior)
                if os.path.exists(dest_path):
                    logger.debug(f"Overwriting existing {new_filename} (24h rollover)")
                    os.remove(dest_path)
                
                shutil.move(str(filepath), dest_path)
                
                archived_count += 1
                mode_label = "RAM→SD" if ram_mode else "hot→cold"
                logger.debug(f"Archived {filepath.name} → {file_type}/{file_hour}/{new_filename} ({mode_label})")
                
            except Exception as e:
                logger.error(f"Error archiving {filepath}: {e}")
        
        # Verify: Count remaining files in hot storage
        remaining_files = [f for f in Path(hot_dir).glob(pattern) if f.is_file() and f.parent == Path(hot_dir)]
        remaining_count = len(remaining_files)
        
        if remaining_count > hot_limit + 10:  # Allow 10 file buffer for race conditions
            logger.warning(f"{file_type}: After archiving, hot storage still has {remaining_count} files (expected ~{hot_limit})")
        else:
            logger.info(f"{file_type}: ✓ Verified hot storage has {remaining_count} files (target: {hot_limit})")
        
        return archived_count
        
    except Exception as e:
        logger.error(f"Error archiving {file_type} files: {e}")
        return 0

def cleanup_hot_files(capture_dir: str, file_type: str, pattern: str) -> int:
    """
    Generic safety cleanup for hot storage - keep only newest N files, DELETE old ones.
    
    This is a safety net to prevent RAM exhaustion when merging/archiving processes fail.
    Works independently from progressive merging/archiving.
    
    Args:
        capture_dir: Base capture directory
        file_type: Type of files ('segments', 'captures', 'metadata', 'audio', 'thumbnails')
        pattern: Glob pattern to match files
    
    Returns: Number of files deleted
    """
    ram_mode = is_ram_mode(capture_dir)
    
    # Determine hot path based on mode
    if ram_mode:
        hot_dir = os.path.join(capture_dir, 'hot', file_type)
    else:
        hot_dir = os.path.join(capture_dir, file_type)
    
    if not os.path.isdir(hot_dir):
        return 0
    
    hot_limit = HOT_LIMITS.get(file_type)
    if not hot_limit:
        return 0
    
    try:
        # Get all files in hot storage (root only, not subdirs)
        files = []
        for item in Path(hot_dir).glob(pattern):
            if item.is_file() and item.parent == Path(hot_dir):
                files.append(item)
        
        file_count = len(files)
        
        if file_count <= hot_limit:
            if file_count > 0:
                logger.debug(f"{file_type}: {file_count} files (within limit {hot_limit})")
            return 0
        
        # Calculate how many to delete
        to_delete = file_count - hot_limit
        
        logger.info(f"{file_type}: Found {file_count} files, need to delete {to_delete} (limit: {hot_limit})")
        
        # Sort by modification time (oldest first) - WITH DIAGNOSTIC LOGGING
        logger.debug(f"{file_type}: Starting sort of {file_count} files...")
        sort_start = time.time()
        
        missing_during_sort = 0
        files_with_mtime = []
        
        for i, filepath in enumerate(files):
            try:
                mtime = filepath.stat().st_mtime
                files_with_mtime.append((filepath, mtime))
            except (FileNotFoundError, OSError) as e:
                missing_during_sort += 1
                logger.warning(f"{file_type}: File disappeared during sort: {filepath.name} (error: {e})")
        
        sort_elapsed = time.time() - sort_start
        logger.info(f"{file_type}: Sort completed in {sort_elapsed*1000:.1f}ms ({missing_during_sort} files disappeared)")
        
        # Sort by cached mtime (no more stat calls)
        files_with_mtime.sort(key=lambda x: x[1])
        files = [f for f, _ in files_with_mtime[:to_delete]]
        
        # Delete oldest files
        deleted_count = 0
        deleted_files = []
        for filepath in files:  # Already filtered to [:to_delete] above
            try:
                os.remove(str(filepath))
                deleted_files.append(filepath.name)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {filepath}: {e}")
        
        if deleted_count > 0:
            first_deleted = deleted_files[0] if deleted_files else 'unknown'
            last_deleted = deleted_files[-1] if deleted_files else 'unknown'
            logger.info(f"{file_type}: Safety cleanup deleted {deleted_count} old files ({file_count} → {file_count - deleted_count}, target: {hot_limit})")
            logger.info(f"{file_type}: Deleted range: {first_deleted} ... {last_deleted}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning {file_type}: {e}")
        return 0


def rotate_hot_captures(capture_dir: str) -> int:
    """
    Rotate hot captures - keep only newest 300 files, DELETE old ones.
    
    Captures don't go to cold storage (pushed to cloud), so we just delete old files.
    This keeps RAM usage under control (60s buffer = 74MB worst case for video content).
    
    Returns: Number of files deleted
    """
    return cleanup_hot_files(capture_dir, 'captures', 'capture_*[0-9].jpg')


def clean_old_thumbnails(capture_dir: str) -> int:
    """
    Clean old thumbnails from /hot/thumbnails/ directory - keep only newest 100 files.
    
    Thumbnails are generated by FFmpeg at same rate as captures (5fps v4l2, 2fps VNC).
    We keep a small buffer (100 files = ~3MB) for freeze detection comparisons.
    Old thumbnails are deleted to save RAM.
    
    Returns: Number of files deleted
    """
    return cleanup_hot_files(capture_dir, 'thumbnails', 'capture_*_thumbnail.jpg')


def cleanup_cold_captures(capture_dir: str) -> int:
    """Delete captures from cold root older than 1 HOUR (for long scripts)"""
    if not is_ram_mode(capture_dir):
        return 0
    
    import time
    deleted = 0
    now = time.time()
    max_age_seconds = 3600  # 1 HOUR
    
    cold_dir = os.path.join(capture_dir, 'captures')
    if not os.path.isdir(cold_dir):
        return 0
    
    try:
        for f in Path(cold_dir).glob('capture_*.jpg'):
            if f.parent == Path(cold_dir) and now - f.stat().st_mtime > max_age_seconds:
                os.remove(str(f))
                deleted += 1
    except Exception as e:
        logger.error(f"Error cleaning cold captures: {e}")
    
    if deleted > 0:
        logger.info(f"Cold captures: Deleted {deleted} files older than 1h")
    
    return deleted


def cleanup_cold_thumbnails(capture_dir: str) -> int:
    """Delete thumbnails from cold root older than 1 HOUR (matches captures retention)"""
    if not is_ram_mode(capture_dir):
        return 0
    
    import time
    deleted = 0
    now = time.time()
    max_age_seconds = 3600  # 1 HOUR
    
    cold_dir = os.path.join(capture_dir, 'thumbnails')
    if not os.path.isdir(cold_dir):
        return 0
    
    try:
        for f in Path(cold_dir).glob('capture_*_thumbnail.jpg'):
            if f.parent == Path(cold_dir) and now - f.stat().st_mtime > max_age_seconds:
                os.remove(str(f))
                deleted += 1
    except Exception as e:
        logger.error(f"Error cleaning cold thumbnails: {e}")
    
    if deleted > 0:
        logger.info(f"Cold thumbnails: Deleted {deleted} files older than 1h")
    
    return deleted


def merge_metadata_batch(source_dir: str, pattern: str, output_path: Optional[str], batch_size: int, fps: int = 5, is_final: bool = False, capture_dir: Optional[str] = None) -> bool:
    """
    Merge metadata files into batches (mirrors merge_progressive_batch for MP4)
    Progressive grouping: individual JSONs → 1min → 10min chunks
    
    Args:
        source_dir: Directory with source metadata files
        pattern: File pattern to match ('capture_*.json' or '1min_*.json')
        output_path: Output file path (or None if is_final=True)
        batch_size: Number of items to batch (60 for 1min, 10 for 10min)
        fps: Frames per second (for calculating time ranges, default 5)
        is_final: If True, save to hour folder as chunk_10min_X.json
        capture_dir: Required if is_final=True
    
    Returns:
        bool: True if batch was created
    """
    import json
    
    # Find source files
    files = sorted(Path(source_dir).glob(pattern))
    
    if not files:
        return False
    
    # Calculate required files for batch
    if pattern == 'capture_*.json':
        # Need 300 files for 1 minute at 5fps (or 120 for 2fps VNC)
        required = 60 * fps
    else:  # '1min_*.json'
        # Need 10 files for 10 minutes
        required = batch_size
    
    if len(files) < required:
        return False
    
    # Take oldest files for batching
    batch_files = files[:required]
    
    try:
        # Aggregate data
        all_frames = []
        for file_path in batch_files:
            # Skip empty files
            if file_path.stat().st_size == 0:
                logger.warning(f"Skipping empty file: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping corrupted JSON file {file_path}: {e}")
                continue
            
            if 'frames' in data:
                # Already aggregated (1min file)
                all_frames.extend(data['frames'])
            else:
                # Individual frame file
                sequence_match = file_path.stem.replace('capture_', '')
                sequence = int(sequence_match)
                all_frames.append({
                    'sequence': sequence,
                    'timestamp': data.get('timestamp'),
                    'filename': data.get('filename'),
                    'blackscreen': data.get('blackscreen', False),
                    'blackscreen_percentage': data.get('blackscreen_percentage', 0),
                    'freeze': data.get('freeze', False),
                    'freeze_diffs': data.get('freeze_diffs', []),
                    'audio': data.get('audio', True),
                    'volume_percentage': data.get('volume_percentage', 0),
                    'mean_volume_db': data.get('mean_volume_db', -100.0)
                })
        
        if not all_frames:
            return False
        
        # Sort by sequence
        all_frames.sort(key=lambda x: x['sequence'])
        
        # Calculate time range and chunk position
        first_seq = all_frames[0]['sequence']
        last_seq = all_frames[-1]['sequence']
        
        # Determine output path
        if is_final:
            # Save to hour folder as chunk_10min_X.json
            hour = (first_seq // (3600 * fps)) % 24
            chunk_index = ((first_seq % (3600 * fps)) // (600 * fps))  # 0-5
            
            hour_dir = os.path.join(capture_dir, 'metadata', str(hour))
            os.makedirs(hour_dir, exist_ok=True)
            
            output_path = os.path.join(hour_dir, f'chunk_10min_{chunk_index}.json')
        
        # Create output structure
        output_data = {
            'frames_count': len(all_frames),
            'frames': all_frames
        }
        
        if is_final:
            hour = (first_seq // (3600 * fps)) % 24
            chunk_index = ((first_seq % (3600 * fps)) // (600 * fps))
            output_data.update({
                'hour': hour,
                'chunk_index': chunk_index,
                'start_time': all_frames[0]['timestamp'],
                'end_time': all_frames[-1]['timestamp']
            })
        
        # Atomic write
        try:
            # Ensure parent directory exists (critical for temp files)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path + '.tmp', 'w') as f:
                json.dump(output_data, f, indent=2)
            os.rename(output_path + '.tmp', output_path)
        except Exception as e:
            logger.error(f"Metadata merge write/rename failed: {e}")
            # Clean up temp file if it exists
            try:
                os.remove(output_path + '.tmp')
            except:
                pass
            return False
        
        # Delete source files (including empty/corrupted ones)
        for file_path in batch_files:
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error merging metadata batch: {e}")
        return False


def rebuild_archive_manifest_from_disk(capture_dir: str) -> dict:
    """
    Scan hour directories and rebuild manifest with ALL available chunks from last 24h.
    
    Returns all chunks regardless of gaps - frontend will grey out missing chunks.
    This allows users to access any archived content even with recording gaps.
    
    Returns: Manifest dict with all chunks found on disk
    """
    import json
    
    segments_dir = os.path.join(capture_dir, 'segments')
    
    if not os.path.isdir(segments_dir):
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    # Build list of all existing chunks from all hour directories
    all_chunks = []
    
    for hour in range(24):
        hour_dir = os.path.join(segments_dir, str(hour))
        if not os.path.isdir(hour_dir):
            continue
        
        for mp4_file in Path(hour_dir).glob('chunk_10min_*.mp4'):
            try:
                chunk_index = int(mp4_file.stem.replace('chunk_10min_', ''))
                mp4_stat = mp4_file.stat()
                
                metadata_path = os.path.join(capture_dir, 'metadata', str(hour), f'chunk_10min_{chunk_index}.json')
                has_metadata = os.path.exists(metadata_path)
                
                chunk_info = {
                    "hour": hour,
                    "chunk_index": chunk_index,
                    "name": mp4_file.name,
                    "size": mp4_stat.st_size,
                    "created": mp4_stat.st_mtime,
                    "has_metadata": has_metadata
                }
                
                if has_metadata:
                    try:
                        with open(metadata_path) as f:
                            meta = json.load(f)
                        chunk_info.update({
                            "start_time": meta.get("start_time"),
                            "end_time": meta.get("end_time"),
                            "frames_count": meta.get("frames_count")
                        })
                    except:
                        pass
                
                all_chunks.append(chunk_info)
                
            except Exception as e:
                logger.warning(f"Error processing chunk file {mp4_file}: {e}")
    
    if not all_chunks:
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    # Sort chunks chronologically (by hour, then chunk_index)
    all_chunks.sort(key=lambda x: (x["hour"], x["chunk_index"]))
    
    manifest = {
        "chunks": all_chunks,
        "last_updated": time.time(),
        "available_hours": sorted(list(set(c["hour"] for c in all_chunks))),
        "total_chunks": len(all_chunks)
    }
    
    return manifest


def rebuild_manifest_from_disk(capture_dir: str, manifest_type: str) -> dict:
    """
    Generic manifest builder for both archive and transcript chunks.
    
    Args:
        capture_dir: Base capture directory
        manifest_type: 'archive' or 'transcript'
    
    Returns: Manifest dict with all chunks found on disk
    """
    import json
    
    if manifest_type == 'archive':
        base_dir = os.path.join(capture_dir, 'segments')
        file_pattern = 'chunk_10min_*.mp4'
        metadata_dir = os.path.join(capture_dir, 'metadata')
    else:  # transcript
        base_dir = os.path.join(capture_dir, 'transcript')
        file_pattern = 'chunk_10min_*.json'
        metadata_dir = None
    
    if not os.path.isdir(base_dir):
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    all_chunks = []
    
    for hour in range(24):
        hour_dir = os.path.join(base_dir, str(hour))
        if not os.path.isdir(hour_dir):
            continue
        
        for chunk_file in Path(hour_dir).glob(file_pattern):
            try:
                chunk_index = int(chunk_file.stem.replace('chunk_10min_', ''))
                file_stat = chunk_file.stat()
                
                chunk_info = {
                    "hour": hour,
                    "chunk_index": chunk_index,
                    "name": chunk_file.name,
                    "size": file_stat.st_size,
                    "created": file_stat.st_mtime,
                }
                
                # Add type-specific metadata
                if manifest_type == 'archive' and metadata_dir:
                    metadata_path = os.path.join(metadata_dir, str(hour), f'chunk_10min_{chunk_index}.json')
                    chunk_info["has_metadata"] = os.path.exists(metadata_path)
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path) as f:
                                meta = json.load(f)
                            chunk_info.update({
                                "start_time": meta.get("start_time"),
                                "end_time": meta.get("end_time"),
                                "frames_count": meta.get("frames_count")
                            })
                        except:
                            pass
                elif manifest_type == 'transcript':
                    try:
                        with open(chunk_file) as f:
                            data = json.load(f)
                        chunk_info.update({
                            "language": data.get("language", "unknown"),
                            "confidence": data.get("confidence", 0.0),
                            "has_transcript": bool(data.get("transcript", "").strip()),
                            "timestamp": data.get("timestamp")
                        })
                    except:
                        pass
                
                all_chunks.append(chunk_info)
                
            except Exception as e:
                logger.warning(f"Error processing {manifest_type} file {chunk_file}: {e}")
    
    if not all_chunks:
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    all_chunks.sort(key=lambda x: (x["hour"], x["chunk_index"]))
    
    return {
        "chunks": all_chunks,
        "last_updated": time.time(),
        "available_hours": sorted(list(set(c["hour"] for c in all_chunks))),
        "total_chunks": len(all_chunks)
    }


def rebuild_archive_manifest_from_disk(capture_dir: str) -> dict:
    """Rebuild archive manifest - wrapper for generic function"""
    return rebuild_manifest_from_disk(capture_dir, 'archive')


def rebuild_transcript_manifest_from_disk(capture_dir: str) -> dict:
    """Rebuild transcript manifest - wrapper for generic function"""
    return rebuild_manifest_from_disk(capture_dir, 'transcript')


def update_manifest(capture_dir: str, hour: int, chunk_index: int, chunk_path: str, manifest_type: str):
    """
    Generic manifest updater for both archive and transcript chunks.
    
    Args:
        capture_dir: Base capture directory
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        chunk_path: Path to chunk file
        manifest_type: 'archive' or 'transcript'
    """
    import json
    
    if manifest_type == 'archive':
        manifest_path = os.path.join(capture_dir, 'segments', 'archive_manifest.json')
    else:  # transcript
        manifest_path = os.path.join(capture_dir, 'transcript', 'transcript_manifest.json')
    
    # Load existing manifest
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except:
            manifest = {"chunks": [], "last_updated": None}
    else:
        manifest = {"chunks": [], "last_updated": None}
    
    file_stat = Path(chunk_path).stat()
    chunk_info = {
        "hour": hour,
        "chunk_index": chunk_index,
        "name": os.path.basename(chunk_path),
        "size": file_stat.st_size,
        "created": file_stat.st_mtime,
    }
    
    # Add type-specific metadata
    if manifest_type == 'archive':
        metadata_path = os.path.join(capture_dir, 'metadata', str(hour), f'chunk_10min_{chunk_index}.json')
        chunk_info["has_metadata"] = os.path.exists(metadata_path)
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path) as f:
                    meta = json.load(f)
                chunk_info.update({
                    "start_time": meta.get("start_time"),
                    "end_time": meta.get("end_time"),
                    "frames_count": meta.get("frames_count")
                })
            except:
                pass
    elif manifest_type == 'transcript':
        try:
            with open(chunk_path) as f:
                data = json.load(f)
            chunk_info.update({
                "language": data.get("language", "unknown"),
                "confidence": data.get("confidence", 0.0),
                "has_transcript": bool(data.get("transcript", "").strip()),
                "timestamp": data.get("timestamp")
            })
        except:
            pass
    
    # Update manifest
    manifest["chunks"] = [c for c in manifest["chunks"] if not (c["hour"] == hour and c["chunk_index"] == chunk_index)]
    manifest["chunks"].append(chunk_info)
    manifest["chunks"].sort(key=lambda x: (x["hour"], x["chunk_index"]))
    manifest["last_updated"] = time.time()
    manifest["available_hours"] = sorted(list(set(c["hour"] for c in manifest["chunks"])))
    manifest["total_chunks"] = len(manifest["chunks"])
    
    # Save atomically
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path + '.tmp', 'w') as f:
        json.dump(manifest, f, indent=2)
    os.rename(manifest_path + '.tmp', manifest_path)
    
    logger.info(f"Updated {manifest_type} manifest: {manifest['total_chunks']} chunks across {len(manifest['available_hours'])} hours")


def update_archive_manifest(capture_dir: str, hour: int, chunk_index: int, mp4_path: str):
    """Update archive manifest - wrapper for generic function"""
    update_manifest(capture_dir, hour, chunk_index, mp4_path, 'archive')


def update_transcript_manifest(capture_dir: str, hour: int, chunk_index: int, transcript_path: str):
    """Update transcript manifest - wrapper for generic function"""
    update_manifest(capture_dir, hour, chunk_index, transcript_path, 'transcript')


def cleanup_temp_files(capture_dir: str) -> Tuple[int, int]:
    """
    Safety cleanup for temp/ directories - delete orphaned 1min files older than 2 hours.
    
    Why this is needed:
    - If 10min merging fails repeatedly, 1min files accumulate forever
    - Prevents disk exhaustion from orphaned temp files
    - 2 hour buffer ensures we don't delete files being actively processed
    
    Returns: (segments_deleted, metadata_deleted)
    """
    import time
    
    segments_deleted = 0
    metadata_deleted = 0
    now = time.time()
    max_age_seconds = 7200  # 2 hours
    
    # Cleanup segments temp directory
    segments_temp = os.path.join(capture_dir, 'segments', 'temp')
    if os.path.isdir(segments_temp):
        try:
            for f in Path(segments_temp).glob('1min_*.mp4'):
                if f.is_file() and now - f.stat().st_mtime > max_age_seconds:
                    try:
                        os.remove(str(f))
                        segments_deleted += 1
                    except Exception as e:
                        logger.error(f"Error deleting old temp segment {f}: {e}")
        except Exception as e:
            logger.error(f"Error scanning segments temp directory: {e}")
    
    # Cleanup metadata temp directory
    metadata_temp = os.path.join(capture_dir, 'metadata', 'temp')
    if os.path.isdir(metadata_temp):
        try:
            for f in Path(metadata_temp).glob('1min_*.json'):
                if f.is_file() and now - f.stat().st_mtime > max_age_seconds:
                    try:
                        os.remove(str(f))
                        metadata_deleted += 1
                    except Exception as e:
                        logger.error(f"Error deleting old temp metadata {f}: {e}")
        except Exception as e:
            logger.error(f"Error scanning metadata temp directory: {e}")
    
    if segments_deleted > 0 or metadata_deleted > 0:
        logger.info(f"Temp cleanup: Deleted {segments_deleted} old segment files, {metadata_deleted} old metadata files (>2h old)")
    
    return segments_deleted, metadata_deleted


def process_capture_directory(capture_dir: str):
    """
    Process single capture directory:
    1. SAFETY CLEANUP: Delete old files for ALL types (prevent RAM exhaustion)
       - Segments: Keep 200 newest (safety net - FFmpeg normally auto-deletes @ 150)
       - Captures: Keep 300 newest (deleted, uploaded to R2 when needed)
       - Thumbnails: Keep 100 newest (deleted, local freeze detection only)
       - Metadata: Keep 750 newest (individual JSONs deleted after grouping to cold)
    2. Progressive metadata grouping: HOT individual JSONs → 1min → 10min chunks in COLD /metadata/{hour}/
    3. Progressive MP4 merging: HOT TS → 1min → 10min MP4 chunks in COLD /segments/{hour}/
    4. Audio extraction: COLD 10min MP4 → direct to COLD /audio/{hour}/
    
    Safety cleanup runs FIRST to guarantee RAM limits regardless of pipeline status.
    Note: Segment limit (200) > FFmpeg's hls_list_size (150) to avoid race conditions.
    """
    logger.info(f"Processing {capture_dir}")
    
    start_time = time.time()
    
    # SAFETY CLEANUP: Keep only newest N files for ALL types (prevent RAM exhaustion)
    # Segments: Let FFmpeg handle cleanup (hls_list_size + delete_segments flag)
    deleted_segments = 0
    deleted_captures = rotate_hot_captures(capture_dir)
    deleted_thumbnails = clean_old_thumbnails(capture_dir)
    deleted_metadata = cleanup_hot_files(capture_dir, 'metadata', 'capture_*.json')
    deleted_cold_captures = cleanup_cold_captures(capture_dir)      # 1 hour retention (for scripts)
    deleted_cold_thumbnails = cleanup_cold_thumbnails(capture_dir)  # 1 hour retention (matches captures)
    # Note: Audio extracted directly to COLD - no hot cleanup needed
    
    ram_mode = is_ram_mode(capture_dir)
    
    # METADATA PROGRESSIVE GROUPING (mirrors MP4 flow: individual → 1min → 10min)
    hot_metadata = os.path.join(capture_dir, 'hot', 'metadata') if ram_mode else os.path.join(capture_dir, 'metadata')
    metadata_temp_dir = os.path.join(capture_dir, 'metadata', 'temp')
    os.makedirs(metadata_temp_dir, exist_ok=True)
    
    # Step 1: Group 1 minute of metadata (300 files at 5fps)
    metadata_1min = merge_metadata_batch(hot_metadata, 'capture_*.json', os.path.join(metadata_temp_dir, f'1min_{int(time.time())}.json'), 60, fps=5)
    if metadata_1min:
        logger.info("Created 1min metadata")
    
    # Step 2: Group 10× 1-minute into 10-minute chunk
    metadata_10min = merge_metadata_batch(metadata_temp_dir, '1min_*.json', None, 10, fps=5, is_final=True, capture_dir=capture_dir)
    if metadata_10min:
        logger.info("Created 10min metadata chunk")
    
    # SEGMENTS PROGRESSIVE GROUPING (2-step: TS → 1min → 10min)
    hot_segments = os.path.join(capture_dir, 'hot', 'segments') if ram_mode else os.path.join(capture_dir, 'segments')
    temp_dir = os.path.join(capture_dir, 'segments', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Step 1: Merge 60 TS segments directly into 1min MP4 (no 6s intermediate)
    mp4_1min = merge_progressive_batch(hot_segments, 'segment_*.ts', os.path.join(temp_dir, f'1min_{int(time.time())}.mp4'), 60, True, 20)
    if mp4_1min:
        logger.info("Created 1min MP4")
    
    # Check if we have enough 1min files for a 10min chunk
    one_min_files = sorted(
        [f for f in Path(temp_dir).glob('1min_*.mp4') if f.is_file()],
        key=os.path.getmtime
    )
    
    mp4_10min = None
    if len(one_min_files) >= 10:
        # Get timestamp from OLDEST 1min file to determine correct chunk time
        oldest_file = one_min_files[0]
        try:
            oldest_timestamp = int(oldest_file.stem.replace('1min_', ''))
            oldest_dt = datetime.fromtimestamp(oldest_timestamp)
            
            # Calculate hour and chunk_index from actual video time (not current time!)
            hour = oldest_dt.hour
            chunk_index = oldest_dt.minute // 10  # 0-5 based on 10-minute window
            
            hour_dir = os.path.join(capture_dir, 'segments', str(hour))
            os.makedirs(hour_dir, exist_ok=True)
            mp4_path = os.path.join(hour_dir, f'chunk_10min_{chunk_index}.mp4')
            
            # Check if chunk exists and if it's old (>12h = previous day's data)
            should_create = True
            if os.path.exists(mp4_path):
                chunk_age = time.time() - os.path.getmtime(mp4_path)
                if chunk_age < 43200:  # 12 hours - still within same day
                    logger.debug(f"Chunk already exists and is recent ({chunk_age/3600:.1f}h old): {hour}/chunk_10min_{chunk_index}.mp4 (skipping duplicate)")
                    should_create = False
                else:
                    logger.info(f"Overwriting old chunk ({chunk_age/3600:.1f}h old): {hour}/chunk_10min_{chunk_index}.mp4 (24h rollover)")
            
            if should_create:
                mp4_10min = merge_progressive_batch(temp_dir, '1min_*.mp4', mp4_path, 10, True, 20)
            else:
                mp4_10min = None
        except (ValueError, OSError) as e:
            logger.error(f"Error calculating chunk time from {oldest_file}: {e}")
    
    if mp4_10min:
        logger.info(f"Created 10min chunk: {hour}/chunk_10min_{chunk_index}.mp4")
        
        update_archive_manifest(capture_dir, hour, chunk_index, mp4_path)
        
        # Extract audio directly to COLD storage (source MP4 already in COLD)
        # Audio extraction is fast (~2-3s) and doesn't need hot storage buffer
        audio_hour_dir = os.path.join(capture_dir, 'audio', str(hour))
        os.makedirs(audio_hour_dir, exist_ok=True)
        audio_path = os.path.join(audio_hour_dir, f'chunk_10min_{chunk_index}.mp3')
        
        try:
            import subprocess
            # Extract audio using FFmpeg: MP4 → MP3 (direct to COLD)
            subprocess.run(
                ['ffmpeg', '-i', mp4_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '4', audio_path, '-y'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30
            )
            logger.info(f"Extracted audio to COLD: /audio/{hour}/chunk_10min_{chunk_index}.mp3")
        except Exception as e:
            logger.warning(f"Failed to extract audio from chunk {chunk_index}: {e}")
    
    # SAFETY CLEANUP: Delete orphaned 1min files older than 2 hours from temp/
    # These are files that failed to merge into 10min chunks (e.g., due to errors)
    # Keep 2h buffer to avoid deleting files currently being processed
    cleanup_temp_files(capture_dir)
    
    elapsed = time.time() - start_time
    
    # Build status summary
    mp4_status = [s for s, result in [("1min", mp4_1min), ("10min", mp4_10min)] if result]
    mp4_info = f", MP4: {'+'.join(mp4_status)}" if mp4_status else ""
    
    metadata_status = [s for s, result in [("1min", metadata_1min), ("10min", metadata_10min)] if result]
    metadata_info = f", Metadata: {'+'.join(metadata_status)}" if metadata_status else ""
    
    # Safety cleanup stats
    safety_deletes = []
    if deleted_segments > 0:
        safety_deletes.append(f"{deleted_segments} seg")
    if deleted_captures > 0:
        safety_deletes.append(f"{deleted_captures} cap")
    if deleted_thumbnails > 0:
        safety_deletes.append(f"{deleted_thumbnails} thumb")
    if deleted_metadata > 0:
        safety_deletes.append(f"{deleted_metadata} meta")
    if deleted_cold_captures > 0:
        safety_deletes.append(f"{deleted_cold_captures} cold_cap")
    if deleted_cold_thumbnails > 0:
        safety_deletes.append(f"{deleted_cold_thumbnails} cold_thumb")
    
    cleanup_info = f"del: {', '.join(safety_deletes)}" if safety_deletes else "del: 0"
    
    logger.info(f"✓ Completed in {elapsed:.2f}s ({cleanup_info}{metadata_info}{mp4_info})")


def main_loop():
    """
    Main service loop - Safety Cleanup + Progressive Grouping + Audio Extraction
    Processes every 1min:
    - SAFETY CLEANUP: Enforce limits on ALL hot storage types (prevent RAM exhaustion)
    - Metadata: HOT individual JSONs → 1min → 10min chunks saved to COLD /metadata/{hour}/
    - Segments: HOT TS → 1min → 10min MP4 saved to COLD /segments/{hour}/
    - Audio: Extract from COLD 10min MP4 → directly to COLD /audio/{hour}/
    
    Safety cleanup runs FIRST and independently from merging/archiving to guarantee
    hot storage never exceeds limits even when pipeline processes fail.
    """
    # Kill any existing archiver instances before starting
    from shared.src.lib.utils.system_utils import kill_existing_script_instances
    killed = kill_existing_script_instances('hot_cold_archiver.py')
    if killed:
        logger.info(f"Killed existing archiver instances: {killed}")
        time.sleep(1)
    
    logger.info("=" * 60)
    logger.info("HOT/COLD ARCHIVER - SAFETY CLEANUP + PROGRESSIVE GROUPING")
    logger.info("=" * 60)
    
    # Detect mode from first capture directory
    capture_dirs = get_capture_base_directories()
    ram_mode = any(is_ram_mode(d) for d in capture_dirs if os.path.exists(d))
    run_interval = RAM_RUN_INTERVAL if ram_mode else SD_RUN_INTERVAL
    
    mode_name = "RAM MODE" if ram_mode else "SD MODE"
    logger.info(f"Mode: {mode_name}")
    logger.info(f"Run interval: {run_interval}s")
    logger.info(f"Hot limits: {HOT_LIMITS}")
    logger.info("Strategy: Safety cleanup (ALL types) + Progressive grouping (MP4/Metadata) + Audio extraction (direct to COLD)")
    logger.info("Safety: Enforces limits FIRST to prevent RAM exhaustion from pipeline failures")
    logger.info("=" * 60)
    
    # STARTUP ONLY: Rebuild all manifests from disk to discover existing chunks
    logger.info("")
    logger.info("=" * 60)
    logger.info("STARTUP: Rebuilding archive and transcript manifests from disk...")
    logger.info("=" * 60)
    for capture_dir in capture_dirs:
        try:
            import json
            
            # Rebuild video archive manifest
            manifest = rebuild_archive_manifest_from_disk(capture_dir)
            manifest_path = os.path.join(capture_dir, 'segments', 'archive_manifest.json')
            
            # Save rebuilt manifest
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path + '.tmp', 'w') as f:
                json.dump(manifest, f, indent=2)
            os.rename(manifest_path + '.tmp', manifest_path)
            
            logger.info(f"✓ {os.path.basename(capture_dir)}: Rebuilt archive manifest with {manifest['total_chunks']} chunks across {len(manifest['available_hours'])} hours")
            
            # Log detailed manifest info
            if manifest['total_chunks'] > 0:
                logger.info(f"   📹 Archive: Available hours: {manifest['available_hours']}")
                # Show first and last chunk as examples
                first_chunk = manifest['chunks'][0]
                last_chunk = manifest['chunks'][-1]
                logger.info(f"   📹 Archive: First chunk: hour {first_chunk['hour']}, chunk {first_chunk['chunk_index']}, size {first_chunk['size']/1024/1024:.1f}MB")
                logger.info(f"   📹 Archive: Last chunk: hour {last_chunk['hour']}, chunk {last_chunk['chunk_index']}, size {last_chunk['size']/1024/1024:.1f}MB")
            else:
                logger.info(f"   📹 Archive: No chunks found")
            
            # Rebuild transcript manifest
            transcript_manifest = rebuild_transcript_manifest_from_disk(capture_dir)
            transcript_manifest_path = os.path.join(capture_dir, 'transcript', 'transcript_manifest.json')
            
            # Save rebuilt transcript manifest
            os.makedirs(os.path.dirname(transcript_manifest_path), exist_ok=True)
            with open(transcript_manifest_path + '.tmp', 'w') as f:
                json.dump(transcript_manifest, f, indent=2)
            os.rename(transcript_manifest_path + '.tmp', transcript_manifest_path)
            
            logger.info(f"✓ {os.path.basename(capture_dir)}: Rebuilt transcript manifest with {transcript_manifest['total_chunks']} chunks across {len(transcript_manifest['available_hours'])} hours")
            
            # Log detailed transcript manifest info
            if transcript_manifest['total_chunks'] > 0:
                logger.info(f"   📝 Transcript: Available hours: {transcript_manifest['available_hours']}")
                # Show first and last transcript chunk
                first_trans = transcript_manifest['chunks'][0]
                last_trans = transcript_manifest['chunks'][-1]
                logger.info(f"   📝 Transcript: First chunk: hour {first_trans['hour']}, chunk {first_trans['chunk_index']}, lang={first_trans.get('language', 'unknown')}, has_text={first_trans.get('has_transcript', False)}")
                logger.info(f"   📝 Transcript: Last chunk: hour {last_trans['hour']}, chunk {last_trans['chunk_index']}, lang={last_trans.get('language', 'unknown')}, has_text={last_trans.get('has_transcript', False)}")
            else:
                logger.info(f"   📝 Transcript: No chunks found")
            
        except Exception as e:
            logger.error(f"Error rebuilding manifests for {capture_dir}: {e}")
    logger.info("=" * 60)
    
    while True:
        try:
            cycle_start = time.time()
            
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"Starting archival cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Current hour: {datetime.now().hour}")
            logger.info("=" * 60)
            
            # Get active capture directories
            capture_dirs = get_capture_base_directories()
            logger.info(f"Processing {len(capture_dirs)} capture directories")
            
            # Process each directory
            for capture_dir in capture_dirs:
                try:
                    process_capture_directory(capture_dir)
                except Exception as e:
                    logger.error(f"Error processing {capture_dir}: {e}", exc_info=True)
            
            cycle_elapsed = time.time() - cycle_start
            logger.info("=" * 60)
            logger.info(f"Cycle completed in {cycle_elapsed:.2f}s")
            logger.info(f"Next run in {run_interval}s")
            logger.info("=" * 60)
            
            # Sleep until next cycle
            time.sleep(run_interval)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(run_interval)


if __name__ == '__main__':
    try:
        main_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

