"""
Settings Management Routes

API endpoints for managing non-sensitive system configuration.
Allows safe editing of .env files without exposing credentials.
"""

from flask import Blueprint, request, jsonify
import os
import re
from datetime import datetime

server_settings_bp = Blueprint('server_settings', __name__, url_prefix='/server/settings')

# =====================================================
# CONFIGURATION WHITELISTS
# =====================================================

# Fields that are safe to expose and edit
SAFE_FIELDS = {
    'server': [
        'SERVER_NAME',
        'SERVER_URL',
        'SERVER_PORT',
        'ENVIRONMENT',
        'DEBUG',
        'PYTHONUNBUFFERED',
    ],
    'frontend': [
        'VITE_SERVER_URL',
        'VITE_SLAVE_SERVER_URL',
        'VITE_GRAFANA_URL',
        'VITE_CLOUDFLARE_R2_PUBLIC_URL',
        'VITE_DEV_MODE',
    ],
    'host': [
        'HOST_NAME',
        'HOST_PORT',
        'HOST_URL',
        'HOST_API_URL',
    ],
    'device_fields': [
        'NAME',
        'MODEL',
        'VIDEO',
        'VIDEO_STREAM_PATH',
        'VIDEO_CAPTURE_PATH',
        'VIDEO_FPS',
        'VIDEO_AUDIO',
        'IP',
        'PORT',
        'POWER_NAME',
        'POWER_IP',
    ]
}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from backend_server/src/routes to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    return project_root

def get_env_paths():
    """Get paths to all .env files"""
    project_root = get_project_root()
    return {
        'server': os.path.join(project_root, '.env'),
        'frontend': os.path.join(project_root, 'frontend', '.env'),
        'host': os.path.join(project_root, 'backend_host', 'src', '.env'),
    }

def parse_env_file(file_path):
    """
    Parse .env file and return dict of key-value pairs.
    Preserves comments and empty lines for writing back.
    """
    if not os.path.exists(file_path):
        return {}
    
    env_dict = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if match:
                key = match.group(1)
                value = match.group(2)
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_dict[key] = value
    
    return env_dict

