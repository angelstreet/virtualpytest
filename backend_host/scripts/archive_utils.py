#!/usr/bin/env python3
"""
Shared utilities for archive manifest and transcript generation
Extracted from capture_monitor.py to avoid code duplication
"""
import os
import glob
import json
import logging

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
        logger.warning(f"[@generate_manifest] No segments provided for {manifest_name}")
        return False
    
    # Calculate proper media sequence number (first segment number in window)
    first_segment_num = int(os.path.basename(segments[0]).split('_')[1].split('.')[0])
    last_segment_num = int(os.path.basename(segments[-1]).split('_')[1].split('.')[0])
    
    logger.debug(f"[@generate_manifest] {manifest_name}: segments #{first_segment_num}-#{last_segment_num} ({len(segments)} files)")
    
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
    logger.info(f"[@generate_manifest] ✓ {manifest_name}: {len(segments)} segments (#{first_segment_num}-#{last_segment_num})")
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
        
        # Get segment number range for logging
        first_seg_num = int(os.path.basename(segments[0]).split('_')[1].split('.')[0])
        last_seg_num = int(os.path.basename(segments[-1]).split('_')[1].split('.')[0])
        
        logger.info(f"[@update_archive] [{capture_folder}] Found {len(segments)} segments (#{first_seg_num} to #{last_seg_num})")
        
        total_segments = len(segments)
        
        # Rolling 24-hour window strategy:
        # - Keep only LAST 24 hours of content
        # - Manifests numbered archive1 through archive24
        # - archive1 = oldest hour (24h ago), archive24 = most recent hour (now)
        # - Frontend uses archive_metadata.json to know which manifest has which time range
        
        # If we have more than 24 hours of segments, use only the last 24 hours
        max_segments_to_use = MAX_MANIFESTS * SEGMENTS_PER_WINDOW  # 24 hours worth
        if total_segments > max_segments_to_use:
            segments = segments[-max_segments_to_use:]  # Keep only last 24 hours
            logger.debug(f"[{capture_folder}] Rolling window: using last {len(segments)} segments (24h)")
        
        total_segments = len(segments)
        num_windows = (total_segments + SEGMENTS_PER_WINDOW - 1) // SEGMENTS_PER_WINDOW
        
        manifests_generated = 0
        manifest_metadata = []  # Store metadata with actual segment numbers
        
        for window_idx in range(num_windows):
            start_idx = window_idx * SEGMENTS_PER_WINDOW
            end_idx = min(start_idx + SEGMENTS_PER_WINDOW, total_segments)
            window_segments = segments[start_idx:end_idx]
            
            # Only generate if we have segments in this window
            if len(window_segments) > 0:
                manifest_name = f"archive{window_idx + 1}.m3u8"
                
                # Extract actual segment numbers from filenames
                first_seg_num = int(os.path.basename(window_segments[0]).split('_')[1].split('.')[0])
                last_seg_num = int(os.path.basename(window_segments[-1]).split('_')[1].split('.')[0])
                
                if generate_manifest_for_segments(stream_dir, window_segments, manifest_name):
                    manifests_generated += 1
                    
                    # Store metadata with actual segment numbers for this manifest
                    manifest_metadata.append({
                        "name": manifest_name,
                        "window_index": window_idx + 1,
                        "start_segment": first_seg_num,
                        "end_segment": last_seg_num,
                        "start_time_seconds": start_idx * SEGMENT_DURATION,
                        "end_time_seconds": end_idx * SEGMENT_DURATION,
                        "duration_seconds": len(window_segments) * SEGMENT_DURATION
                    })
        
        # Generate metadata JSON for frontend to know which manifests to use
        metadata = {
            "total_segments": total_segments,
            "total_duration_seconds": total_segments * SEGMENT_DURATION,
            "window_hours": WINDOW_HOURS,
            "segments_per_window": SEGMENTS_PER_WINDOW,
            "manifests": manifest_metadata
        }
        
        # Write metadata JSON
        metadata_path = os.path.join(stream_dir, 'archive_metadata.json')
        with open(metadata_path + '.tmp', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        os.rename(metadata_path + '.tmp', metadata_path)
        
        # Legacy archive.m3u8 - points to most recent manifest for simple players
        if manifests_generated > 0:
            archive_path = os.path.join(stream_dir, 'archive.m3u8')
            last_manifest_name = f'archive{manifests_generated}.m3u8'
            last_manifest_path = os.path.join(stream_dir, last_manifest_name)
            
            with open(archive_path + '.tmp', 'w') as f:
                f.write(f"# Use archive_metadata.json for multi-manifest playback\n")
                f.write(f"# This manifest points to the most recent archive window ({last_manifest_name})\n")
                # Point to most recent manifest for simple players
                with open(last_manifest_path, 'r') as src:
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
        logger.info(f"[@update_archive] [{capture_folder}] ✓ Generated {manifests_generated} manifests, {total_segments} segments ({total_duration_hours:.1f}h)")
        
    except Exception as e:
        logger.error(f"Error updating archive manifest for {capture_dir}: {e}")

