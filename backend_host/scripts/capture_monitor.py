#!/usr/bin/env python3
"""
Simple incident monitoring main loop
Glues detector + incident_manager together
"""
import os
import time
import glob
from detector import detect_issues
from incident_manager import IncidentManager

def get_capture_directories():
    """Find active capture directories"""
    base_dirs = [
        "/var/www/html/stream/capture1/captures",
        "/var/www/html/stream/capture2/captures", 
        "/var/www/html/stream/capture3/captures",
        "/var/www/html/stream/capture4/captures"
    ]
    return [d for d in base_dirs if os.path.exists(d)]

def get_device_id(capture_dir):
    """Extract device ID from path"""
    # /var/www/html/stream/capture1/captures -> device1
    parent = os.path.basename(os.path.dirname(capture_dir))
    if parent.startswith('capture'):
        return f"device{parent[7:]}"
    return "device-unknown"

def find_latest_frame(capture_dir):
    """Find most recent unanalyzed frame"""
    pattern = os.path.join(capture_dir, "capture_*.jpg")
    frames = [f for f in glob.glob(pattern) if '_thumbnail' not in f]
    
    if not frames:
        return None
    
    # Get most recent frame that doesn't have a JSON file
    frames.sort(key=os.path.getmtime, reverse=True)
    for frame in frames[:3]:  # Check last 3 frames
        json_file = frame.replace('.jpg', '.json')
        if not os.path.exists(json_file):
            return frame
    return None

def main():
    """Main monitoring loop"""
    print("Starting simple incident monitor...")
    
    host_name = os.getenv('USER', 'unknown')
    incident_manager = IncidentManager()
    capture_dirs = get_capture_directories()
    
    print(f"Monitoring {len(capture_dirs)} capture directories")
    
    while True:
        for capture_dir in capture_dirs:
            device_id = get_device_id(capture_dir)
            frame_path = find_latest_frame(capture_dir)
            
            if frame_path:
                # Detect issues
                detection_result = detect_issues(frame_path)
                
                # Process with incident manager
                incident_manager.process_detection(device_id, detection_result, host_name)
                
                # Mark frame as analyzed
                json_file = frame_path.replace('.jpg', '.json')
                with open(json_file, 'w') as f:
                    f.write('{"analyzed": true}')
        
        time.sleep(2)  # Check every 2 seconds

if __name__ == '__main__':
    main()
