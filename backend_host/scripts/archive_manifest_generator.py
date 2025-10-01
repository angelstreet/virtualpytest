#!/usr/bin/env python3
"""
Dedicated Archive Manifest Generator
Separated from capture_monitor.py to prevent blocking incident detection
"""
import os
import time
import logging
from datetime import datetime
from archive_utils import get_capture_directories, get_capture_folder, update_archive_manifest, get_device_info_from_capture_folder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/archive_manifest_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_logs_on_startup():
    """Clean up log file on service restart for fresh debugging"""
    try:
        log_file = '/tmp/archive_manifest_generator.log'
        
        print(f"[@archive_manifest_generator] Cleaning log on service restart...")
        
        if os.path.exists(log_file):
            # Truncate the file instead of deleting to avoid permission issues
            with open(log_file, 'w') as f:
                f.write(f"=== LOG CLEANED ON SERVICE RESTART: {datetime.now().isoformat()} ===\n")
            print(f"[@archive_manifest_generator] ✓ Cleaned: {log_file}")
        else:
            print(f"[@archive_manifest_generator] ○ Not found (will be created): {log_file}")
                
        print(f"[@archive_manifest_generator] Log cleanup complete - fresh logs for debugging")
                
    except Exception as e:
        print(f"[@archive_manifest_generator] Warning: Could not clean log file: {e}")

def main():
    cleanup_logs_on_startup()  # Clean log on startup
    
    logger.info("Starting Archive Manifest Generator...")
    capture_dirs = get_capture_directories()
    logger.info(f"Found {len(capture_dirs)} capture directories")
    
    # Filter out host device (host has no video segments to archive)
    monitored_devices = []
    for capture_dir in capture_dirs:
        capture_folder = get_capture_folder(capture_dir)
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_id = device_info.get('device_id', capture_folder)
        is_host = (device_id == 'host')
        
        if is_host:
            logger.info(f"  ⊗ Skipping: {capture_dir} -> {capture_folder} (host has no video segments)")
        else:
            logger.info(f"  → Monitoring: {capture_dir} -> {capture_folder}")
            monitored_devices.append(capture_dir)
    
    logger.info(f"Monitoring {len(monitored_devices)} devices for archive manifests (excluding host)")
    
    while True:
        for capture_dir in monitored_devices:
            update_archive_manifest(capture_dir)
        time.sleep(60)

if __name__ == '__main__':
    main()

