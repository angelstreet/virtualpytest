#!/usr/bin/env python3
"""
HOT/COLD STORAGE ARCHIVER - Unified Architecture
=================================================

This service manages the hot/cold storage pattern for all file types:
- Segments: 10 hot files + 24 hour folders
- Captures: 100 hot files + 24 hour folders
- Thumbnails: 100 hot files + 24 hour folders
- Metadata: 100 hot files + 24 hour folders

Responsibilities:
1. Archive hot files when they exceed limits
2. Generate HLS manifests for hour folders (segments only)
3. Clean 24h old hour folders
4. No full directory scans - fast and efficient!

Runs every 5 minutes to maintain storage health.
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
RUN_INTERVAL = 300  # 5 minutes

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
    
    Returns: Number of files archived
    """
    hot_dir = os.path.join(capture_dir, file_type)
    
    if not os.path.isdir(hot_dir):
        return 0
    
    pattern = FILE_PATTERNS[file_type]
    hot_limit = HOT_LIMITS[file_type]
    
    # Get files in hot storage (root only, not subdirs)
    try:
        files = []
        for item in Path(hot_dir).glob(pattern):
            if item.is_file() and item.parent == Path(hot_dir):
                files.append(item)
        
        file_count = len(files)
        
        if file_count <= hot_limit:
            logger.debug(f"{file_type}: {file_count} files (within limit {hot_limit})")
            return 0
        
        # Calculate how many to archive
        to_archive = file_count - hot_limit
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda f: f.stat().st_mtime)
        files_to_archive = files[:to_archive]
        
        logger.info(f"{file_type}: Archiving {to_archive} old files ({file_count} → {hot_limit})")
        
        archived_count = 0
        for filepath in files_to_archive:
            try:
                # Get hour from file mtime
                file_hour = get_file_hour(str(filepath))
                hour_folder = os.path.join(hot_dir, str(file_hour))
                
                # Ensure hour folder exists
                os.makedirs(hour_folder, exist_ok=True)
                
                # Move file to hour folder
                dest_path = os.path.join(hour_folder, filepath.name)
                shutil.move(str(filepath), dest_path)
                
                archived_count += 1
                logger.debug(f"Archived {filepath.name} → {file_type}/{file_hour}/")
                
            except Exception as e:
                logger.error(f"Error archiving {filepath}: {e}")
        
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
    Main service loop - runs every 5 minutes
    """
    logger.info("=" * 60)
    logger.info("HOT/COLD ARCHIVER STARTED - Unified Architecture")
    logger.info("=" * 60)
    logger.info(f"Run interval: {RUN_INTERVAL}s ({RUN_INTERVAL // 60} minutes)")
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
            logger.info(f"Next run in {RUN_INTERVAL}s")
            logger.info("=" * 60)
            
            # Sleep until next cycle
            time.sleep(RUN_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(RUN_INTERVAL)


if __name__ == '__main__':
    try:
        main_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

