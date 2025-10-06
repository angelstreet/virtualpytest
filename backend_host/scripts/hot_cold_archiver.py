#!/usr/bin/env python3
"""
HOT/COLD STORAGE ARCHIVER - Safety Cleanup + Progressive Grouping
==================================================================

Responsibilities:
1. SAFETY CLEANUP: Enforce hot storage limits on ALL file types (prevent RAM exhaustion)
2. Progressive MP4 merging: HOT TS → 6s → 1min → 10min MP4 saved to COLD /segments/{hour}/
3. Progressive metadata grouping: HOT JSONs → 1min → 10min chunks saved to COLD /metadata/{hour}/
4. Audio extraction & archival: 10min MP4 → HOT audio → COLD /audio/{hour}/
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
# Note: ACTIVE_CAPTURES_FILE managed by run_ffmpeg_and_rename_local.sh (not used here)
ACTIVE_CAPTURES_FILE = '/tmp/active_captures.conf'
RAM_RUN_INTERVAL = 60   # 1min for RAM mode (faster cleanup for video content)
SD_RUN_INTERVAL = 60    # 1min (same for consistency)

# Hot storage limits
# LIFECYCLE:
# - Segments: HOT TS (FFmpeg auto-deletes @ 150, safety cleanup @ 200 if needed) → grouped as MP4 to COLD
# - Captures: HOT only → deleted (uploaded to R2 cloud when needed)
# - Thumbnails: HOT only → deleted (local freeze detection only)
# - Metadata: HOT individual JSONs → grouped & saved to COLD /metadata/{hour}/
# - Transcripts: Saved directly to COLD /transcript/{hour}/ (by transcript_accumulator.py)
# - Audio: HOT 10min chunks → archived to COLD /audio/{hour}/
#
# RAM Usage (HIGH QUALITY CAPTURES - Video content worst case):
# - Segments: 150 × 38KB = 6MB (FFmpeg auto-deletes, 200 limit = safety net)
# - Captures: 300 × 245KB = 74MB (60s buffer → deleted, R2 when needed)
# - Thumbnails: 100 × 28KB = 3MB (freeze detection → deleted)
# - Metadata: 750 × 1KB = 0.75MB (150s buffer → grouped to cold)
# - Transcripts: N/A (saved directly to cold by transcript_accumulator)
# - Audio: 6 × 1MB = 6MB (1h buffer → archived to cold)
# Total: ~90MB per device ✅ (45% of 200MB budget, high quality preserved)
#
HOT_LIMITS = {
    'segments': 200,      # Safety limit > FFmpeg's 150 (only cleanup if FFmpeg fails)
    'captures': 300,      # 60s buffer → deleted (R2 cloud when needed)
    'thumbnails': 100,    # For freeze detection → deleted
    'metadata': 750,      # 150s buffer → grouped to 10min chunks in cold
    'audio': 6,           # 1h buffer (10-min chunks) → archived to cold
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
FILE_PATTERNS = {
    'segments': 'segment_*.ts',     # Archived to cold (will be grouped as MP4)
    'audio': 'chunk_10min_*.mp3',   # Archived to cold /audio/{hour}/
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
        
        # Sort by modification time (oldest first) - CRITICAL for keeping newest files
        files.sort(key=lambda f: f.stat().st_mtime)
        
        # Delete oldest files
        deleted_count = 0
        for filepath in files[:to_delete]:
            try:
                os.remove(str(filepath))
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {filepath}: {e}")
        
        logger.info(f"{file_type}: Safety cleanup deleted {deleted_count} old files ({file_count} → {file_count - deleted_count}, target: {hot_limit})")
        
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
        with open(output_path + '.tmp', 'w') as f:
            json.dump(output_data, f, indent=2)
        os.rename(output_path + '.tmp', output_path)
        
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
    Scan hour directories and rebuild manifest with CONTINUOUS chunks only.
    Works backwards from current time - stops at first missing chunk.
    
    This ensures users get continuous playback experience without gaps.
    
    Returns: Manifest dict with only continuous chunks from now backwards
    """
    import json
    
    segments_dir = os.path.join(capture_dir, 'segments')
    
    if not os.path.isdir(segments_dir):
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    # Build lookup map of all existing chunks: (hour, chunk_index) -> file_info
    existing_chunks = {}
    
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
                
                existing_chunks[(hour, chunk_index)] = chunk_info
                
            except Exception as e:
                logger.warning(f"Error processing chunk file {mp4_file}: {e}")
    
    if not existing_chunks:
        return {"chunks": [], "last_updated": None, "available_hours": [], "total_chunks": 0}
    
    # Find continuous chunks working backwards from NOW
    now = datetime.now()
    current_hour = now.hour
    # Estimate current chunk index based on minutes (0-5 for each 10min chunk)
    current_chunk_index = now.minute // 10
    
    continuous_chunks = []
    
    # Convert to absolute position in 24h cycle (0-143)
    current_position = current_hour * 6 + current_chunk_index
    
    # Work backwards checking each chunk in sequence
    for step in range(144):  # 24 hours × 6 chunks = 144 total positions
        # Calculate position going backwards, wrapping around 24h
        position = (current_position - step) % 144
        hour = position // 6
        chunk_index = position % 6
        
        # Check if this chunk exists
        if (hour, chunk_index) in existing_chunks:
            continuous_chunks.append(existing_chunks[(hour, chunk_index)])
        else:
            # First gap found - stop here for continuous playback
            logger.info(f"Continuous chunks stop at gap: hour={hour}, chunk_index={chunk_index} (found {len(continuous_chunks)} continuous chunks)")
            break
    
    # Sort chunks chronologically (oldest first)
    continuous_chunks.sort(key=lambda x: (x["hour"], x["chunk_index"]))
    
    manifest = {
        "chunks": continuous_chunks,
        "last_updated": time.time(),
        "available_hours": sorted(list(set(c["hour"] for c in continuous_chunks))),
        "total_chunks": len(continuous_chunks),
        "continuous_from": continuous_chunks[0] if continuous_chunks else None,
        "continuous_to": continuous_chunks[-1] if continuous_chunks else None
    }
    
    return manifest


