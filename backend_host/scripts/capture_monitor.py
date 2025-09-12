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

# Configuration - Dynamic capture directories
def get_active_capture_dirs():
    """Read active capture directories from configuration file created by FFmpeg script"""
    config_file = "/tmp/active_captures.conf"
    capture_dirs = []
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    capture_dir = line.strip()
                    if capture_dir:
                        # Add /captures subdirectory for monitor
                        captures_subdir = os.path.join(capture_dir, 'captures')
                        if os.path.exists(captures_subdir):
                            capture_dirs.append(captures_subdir)
            logger.info(f"Loaded {len(capture_dirs)} active capture directories from {config_file}")
            if capture_dirs:
                logger.info(f"Active directories: {', '.join([os.path.basename(os.path.dirname(d)) for d in capture_dirs])}")
        else:
            logger.warning(f"Configuration file not found: {config_file}, using fallback")
            # Fallback to hardcoded for safety
            capture_dirs = [
                "/var/www/html/stream/capture1/captures",
                "/var/www/html/stream/capture2/captures", 
                "/var/www/html/stream/capture3/captures",
                "/var/www/html/stream/capture4/captures"
            ]
    except Exception as e:
        logger.error(f"Error reading active captures config: {e}, using fallback")
        # Fallback to hardcoded
        capture_dirs = [
            "/var/www/html/stream/capture1/captures",
            "/var/www/html/stream/capture2/captures", 
            "/var/www/html/stream/capture3/captures",
            "/var/www/html/stream/capture4/captures"
        ]
        
    return capture_dirs

HOST_NAME = os.getenv('USER')
# Use backend_host scripts directory
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))  # backend_host/scripts/
# Use project venv (go up 2 levels from backend_host/scripts/ to project root)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, '..', '..'))
VENV_PATH = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'activate')

UNIFIED_ANALYSIS_INTERVAL = 1   # seconds - aligned timing for video + audio

