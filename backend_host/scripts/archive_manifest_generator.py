#!/usr/bin/env python3
"""
Dedicated Archive Manifest Generator
Separated from capture_monitor.py to prevent blocking incident detection
"""
import os
import time
import logging
from datetime import datetime
from archive_utils import get_capture_directories, get_capture_folder, update_archive_manifest

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
    logger.info(f"Monitoring {len(capture_dirs)} capture directories")
    
    while True:
        for capture_dir in capture_dirs:
            update_archive_manifest(capture_dir)
        time.sleep(60)

if __name__ == '__main__':
    main()

