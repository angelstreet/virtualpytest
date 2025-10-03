#!/usr/bin/env python3
"""
HOT/COLD STORAGE ARCHIVER - RAM + SD Architecture
==================================================

This service manages hot/cold storage with two modes:

**RAM MODE (if /hot/ exists):**
- FFmpeg writes to /hot/captures/, /hot/thumbnails/, /hot/segments/ (tmpfs RAM)
- Archives to SD: /captures/X/, /thumbnails/X/, /segments/X/
- Runs every 5 seconds (RAM is limited!)
- 99% SD write reduction

**SD MODE (fallback if no /hot/):**
- Files in root directories (captures/, thumbnails/, segments/)
- Archives to hour subfolders
- Runs every 5 minutes (traditional behavior)

Responsibilities:
1. Archive hot files when they exceed limits
2. Generate HLS manifests for hour folders (segments only)
3. Clean old hour folders (1h for captures, 24h for others)
4. No full directory scans - fast and efficient!
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [HOT_COLD_ARCHIVER] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/hot_cold_archiver.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
ACTIVE_CAPTURES_FILE = '/tmp/active_captures.conf'
RAM_RUN_INTERVAL = 5    # 5 seconds for RAM mode (critical!)
SD_RUN_INTERVAL = 300   # 5 minutes for SD mode

# Hot storage limits (files to keep in root before archiving)
HOT_LIMITS = {
    'segments': 10,
    'captures': 100,
    'thumbnails': 100,
    'metadata': 100
}

# Retention policy (hours to keep in archive folders)
# Different retention based on file purpose
RETENTION_HOURS = {
    'segments': 24,      # Full 24h for video playback
    'captures': 1,       # Only 1h for full-res (incident verification)
    'thumbnails': 24,    # Full 24h for heatmap/gallery
    'metadata': 24       # Full 24h for incident analysis
}

# File patterns for each type
FILE_PATTERNS = {
    'segments': 'segment_*.ts',
    'captures': 'capture_*[0-9].jpg',  # Exclude thumbnails
    'thumbnails': 'capture_*_thumbnail.jpg',
    'metadata': 'capture_*.json'
}


def get_capture_directories() -> List[str]:
    """Get list of active capture directories from config file"""
    capture_dirs = []
    
    if os.path.exists(ACTIVE_CAPTURES_FILE):
        try:
            with open(ACTIVE_CAPTURES_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and os.path.isdir(line):
                        capture_dirs.append(line)
            logger.info(f"Loaded {len(capture_dirs)} capture directories from config")
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
    
    # Fallback: Auto-discover
    if not capture_dirs:
        logger.warning("Config not found, auto-discovering capture directories")
        base_path = Path('/var/www/html/stream')
        if base_path.exists():
            for capture_dir in base_path.glob('capture[0-9]*'):
                if capture_dir.is_dir():
                    capture_dirs.append(str(capture_dir))
        
        # Last resort fallback
        if not capture_dirs:
            capture_dirs = [
                '/var/www/html/stream/capture1',
                '/var/www/html/stream/capture2',
                '/var/www/html/stream/capture3',
                '/var/www/html/stream/capture4'
            ]
    
    return capture_dirs


def is_ram_mode(capture_dir: str) -> bool:
    """Check if capture directory uses RAM hot storage"""
    hot_path = os.path.join(capture_dir, 'hot')
    if not os.path.exists(hot_path):
        return False
    
    # Check if it's a tmpfs mount (RAM)
    try:
        with open('/proc/mounts', 'r') as f:
            mounts = f.read()
            if hot_path in mounts and 'tmpfs' in mounts:
                return True
    except Exception:
        pass
    
    # If /hot/ exists but isn't tmpfs, still treat as RAM mode
    # (for development/testing)
    return True


def get_file_hour(filepath: str) -> int:
    """Get hour (0-23) from file modification time"""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).hour
    except Exception as e:
        logger.error(f"Error getting file hour for {filepath}: {e}")
        return datetime.now().hour


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
        
        if file_count <= hot_limit:
            logger.debug(f"{file_type}: {file_count} files (within limit {hot_limit})")
            return 0
        
        # Calculate how many to archive
        to_archive = file_count - hot_limit
        
        # Sort by modification time (oldest first) - CRITICAL for keeping newest files
        files.sort(key=lambda f: f.stat().st_mtime)
        
        # Safety check: Never archive files less than 60 seconds old
        # This protects restart video operations from race conditions
        MIN_AGE_SECONDS = 60
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
                
                # Move file to hour folder (RAM → SD or SD root → SD hour)
                dest_path = os.path.join(hour_folder, filepath.name)
                shutil.move(str(filepath), dest_path)
                
                archived_count += 1
                mode_label = "RAM→SD" if ram_mode else "hot→cold"
                logger.debug(f"Archived {filepath.name} → {file_type}/{file_hour}/ ({mode_label})")
                
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


def generate_hour_manifest(capture_dir: str, hour: int) -> bool:
    """
    Generate HLS manifest for a specific hour folder
    
    Only for segments/ - creates archive.m3u8
    """
    hour_dir = os.path.join(capture_dir, 'segments', str(hour))
    
    if not os.path.isdir(hour_dir):
        return False
    
    try:
        # Get all segments in this hour folder
        segments = sorted(
            Path(hour_dir).glob('segment_*.ts'),
            key=lambda f: int(f.stem.split('_')[1])
        )
        
        if not segments:
            return False
        
        manifest_path = os.path.join(hour_dir, 'archive.m3u8')
        
        # Generate HLS manifest
        with open(manifest_path, 'w') as f:
            f.write('#EXTM3U\n')
            f.write('#EXT-X-VERSION:3\n')
            f.write('#EXT-X-TARGETDURATION:4\n')
            f.write(f'#EXT-X-MEDIA-SEQUENCE:{int(segments[0].stem.split("_")[1])}\n')
            
            for seg in segments:
                f.write('#EXTINF:1.000000,\n')
                f.write(f'{seg.name}\n')
            
            f.write('#EXT-X-ENDLIST\n')
        
        logger.info(f"Generated manifest: segments/{hour}/archive.m3u8 ({len(segments)} segments)")
        return True
        
    except Exception as e:
        logger.error(f"Error generating manifest for hour {hour}: {e}")
        return False


def update_all_manifests(capture_dir: str):
    """
    Update manifests for all hour folders that have segments
    
    Fast operation: only checks hour folders, not full directory scan
    """
    segments_dir = os.path.join(capture_dir, 'segments')
    
    if not os.path.isdir(segments_dir):
        return
    
    updated_count = 0
    
    # Check all 24 hour folders
    for hour in range(24):
        hour_dir = os.path.join(segments_dir, str(hour))
        if os.path.isdir(hour_dir):
            # Only update if there are segments
            has_segments = any(Path(hour_dir).glob('segment_*.ts'))
            if has_segments:
                if generate_hour_manifest(capture_dir, hour):
                    updated_count += 1
    
    if updated_count > 0:
        logger.info(f"Updated {updated_count} archive manifests")


def clean_old_hour_folders(capture_dir: str, file_type: str) -> int:
    """
    Clean old hour folders based on retention policy
    
    Different file types have different retention:
    - captures: 1 hour (large files, only for recent incidents)
    - thumbnails/metadata/segments: 24 hours
    
    Returns: Number of folders deleted
    """
    retention_hours = RETENTION_HOURS.get(file_type, 24)
    current_time = datetime.now()
    deleted_count = 0
    
    type_dir = os.path.join(capture_dir, file_type)
    
    if not os.path.isdir(type_dir):
        return 0
    
    try:
        # Check all 24 hour folders
        for hour in range(24):
            folder_path = os.path.join(type_dir, str(hour))
            
            if not os.path.isdir(folder_path):
                continue
            
            # Check if this folder is older than retention period
            # Calculate the most recent time this hour occurred
            if hour == current_time.hour:
                # Current hour - check if folder has old files (from 24h ago)
                hours_ago = 24
            elif hour > current_time.hour:
                # Future hour in clock time = yesterday
                hours_ago = 24 - (hour - current_time.hour)
            else:
                # Past hour today
                hours_ago = current_time.hour - hour
            
            if hours_ago >= retention_hours:
                # This folder is beyond retention period
                file_count = len(list(Path(folder_path).glob('*')))
                
                if file_count > 0:
                    logger.info(f"Deleting {file_type}/{hour}/ ({hours_ago}h old, {file_count} files, retention={retention_hours}h)")
                    shutil.rmtree(folder_path)
                    os.makedirs(folder_path, exist_ok=True)  # Recreate empty
                    deleted_count += 1
        
    except Exception as e:
        logger.error(f"Error cleaning {file_type} folders: {e}")
    
    return deleted_count


def process_capture_directory(capture_dir: str):
    """
    Process a single capture directory:
    1. Archive hot files for all types
    2. Update archive manifests
    3. Clean old folders (different retention per type)
    """
    logger.info(f"Processing {capture_dir}")
    
    start_time = time.time()
    total_archived = 0
    total_deleted = 0
    
    # 1. Archive hot files (unified pattern for all types)
    for file_type in ['segments', 'captures', 'thumbnails', 'metadata']:
        archived = archive_hot_files(capture_dir, file_type)
        total_archived += archived
    
    # 2. Update archive manifests (segments only)
    update_all_manifests(capture_dir)
    
    # 3. Clean old folders (different retention per type)
    # - captures: 1h retention (large files)
    # - others: 24h retention
    for file_type in ['segments', 'captures', 'thumbnails', 'metadata']:
        deleted = clean_old_hour_folders(capture_dir, file_type)
        total_deleted += deleted
    
    elapsed = time.time() - start_time
    
    logger.info(f"✓ Completed {capture_dir} in {elapsed:.2f}s (archived {total_archived} files, deleted {total_deleted} folders)")


def main_loop():
    """
    Main service loop - interval depends on mode
    RAM mode: 5 seconds (critical!)
    SD mode: 5 minutes (traditional)
    """
    logger.info("=" * 60)
    logger.info("HOT/COLD ARCHIVER STARTED - RAM + SD Architecture")
    logger.info("=" * 60)
    
    # Detect mode from first capture directory
    capture_dirs = get_capture_directories()
    ram_mode = any(is_ram_mode(d) for d in capture_dirs if os.path.exists(d))
    run_interval = RAM_RUN_INTERVAL if ram_mode else SD_RUN_INTERVAL
    
    mode_name = "RAM MODE (5s interval)" if ram_mode else "SD MODE (5min interval)"
    logger.info(f"Mode: {mode_name}")
    logger.info(f"Run interval: {run_interval}s")
    logger.info(f"Hot limits: {HOT_LIMITS}")
    logger.info(f"Retention: {RETENTION_HOURS}")
    logger.info("NOTE: Captures = 1h retention (large files), Others = 24h")
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
            capture_dirs = get_capture_directories()
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