class CaptureMonitor:
    def __init__(self):
        self.running = True
        self.incident_states = {}  # Memory-based incident state: {device_id: {active_incidents: {}, last_analysis: timestamp}}
        self.cleanup_logs_on_startup()
        self.setup_signal_handlers()
        
    def cleanup_logs_on_startup(self):
        """Clean up all monitoring log files on service restart for fresh debugging"""
        try:
            log_files = [
                '/tmp/capture_monitor.log',  # This service's log
                '/tmp/analysis.log',         # analyze_audio_video.py log
                '/tmp/alerts.log'            # alert_system.py log
            ]
            
            print(f"[@capture_monitor] Cleaning monitoring logs on service restart...")
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    # Truncate the file instead of deleting to avoid permission issues
                    with open(log_file, 'w') as f:
                        f.write(f"=== LOG CLEANED ON MONITOR RESTART: {datetime.now().isoformat()} ===\n")
                    print(f"[@capture_monitor] ✓ Cleaned: {log_file}")
                else:
                    print(f"[@capture_monitor] ○ Not found (will be created): {log_file}")
                    
            print(f"[@capture_monitor] Log cleanup complete - fresh logs for debugging")
                    
        except Exception as e:
            print(f"[@capture_monitor] Warning: Could not clean log files: {e}")
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def get_existing_directories(self):
        """Get list of existing capture directories (dynamic from config)"""
        capture_dirs = get_active_capture_dirs()
        existing = []
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                existing.append(capture_dir)
                logger.info(f"Monitoring: {capture_dir}")
            else:
                logger.info(f"Skipping non-existent: {capture_dir}")
        return existing
    
    def get_device_id_from_path(self, capture_dir):
        """Extract device_id from capture directory path with enhanced mapping"""
        try:
            # capture_dir = "/var/www/html/stream/capture1/captures"
            parent_dir = os.path.dirname(capture_dir)  # "/var/www/html/stream/capture1"
            folder_name = os.path.basename(parent_dir)  # "capture1"
            
            logger.debug(f"Mapping capture directory: {capture_dir} -> folder: {folder_name}")
            
            if folder_name.startswith('capture') and len(folder_name) > 7:
                capture_num = folder_name[7:]  # Extract number after "capture"
                if capture_num.isdigit():
                    device_id = f"device{capture_num}"
                    logger.debug(f"Mapped {folder_name} -> {device_id}")
                    return device_id
                else:
                    logger.warning(f"Invalid capture number in {folder_name}: '{capture_num}'")
            elif folder_name == 'capture':
                # Handle case where folder is just "capture" (no number)
                logger.debug(f"Mapped {folder_name} -> host (VNC device)")
                return "host"
            else:
                logger.warning(f"Unrecognized capture folder pattern: {folder_name}")
            
            return "device-unknown"
        except Exception as e:
            logger.error(f"Error extracting device_id from {capture_dir}: {e}")
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
            device_name = os.path.basename(os.path.dirname(capture_dir))  # e.g., "capture3"
            
            if not frames:
                logger.debug(f"[{device_name}] No capture files found in {capture_dir}")
                return []

            # Filter out thumbnail files and numbered files (_1, _2, _3, _4) - only process original images
            # Pattern: capture_N.jpg (where N is sequential number)
            original_frames = []
            skipped_files = []
            
            for f in frames:
                filename = os.path.basename(f)
                
                # Skip thumbnail files
                if '_thumbnail' in filename:
                    skipped_files.append(f"THUMBNAIL: {filename}")
                # Skip files that don't match sequential pattern (capture_*.jpg)
                elif not re.search(r'capture_\d+\.jpg$', filename):
                    skipped_files.append(f"INVALID_PATTERN: {filename}")
                # Only include files that still exist (avoid race conditions)
                elif os.path.exists(f):
                    original_frames.append(f)
                else:
                    skipped_files.append(f"DISAPPEARED: {filename}")
            
            # Enhanced logging for debugging missing JSON issues
            logger.info(f"[{device_name}] SCAN SUMMARY: {len(frames)} total files, {len(original_frames)} valid for processing")
            if skipped_files and len(skipped_files) <= 10:  # Show more skipped files for debugging
                logger.debug(f"[{device_name}] Skipped: {', '.join(skipped_files)}")
            elif len(skipped_files) > 10:
                logger.debug(f"[{device_name}] Skipped {len(skipped_files)} files (too many to list)")
                
            if not original_frames:
                logger.warning(f"[{device_name}] No valid frames found for processing")
                return []

            # Sort by modification time, get most recent frames
            original_frames.sort(key=os.path.getmtime, reverse=True)
            
            # Find frames without JSON files (limit to recent ones) with detailed logging
            unanalyzed = []
            analyzed_count = 0
            missing_json_details = []
            
            for frame_path in original_frames[:max_frames * 3]:  # Check more frames for debugging
                # Double-check file still exists (race condition protection)
                if not os.path.exists(frame_path):
                    logger.debug(f"[{device_name}] File disappeared during processing: {os.path.basename(frame_path)}")
                    continue
                    
                json_path = frame_path.replace('.jpg', '.json')
                filename = os.path.basename(frame_path)
                
                # Get file timestamps for debugging
                frame_mtime = os.path.getmtime(frame_path)
                frame_age = time.time() - frame_mtime
                
                if not os.path.exists(json_path):
                    unanalyzed.append(frame_path)
                    missing_json_details.append(f"{filename} (age: {frame_age:.1f}s)")
                    logger.debug(f"[{device_name}] UNANALYZED: {filename} (no JSON, age: {frame_age:.1f}s)")
                    if len(unanalyzed) >= max_frames:
                        break
                else:
                    analyzed_count += 1
                    json_mtime = os.path.getmtime(json_path)
                    json_age = time.time() - json_mtime
                    logger.debug(f"[{device_name}] ANALYZED: {filename} (JSON exists, age: {json_age:.1f}s)")
            
            # Enhanced logging for missing JSON debugging
            if unanalyzed:
                logger.warning(f"[{device_name}] MISSING JSON: Found {len(unanalyzed)} unanalyzed frames: {', '.join(missing_json_details[:3])}{'...' if len(missing_json_details) > 3 else ''}")
            
            if analyzed_count > 0:
                logger.info(f"[{device_name}] Found {analyzed_count} already analyzed files")
            
            # Additional debugging: Check if analysis script is running properly
            if len(unanalyzed) > max_frames:
                logger.error(f"[{device_name}] ANALYSIS BACKLOG: {len(unanalyzed)} unanalyzed frames detected - analysis may be failing or too slow")
            
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
                        
                    # Enhanced JSON verification with debugging
                    json_path = frame_path.replace('.jpg', '.json')
                    thumbnail_path = frame_path.replace('.jpg', '_thumbnail.jpg')
                    
                    # Wait a moment for file system to sync
                    time.sleep(0.1)
                    
                    if os.path.exists(json_path):
                        # Verify JSON is valid and complete
                        try:
                            with open(json_path, 'r') as f:
                                json_data = json.load(f)
                            
                            # Check if JSON has required fields
                            required_fields = ['timestamp', 'filename', 'blackscreen', 'freeze', 'audio']
                            missing_fields = [field for field in required_fields if field not in json_data]
                            
                            if missing_fields:
                                logger.error(f"[{device_id}] ✗ JSON INCOMPLETE: {os.path.basename(json_path)} missing fields: {missing_fields}")
                            else:
                                logger.info(f"[{device_id}] ✓ JSON VERIFIED: {os.path.basename(json_path)} (complete)")
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"[{device_id}] ✗ JSON CORRUPTED: {os.path.basename(json_path)} - {e}")
                        except Exception as e:
                            logger.error(f"[{device_id}] ✗ JSON READ ERROR: {os.path.basename(json_path)} - {e}")
                    else:
                        logger.error(f"[{device_id}] ✗ JSON MISSING: {os.path.basename(json_path)} - analysis succeeded but no JSON created")
                        
                        # Additional debugging for missing JSON
                        logger.error(f"[{device_id}] DEBUG INFO:")
                        logger.error(f"[{device_id}]   - Frame exists: {os.path.exists(frame_path)}")
                        logger.error(f"[{device_id}]   - Thumbnail exists: {os.path.exists(thumbnail_path)}")
                        logger.error(f"[{device_id}]   - Working directory: {os.path.dirname(frame_path)}")
                        logger.error(f"[{device_id}]   - Expected JSON path: {json_path}")
                        
                        # Check if analysis script created any files
                        frame_dir = os.path.dirname(frame_path)
                        recent_files = []
                        try:
                            for f in os.listdir(frame_dir):
                                if f.endswith('.json'):
                                    file_path = os.path.join(frame_dir, f)
                                    if os.path.getmtime(file_path) > time.time() - 60:  # Created in last minute
                                        recent_files.append(f)
                            logger.error(f"[{device_id}]   - Recent JSON files in directory: {recent_files}")
                        except Exception as e:
                            logger.error(f"[{device_id}]   - Could not list directory: {e}")
                        
                else:
                    logger.error(f"[{device_id}] Unified analysis FAILED (exit code {result.returncode})")
                    logger.error(f"[{device_id}] COMMAND: {' '.join(cmd)}")
                    logger.error(f"[{device_id}] STDERR: {result.stderr}")
                    logger.error(f"[{device_id}] STDOUT: {result.stdout}")
                    
                    # Additional debugging for failed analysis
                    thumbnail_path = frame_path.replace('.jpg', '_thumbnail.jpg')
                    logger.error(f"[{device_id}] FAILURE DEBUG:")
                    logger.error(f"[{device_id}]   - Frame exists: {os.path.exists(frame_path)}")
                    logger.error(f"[{device_id}]   - Thumbnail exists: {os.path.exists(thumbnail_path)}")
                    logger.error(f"[{device_id}]   - Scripts dir: {SCRIPTS_DIR}")
                    logger.error(f"[{device_id}]   - Venv path: {VENV_PATH}")
                    logger.error(f"[{device_id}]   - Host name: {HOST_NAME}")
                    
                    # Check if analysis script exists
                    analysis_script = os.path.join(SCRIPTS_DIR, 'analyze_audio_video.py')
                    logger.error(f"[{device_id}]   - Analysis script exists: {os.path.exists(analysis_script)}")
                    
                    # Check venv activation
                    if os.path.exists(VENV_PATH):
                        logger.error(f"[{device_id}]   - Venv activate script exists: True")
                    else:
                        logger.error(f"[{device_id}]   - Venv activate script exists: False")
                    
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