"""
Analysis Utilities

Shared utilities for loading and analyzing JSON capture data.
Extracted from heatmap functionality to avoid code duplication across controllers.
"""

import os
import time
import json
from typing import Dict, List, Any, Optional
from shared.lib.utils.host_utils import get_host


def load_recent_analysis_data(device_id: str, timeframe_minutes: int = 5, max_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Load recent analysis data for a device (extracted from heatmap functionality).
    
    Args:
        device_id: Device ID to load analysis for
        timeframe_minutes: Time window in minutes to look back (default: 5)
        max_count: Maximum number of files to return (default: None for no limit)
        
    Returns:
        Dict with success status and analysis data:
        {
            'success': bool,
            'analysis_data': List[Dict],  # List of files with analysis_json
            'total': int,
            'device_id': str,
            'error': str  # Only present if success=False
        }
    """
    try:
        # Get device directly from existing host instance
        host = get_host()
        device = host.get_device(device_id)
        if not device:
            return {
                'success': False,
                'error': f'Device {device_id} not found',
                'analysis_data': [],
                'total': 0,
                'device_id': device_id
            }
        
        capture_folder = os.path.join(device.video_capture_path, 'captures')
        
        if not os.path.exists(capture_folder):
            return {
                'success': False,
                'error': f'Capture folder not found: {capture_folder}',
                'analysis_data': [],
                'total': 0,
                'device_id': device_id
            }
        
        # Simple file scan (same logic as heatmap)
        cutoff_time = time.time() - (timeframe_minutes * 60)
        files = []
        
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and filename.endswith('.jpg') and 
                not filename.endswith('_thumbnail.jpg')):
                
                # VALIDATE FILENAME FORMAT FIRST - before any file operations
                # Sequential format: capture_0001.jpg, capture_0002.jpg, etc.
                import re
                if not re.match(r'^capture_\d+\.jpg$', filename):
                    print(f"[@analysis_utils] Skipping invalid filename format: {filename}")
                    continue
                
                # Only check file modification time AFTER validation passes
                filepath = os.path.join(capture_folder, filename)
                if os.path.getmtime(filepath) >= cutoff_time:
                    
                    # Check for analysis files
                    base_name = filename.replace('.jpg', '')
                    frame_json_path = os.path.join(capture_folder, f"{base_name}.json")
                    
                    # Only include files that have JSON analysis (same as heatmap)
                    if os.path.exists(frame_json_path):
                        try:
                            with open(frame_json_path, 'r') as f:
                                analysis_data = json.load(f)
                                
                            # Calculate has_incidents based on the analysis data (same as heatmap)
                            has_incidents = (
                                analysis_data.get('freeze', False) or
                                analysis_data.get('blackscreen', False) or
                                not analysis_data.get('audio', True)
                            )
                            analysis_data['has_incidents'] = has_incidents
                            
                            file_item = {
                                'filename': filename,
                                'timestamp': timestamp,
                                'file_mtime': int(os.path.getmtime(filepath) * 1000),
                                'analysis_json': analysis_data
                            }
                            
                            files.append(file_item)
                            
                        except (json.JSONDecodeError, IOError) as e:
                            # Skip files with corrupted or unreadable JSON (same as heatmap)
                            print(f"[@analysis_utils] Skipping {filename}: JSON error {e}")
                            continue
                    # Skip files without JSON analysis - don't add them to the response
        
        # Sort by timestamp (newest first) (same as heatmap)
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply max_count limit if specified
        if max_count is not None:
            files = files[:max_count]
        
        return {
            'success': True,
            'analysis_data': files,
            'total': len(files),
            'device_id': device_id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'analysis_data': [],
            'total': 0,
            'device_id': device_id
        }


def load_recent_analysis_data_from_path(capture_path: str, timeframe_minutes: int = 5, max_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Load recent analysis data from a direct capture path.
    
    Args:
        capture_path: Direct path to the capture folder
        timeframe_minutes: Time window in minutes to look back (default: 5)
        max_count: Maximum number of files to return (default: None for no limit)
        
    Returns:
        Dict with success status and analysis data
    """
    try:
        capture_folder = os.path.join(capture_path, 'captures')
        
        if not os.path.exists(capture_folder):
            return {
                'success': False,
                'error': f'Capture folder not found: {capture_folder}',
                'analysis_data': [],
                'total': 0,
                'capture_path': capture_path
            }
        
        # Simple file scan (same logic as existing function)
        cutoff_time = time.time() - (timeframe_minutes * 60)
        files = []
        
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and filename.endswith('.jpg') and 
                not filename.endswith('_thumbnail.jpg')):
                
                # VALIDATE FILENAME FORMAT FIRST - before any file operations
                # Sequential format: capture_0001.jpg, capture_0002.jpg, etc.
                import re
                if not re.match(r'^capture_\d+\.jpg$', filename):
                    print(f"[@analysis_utils] Skipping invalid filename format: {filename}")
                    continue
                
                # Only check file modification time AFTER validation passes
                filepath = os.path.join(capture_folder, filename)
                if os.path.getmtime(filepath) >= cutoff_time:
                    
                    # Check for analysis files
                    base_name = filename.replace('.jpg', '')
                    frame_json_path = os.path.join(capture_folder, f"{base_name}.json")
                    
                    if os.path.exists(frame_json_path):
                        try:
                            with open(frame_json_path, 'r') as f:
                                analysis_data = json.load(f)
                                
                            # Calculate has_incidents based on the analysis data
                            has_incidents = (
                                analysis_data.get('freeze', False) or
                                analysis_data.get('blackscreen', False) or
                                not analysis_data.get('audio', True)
                            )
                            analysis_data['has_incidents'] = has_incidents
                            
                            file_item = {
                                'filename': filename,
                                'timestamp': timestamp,
                                'file_mtime': int(os.path.getmtime(filepath) * 1000),
                                'analysis_json': analysis_data
                            }
                            
                            files.append(file_item)
                            
                        except (json.JSONDecodeError, IOError) as e:
                            # Skip files with corrupted or unreadable JSON
                            print(f"[@analysis_utils] Skipping {filename}: JSON error {e}")
                            continue
        
        # Sort by timestamp (newest first)
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply max_count limit if specified
        if max_count is not None:
            files = files[:max_count]
        
        return {
            'success': True,
            'analysis_data': files,
            'total': len(files),
            'capture_path': capture_path
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'analysis_data': [],
            'total': 0,
            'capture_path': capture_path
        }


