"""
Host Monitoring Routes

Monitoring system endpoints for capture frame listing and JSON analysis file retrieval.
"""

from flask import Blueprint, request, jsonify
from  backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id
import os
import re
import subprocess

host_monitoring_bp = Blueprint('host_monitoring', __name__, url_prefix='/host/monitoring')

@host_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """List captured frames for monitoring with URLs built like screenshots"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        limit = data.get('limit', 180)
        
        # Get AV controller to access monitoring helpers
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        # Use monitoring helpers
        result = av_controller.monitoring_helpers.list_captures(limit)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'List captures error: {str(e)}'
        }), 500

@host_monitoring_bp.route('/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file for monitoring"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        # Get AV controller to access monitoring helpers
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        # Use monitoring helpers
        result = av_controller.monitoring_helpers.get_latest_monitoring_json()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Latest JSON error: {str(e)}'
        }), 500


@host_monitoring_bp.route('/disk-usage', methods=['GET'])
def disk_usage_diagnostics():
    """
    Comprehensive disk space diagnostics for all capture directories.
    Returns detailed breakdown of segments, captures, thumbnails, and cleanup status.
    
    Query params:
        - capture_dir: Optional specific capture (e.g., 'capture1'), or 'all' for all captures (default)
    """
    try:
        capture_filter = request.args.get('capture_dir', 'all')
        
        # Get capture directories
        if capture_filter == 'all':
            capture_dirs = [
                '/var/www/html/stream/capture1',
                '/var/www/html/stream/capture2',
                '/var/www/html/stream/capture3',
                '/var/www/html/stream/capture4'
            ]
        else:
            capture_dirs = [f'/var/www/html/stream/{capture_filter}']
        
        # Filter to existing directories
        capture_dirs = [d for d in capture_dirs if os.path.exists(d)]
        
        if not capture_dirs:
            return jsonify({
                'success': False,
                'error': 'No capture directories found'
            }), 404
        
        # Overall system disk usage
        try:
            df_result = subprocess.run(
                ['df', '-h', '/var/www/html/stream'],
                capture_output=True, text=True, timeout=5
            )
            df_lines = df_result.stdout.strip().split('\n')
            if len(df_lines) >= 2:
                parts = df_lines[1].split()
                system_disk = {
                    'filesystem': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4],
                    'mounted_on': parts[5] if len(parts) > 5 else '/var/www/html/stream'
                }
            else:
                system_disk = {'error': 'Failed to parse df output'}
        except Exception as e:
            system_disk = {'error': str(e)}
        
        # Analyze each capture directory
        captures_analysis = []
        
        for capture_dir in capture_dirs:
            capture_name = os.path.basename(capture_dir)
            captures_subdir = os.path.join(capture_dir, 'captures')
            
            analysis = {
                'capture_name': capture_name,
                'path': capture_dir,
                'exists': os.path.exists(capture_dir)
            }
            
            if not analysis['exists']:
                captures_analysis.append(analysis)
                continue
            
            # Total size
            try:
                du_result = subprocess.run(
                    ['du', '-sh', capture_dir],
                    capture_output=True, text=True, timeout=10
                )
                analysis['total_size'] = du_result.stdout.split()[0] if du_result.returncode == 0 else 'unknown'
            except:
                analysis['total_size'] = 'error'
            
            # Segments analysis
            try:
                find_result = subprocess.run(
                    ['find', capture_dir, '-maxdepth', '1', '-name', 'segment_*.ts', '-type', 'f', '-printf', '%s\\n'],
                    capture_output=True, text=True, timeout=30
                )
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    sizes = [int(s) for s in find_result.stdout.strip().split('\n') if s]
                    total_bytes = sum(sizes)
                    analysis['segments'] = {
                        'count': len(sizes),
                        'size_gb': round(total_bytes / (1024**3), 2),
                        'size_bytes': total_bytes,
                        'avg_size_kb': round(total_bytes / len(sizes) / 1024, 1) if sizes else 0
                    }
                else:
                    analysis['segments'] = {'count': 0, 'size_gb': 0}
            except Exception as e:
                analysis['segments'] = {'error': str(e)}
            
            # Full-res captures analysis
            try:
                find_result = subprocess.run(
                    ['find', captures_subdir, '-name', 'capture_*[0-9].jpg', '-type', 'f', '-printf', '%s\\n'],
                    capture_output=True, text=True, timeout=30
                )
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    sizes = [int(s) for s in find_result.stdout.strip().split('\n') if s]
                    total_bytes = sum(sizes)
                    analysis['captures'] = {
                        'count': len(sizes),
                        'size_gb': round(total_bytes / (1024**3), 2),
                        'size_bytes': total_bytes,
                        'avg_size_kb': round(total_bytes / len(sizes) / 1024, 1) if sizes else 0
                    }
                else:
                    analysis['captures'] = {'count': 0, 'size_gb': 0}
            except Exception as e:
                analysis['captures'] = {'error': str(e)}
            
            # Thumbnails analysis
            try:
                find_result = subprocess.run(
                    ['find', captures_subdir, '-name', '*_thumbnail.jpg', '-type', 'f', '-printf', '%s\\n'],
                    capture_output=True, text=True, timeout=30
                )
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    sizes = [int(s) for s in find_result.stdout.strip().split('\n') if s]
                    total_bytes = sum(sizes)
                    analysis['thumbnails'] = {
                        'count': len(sizes),
                        'size_gb': round(total_bytes / (1024**3), 2),
                        'size_bytes': total_bytes,
                        'avg_size_kb': round(total_bytes / len(sizes) / 1024, 1) if sizes else 0
                    }
                else:
                    analysis['thumbnails'] = {'count': 0, 'size_gb': 0}
            except Exception as e:
                analysis['thumbnails'] = {'error': str(e)}
            
            # JSON files analysis
            try:
                find_result = subprocess.run(
                    ['find', captures_subdir, '-name', '*.json', '-type', 'f', '-printf', '%s\\n'],
                    capture_output=True, text=True, timeout=10
                )
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    sizes = [int(s) for s in find_result.stdout.strip().split('\n') if s]
                    total_bytes = sum(sizes)
                    analysis['json_files'] = {
                        'count': len(sizes),
                        'size_mb': round(total_bytes / (1024**2), 1),
                        'size_bytes': total_bytes
                    }
                else:
                    analysis['json_files'] = {'count': 0, 'size_mb': 0}
            except Exception as e:
                analysis['json_files'] = {'error': str(e)}
            
            # Transcript files analysis
            try:
                # Use find for consistency (though only ~24 files expected)
                result = subprocess.run([
                    'find', capture_dir, '-maxdepth', '1',
                    '-name', 'transcript_*.json', '-type', 'f'
                ], capture_output=True, text=True, timeout=10)
                
                transcript_files = [f for f in result.stdout.strip().split('\n') if f] if result.returncode == 0 else []
                
                if transcript_files:
                    total_bytes = sum(os.path.getsize(f) for f in transcript_files)
                    analysis['transcripts'] = {
                        'count': len(transcript_files),
                        'size_mb': round(total_bytes / (1024**2), 1),
                        'size_bytes': total_bytes
                    }
                else:
                    analysis['transcripts'] = {'count': 0, 'size_mb': 0}
            except Exception as e:
                analysis['transcripts'] = {'error': str(e)}
            
            # File age analysis - check for files older than 24h (cleanup failure indicator)
            try:
                # Segments older than 24h
                old_segments = subprocess.run(
                    ['find', capture_dir, '-maxdepth', '1', '-name', 'segment_*.ts', '-type', 'f', '-mmin', '+1440'],
                    capture_output=True, text=True, timeout=10
                )
                old_segments_count = len([l for l in old_segments.stdout.strip().split('\n') if l])
                
                # Captures older than 24h
                old_captures = subprocess.run(
                    ['find', captures_subdir, '-name', 'capture_*.jpg', '-type', 'f', '-mmin', '+1440'],
                    capture_output=True, text=True, timeout=10
                )
                old_captures_count = len([l for l in old_captures.stdout.strip().split('\n') if l])
                
                analysis['cleanup_health'] = {
                    'old_segments_24h': old_segments_count,
                    'old_captures_24h': old_captures_count,
                    'is_healthy': old_segments_count == 0 and old_captures_count == 0,
                    'warning': 'Files older than 24h found - cleanup may not be working' if (old_segments_count > 0 or old_captures_count > 0) else None
                }
            except Exception as e:
                analysis['cleanup_health'] = {'error': str(e)}
            
            captures_analysis.append(analysis)
        
        # Check cleanup status
        cleanup_status = {}
        try:
            # Check if cleanup log exists
            if os.path.exists('/tmp/clean.log'):
                with open('/tmp/clean.log', 'r') as f:
                    log_content = f.read()
                    lines = log_content.strip().split('\n')
                    cleanup_status['log_exists'] = True
                    cleanup_status['last_run'] = lines[0] if lines else None
                    cleanup_status['log_lines'] = len(lines)
            else:
                cleanup_status['log_exists'] = False
                cleanup_status['warning'] = 'Cleanup log not found'
            
            # Check cleanup processes
            ps_result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True, timeout=5
            )
            cleanup_processes = [l for l in ps_result.stdout.split('\n') if 'clean_captures' in l and 'grep' not in l]
            cleanup_status['active_processes'] = len(cleanup_processes)
            
        except Exception as e:
            cleanup_status['error'] = str(e)
        
        # Check active captures config
        config_status = {}
        try:
            if os.path.exists('/tmp/active_captures.conf'):
                with open('/tmp/active_captures.conf', 'r') as f:
                    config_dirs = [line.strip() for line in f if line.strip()]
                config_status['exists'] = True
                config_status['configured_captures'] = config_dirs
                config_status['count'] = len(config_dirs)
            else:
                config_status['exists'] = False
                config_status['warning'] = 'Config file missing - cleanup using fallback/auto-discovery'
        except Exception as e:
            config_status['error'] = str(e)
        
        # Check temp file accumulation
        temp_files_status = {}
        try:
            # Old temp directories
            old_dirs = subprocess.run(
                ['find', '/tmp', '-name', 'audio_extract_*', '-type', 'd'],
                capture_output=True, text=True, timeout=5
            )
            temp_dirs_count = len([l for l in old_dirs.stdout.strip().split('\n') if l])
            
            # Old audio files
            old_audio = subprocess.run(
                ['find', '/tmp', '-name', 'audio_*.wav', '-mmin', '+60', '-type', 'f'],
                capture_output=True, text=True, timeout=5
            )
            old_audio_count = len([l for l in old_audio.stdout.strip().split('\n') if l])
            
            # Old merged TS
            old_merged = subprocess.run(
                ['find', '/tmp', '-name', 'merged_ts_*.ts', '-mmin', '+60', '-type', 'f'],
                capture_output=True, text=True, timeout=5
            )
            old_merged_count = len([l for l in old_merged.stdout.strip().split('\n') if l])
            
            temp_files_status = {
                'leaked_temp_dirs': temp_dirs_count,
                'old_audio_files': old_audio_count,
                'old_merged_ts': old_merged_count,
                'is_healthy': temp_dirs_count == 0 and old_audio_count == 0 and old_merged_count == 0,
                'warning': 'Temp file accumulation detected' if (temp_dirs_count > 0 or old_audio_count > 0 or old_merged_count > 0) else None
            }
        except Exception as e:
            temp_files_status['error'] = str(e)
        
        # Build summary
        total_segments = sum(c.get('segments', {}).get('count', 0) for c in captures_analysis)
        total_captures = sum(c.get('captures', {}).get('count', 0) for c in captures_analysis)
        total_thumbnails = sum(c.get('thumbnails', {}).get('count', 0) for c in captures_analysis)
        
        return jsonify({
            'success': True,
            'system_disk': system_disk,
            'summary': {
                'captures_analyzed': len(captures_analysis),
                'total_segments': total_segments,
                'total_captures': total_captures,
                'total_thumbnails': total_thumbnails,
                'cleanup_healthy': all(c.get('cleanup_health', {}).get('is_healthy', False) for c in captures_analysis),
                'temp_files_healthy': temp_files_status.get('is_healthy', False)
            },
            'captures': captures_analysis,
            'cleanup_status': cleanup_status,
            'config_status': config_status,
            'temp_files_status': temp_files_status,
            'warnings': [
                c.get('cleanup_health', {}).get('warning') 
                for c in captures_analysis 
                if c.get('cleanup_health', {}).get('warning')
            ] + [
                config_status.get('warning'),
                temp_files_status.get('warning')
            ] if any([
                not config_status.get('exists'),
                not temp_files_status.get('is_healthy', True)
            ]) else []
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Disk usage diagnostics error: {str(e)}'
        }), 500
