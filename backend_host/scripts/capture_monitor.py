#!/usr/bin/env python3
"""
Standalone Capture Monitor Service
Monitors capture directories for new files and processes them independently
Completely separate from video capture workflow to avoid interference
"""

import os
import sys
import time
import signal
import subprocess
import threading
import glob
import logging
import json
import re
from datetime import datetime
from pathlib import Path

# Setup logging to /tmp/capture_monitor.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/capture_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CAPTURE_DIRS = [
    "/var/www/html/stream/capture1/captures",
    "/var/www/html/stream/capture2/captures", 
    "/var/www/html/stream/capture3/captures",
    "/var/www/html/stream/capture4/captures"
]

HOST_NAME = os.getenv('USER')
# Use backend_host scripts directory
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))  # backend_host/scripts/
VENV_PATH = os.path.expanduser("~/myvenv/bin/activate")  # Use ~ expansion

UNIFIED_ANALYSIS_INTERVAL = 3   # seconds - aligned timing for video + audio

class CaptureMonitor:
    def __init__(self):
        self.running = True
        self.incident_states = {}  # Memory-based incident state: {device_id: {active_incidents: {}, last_analysis: timestamp}}
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def get_existing_directories(self):
        """Get list of existing capture directories"""
        existing = []
        for capture_dir in CAPTURE_DIRS:
            if os.path.exists(capture_dir):
                existing.append(capture_dir)
                logger.info(f"Monitoring: {capture_dir}")
            else:
                logger.info(f"Skipping non-existent: {capture_dir}")
        return existing
    
    def get_device_id_from_path(self, capture_dir):
        """Extract device_id from capture directory path"""
        try:
            # capture_dir = "/var/www/html/stream/capture1/captures"
            parent_dir = os.path.dirname(capture_dir)  # "/var/www/html/stream/capture1"
            folder_name = os.path.basename(parent_dir)  # "capture1"
            if folder_name.startswith('capture') and folder_name[7:].isdigit():
                return f"device{folder_name[7:]}"  # "device1"
            return "device-unknown"
        except Exception:
            return "device-unknown"
    
    def get_incident_state(self, device_id):
        """Get incident state for device (creates if not exists)"""
        if device_id not in self.incident_states:
            self.incident_states[device_id] = {
                "active_incidents": {},
                "last_analysis": None
            }
        return self.incident_states[device_id]
    
    def update_incident_state(self, device_id, state):
        """Update incident state for device"""
        self.incident_states[device_id] = state

    def find_recent_unanalyzed_frames(self, capture_dir, max_frames=5):
        """Find recent frames that don't have JSON analysis files yet"""
        try:
            pattern = os.path.join(capture_dir, "capture_*.jpg")
            frames = glob.glob(pattern)
            if not frames:
                return []

            # Filter out thumbnail files and numbered files (_1, _2, _3, _4) - only process original images
            # Pattern: capture_YYYYMMDDHHMMSS_N.jpg (where N is 1,2,3,4...)
            original_frames = []
            skipped_files = []
            
            for f in frames:
                filename = os.path.basename(f)
                
                # Skip thumbnail files
                if '_thumbnail' in filename:
                    skipped_files.append(f"THUMBNAIL: {filename}")
                # Skip numbered files (_1, _2, _3, _4)
                elif re.search(r'capture_\d{14}_\d+\.jpg$', filename):
                    skipped_files.append(f"NUMBERED: {filename}")
                # Skip files that don't match proper timestamp pattern (race condition files)
                elif not re.search(r'capture_\d{14}\.jpg$', filename):
                    skipped_files.append(f"INVALID_PATTERN: {filename}")
                # Only include files that still exist (avoid race conditions)
                elif os.path.exists(f):
                    original_frames.append(f)
                else:
                    skipped_files.append(f"DISAPPEARED: {filename}")
            
            # Log what we found
            if frames:
                logger.debug(f"[{device_id}] Found {len(frames)} total files, {len(original_frames)} valid for processing")
                if skipped_files and len(skipped_files) <= 5:  # Only log if reasonable number
                    logger.debug(f"[{device_id}] Skipped: {', '.join(skipped_files)}")
                elif len(skipped_files) > 5:
                    logger.debug(f"[{device_id}] Skipped {len(skipped_files)} files (too many to list)")
            if not original_frames:
                return []

            # Sort by modification time, get most recent frames
            original_frames.sort(key=os.path.getmtime, reverse=True)
            
            # Find frames without JSON files (limit to recent ones)
            unanalyzed = []
            analyzed_count = 0
            
            for frame_path in original_frames[:max_frames * 2]:  # Check more frames
                # Double-check file still exists (race condition protection)
                if not os.path.exists(frame_path):
                    logger.debug(f"[{device_id}] File disappeared during processing: {os.path.basename(frame_path)}")
                    continue
                    
                json_path = frame_path.replace('.jpg', '.json')
                filename = os.path.basename(frame_path)
                
                if not os.path.exists(json_path):
                    unanalyzed.append(frame_path)
                    logger.debug(f"[{device_id}] UNANALYZED: {filename} (no JSON)")
                    if len(unanalyzed) >= max_frames:
                        break
                else:
                    analyzed_count += 1
                    logger.debug(f"[{device_id}] ANALYZED: {filename} (JSON exists)")
            
            if analyzed_count > 0:
                logger.debug(f"[{device_id}] Found {analyzed_count} already analyzed files")
            
            return unanalyzed
            
        except Exception as e:
            logger.error(f"Error finding recent frames in {capture_dir}: {e}")
            return []

    def process_recent_frames(self, capture_dir, device_id):
        """Process recent unanalyzed frames in a capture directory"""
        try:
            # Find recent frames that need analysis
            unanalyzed_frames = self.find_recent_unanalyzed_frames(capture_dir, max_frames=3)
            
            if not unanalyzed_frames:
                return
                
            logger.info(f"[{device_id}] Found {len(unanalyzed_frames)} unanalyzed frames in {os.path.basename(capture_dir)}")
            
            # Process each frame (most recent first)
            for frame_path in unanalyzed_frames:
                if not self.running:
                    break
                
                # Check if thumbnail exists (required for thumbnail-only processing)
                thumbnail_path = frame_path.replace('.jpg', '_thumbnail.jpg')
                if not os.path.exists(thumbnail_path):
                    logger.warning(f"[{device_id}] Skipping {os.path.basename(frame_path)} - thumbnail not found")
                    continue
                    
                # Wait a bit to ensure files are fully written
                time.sleep(0.5)
                
                # Check if files still exist and are readable
                if not os.path.exists(frame_path) or not os.path.exists(thumbnail_path):
                    logger.warning(f"[{device_id}] Frame or thumbnail disappeared: {os.path.basename(frame_path)}")
                    continue
                    
                logger.info(f"[{device_id}] Processing frame (thumbnail-only): {os.path.basename(frame_path)}")
                
                # Get current incident state for this device
                current_state = self.get_incident_state(device_id)
                
                # Run unified analysis with ORIGINAL path (analyze_audio_video.py will find the thumbnail)
                # Pass device_id and incident state as JSON parameter for memory-based processing
                cmd = [
                    "bash", "-c",
                    f"source {VENV_PATH} && python {SCRIPTS_DIR}/analyze_audio_video.py '{frame_path}' '{HOST_NAME}' '{device_id}' '{json.dumps(current_state)}'"
                ]
                
                logger.info(f"[{device_id}] EXECUTING: {' '.join(cmd)}")
                logger.debug(f"[{device_id}] Working directory: {os.path.dirname(frame_path)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # Increased timeout to prevent premature termination
                    cwd=os.path.dirname(frame_path)
                )
                
                if result.returncode == 0:
                    logger.info(f"[{device_id}] Unified analysis completed: {os.path.basename(frame_path)}")
                    
                    # Log stdout for debugging
                    if result.stdout:
                        logger.debug(f"[{device_id}] Analysis stdout: {result.stdout[:200]}...")
                    
                    # Parse updated incident state from stdout (if provided)
                    try:
                        output_lines = result.stdout.strip().split('\n')
                        for line in output_lines:
                            if line.startswith('INCIDENT_STATE:'):
                                updated_state_json = line.replace('INCIDENT_STATE:', '')
                                updated_state = json.loads(updated_state_json)
                                self.update_incident_state(device_id, updated_state)
                                logger.debug(f"[{device_id}] Updated incident state")
                                break
                    except Exception as e:
                        logger.warning(f"[{device_id}] Could not parse incident state update: {e}")
                        
                    # Check if JSON was actually created
                    json_path = frame_path.replace('.jpg', '.json')
                    if os.path.exists(json_path):
                        logger.info(f"[{device_id}] ✓ JSON VERIFIED: {os.path.basename(json_path)}")
                    else:
                        logger.error(f"[{device_id}] ✗ JSON MISSING: {os.path.basename(json_path)} - analysis succeeded but no JSON created")
                        
                else:
                    logger.error(f"[{device_id}] Unified analysis FAILED (exit code {result.returncode})")
                    logger.error(f"[{device_id}] STDERR: {result.stderr}")
                    logger.error(f"[{device_id}] STDOUT: {result.stdout}")
                    
        except subprocess.TimeoutExpired:
            logger.error(f"[{device_id}] Unified analysis timeout: {os.path.basename(frame_path)}")
        except Exception as e:
            logger.error(f"[{device_id}] Unified analysis error: {e}")



    def unified_worker(self, capture_dir, device_id):
        """Unified analysis worker - processes both video and audio"""
        print(f"[@capture_monitor] Started unified worker for: {capture_dir} ({device_id})")
        
        while self.running:
            try:
                self.process_recent_frames(capture_dir, device_id)
                
                # Sleep in small intervals to allow quick shutdown
                for _ in range(UNIFIED_ANALYSIS_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[@capture_monitor] Unified worker error: {e}")
                time.sleep(5)
                
        print(f"[@capture_monitor] Unified worker stopped for: {capture_dir} ({device_id})")
            
    def start_unified_workers(self, capture_dirs):
        """Start unified analysis workers for all capture directories"""
        for capture_dir in capture_dirs:
            device_id = self.get_device_id_from_path(capture_dir)
            thread = threading.Thread(
                target=self.unified_worker,
                args=(capture_dir, device_id),
                daemon=True
            )
            thread.start()
            print(f"[@capture_monitor] Started unified thread for: {capture_dir} ({device_id})")
            
    def run(self):
        """Main monitoring loop - SIMPLIFIED"""
        print(f"[@capture_monitor] Starting Capture Monitor Service v3.0 - UNIFIED ANALYSIS")
        print(f"[@capture_monitor] Host: {HOST_NAME}")
        print(f"[@capture_monitor] Scripts: {SCRIPTS_DIR}")
        print(f"[@capture_monitor] Unified analysis interval: {UNIFIED_ANALYSIS_INTERVAL}s (video + audio)")
        print(f"[@capture_monitor] PID: {os.getpid()}")
        
        # Memory-based system - no cleanup needed on restart!
        
        # Get existing directories
        capture_dirs = self.get_existing_directories()
        
        if not capture_dirs:
            print(f"[@capture_monitor] No capture directories found, exiting")
            return
            
        # Start unified analysis workers (they handle alerts directly)
        self.start_unified_workers(capture_dirs)
        
        print(f"[@capture_monitor] All workers started - unified analysis with direct alert processing (every {UNIFIED_ANALYSIS_INTERVAL}s)")
        
        # Simple main loop - just keep alive
        while self.running:
            try:
                time.sleep(10)  # Just keep alive, workers do the real work
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[@capture_monitor] Unexpected error: {e}")
                time.sleep(5)
                
        print(f"[@capture_monitor] Monitoring stopped")
        


def main():
    """Main entry point"""
    print(f"[@capture_monitor] Capture Monitor Service v2.2 - Multi-Frame Processing")
    
    monitor = CaptureMonitor()
    
    try:
        monitor.run()
    except Exception as e:
        print(f"[@capture_monitor] Fatal error: {e}")
        sys.exit(1)
        
if __name__ == '__main__':
    main() 