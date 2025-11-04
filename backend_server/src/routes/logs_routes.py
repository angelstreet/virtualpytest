"""
Logs Routes - System logs and service monitoring

Provides access to systemd service logs via journalctl.
"""

from flask import Blueprint, request, jsonify
import subprocess
import os

# Create blueprint
logs_bp = Blueprint('logs', __name__, url_prefix='/server/logs')

# Allowed services (whitelist for security)
ALLOWED_SERVICES = [
    'vpt_server_host',
    'vpt_server_backend',
    'vpt_host',
    'vpt_backend'
]


@logs_bp.route('/view', methods=['POST'])
def view_logs():
    """
    View systemd service logs via journalctl
    
    Request body:
    {
        "service": "vpt_server_host",
        "lines": 50,
        "follow": false,
        "since": "1h",
        "level": "info",
        "grep": "error"
    }
    """
    try:
        data = request.get_json() or {}
        
        service = data.get('service')
        lines = data.get('lines', 50)
        follow = data.get('follow', False)
        since = data.get('since')
        level = data.get('level')
        grep_pattern = data.get('grep')
        
        # Validate service
        if not service:
            return jsonify({
                'success': False,
                'error': 'service is required',
                'available_services': ALLOWED_SERVICES
            }), 400
        
        # Security: only allow whitelisted services
        if service not in ALLOWED_SERVICES:
            return jsonify({
                'success': False,
                'error': f'Service {service} not allowed',
                'available_services': ALLOWED_SERVICES
            }), 400
        
        # Build journalctl command
        cmd = ['journalctl', '-u', f'{service}.service']
        
        # Add options
        if lines and not follow:
            cmd.extend(['-n', str(lines)])
        
        if follow:
            cmd.append('-f')
            # Note: Follow mode should be handled differently (streaming)
            return jsonify({
                'success': False,
                'error': 'Follow mode not supported via API. Use: journalctl -u {}.service -f'.format(service)
            }), 400
        
        if since:
            cmd.extend(['--since', since])
        
        if level:
            cmd.extend(['-p', level])
        
        # Execute journalctl
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            logs = result.stdout
            
            # Apply grep filter if provided
            if grep_pattern and logs:
                filtered_lines = [line for line in logs.split('\n') if grep_pattern.lower() in line.lower()]
                logs = '\n'.join(filtered_lines)
            
            return jsonify({
                'success': True,
                'service': service,
                'logs': logs,
                'lines_count': len(logs.split('\n')) if logs else 0,
                'command': ' '.join(cmd)
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'journalctl command timed out'
            }), 500
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'error': 'journalctl not found. Is this a systemd system?'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Logs view error: {str(e)}'
        }), 500


@logs_bp.route('/services', methods=['GET'])
def list_services():
    """List available VirtualPyTest services"""
    try:
        # Check which services exist
        available = []
        
        for service in ALLOWED_SERVICES:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', f'{service}.service'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                status = result.stdout.strip()
                available.append({
                    'name': service,
                    'status': status,
                    'active': status == 'active'
                })
            except Exception:
                continue
        
        return jsonify({
            'success': True,
            'services': available,
            'count': len(available)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'List services error: {str(e)}'
        }), 500

