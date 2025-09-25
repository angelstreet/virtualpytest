"""
Device Flags Routes - Minimal implementation for device clustering/tagging
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.utils.supabase_utils import get_supabase_client

# Create blueprint
device_flags_bp = Blueprint('device_flags', __name__, url_prefix='/server/device-flags')

@device_flags_bp.route('/', methods=['GET'])
def get_all_device_flags():
    """Get all device flags"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('device_flags').select('*').execute()
        
        return jsonify({
            'success': True,
            'data': result.data
        }), 200
        
    except Exception as e:
        print(f"❌ [device_flags] Error fetching device flags: {e}")
        return jsonify({'error': str(e)}), 500

@device_flags_bp.route('/<host_name>/<device_id>', methods=['PUT'])
def update_device_flags(host_name, device_id):
    """Update flags for a specific device"""
    try:
        data = request.get_json()
        flags = data.get('flags', [])
        
        if not isinstance(flags, list):
            return jsonify({'error': 'flags must be an array'}), 400
        
        supabase = get_supabase_client()
        
        # Update flags
        result = supabase.table('device_flags').update({
            'flags': flags,
            'updated_at': 'now()'
        }).eq('host_name', host_name).eq('device_id', device_id).execute()
        
        if not result.data:
            return jsonify({'error': 'Device not found'}), 404
        
        return jsonify({
            'success': True,
            'data': result.data[0]
        }), 200
        
    except Exception as e:
        print(f"❌ [device_flags] Error updating device flags: {e}")
        return jsonify({'error': str(e)}), 500

@device_flags_bp.route('/batch', methods=['GET'])
def get_batch_device_flags():
    """Get both device flags and unique flags in one request"""
    try:
        supabase = get_supabase_client()
        
        # Get all device flags
        device_flags_result = supabase.table('device_flags').select('*').execute()
        device_flags = device_flags_result.data
        
        # Extract unique flags from all devices
        unique_flags = set()
        for row in device_flags:
            flags = row.get('flags', [])
            if flags:
                unique_flags.update(flags)
        
        return jsonify({
            'success': True,
            'data': {
                'device_flags': device_flags,
                'unique_flags': sorted(list(unique_flags))
            }
        }), 200
        
    except Exception as e:
        print(f"❌ [device_flags] Error fetching batch device flags: {e}")
        return jsonify({'error': str(e)}), 500

@device_flags_bp.route('/flags', methods=['GET'])
def get_unique_flags():
    """Get all unique flags across all devices"""
    try:
        supabase = get_supabase_client()
        
        # Get all flags and flatten them
        result = supabase.table('device_flags').select('flags').execute()
        
        unique_flags = set()
        for row in result.data:
            flags = row.get('flags', [])
            if flags:
                unique_flags.update(flags)
        
        return jsonify({
            'success': True,
            'data': sorted(list(unique_flags))
        }), 200
        
    except Exception as e:
        print(f"❌ [device_flags] Error fetching unique flags: {e}")
        return jsonify({'error': str(e)}), 500

def upsert_device_on_registration(host_name: str, device_id: str, device_name: str):
    """Auto-insert device into flags table during registration"""
    try:
        supabase = get_supabase_client()
        
        # Use upsert to insert or update
        supabase.table('device_flags').upsert({
            'host_name': host_name,
            'device_id': device_id,
            'device_name': device_name,
            'flags': []
        }, on_conflict='host_name,device_id').execute()
        
        print(f"✅ [device_flags] Auto-registered device: {host_name}/{device_id}")
        
    except Exception as e:
        print(f"❌ [device_flags] Error auto-registering device: {e}")
