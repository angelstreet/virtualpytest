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

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_base_directories, is_ram_mode

# Configure logging (systemd handles file output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [HOT_COLD_ARCHIVER] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
ACTIVE_CAPTURES_FILE = '/tmp/active_captures.conf'
RAM_RUN_INTERVAL = 120  # 2min for RAM mode (segments-only archival)
SD_RUN_INTERVAL = 120   # 2min (same for consistency)

# Hot storage limits - SEGMENTS-ONLY ARCHIVE
# Images (captures/thumbnails) pushed to cloud, don't need local archive
# Only segments need 24h history for video playback
#
# RAM Usage (200MB per device):
# - Segments: 150 × 45KB = 6.8MB (2.5min buffer, archive every 2min)
# - Captures: 1500 × 16KB = 24MB (5min rolling buffer, no archive)
# - Thumbnails: 3000 × 6KB = 18MB (10min rolling buffer, no archive)
# Total: ~49MB per device ✅ (75% free, safe for HD segments)
#
HOT_LIMITS = {
    'segments': 150,      # 2.5min buffer → archive to hour folders
    'captures': 1500,     # 5min rolling buffer (no archive, just rotate)
    'thumbnails': 3000,   # 10min rolling buffer (no archive, just rotate)
    'metadata': 100       # Minimal (not used)
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

# File patterns for each type
FILE_PATTERNS = {
    'segments': 'segment_*.ts',
    'captures': 'capture_*[0-9].jpg',  # Exclude thumbnails
    'thumbnails': 'capture_*_thumbnail.jpg',
    'metadata': 'capture_*.json'
}


# Use centralized function from archive_utils.py
# No local implementation needed - single source of truth!


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
    
    Args:
        filepath: Original file path
        file_type: 'segments', 'captures', 'thumbnails', 'metadata'
        fps: Frames per second (for images only)
    
    Returns:
        New filename with time-based sequential number
    """
    try:
        mtime = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(mtime)
        
        # Calculate seconds since midnight
        seconds_today = (dt.hour * 3600) + (dt.minute * 60) + dt.second
        
        if file_type == 'segments':
            # 1 segment per second: 0-86399
            sequence_num = seconds_today
            new_name = f"segment_{sequence_num:06d}.ts"
        elif file_type in ['captures', 'thumbnails', 'metadata']:
            # Images at FPS rate
            sequence_num = seconds_today * fps
            
            # Get original filename to extract extension and type
            original_name = os.path.basename(filepath)
            
            if file_type == 'thumbnails':
                new_name = f"capture_{sequence_num:06d}_thumbnail.jpg"
            elif file_type == 'metadata':
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
                
                # Calculate time-based sequential name for 24h rolling buffer
                # FPS detection: segments=1fps, captures/thumbnails=5fps default
                fps = 5 if file_type in ['captures', 'thumbnails', 'metadata'] else 1
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


# REMOVED: clean_old_hour_folders() function
#
# WHY: Natural 24h rolling buffer through time-based sequential filenames
# Files automatically overwrite after 24h cycle - no cleanup needed!
# 
# How it works:
# - Files get time-based names based on seconds since midnight
# - After 24h, same time → same filename → automatic overwrite
# - Result: All hour folders maintain 24h of data automatically
#
# No retention configuration or cleanup logic needed!


def process_capture_directory(capture_dir: str):
    """
    Process a single capture directory:
    1. Archive ONLY segments (captures/thumbnails stay in RAM, rotate naturally)
    2. Update segment manifests
    
    NOTE: Images pushed to cloud, no local archive needed. Only segments for video playback.
    """
    logger.info(f"Processing {capture_dir}")
    
    start_time = time.time()
    
    # 1. Archive ONLY segments (images stay in RAM)
    archived = archive_hot_files(capture_dir, 'segments')
    
    # 2. Update archive manifests (segments only)
    update_all_manifests(capture_dir)
    
    elapsed = time.time() - start_time
    
    logger.info(f"✓ Completed {capture_dir} in {elapsed:.2f}s (archived {archived} segments)")


def main_loop():
    """
    Main service loop - SEGMENTS-ONLY archival
    Archives only segments every 2min (captures/thumbnails rotate in RAM)
    """
    logger.info("=" * 60)
    logger.info("HOT/COLD ARCHIVER - SEGMENTS-ONLY ARCHIVE")
    logger.info("=" * 60)
    
    # Detect mode from first capture directory
    capture_dirs = get_capture_base_directories()
    ram_mode = any(is_ram_mode(d) for d in capture_dirs if os.path.exists(d))
    run_interval = RAM_RUN_INTERVAL if ram_mode else SD_RUN_INTERVAL
    
    mode_name = "RAM MODE (2min interval)" if ram_mode else "SD MODE (2min interval)"
    logger.info(f"Mode: {mode_name}")
    logger.info(f"Run interval: {run_interval}s")
    logger.info(f"Hot limits: {HOT_LIMITS}")
    logger.info("Strategy: Archive segments only (images pushed to cloud)")
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

