#!/usr/bin/env python3
"""
Simple incident monitoring main loop
Glues detector + incident_manager together
"""
import os
import time
import glob
import json
import logging
from datetime import datetime
from detector import detect_issues
from incident_manager import IncidentManager

# Setup logging to /tmp/capture_monitor.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/capture_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_capture_directories():
    """Find active capture directories from /tmp/active_captures.conf (centralized config)"""
    active_captures_file = '/tmp/active_captures.conf'
    
    # Read from centralized config file written by run_ffmpeg_and_rename_local.sh
    if os.path.exists(active_captures_file):
        try:
            with open(active_captures_file, 'r') as f:
                # Each line contains a capture directory path (e.g., /var/www/html/stream/capture1)
                base_dirs = []
                for line in f:
                    capture_base = line.strip()
                    if capture_base:
                        # Add /captures subdirectory
                        capture_dir = os.path.join(capture_base, 'captures')
                        if os.path.exists(capture_dir):
                            base_dirs.append(capture_dir)
                
                logger.info(f"✅ Loaded {len(base_dirs)} capture directories from {active_captures_file}")
                return base_dirs
        except Exception as e:
            logger.error(f"❌ Error reading {active_captures_file}: {e}")
    
    # Fallback to default directories if config file doesn't exist
    logger.warning(f"⚠️ {active_captures_file} not found, using fallback directories")
    base_dirs = [
        "/var/www/html/stream/capture1/captures",
        "/var/www/html/stream/capture2/captures", 
    ]
    return [d for d in base_dirs if os.path.exists(d)]

def get_capture_folder(capture_dir):
    """Extract capture folder from path"""
    # /var/www/html/stream/capture1/captures -> capture1
    return os.path.basename(os.path.dirname(capture_dir))

def generate_manifest_for_segments(stream_dir, segments, manifest_name):
    """Generate a single manifest file for given segments"""
    if not segments:
        return False
    
    # Calculate proper media sequence number (first segment number in window)
    first_segment_num = int(os.path.basename(segments[0]).split('_')[1].split('.')[0])
    
    # Generate manifest content
    manifest_content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:4",
        f"#EXT-X-MEDIA-SEQUENCE:{first_segment_num}"
    ]
    
    for segment in segments:
        segment_name = os.path.basename(segment)
        manifest_content.extend([
            "#EXTINF:1.000000,",
            segment_name
        ])
    
    manifest_content.append("#EXT-X-ENDLIST")
    
    # Write manifest atomically
    manifest_path = os.path.join(stream_dir, manifest_name)
    with open(manifest_path + '.tmp', 'w') as f:
        f.write('\n'.join(manifest_content))
    
    os.rename(manifest_path + '.tmp', manifest_path)
    return True