def write_env_file(file_path, env_dict, backup=True):
    """
    Write environment dictionary to .env file.
    Preserves file structure and only updates specified keys.
    """
    if not os.path.exists(file_path):
        # Create new file
        with open(file_path, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        return True
    
    # Backup existing file
    if backup:
        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(file_path, 'r') as src:
            with open(backup_path, 'w') as dst:
                dst.write(src.read())
        print(f"[@settings] Backed up {file_path} to {backup_path}")
    
    # Read existing file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Update values
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        
        # Preserve comments and empty lines
        if not stripped or stripped.startswith('#'):
            updated_lines.append(line)
            continue
        
        # Check if this is a key=value line
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', stripped)
        if match:
            key = match.group(1)
            if key in env_dict:
                # Update this value
                updated_lines.append(f"{key}={env_dict[key]}\n")
                updated_keys.add(key)
            else:
                # Keep original line
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add any new keys that weren't in the file
    for key, value in env_dict.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back
    with open(file_path, 'w') as f:
        f.writelines(updated_lines)
    
    return True

def extract_safe_config(env_dict, safe_fields):
    """Extract only whitelisted fields from environment dict"""
    return {k: v for k, v in env_dict.items() if k in safe_fields}

def extract_device_configs(env_dict):
    """Extract device configurations (DEVICE1_*, DEVICE2_*, etc.)"""
    devices = {}
    device_pattern = re.compile(r'^DEVICE(\d+)_(.+)$')
    
    for key, value in env_dict.items():
        match = device_pattern.match(key)
        if match:
            device_num = match.group(1)
            field = match.group(2)
            
            # Only include whitelisted device fields
            if field in SAFE_FIELDS['device_fields']:
                device_key = f"DEVICE{device_num}"
                if device_key not in devices:
                    devices[device_key] = {}
                devices[device_key][f"DEVICE_{field}"] = value
    
    return devices

# =====================================================
# API ENDPOINTS
# =====================================================

@server_settings_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get non-sensitive configuration from all .env files.
    Returns structured JSON with server, frontend, host, and devices config.
    """
    try:
        env_paths = get_env_paths()
        
        # Read server config (root .env)
        server_env = parse_env_file(env_paths['server'])
        server_config = extract_safe_config(server_env, SAFE_FIELDS['server'])
        
        # Read frontend config
        frontend_env = parse_env_file(env_paths['frontend'])
        frontend_config = extract_safe_config(frontend_env, SAFE_FIELDS['frontend'])
        
        # Read host config
        host_env = parse_env_file(env_paths['host'])
        host_config = extract_safe_config(host_env, SAFE_FIELDS['host'])
        
        # Extract device configurations
        devices = extract_device_configs(host_env)
        
        return jsonify({
            'server': server_config,
            'frontend': frontend_config,
            'host': host_config,
            'devices': devices
        })
        
    except Exception as e:
        print(f"[@settings] Error loading config: {e}")
        return jsonify({'error': str(e)}), 500

@server_settings_bp.route('/config', methods=['POST'])
def update_config():
    """
    Update non-sensitive configuration in .env files.
    Only updates whitelisted fields, preserving all sensitive data.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        env_paths = get_env_paths()
        updated_files = []
        
        # Update server config
        if 'server' in data:
            server_updates = {k: v for k, v in data['server'].items() 
                            if k in SAFE_FIELDS['server']}
            if server_updates:
                write_env_file(env_paths['server'], server_updates)
                updated_files.append('server')
        
        # Update frontend config
        if 'frontend' in data:
            frontend_updates = {k: v for k, v in data['frontend'].items() 
                              if k in SAFE_FIELDS['frontend']}
            if frontend_updates:
                write_env_file(env_paths['frontend'], frontend_updates)
                updated_files.append('frontend')
        
        # Update host config
        if 'host' in data or 'devices' in data:
            host_updates = {}
            
            # Basic host fields
            if 'host' in data:
                host_updates.update({k: v for k, v in data['host'].items() 
                                   if k in SAFE_FIELDS['host']})
            
            # Device configurations
            if 'devices' in data:
                for device_key, device_data in data['devices'].items():
                    # Extract device number (e.g., "DEVICE1" -> "1")
                    device_match = re.match(r'^DEVICE(\d+)$', device_key)
                    if not device_match:
                        continue
                    
                    device_num = device_match.group(1)
                    
                    # Add all safe device fields
                    for field_key, field_value in device_data.items():
                        # Convert DEVICE_NAME to DEVICE1_NAME format
                        field_match = re.match(r'^DEVICE_(.+)$', field_key)
                        if field_match:
                            field_suffix = field_match.group(1)
                            if field_suffix in SAFE_FIELDS['device_fields']:
                                full_key = f"DEVICE{device_num}_{field_suffix}"
                                host_updates[full_key] = field_value
            
            if host_updates:
                write_env_file(env_paths['host'], host_updates)
                updated_files.append('host')
        
        return jsonify({
            'success': True,
            'updated_files': updated_files,
            'message': 'Configuration updated successfully'
        })
        
    except Exception as e:
        print(f"[@settings] Error updating config: {e}")
        return jsonify({'error': str(e)}), 500

@server_settings_bp.route('/backup', methods=['POST'])
def backup_config():
    """Create manual backup of all .env files"""
    try:
        env_paths = get_env_paths()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backed_up = []
        
        for service, path in env_paths.items():
            if os.path.exists(path):
                backup_path = f"{path}.backup.{timestamp}"
                with open(path, 'r') as src:
                    with open(backup_path, 'w') as dst:
                        dst.write(src.read())
                backed_up.append(service)
        
        return jsonify({
            'success': True,
            'backed_up': backed_up,
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"[@settings] Error creating backup: {e}")
        return jsonify({'error': str(e)}), 500