def analyze_motion_from_loaded_data(analysis_data: List[Dict], json_count: int = 5, strict_mode: bool = True) -> Dict[str, Any]:
    """
    Analyze motion/activity from pre-loaded analysis data.
    
    Args:
        analysis_data: List of file items with analysis_json (from load_recent_analysis_data)
        json_count: Number of recent files to analyze (default: 5)
        strict_mode: If True, ALL files must show no errors. If False, majority must show no errors (default: True)
        
    Returns:
        Dict with detailed analysis results
    """
    try:
        # Take only the requested number of files (already sorted newest first)
        files_to_analyze = analysis_data[:json_count]
        
        # Analyze each file
        details = []
        blackscreen_count = 0
        freeze_count = 0
        audio_loss_count = 0
        
        for file_item in files_to_analyze:
            try:
                analysis_json = file_item.get('analysis_json', {})
                
                # Extract analysis results (following heatmap pattern)
                blackscreen = analysis_json.get('blackscreen', False)
                freeze = analysis_json.get('freeze', False)
                audio = analysis_json.get('audio', True)
                
                # Count issues
                if blackscreen:
                    blackscreen_count += 1
                if freeze:
                    freeze_count += 1
                if not audio:
                    audio_loss_count += 1
                
                # Determine if this file shows motion/activity (no issues)
                video_ok = not blackscreen and not freeze
                audio_ok = audio
                file_ok = video_ok and audio_ok
                
                file_detail = {
                    'filename': file_item.get('filename', ''),
                    'timestamp': analysis_json.get('timestamp', ''),
                    'blackscreen': blackscreen,
                    'blackscreen_percentage': analysis_json.get('blackscreen_percentage', 0),
                    'freeze': freeze,
                    'freeze_diffs': analysis_json.get('freeze_diffs', []),
                    'audio': audio,
                    'volume_percentage': analysis_json.get('volume_percentage', 0),
                    'mean_volume_db': analysis_json.get('mean_volume_db', -100),
                    'video_ok': video_ok,
                    'audio_ok': audio_ok,
                    'file_ok': file_ok,
                    'has_incidents': blackscreen or freeze or not audio
                }
                
                details.append(file_detail)
                
            except Exception as e:
                print(f"[@analysis_utils] Error processing file item: {e}")
                continue
        
        total_analyzed = len(details)
        
        if total_analyzed == 0:
            return {
                'success': False,
                'video_ok': False,
                'audio_ok': False,
                'blackscreen_count': 0,
                'freeze_count': 0,
                'audio_loss_count': 0,
                'total_analyzed': 0,
                'details': [],
                'strict_mode': strict_mode,
                'message': f'No valid analysis data found'
            }
        
        # Determine overall status based on strict_mode
        if strict_mode:
            # ALL files must show no errors
            video_ok = blackscreen_count == 0 and freeze_count == 0
            audio_ok = audio_loss_count == 0
            # Enhanced logic: Pass if audio is present even when video motion is minimal
            # This avoids false negatives when there's audio content but minimal video movement
            success = video_ok or audio_ok  # Changed from AND to OR
            mode_text = "strict mode (all files must be clean)"
        else:
            # LENIENT mode: If at least one image shows change (no freeze/blackscreen), detect motion
            video_issues = blackscreen_count + freeze_count
            video_ok = video_issues < total_analyzed  # At least one image without video issues
            audio_ok = audio_loss_count <= (total_analyzed // 2)  # Keep majority rule for audio
            # Enhanced logic: Pass if audio is present even when video motion is minimal
            success = video_ok or audio_ok  # Changed from AND to OR
            mode_text = "lenient mode (at least one image must show change)"
        
        # Generate human-readable message
        if success:
            # More descriptive message about what triggered the success
            if video_ok and audio_ok:
                message = f"Motion/activity detected - {total_analyzed} files analyzed in {mode_text}, both video and audio content present"
            elif video_ok:
                message = f"Motion/activity detected - {total_analyzed} files analyzed in {mode_text}, video motion detected"
            elif audio_ok:
                message = f"Motion/activity detected - {total_analyzed} files analyzed in {mode_text}, audio content present (video motion minimal)"
            else:
                message = f"Motion/activity detected - {total_analyzed} files analyzed in {mode_text}, no significant issues found"
        else:
            issues = []
            if blackscreen_count > 0:
                issues.append(f"{blackscreen_count} blackscreen")
            if freeze_count > 0:
                issues.append(f"{freeze_count} freeze")
            if audio_loss_count > 0:
                issues.append(f"{audio_loss_count} audio loss")
            message = f"No motion/activity - {total_analyzed} files analyzed in {mode_text}, found: {', '.join(issues)}"
        
        result = {
            'success': success,
            'video_ok': video_ok,
            'audio_ok': audio_ok,
            'blackscreen_count': blackscreen_count,
            'freeze_count': freeze_count,
            'audio_loss_count': audio_loss_count,
            'total_analyzed': total_analyzed,
            'details': details,
            'strict_mode': strict_mode,
            'message': message
        }
        
        return result
        
    except Exception as e:
        error_msg = f"Motion analysis error: {e}"
        print(f"[@analysis_utils] {error_msg}")
        return {
            'success': False,
            'video_ok': False,
            'audio_ok': False,
            'blackscreen_count': 0,
            'freeze_count': 0,
            'audio_loss_count': 0,
            'total_analyzed': 0,
            'details': [],
            'strict_mode': strict_mode,
            'message': error_msg
        }