def update_archive_manifest(capture_dir: str, hour: int, chunk_index: int, mp4_path: str):
    import json
    
    manifest_path = os.path.join(capture_dir, 'segments', 'archive_manifest.json')
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except:
            manifest = {"chunks": [], "last_updated": None}
    else:
        manifest = {"chunks": [], "last_updated": None}
    
    mp4_stat = Path(mp4_path).stat()
    metadata_path = os.path.join(capture_dir, 'metadata', str(hour), f'chunk_10min_{chunk_index}.json')
    
    chunk_info = {
        "hour": hour,
        "chunk_index": chunk_index,
        "name": f"chunk_10min_{chunk_index}.mp4",
        "size": mp4_stat.st_size,
        "created": mp4_stat.st_mtime,
        "has_metadata": os.path.exists(metadata_path)
    }
    
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
    
    manifest["chunks"] = [c for c in manifest["chunks"] if not (c["hour"] == hour and c["chunk_index"] == chunk_index)]
    manifest["chunks"].append(chunk_info)
    manifest["chunks"].sort(key=lambda x: (x["hour"], x["chunk_index"]))
    manifest["last_updated"] = time.time()
    manifest["available_hours"] = sorted(list(set(c["hour"] for c in manifest["chunks"])))
    manifest["total_chunks"] = len(manifest["chunks"])
    
    with open(manifest_path + '.tmp', 'w') as f:
        json.dump(manifest, f, indent=2)
    os.rename(manifest_path + '.tmp', manifest_path)
    
    logger.info(f"Updated archive manifest: {manifest['total_chunks']} chunks across {len(manifest['available_hours'])} hours")