def update_archive_manifest(capture_dir):
    """Generate dynamic 1-hour archive manifests with progressive creation"""
    try:
        capture_folder = get_capture_folder(capture_dir)
        stream_dir = capture_dir.replace('/captures', '')  # /var/www/html/stream/capture1
        
        # Configuration for 1-hour manifest windows
        WINDOW_HOURS = 1
        SEGMENT_DURATION = 1  # seconds per segment (from FFmpeg config)
        SEGMENTS_PER_WINDOW = WINDOW_HOURS * 3600 // SEGMENT_DURATION  # 3,600 segments per 1h window
        MAX_MANIFESTS = 24  # Support up to 24 hours (24 manifests)
        
        # Find all segment files
        segments = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
        if not segments:
            return
            
        # Sort segments by file modification time (chronological order)
        # This handles FFmpeg restarts, segment wrap-around, and gaps correctly
        segments.sort(key=lambda x: os.path.getmtime(x))
        
        logger.debug(f"[{capture_folder}] Found {len(segments)} segments, sorted by timestamp")
        
        total_segments = len(segments)
        
        # Rolling 24-hour window strategy:
        # - Keep only LAST 24 hours of content
        # - Always use archive1 through archive24 (fixed naming)
        # - archive1 = most recent hour, archive24 = 24 hours ago
        
        # If we have more than 24 hours of segments, use only the last 24 hours
        max_segments_to_use = MAX_MANIFESTS * SEGMENTS_PER_WINDOW  # 24 hours worth
        if total_segments > max_segments_to_use:
            segments = segments[-max_segments_to_use:]  # Keep only last 24 hours
            logger.debug(f"[{capture_folder}] Rolling window: using last {len(segments)} segments (24h)")
        
        total_segments = len(segments)
        num_windows = (total_segments + SEGMENTS_PER_WINDOW - 1) // SEGMENTS_PER_WINDOW
        
        manifests_generated = 0
        for window_idx in range(num_windows):
            start_idx = window_idx * SEGMENTS_PER_WINDOW
            end_idx = min(start_idx + SEGMENTS_PER_WINDOW, total_segments)
            window_segments = segments[start_idx:end_idx]
            
            # Only generate if we have segments in this window
            if len(window_segments) > 0:
                manifest_name = f"archive{window_idx + 1}.m3u8"
                if generate_manifest_for_segments(stream_dir, window_segments, manifest_name):
                    manifests_generated += 1
                    logger.debug(f"[{capture_folder}] Generated {manifest_name}: {len(window_segments)} segments ({len(window_segments)/3600:.2f}h)")
        
        # Generate metadata JSON for frontend to know which manifests to use
        metadata = {
            "total_segments": total_segments,
            "total_duration_seconds": total_segments * SEGMENT_DURATION,
            "window_hours": WINDOW_HOURS,
            "segments_per_window": SEGMENTS_PER_WINDOW,
            "manifests": []
        }
        
        for i in range(manifests_generated):
            start_segment = i * SEGMENTS_PER_WINDOW
            end_segment = min(start_segment + SEGMENTS_PER_WINDOW, total_segments)
            metadata["manifests"].append({
                "name": f"archive{i + 1}.m3u8",
                "window_index": i + 1,
                "start_segment": start_segment,
                "end_segment": end_segment,
                "start_time_seconds": start_segment * SEGMENT_DURATION,
                "end_time_seconds": end_segment * SEGMENT_DURATION,
                "duration_seconds": (end_segment - start_segment) * SEGMENT_DURATION
            })
        
        # Write metadata JSON
        metadata_path = os.path.join(stream_dir, 'archive_metadata.json')
        with open(metadata_path + '.tmp', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        os.rename(metadata_path + '.tmp', metadata_path)
        
        # Backward compatibility: archive.m3u8 points to archive1.m3u8
        if manifests_generated > 0:
            archive_path = os.path.join(stream_dir, 'archive.m3u8')
            with open(archive_path + '.tmp', 'w') as f:
                f.write(f"# Use archive_metadata.json for multi-manifest playback\n")
                f.write(f"# Or access archive1.m3u8, archive2.m3u8, etc. directly\n")
                # Point to first manifest for simple players
                with open(os.path.join(stream_dir, 'archive1.m3u8'), 'r') as src:
                    f.write(src.read())
            
            os.rename(archive_path + '.tmp', archive_path)
        
        # Cleanup old manifests beyond current window
        # If we only generated 5 manifests, remove archive6-24 if they exist from previous runs
        for old_idx in range(manifests_generated + 1, MAX_MANIFESTS + 1):
            old_manifest = os.path.join(stream_dir, f'archive{old_idx}.m3u8')
            if os.path.exists(old_manifest):
                try:
                    os.remove(old_manifest)
                    logger.debug(f"[{capture_folder}] Cleaned up unused {os.path.basename(old_manifest)}")
                except Exception as e:
                    logger.warning(f"[{capture_folder}] Failed to remove {old_manifest}: {e}")
        
        total_duration_hours = total_segments * SEGMENT_DURATION / 3600
        logger.info(f"[{capture_folder}] Rolling archive: {manifests_generated} manifests (1-{manifests_generated}), {total_segments} segments ({total_duration_hours:.1f}h)")
        
    except Exception as e:
        logger.error(f"Error updating archive manifest for {capture_dir}: {e}")

def find_latest_frame(capture_dir):
    """Find most recent unanalyzed frame - OPTIMIZED with scandir"""
    try:
        entries = []
        with os.scandir(capture_dir) as it:
            for entry in it:
                if (entry.name.startswith('capture_') and 
                    entry.name.endswith('.jpg') and 
                    '_thumbnail' not in entry.name):
                    # Get stat info once during scandir (faster than separate os.path.getmtime)
                    entries.append((entry.path, entry.stat().st_mtime))
        
        if not entries:
            return None
        
        # Sort by mtime (already retrieved during scandir)
        entries.sort(key=lambda x: x[1], reverse=True)
        
        # Check last 3 frames for unanalyzed
        for frame_path, _ in entries[:3]:
            json_file = frame_path.replace('.jpg', '.json')
            if not os.path.exists(json_file):
                return frame_path
        return None
    except Exception as e:
        logger.error(f"Error finding latest frame in {capture_dir}: {e}")
        return None

def cleanup_logs_on_startup():
    """Clean up all monitoring log files on service restart for fresh debugging - EXACT COPY"""
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

def main():
    """Main monitoring loop"""
    cleanup_logs_on_startup()  # Clean logs on startup - EXACT COPY
    
    logger.info("Starting simple incident monitor...")
    
    host_name = os.getenv('USER', 'unknown')
    incident_manager = IncidentManager()
    capture_dirs = get_capture_directories()
    
    logger.info(f"Monitoring {len(capture_dirs)} capture directories")
    for capture_dir in capture_dirs:
        capture_folder = get_capture_folder(capture_dir)
        logger.info(f"Monitoring: {capture_dir} -> {capture_folder}")
    
    # Auto-resolve orphaned incidents for capture folders no longer being monitored
    monitored_capture_folders = [get_capture_folder(d) for d in capture_dirs]
    incident_manager.cleanup_orphaned_incidents(monitored_capture_folders, host_name)
    
    # Performance: Throttle manifest updates to once per 60 seconds per capture directory
    last_manifest_update = {}
    
    while True:
        current_time = time.time()
        
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            
            # Update archive manifest only every 60 seconds (performance optimization)
            if current_time - last_manifest_update.get(capture_folder, 0) >= 60:
                update_archive_manifest(capture_dir)
                last_manifest_update[capture_folder] = current_time
            
            frame_path = find_latest_frame(capture_dir)
            
            if frame_path:
                detection_result = detect_issues(frame_path)
                
                issues = []
                if detection_result and detection_result.get('blackscreen', False):
                    issues.append('blackscreen')
                if detection_result and detection_result.get('freeze', False):
                    issues.append('freeze')
                if detection_result and not detection_result.get('audio', True):
                    issues.append('audio_loss')
                
                if issues:
                    logger.info(f"[{capture_folder}] Issues detected: {issues}")
                
                incident_manager.process_detection(capture_folder, detection_result, host_name)
                
                # Save complete analysis data to JSON file
                json_file = frame_path.replace('.jpg', '.json')
                try:
                    if detection_result:
                        analysis_data = {
                            "analyzed": True,
                            **detection_result  # Include all detection data (freeze, blackscreen, audio, etc.)
                        }
                    else:
                        logger.error(f"[{capture_folder}] ERROR: detection_result is None/empty, saving fallback")
                        analysis_data = {
                            "analyzed": True,
                            "error": "detection_result_was_none"
                        }
                    
                    with open(json_file, 'w') as f:
                        json.dump(analysis_data, f, indent=2)
                        
                except Exception as e:
                    logger.error(f"[{capture_folder}] Error saving analysis data: {e}")
                    # Fallback to simple marker
                    with open(json_file, 'w') as f:
                        f.write('{"analyzed": true, "error": "failed_to_save_full_data"}')
        
        time.sleep(2)  # Check every 2 seconds
        
if __name__ == '__main__':
    main() 
