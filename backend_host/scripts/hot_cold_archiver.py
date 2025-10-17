#!/usr/bin/env python3
"""
HOT/COLD STORAGE ARCHIVER - Safety Cleanup + Progressive MP4 Building
======================================================================

Responsibilities:
1. SAFETY CLEANUP: Enforce hot storage limits on ALL file types (prevent RAM exhaustion)
2. Progressive MP4 building: HOT TS → 1min MP4 → append to growing 10min chunk in COLD
3. Audio extraction: 10min MP4 → MP3 saved directly to COLD /audio/{hour}/
4. KEEP 1min MP4s: Rotating slots (0-9) for individual playback until overwritten

Progressive append: Each minute appends 1min to the growing chunk (same URL, grows 1→10min)
Result: Frontend timeline has NO CHANGES - same chunk URL just grows in duration
1min MP4s: Kept in temp/ using rotating slots, playable individually for ~10 minutes

Note: Metadata archival is handled by capture_monitor.py (incremental append to chunks)

What goes to COLD storage (SD mode) or HOT storage (RAM mode):
- Segments (as 10min MP4 chunks in /segments/{hour}/)
- Metadata (as 10min JSON chunks in /metadata/{hour}/)
- Audio (as 10min MP3 chunks in /audio/{hour}/ - HOT in RAM mode!)
- Transcripts (saved directly by transcript_accumulator.py in /transcript/{hour}/ - always COLD)

What stays HOT-only (deleted):
- Captures (uploaded to R2 cloud when needed)
- Thumbnails (local freeze detection only)
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict

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

# ANSI color codes for terminal output
class Colors:
    BLUE = '\033[94m'      # Cold storage
    CYAN = '\033[96m'      # Info/stats
    GREEN = '\033[92m'     # Success
    YELLOW = '\033[93m'    # Warning
    RED = '\033[91m'       # Error
    BOLD = '\033[1m'
    RESET = '\033[0m'      # Reset to default

# Configuration
# Note: This script doesn't use active_captures.conf - it discovers devices via get_capture_base_directories()
# which reads the file from the centralized location (/var/www/html/stream/active_captures.conf)

# DUAL-THREAD ARCHITECTURE:
# - HOT thread: Critical RAM management (fast, every 15s)
# - COLD thread: Batch cleanup (slow, every 60s, max 200 files per device)
HOT_THREAD_INTERVAL = 15    # 15s - hot storage cleanup + MP4 building
COLD_THREAD_INTERVAL = 60   # 60s - cold storage cleanup (batched)
COLD_BATCH_LIMIT = 200      # Max files to delete per device per cold cycle (prevents hour-long cycles)

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

def get_directory_size(path: str) -> int:
    """Get directory size in bytes"""
    try:
        result = subprocess.run(
            ['du', '-sb', path],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.split()[0])
    except:
        pass
    return 0


def get_ram_disk_usage() -> Dict[str, any]:
    """Get RAM disk usage statistics for /var/www/html/stream/"""
    try:
        result = subprocess.run(
            ['df', '-h', '/var/www/html/stream/'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                return {
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4]
                }
    except:
        pass
    return {}


def get_hot_folder_stats(capture_dir: str) -> Dict[str, int]:
    """Get file counts and sizes for hot storage folders"""
    ram_mode = is_ram_mode(capture_dir)
    hot_base = os.path.join(capture_dir, 'hot') if ram_mode else capture_dir
    
    stats = {}
    for file_type in ['segments', 'captures', 'thumbnails', 'metadata']:
        hot_dir = os.path.join(hot_base, file_type)
        if os.path.isdir(hot_dir):
            # Count files in root only (not subdirs)
            files = [f for f in Path(hot_dir).iterdir() if f.is_file() and f.parent == Path(hot_dir)]
            stats[file_type] = {
                'count': len(files),
                'size_bytes': sum(f.stat().st_size for f in files if f.exists())
            }
        else:
            stats[file_type] = {'count': 0, 'size_bytes': 0}
    
    return stats


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}TB"


def print_ram_summary(capture_dirs: List[str], label: str):
    """Print comprehensive RAM usage summary"""
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"{label}")
    logger.info("=" * 80)
    
    # Global RAM disk stats
    ram_stats = get_ram_disk_usage()
    if ram_stats:
        logger.info(f"🖴  RAM DISK (/var/www/html/stream/): {ram_stats['used']}/{ram_stats['size']} ({ram_stats['use_percent']}) - Available: {ram_stats['available']}")
    
    # Per-capture directory breakdown
    total_hot_size = 0
    for capture_dir in capture_dirs:
        device_name = os.path.basename(capture_dir)
        stats = get_hot_folder_stats(capture_dir)
        
        # Calculate totals
        total_files = sum(s['count'] for s in stats.values())
        total_size = sum(s['size_bytes'] for s in stats.values())
        total_hot_size += total_size
        
        # Build breakdown string
        breakdown = []
        for file_type, data in stats.items():
            if data['count'] > 0:
                limit = HOT_LIMITS.get(file_type, 0)
                limit_str = f"/{limit}" if limit > 0 else ""
                breakdown.append(f"{file_type}={data['count']}{limit_str}({format_bytes(data['size_bytes'])})")
        
        logger.info(f"  📁 {device_name}/hot: {total_files} files, {format_bytes(total_size)} - [{', '.join(breakdown)}]")
    
    logger.info(f"  ∑ Total hot storage: {format_bytes(total_hot_size)}")
    logger.info("=" * 80)


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


def cleanup_cold_captures(capture_dir: str, batch_limit: Optional[int] = None) -> int:
    """
    Delete captures from cold root older than 1 HOUR (for long scripts)
    
    Args:
        capture_dir: Base capture directory
        batch_limit: Max files to delete (prevents long-running cycles)
    
    Returns: Number of files deleted
    """
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
        # Collect old files (sorted by age, oldest first)
        old_files = []
        for f in Path(cold_dir).glob('capture_*.jpg'):
            if f.parent == Path(cold_dir):
                age = now - f.stat().st_mtime
                if age > max_age_seconds:
                    old_files.append((age, f))
        
        # Sort by age (oldest first) and apply batch limit
        old_files.sort(key=lambda x: x[0], reverse=True)
        if batch_limit and len(old_files) > batch_limit:
            old_files = old_files[:batch_limit]
            logger.info(f"Cold captures: Batching {batch_limit} of {len(old_files)} old files")
        
        # Delete files
        for _, f in old_files:
            os.remove(str(f))
            deleted += 1
            
    except Exception as e:
        logger.error(f"Error cleaning cold captures: {e}")
    
    if deleted > 0:
        logger.info(f"Cold captures: Deleted {deleted} files older than 1h")
    
    return deleted


def cleanup_cold_thumbnails(capture_dir: str, batch_limit: Optional[int] = None) -> int:
    """
    Delete thumbnails from cold root older than 1 HOUR (matches captures retention)
    
    Args:
        capture_dir: Base capture directory
        batch_limit: Max files to delete (prevents long-running cycles)
    
    Returns: Number of files deleted
    """
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
        # Collect old files (sorted by age, oldest first)
        old_files = []
        for f in Path(cold_dir).glob('capture_*_thumbnail.jpg'):
            if f.parent == Path(cold_dir):
                age = now - f.stat().st_mtime
                if age > max_age_seconds:
                    old_files.append((age, f))
        
        # Sort by age (oldest first) and apply batch limit
        old_files.sort(key=lambda x: x[0], reverse=True)
        if batch_limit and len(old_files) > batch_limit:
            old_files = old_files[:batch_limit]
            logger.info(f"Cold thumbnails: Batching {batch_limit} of {len(old_files)} old files")
        
        # Delete files
        for _, f in old_files:
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
        # Individual files: batch_size is in seconds
        # e.g., 600 seconds * 5fps = 3000 files for 10 minutes
        required = batch_size * fps
    else:  # '1min_*.json' (legacy, not used anymore)
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
                # Skip language-specific files (chunk_10min_0_fr.json, chunk_10min_0_de.json, etc.)
                # Only process base chunk files (chunk_10min_0.json)
                stem = chunk_file.stem.replace('chunk_10min_', '')
                if '_' in stem:
                    # This is a language-specific file (e.g., "0_fr"), skip it
                    continue
                
                chunk_index = int(stem)
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
                        
                        # Check if corresponding MP3 exists in same hour folder
                        # No timestamp comparison needed - hour folder matching ensures they belong together
                        # (24h rolling buffer automatically overwrites old files in same hour/chunk slot)
                        device_folder = os.path.basename(capture_dir)
                        from shared.src.lib.utils.storage_path_utils import get_audio_path
                        audio_base = get_audio_path(device_folder)
                        audio_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
                        
                        has_mp3 = os.path.exists(audio_path)
                        
                        chunk_info["has_mp3"] = has_mp3
                        if not has_mp3:
                            chunk_info["unavailable_since"] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
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


def update_manifest(capture_dir: str, hour: int, chunk_index: int, chunk_path: str, manifest_type: str, has_mp3: bool = True):
    """
    Generic manifest updater for both archive and transcript chunks.
    
    Args:
        capture_dir: Base capture directory
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        chunk_path: Path to chunk file
        manifest_type: 'archive' or 'transcript'
        has_mp3: Whether corresponding MP3 exists (transcript only)
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
        # Validate MP3 existence in same hour folder
        # No timestamp comparison needed - hour folder matching ensures they belong together
        # (24h rolling buffer automatically overwrites old files in same hour/chunk slot)
        device_folder = os.path.basename(capture_dir)
        from shared.src.lib.utils.storage_path_utils import get_audio_path
        audio_base = get_audio_path(device_folder)
        audio_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
        
        has_mp3_validated = os.path.exists(audio_path)
        
        chunk_info["has_mp3"] = has_mp3_validated
        if not has_mp3_validated:
            chunk_info["unavailable_since"] = datetime.now().isoformat()
        
        try:
            with open(chunk_path) as f:
                data = json.load(f)
            
            # Include full transcript data in manifest (optimization: 1 call instead of 2)
            chunk_info.update({
                "language": data.get("language", "unknown"),
                "confidence": data.get("confidence", 0.0),
                "has_transcript": bool(data.get("transcript", "").strip()),
                "timestamp": data.get("timestamp"),
                "transcript": data.get("transcript", ""),  # Full transcript text
                "segments": data.get("segments", []),  # Timed segments for subtitles
                "transcription_time_seconds": data.get("transcription_time_seconds", 0),
                "mp3_file": data.get("mp3_file", "")
            })
            
            # Check for pre-translated language files
            available_languages = ['original']  # Original language is always available
            available_dubbed_languages = []  # Dubbed audio files
            
            chunk_dir = os.path.dirname(chunk_path)
            chunk_basename = os.path.basename(chunk_path).replace('.json', '')
            
            # Check for language-specific transcript files
            # If transcript exists for a language, dubbed audio can be generated on-demand
            for lang_code in ['fr', 'en', 'es', 'de', 'it']:
                # Check transcript file
                lang_file = os.path.join(chunk_dir, f'{chunk_basename}_{lang_code}.json')
                if os.path.exists(lang_file):
                    available_languages.append(lang_code)
                    # If transcript exists, audio can be dubbed on-demand
                    available_dubbed_languages.append(lang_code)
            
            chunk_info["available_languages"] = available_languages
            chunk_info["available_dubbed_languages"] = available_dubbed_languages
            
            logger.debug(f"Transcript manifest updated: {chunk_basename} - languages={available_languages}, dubbed={available_dubbed_languages}, transcript_chars={len(data.get('transcript', ''))}")
        except Exception as e:
            logger.error(f"Error updating transcript manifest for {chunk_path}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Set defaults on error
            chunk_info["available_languages"] = ['original']
            chunk_info["available_dubbed_languages"] = []
    
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


def update_transcript_manifest(capture_dir: str, hour: int, chunk_index: int, transcript_path: str, has_mp3: bool = True):
    """Update transcript manifest - wrapper for generic function"""
    update_manifest(capture_dir, hour, chunk_index, transcript_path, 'transcript', has_mp3=has_mp3)


def cleanup_temp_files(capture_dir: str) -> Tuple[int, int, int]:
    """
    Safety cleanup for temp/ directories - delete orphaned 1min files.
    
    Why this is needed:
    - 1min MP4: Rotating slots (0-9) auto-overwrite, NO cleanup needed!
    - 1min JSON: Delete after 2 hours (if 10min merging fails repeatedly)
    - 1min MP3: Rotating slots (0-9) auto-overwrite, light cleanup as safety net
    - Prevents disk exhaustion from orphaned temp files
    
    Returns: (segments_deleted, metadata_deleted, mp3_deleted)
    """
    import time
    
    segments_deleted = 0
    metadata_deleted = 0
    mp3_deleted = 0
    now = time.time()
    max_age_seconds = 7200  # 2 hours for JSON
    max_age_mp3_seconds = 900  # 15 minutes for MP3 (rotating slots should handle @ 10min)
    
    # Cleanup segments temp directory
    # NOTE: 1min MP4s use rotating slots (0-9) and auto-overwrite - NO cleanup needed!
    # They remain playable individually until overwritten (~10 minutes)
    segments_temp = os.path.join(capture_dir, 'segments', 'temp')
    if os.path.isdir(segments_temp):
        # SKIP 1min_*.mp4 files - they use rotating slots and shouldn't be deleted
        logger.debug(f"Skipping cleanup of 1min MP4s (rotating slot system - last 10 files kept)")
        
        # Only cleanup if there are non-rotating files (shouldn't happen, but safety net)
        try:
            pass  # No cleanup needed for rotating slot MP4s
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
    
    # Cleanup audio temp directory (1min MP3s with rotating slots)
    # Rotating slots (0-9) should auto-delete old files, but this is a safety net
    device_folder = os.path.basename(capture_dir)
    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
    audio_cold = get_cold_storage_path(device_folder, 'audio')
    audio_temp = os.path.join(audio_cold, 'temp')
    
    if os.path.isdir(audio_temp):
        try:
            for f in Path(audio_temp).glob('1min_*.mp3'):
                if f.is_file():
                    file_age = now - f.stat().st_mtime
                    if file_age > max_age_mp3_seconds:
                        try:
                            os.remove(str(f))
                            mp3_deleted += 1
                            logger.warning(f"Safety cleanup: Deleted stuck 1min MP3 ({file_age:.0f}s old): {f.name}")
                        except Exception as e:
                            logger.error(f"Error deleting old temp MP3 {f}: {e}")
        except Exception as e:
            logger.error(f"Error scanning audio temp directory: {e}")
    
    if segments_deleted > 0 or metadata_deleted > 0 or mp3_deleted > 0:
        logger.info(f"Temp cleanup: Deleted {segments_deleted} old segments (>2h), {metadata_deleted} old metadata (>2h), {mp3_deleted} old MP3s (>15min)")
    
    return segments_deleted, metadata_deleted, mp3_deleted


def process_hot_storage(capture_dir: str):
    """
    HOT STORAGE PROCESSING (Fast, Critical, Every 15s)
    
    1. SAFETY CLEANUP: Delete old files from HOT storage (prevent RAM exhaustion)
       - Segments: Keep 200 newest (safety net - FFmpeg normally auto-deletes @ 150)
       - Captures: Keep 300 newest (deleted, uploaded to R2 when needed)
       - Thumbnails: Keep 100 newest (deleted, local freeze detection only)
       - Metadata: Keep 750 newest (individual JSONs, archived incrementally by capture_monitor)
    2. Progressive MP4 building: HOT TS → 1min MP4 → append to growing 10min chunk in COLD
    3. Audio extraction: COLD 10min MP4 → direct to COLD /audio/{hour}/
    
    Progressive append: Same chunk URL grows from 1min to 10min (no timeline changes)
    """
    logger.info(f"🔥 HOT: {os.path.basename(capture_dir)}")
    
    start_time = time.time()
    
    # SAFETY CLEANUP: Keep only newest N files for HOT types (prevent RAM exhaustion)
    # Segments: Let FFmpeg handle cleanup (hls_list_size + delete_segments flag)
    deleted_segments = 0
    deleted_captures = rotate_hot_captures(capture_dir)
    deleted_thumbnails = clean_old_thumbnails(capture_dir)
    deleted_metadata = cleanup_hot_files(capture_dir, 'metadata', 'capture_*.json')
    # Note: Cold cleanup moved to separate thread
    # Note: Audio extracted directly to COLD - no hot cleanup needed
    
    ram_mode = is_ram_mode(capture_dir)
    
    # METADATA ARCHIVAL: Handled by capture_monitor.py (incremental append)
    # Chunks are created/updated in real-time as frames arrive - no batch merging needed!
    
    # SEGMENTS PROGRESSIVE BUILDING: TS → 1min MP4 → append to growing 10min chunk
    hot_segments = os.path.join(capture_dir, 'hot', 'segments') if ram_mode else os.path.join(capture_dir, 'segments')
    temp_dir = os.path.join(capture_dir, 'segments', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Step 1: Merge 60 TS → 1min MP4 (with rotating slot naming for individual playback)
    # Calculate minute slot (0-9) for rotating filenames - same as MP3
    current_minute = datetime.now().minute
    minute_slot = current_minute % 10  # 0-9 rotating slot
    
    # Use rotating slot naming instead of timestamp - keeps last 10 files playable
    mp4_1min_path = os.path.join(temp_dir, f'1min_{minute_slot}.mp4')
    
    # Delete old file in this slot BEFORE creating new one (prevents race condition)
    if os.path.exists(mp4_1min_path):
        try:
            os.remove(mp4_1min_path)
            logger.debug(f"Deleted old 1min_{minute_slot}.mp4 (rotating slot)")
        except Exception as e:
            logger.warning(f"Failed to delete old 1min MP4 slot: {e}")
    
    mp4_start = time.time()
    mp4_1min = merge_progressive_batch(hot_segments, 'segment_*.ts', mp4_1min_path, 60, True, 20)
    if mp4_1min:
        mp4_elapsed = time.time() - mp4_start
        logger.info(f"\033[34m🎬 Created 1min MP4 (slot {minute_slot}):\033[0m {mp4_1min} \033[90m({mp4_elapsed:.2f}s)\033[0m")
    
    mp4_10min = None
    if mp4_1min:
        # Create 1min MP3 in audio temp dir (hot/cold aware for inotify + instant transcription)
        # Use rotating slot naming (0-9) instead of timestamps to avoid cleanup
        from shared.src.lib.utils.storage_path_utils import calculate_chunk_location, get_audio_path, get_device_info_from_capture_folder
        from pathlib import Path as PathLib
        
        # Get device folder and calculate chunk location from current time
        device_folder = os.path.basename(capture_dir)
        now = datetime.now()
        hour, chunk_index = calculate_chunk_location(now)
        
        # minute_slot already calculated above at line 1004 - reuse it
        
        # Check if device has audio (skip host/VNC devices without audio)
        device_info = get_device_info_from_capture_folder(device_folder)
        device_id = device_info.get('device_id', device_folder)
        is_host = (device_id == 'host')
        
        mp3_1min = None
        if is_host:
            logger.debug(f"[{device_folder}] Skipped MP3 (host device)")
        else:
            # Use COLD storage for temp (same as segments/temp)
            from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
            audio_cold = get_cold_storage_path(device_folder, 'audio')
            audio_temp_dir = os.path.join(audio_cold, 'temp')
            os.makedirs(audio_temp_dir, exist_ok=True)
            
            # Use rotating slot naming: 1min_0.mp3 through 1min_9.mp3
            # Delete old file in this slot BEFORE creating new one (prevents race condition)
            mp3_1min = os.path.join(audio_temp_dir, f'1min_{minute_slot}.mp3')
            
            # Delete old file in this slot first (if exists)
            if os.path.exists(mp3_1min):
                try:
                    os.remove(mp3_1min)
                    logger.debug(f"[{device_folder}] Deleted old 1min_{minute_slot}.mp3 (rotating slot)")
                except Exception as e:
                    logger.warning(f"[{device_folder}] Failed to delete old MP3 slot: {e}")
            
            try:
                import subprocess
                mp3_start = time.time()
                subprocess.run(
                    ['ffmpeg', '-i', mp4_1min, '-vn', '-acodec', 'libmp3lame', '-q:a', '4', '-f', 'mp3', f'{mp3_1min}.tmp', '-y'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15
                )
                os.rename(f'{mp3_1min}.tmp', mp3_1min)
                mp3_elapsed = time.time() - mp3_start
                logger.info(f"\033[32m🎵 Created 1min MP3 (slot {minute_slot}):\033[0m {mp3_1min} \033[90m({mp3_elapsed:.2f}s)\033[0m")
            except subprocess.CalledProcessError as e:
                # MP4 has no audio track (VNC/silent source) - this is expected
                logger.info(f"⊗ Skipped MP3 (no audio in source): {mp4_1min}")
                mp3_1min = None
            except Exception as e:
                logger.warning(f"MP3 extraction error: {e}")
                mp3_1min = None
        
        # Progressive append MP4
        hour_dir = os.path.join(capture_dir, 'segments', str(hour))
        os.makedirs(hour_dir, exist_ok=True)
        mp4_path = os.path.join(hour_dir, f'chunk_10min_{chunk_index}.mp4')
        
        mp4_append_start = time.time()
        if os.path.exists(mp4_path):
            # Check if existing chunk is from current 10-minute window (24h rolling buffer fix)
            # If file is from yesterday's same time slot, OVERWRITE it instead of APPEND
            file_mtime = os.path.getmtime(mp4_path)
            file_dt = datetime.fromtimestamp(file_mtime)
            file_hour, file_chunk = calculate_chunk_location(file_dt)
            
            # Check if file is from current window (within last 10 minutes)
            is_current_window = (file_hour == hour and file_chunk == chunk_index and 
                                now.timestamp() - file_mtime < 600)  # 10 minutes
            
            if not is_current_window:
                # File is old (from yesterday or earlier) - OVERWRITE instead of append
                logger.info(f"🔄 Old chunk detected (age: {(now.timestamp() - file_mtime)/3600:.1f}h), overwriting: {mp4_path}")
                shutil.copy(mp4_1min, mp4_path)
                mp4_append_elapsed = time.time() - mp4_append_start
                created_size = os.path.getsize(mp4_path)
                logger.info(f"\033[34m✓ Overwritten 10min MP4:\033[0m {mp4_path} \033[90m({mp4_append_elapsed:.2f}s, {created_size/1024/1024:.2f}MB)\033[0m")
                mp4_10min = mp4_path
            else:
                # File is current - APPEND as normal
                from shared.src.lib.utils.video_utils import merge_video_files
                # Use temporary file to prevent corruption from in-place overwrite
                temp_output = mp4_path + '.tmp'
                
                # Log input file details for diagnostics
                input1_size = os.path.getsize(mp4_path)
                input2_size = os.path.getsize(mp4_1min)
                logger.debug(f"MP4 merge inputs: {mp4_path} ({input1_size/1024/1024:.2f}MB) + {mp4_1min} ({input2_size/1024/1024:.2f}MB)")
                
                # Enable faststart flag for progressive chunks (prevents corruption from broken moov atoms)
                result = merge_video_files([mp4_path, mp4_1min], temp_output, 'mp4', False, 60, None, False)
                mp4_append_elapsed = time.time() - mp4_append_start
                
                # Enhanced diagnostics
                if not result:
                    logger.error(f"merge_video_files returned False (FFmpeg process failed or timed out after 60s)")
                if result and not os.path.exists(temp_output):
                    logger.error(f"merge_video_files returned True but temp file was not created: {temp_output}")
                
                if result and os.path.exists(temp_output):
                    # Verify output file size before replacing
                    temp_size = os.path.getsize(temp_output)
                    original_size = input1_size  # Reuse from above
                    new_chunk_size = input2_size  # Reuse from above
                    
                    # Expected size should be roughly original + new chunk (allow 5% variance for MP4 overhead)
                    expected_min_size = original_size + (new_chunk_size * 0.95)
                    
                    if temp_size < expected_min_size:
                        logger.error(f"\033[31m✗ MP4 concat produced suspiciously small file:\033[0m {temp_size/1024/1024:.2f}MB (expected ≥{expected_min_size/1024/1024:.2f}MB, original={original_size/1024/1024:.2f}MB + new={new_chunk_size/1024/1024:.2f}MB)")
                        os.remove(temp_output)
                        logger.warning(f"Discarded corrupted output, original file preserved")
                    elif temp_size < 100000:  # Less than 100KB is definitely wrong
                        logger.error(f"\033[31m✗ MP4 concat produced tiny file:\033[0m {temp_size} bytes (likely corrupted)")
                        os.remove(temp_output)
                        logger.warning(f"Discarded corrupted output, original file preserved")
                    else:
                        # Atomic replace: only overwrite original if merge succeeded and size is valid
                        os.rename(temp_output, mp4_path)
                        final_size = os.path.getsize(mp4_path)
                        logger.info(f"\033[34m✓ Appended to 10min MP4:\033[0m {mp4_path} \033[90m({mp4_append_elapsed:.2f}s, {original_size/1024/1024:.2f}MB → {final_size/1024/1024:.2f}MB, +{(final_size-original_size)/1024/1024:.2f}MB)\033[0m")
                        mp4_10min = mp4_path  # Mark success
                else:
                    logger.error(f"\033[31m✗ Failed to append (likely corrupted), recreating from scratch\033[0m")
                    # Clean up temp file
                    if os.path.exists(temp_output):
                        try:
                            os.remove(temp_output)
                        except:
                            pass
                    # Delete corrupted original and immediately start fresh with current 1min MP4
                    try:
                        os.remove(mp4_path)
                        shutil.copy(mp4_1min, mp4_path)
                        created_size = os.path.getsize(mp4_path)
                        logger.info(f"\033[34m✓ Recreated 10min MP4 from scratch:\033[0m {mp4_path} \033[90m({created_size/1024/1024:.2f}MB)\033[0m")
                        mp4_10min = mp4_path  # Mark success
                    except Exception as e:
                        logger.error(f"Recovery failed: {e}")
        else:
            shutil.copy(mp4_1min, mp4_path)
            mp4_append_elapsed = time.time() - mp4_append_start
            created_size = os.path.getsize(mp4_path)
            logger.info(f"\033[34m✓ Created 10min MP4:\033[0m {mp4_path} \033[90m({mp4_append_elapsed:.2f}s, {created_size/1024/1024:.2f}MB)\033[0m")
            mp4_10min = mp4_path  # Mark success
        
        # Progressive append MP3 to 10min chunk (after transcription happens via inotify)
        mp3_10min_path = None
        if mp3_1min and os.path.exists(mp3_1min):
            # Use same audio_cold from above
            audio_hour_dir = os.path.join(audio_cold, str(hour))
            os.makedirs(audio_hour_dir, exist_ok=True)
            mp3_10min_path = os.path.join(audio_hour_dir, f'chunk_10min_{chunk_index}.mp3')
            
            mp3_append_start = time.time()
            if os.path.exists(mp3_10min_path):
                # Check if existing MP3 chunk is from current 10-minute window (24h rolling buffer fix)
                # If file is from yesterday's same time slot, OVERWRITE it instead of APPEND
                file_mtime = os.path.getmtime(mp3_10min_path)
                file_dt = datetime.fromtimestamp(file_mtime)
                file_hour, file_chunk = calculate_chunk_location(file_dt)
                
                # Check if file is from current window (within last 10 minutes)
                is_current_window = (file_hour == hour and file_chunk == chunk_index and 
                                    now.timestamp() - file_mtime < 600)  # 10 minutes
                
                if not is_current_window:
                    # File is old (from yesterday or earlier) - OVERWRITE instead of append
                    logger.info(f"🔄 Old MP3 chunk detected (age: {(now.timestamp() - file_mtime)/3600:.1f}h), overwriting: {mp3_10min_path}")
                    shutil.copy(mp3_1min, mp3_10min_path)
                    mp3_append_elapsed = time.time() - mp3_append_start
                    created_size = os.path.getsize(mp3_10min_path)
                    logger.info(f"\033[32m✓ Overwritten 10min MP3:\033[0m {mp3_10min_path} \033[90m({mp3_append_elapsed:.3f}s, {created_size/1024:.1f}KB)\033[0m")
                else:
                    # File is current - APPEND as normal
                    try:
                        # Use temp file for atomic append (prevents corruption if process killed mid-write)
                        temp_output = mp3_10min_path + '.tmp'
                        original_size = os.path.getsize(mp3_10min_path)
                        new_chunk_size = os.path.getsize(mp3_1min)
                        
                        shutil.copy(mp3_10min_path, temp_output)  # Copy existing file
                        with open(temp_output, 'ab') as dest:
                            with open(mp3_1min, 'rb') as src:
                                dest.write(src.read())
                        
                        # Verify output file size before replacing
                        temp_size = os.path.getsize(temp_output)
                        expected_size = original_size + new_chunk_size
                        
                        if temp_size < expected_size:
                            logger.error(f"\033[31m✗ MP3 append produced wrong size:\033[0m {temp_size/1024:.1f}KB (expected {expected_size/1024:.1f}KB)")
                            os.remove(temp_output)
                            logger.warning(f"Discarded corrupted output, original file preserved")
                        elif temp_size < 10000:  # Less than 10KB is definitely wrong
                            logger.error(f"\033[31m✗ MP3 append produced tiny file:\033[0m {temp_size} bytes (likely corrupted)")
                            os.remove(temp_output)
                            logger.warning(f"Discarded corrupted output, original file preserved")
                        else:
                            os.rename(temp_output, mp3_10min_path)  # Atomic replace
                            final_size = os.path.getsize(mp3_10min_path)
                            mp3_append_elapsed = time.time() - mp3_append_start
                            logger.info(f"\033[32m✓ Appended to 10min MP3:\033[0m {mp3_10min_path} \033[90m({mp3_append_elapsed:.3f}s, {original_size/1024:.1f}KB → {final_size/1024:.1f}KB, +{new_chunk_size/1024:.1f}KB)\033[0m")
                    except Exception as e:
                        logger.warning(f"Failed to append MP3: {e}")
                        # Clean up temp file on failure (original file remains intact)
                        temp_output = mp3_10min_path + '.tmp'
                        if os.path.exists(temp_output):
                            try:
                                os.remove(temp_output)
                                logger.debug(f"Cleaned up failed MP3 temp file: {temp_output}")
                            except Exception as cleanup_error:
                                logger.warning(f"Failed to clean up MP3 temp file: {cleanup_error}")
            else:
                shutil.copy(mp3_1min, mp3_10min_path)
                mp3_append_elapsed = time.time() - mp3_append_start
                created_size = os.path.getsize(mp3_10min_path)
                logger.info(f"\033[32m✓ Created 10min MP3:\033[0m {mp3_10min_path} \033[90m({mp3_append_elapsed:.3f}s, {created_size/1024:.1f}KB)\033[0m")
            
            # No deletion needed - rotating slot system automatically manages old files
            # File will be overwritten in ~10 minutes when slot rotates
            logger.debug(f"1min MP3 appended to 10min chunk (slot {minute_slot} will auto-rotate)")
        
        # No deletion of 1min MP4 - rotating slot system keeps last 10 files playable
        # File will be overwritten in ~10 minutes when slot rotates
        logger.debug(f"1min MP4 kept in temp/ for individual playback (slot {minute_slot} will auto-rotate)")
        
        # Update manifest only if MP4 operation succeeded
        if mp4_10min:
            update_archive_manifest(capture_dir, hour, chunk_index, mp4_path)
    
    # SAFETY CLEANUP: Delete orphaned 1min files from temp/
    # MP4: Rotating slots (no cleanup - kept for playback)
    # JSON: 2h timeout (failed merges)
    # MP3: Rotating slots (15min safety net)
    deleted_temp_segments, deleted_temp_metadata, deleted_temp_mp3 = cleanup_temp_files(capture_dir)
    
    elapsed = time.time() - start_time
    
    # Build status summary
    if mp4_10min:
        mp4_info = ", MP4: ✓"
    elif mp4_1min:  # 1min was created but 10min append failed
        mp4_info = ", MP4: ✗ failed"
    else:
        mp4_info = ""
    
    # Safety cleanup stats (HOT only)
    safety_deletes = []
    if deleted_segments > 0:
        safety_deletes.append(f"{deleted_segments} seg")
    if deleted_captures > 0:
        safety_deletes.append(f"{deleted_captures} cap")
    if deleted_thumbnails > 0:
        safety_deletes.append(f"{deleted_thumbnails} thumb")
    if deleted_metadata > 0:
        safety_deletes.append(f"{deleted_metadata} meta")
    if deleted_temp_segments > 0:
        safety_deletes.append(f"{deleted_temp_segments} temp_seg")
    if deleted_temp_metadata > 0:
        safety_deletes.append(f"{deleted_temp_metadata} temp_meta")
    if deleted_temp_mp3 > 0:
        safety_deletes.append(f"{deleted_temp_mp3} temp_mp3")
    
    cleanup_info = f"del: {', '.join(safety_deletes)}" if safety_deletes else "del: 0"
    
    logger.info(f"  ✓ HOT done in {elapsed:.2f}s ({cleanup_info}{mp4_info})")


def process_cold_storage(capture_dir: str):
    """
    COLD STORAGE PROCESSING (Slow, Batched, Every 60s)
    
    Cleanup old files from COLD storage with batch limits to prevent long-running cycles.
    - Captures: Delete files older than 1h (max 200 files per cycle)
    - Thumbnails: Delete files older than 1h (max 200 files per cycle)
    
    This runs in a separate thread to avoid blocking hot storage cleanup.
    """
    logger.info(f"❄️  COLD: {os.path.basename(capture_dir)}")
    
    start_time = time.time()
    
    # Batch-limited cold cleanup (prevents hour-long cycles)
    deleted_cold_captures = cleanup_cold_captures(capture_dir, COLD_BATCH_LIMIT)
    deleted_cold_thumbnails = cleanup_cold_thumbnails(capture_dir, COLD_BATCH_LIMIT)
    
    elapsed = time.time() - start_time
    
    # Build status summary
    cold_deletes = []
    if deleted_cold_captures > 0:
        cold_deletes.append(f"{deleted_cold_captures} cap")
    if deleted_cold_thumbnails > 0:
        cold_deletes.append(f"{deleted_cold_thumbnails} thumb")
    
    cleanup_info = f"del: {', '.join(cold_deletes)}" if cold_deletes else "del: 0"
    
    logger.info(f"  ✓ COLD done in {elapsed:.2f}s ({cleanup_info})")


def hot_storage_loop():
    """
    HOT STORAGE THREAD (Every 15s)
    
    Fast, critical RAM management:
    - SAFETY CLEANUP: Enforce limits on hot storage types (prevent RAM exhaustion)
    - Segments: HOT TS → 1min MP4 → progressively append to 10min chunk in COLD
    - Audio: Extract from 10min chunks → directly to COLD /audio/{hour}/
    
    Progressive append: Each minute appends to growing chunk (no batch-merge-at-end)
    Result: Timeline has no changes, same URL grows from 1min to 10min duration
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔥 HOT STORAGE THREAD STARTED")
    logger.info("=" * 80)
    logger.info(f"Interval: {HOT_THREAD_INTERVAL}s")
    logger.info(f"Hot limits: {HOT_LIMITS}")
    logger.info("Strategy: Safety cleanup + Progressive append (TS→1min→append to 10min chunk)")
    logger.info("=" * 80)
    
    # STARTUP ONLY: Rebuild all manifests from disk to discover existing chunks
    logger.info("")
    logger.info("=" * 60)
    logger.info("STARTUP: Rebuilding archive and transcript manifests from disk...")
    logger.info("=" * 60)
    
    # Get capture directories for startup
    capture_dirs = get_capture_base_directories()
    
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
            logger.info("=" * 80)
            logger.info(f"🔥 HOT CYCLE at {datetime.now().strftime('%H:%M:%S')}")
            logger.info("=" * 80)
            
            # Get active capture directories
            capture_dirs = get_capture_base_directories()
            
            # BEFORE CLEANING SUMMARY
            print_ram_summary(capture_dirs, "📊 BEFORE HOT CLEANUP")
            
            # Process each directory (hot storage only)
            for capture_dir in capture_dirs:
                try:
                    process_hot_storage(capture_dir)
                except Exception as e:
                    logger.error(f"Error processing hot storage for {capture_dir}: {e}", exc_info=True)
            
            # AFTER CLEANING SUMMARY
            print_ram_summary(capture_dirs, "✅ AFTER HOT CLEANUP")
            
            cycle_elapsed = time.time() - cycle_start
            logger.info(f"🔥 HOT cycle completed in {cycle_elapsed:.2f}s (next in {HOT_THREAD_INTERVAL}s)")
            
            # Sleep until next cycle
            time.sleep(HOT_THREAD_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🔥 HOT thread: Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in hot storage loop: {e}", exc_info=True)
            time.sleep(HOT_THREAD_INTERVAL)


def cold_storage_loop():
    """
    COLD STORAGE THREAD (Every 60s)
    
    Batch cleanup of cold storage (non-blocking):
    - Captures: Delete files older than 1h (max 200 files per device per cycle)
    - Thumbnails: Delete files older than 1h (max 200 files per device per cycle)
    
    Batch limits prevent hour-long cycles that block hot storage cleanup.
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("❄️  COLD STORAGE THREAD STARTED")
    logger.info("=" * 80)
    logger.info(f"Interval: {COLD_THREAD_INTERVAL}s")
    logger.info(f"Batch limit: {COLD_BATCH_LIMIT} files per device per cycle")
    logger.info("=" * 80)
    
    while True:
        try:
            cycle_start = time.time()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"❄️  COLD CYCLE at {datetime.now().strftime('%H:%M:%S')}")
            logger.info("=" * 80)
            
            # Get active capture directories
            capture_dirs = get_capture_base_directories()
            
            # Process each directory (cold storage only)
            for capture_dir in capture_dirs:
                try:
                    process_cold_storage(capture_dir)
                except Exception as e:
                    logger.error(f"Error processing cold storage for {capture_dir}: {e}", exc_info=True)
            
            cycle_elapsed = time.time() - cycle_start
            logger.info(f"❄️  COLD cycle completed in {cycle_elapsed:.2f}s (next in {COLD_THREAD_INTERVAL}s)")
            
            # Sleep until next cycle
            time.sleep(COLD_THREAD_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("❄️  COLD thread: Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in cold storage loop: {e}", exc_info=True)
            time.sleep(COLD_THREAD_INTERVAL)


if __name__ == '__main__':
    try:
        # Kill any existing archiver instances before starting
        from shared.src.lib.utils.system_utils import kill_existing_script_instances
        killed = kill_existing_script_instances('hot_cold_archiver.py')
        if killed:
            logger.info(f"Killed existing archiver instances: {killed}")
            time.sleep(1)
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("HOT/COLD ARCHIVER - DUAL-THREAD ARCHITECTURE")
        logger.info("=" * 80)
        logger.info("🔥 HOT THREAD: Critical RAM management (every 15s)")
        logger.info("❄️  COLD THREAD: Batch cleanup (every 60s, max 200 files/device)")
        logger.info("=" * 80)
        
        # Create and start both threads
        hot_thread = threading.Thread(target=hot_storage_loop, name="HotStorageThread", daemon=True)
        cold_thread = threading.Thread(target=cold_storage_loop, name="ColdStorageThread", daemon=True)
        
        hot_thread.start()
        cold_thread.start()
        
        logger.info("✓ Both threads started successfully")
        
        # Keep main thread alive
        try:
            while True:
                hot_thread.join(timeout=1.0)
                cold_thread.join(timeout=1.0)
                if not hot_thread.is_alive():
                    logger.error("🔥 HOT thread died, restarting...")
                    hot_thread = threading.Thread(target=hot_storage_loop, name="HotStorageThread", daemon=True)
                    hot_thread.start()
                if not cold_thread.is_alive():
                    logger.error("❄️  COLD thread died, restarting...")
                    cold_thread = threading.Thread(target=cold_storage_loop, name="ColdStorageThread", daemon=True)
                    cold_thread.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down both threads...")
            sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