def process_capture_directory(capture_dir: str):
    """
    Process single capture directory:
    1. SAFETY CLEANUP: Delete old files for ALL types (prevent RAM exhaustion)
       - Segments: Keep 200 newest (safety net - FFmpeg normally auto-deletes @ 150)
       - Captures: Keep 300 newest (deleted, uploaded to R2 when needed)
       - Thumbnails: Keep 100 newest (deleted, local freeze detection only)
       - Metadata: Keep 750 newest (individual JSONs deleted after grouping to cold)
       - Audio: Keep 6 newest (archived to cold)
    2. Progressive metadata grouping: HOT individual JSONs → 1min → 10min chunks in COLD /metadata/{hour}/
    3. Progressive MP4 merging: HOT TS → 6s → 1min → 10min MP4 chunks in COLD /segments/{hour}/
    4. Archive audio: HOT 10min chunks → COLD /audio/{hour}/
    
    Safety cleanup runs FIRST to guarantee RAM limits regardless of pipeline status.
    Note: Segment limit (200) > FFmpeg's hls_list_size (150) to avoid race conditions.
    """
    logger.info(f"Processing {capture_dir}")
    
    start_time = time.time()
    
    # SAFETY CLEANUP: Keep only newest N files for ALL types (prevent RAM exhaustion)
    deleted_segments = cleanup_hot_files(capture_dir, 'segments', 'segment_*.ts')
    deleted_captures = rotate_hot_captures(capture_dir)
    deleted_thumbnails = clean_old_thumbnails(capture_dir)
    deleted_metadata = cleanup_hot_files(capture_dir, 'metadata', 'capture_*.json')
    deleted_audio = cleanup_hot_files(capture_dir, 'audio', 'chunk_10min_*.mp3')
    
    # Archive audio chunks from hot to cold storage
    archived_audio = archive_hot_files(capture_dir, 'audio')
    
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
    
    # SEGMENTS PROGRESSIVE GROUPING (existing MP4 flow)
    hot_segments = os.path.join(capture_dir, 'hot', 'segments') if ram_mode else os.path.join(capture_dir, 'segments')
    temp_dir = os.path.join(capture_dir, 'segments', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    mp4_6s = merge_progressive_batch(hot_segments, 'segment_*.ts', os.path.join(temp_dir, f'6s_{int(time.time())}.mp4'), 6, True, 10)
    if mp4_6s:
        logger.info("Created 6s MP4")
    
    mp4_1min = merge_progressive_batch(temp_dir, '6s_*.mp4', os.path.join(temp_dir, f'1min_{int(time.time())}.mp4'), 10, True, 15)
    if mp4_1min:
        logger.info("Created 1min MP4")
    
    hour = datetime.now().hour
    hour_dir = os.path.join(capture_dir, 'segments', str(hour))
    os.makedirs(hour_dir, exist_ok=True)
    chunk_index = len(list(Path(hour_dir).glob('chunk_10min_*.mp4')))
    mp4_path = os.path.join(hour_dir, f'chunk_10min_{chunk_index}.mp4')
    mp4_10min = merge_progressive_batch(temp_dir, '1min_*.mp4', mp4_path, 10, True, 20)
    if mp4_10min:
        logger.info(f"Created 10min chunk: {hour}/chunk_10min_{chunk_index}.mp4")
        
        update_archive_manifest(capture_dir, hour, chunk_index, mp4_path)
        
        if ram_mode:
            hot_audio_dir = os.path.join(capture_dir, 'hot', 'audio')
        else:
            hot_audio_dir = os.path.join(capture_dir, 'audio')
        
        os.makedirs(hot_audio_dir, exist_ok=True)
        audio_path = os.path.join(hot_audio_dir, f'chunk_10min_{chunk_index}.mp3')
        
        try:
            import subprocess
            # Extract audio using FFmpeg: MP4 → MP3
            subprocess.run(
                ['ffmpeg', '-i', mp4_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '4', audio_path, '-y'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30
            )
            logger.info(f"Extracted audio to HOT: chunk_10min_{chunk_index}.mp3")
        except Exception as e:
            logger.warning(f"Failed to extract audio from chunk {chunk_index}: {e}")
    
    elapsed = time.time() - start_time
    
    # Build status summary
    mp4_status = [s for s, result in [("6s", mp4_6s), ("1min", mp4_1min), ("10min", mp4_10min)] if result]
    mp4_info = f", MP4: {'+'.join(mp4_status)}" if mp4_status else ""
    
    metadata_status = [s for s, result in [("1min", metadata_1min), ("10min", metadata_10min)] if result]
    metadata_info = f", Metadata: {'+'.join(metadata_status)}" if metadata_status else ""
    
    audio_info = f", Audio: {archived_audio} archived" if archived_audio > 0 else ""
    
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
    if deleted_audio > 0:
        safety_deletes.append(f"{deleted_audio} aud")
    
    cleanup_info = f"del: {', '.join(safety_deletes)}" if safety_deletes else "del: 0"
    
    logger.info(f"✓ Completed in {elapsed:.2f}s ({cleanup_info}{metadata_info}{mp4_info}{audio_info})")


def main_loop():
    """
    Main service loop - Safety Cleanup + Progressive Grouping + Audio Archival
    Processes every 1min:
    - SAFETY CLEANUP: Enforce limits on ALL hot storage types (prevent RAM exhaustion)
    - Metadata: HOT individual JSONs → 1min → 10min chunks saved to COLD /metadata/{hour}/
    - Segments: HOT TS → 6s → 1min → 10min MP4 saved to COLD /segments/{hour}/
    - Audio: Extract from 10min MP4 → HOT → archive to COLD /audio/{hour}/
    
    Safety cleanup runs FIRST and independently from merging/archiving to guarantee
    hot storage never exceeds limits even when pipeline processes fail.
    """
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
    logger.info("Strategy: Safety cleanup (ALL types) + Progressive grouping (MP4/Metadata) + Audio archival")
    logger.info("Safety: Enforces limits FIRST to prevent RAM exhaustion from pipeline failures")
    logger.info("=" * 60)
    
    # STARTUP ONLY: Rebuild all manifests from disk to discover existing chunks
    logger.info("")
    logger.info("=" * 60)
    logger.info("STARTUP: Rebuilding archive manifests from disk...")
    logger.info("=" * 60)
    for capture_dir in capture_dirs:
        try:
            import json
            manifest = rebuild_archive_manifest_from_disk(capture_dir)
            manifest_path = os.path.join(capture_dir, 'segments', 'archive_manifest.json')
            
            # Save rebuilt manifest
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path + '.tmp', 'w') as f:
                json.dump(manifest, f, indent=2)
            os.rename(manifest_path + '.tmp', manifest_path)
            
            logger.info(f"✓ {os.path.basename(capture_dir)}: Rebuilt manifest with {manifest['total_chunks']} chunks across {len(manifest['available_hours'])} hours")
        except Exception as e:
            logger.error(f"Error rebuilding manifest for {capture_dir}: {e}")
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

