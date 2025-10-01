#!/usr/bin/env python3
"""
Dedicated Archive Manifest Generator
Separated from capture_monitor.py to prevent blocking incident detection
"""
import time
import logging
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

def main():
    logger.info("Starting Archive Manifest Generator...")
    capture_dirs = get_capture_directories()
    logger.info(f"Monitoring {len(capture_dirs)} capture directories")
    
    while True:
        for capture_dir in capture_dirs:
            update_archive_manifest(capture_dir)
        time.sleep(60)

if __name__ == '__main__':
    main()

