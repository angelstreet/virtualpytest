"""
Host Verification Routes

This module contains the host-side verification API endpoints that:
- List available verification references
- Provide status information for verification system
"""

import os
import json
import time
import threading
from flask import Blueprint, request, jsonify, current_app
from backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id

# Create blueprint
host_verification_bp = Blueprint('host_verification', __name__, url_prefix='/host/verification')

# =====================================================
# HOST-SIDE VERIFICATION ENDPOINTS
# =====================================================

@host_verification_bp.route('/getStatus', methods=['GET'])
def verification_status():
    """Get verification system status."""
    try:
        # Get device_id from query params (defaults to device1)
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@route:verification_status] Getting verification system status for device: {device_id}")
        
        # Get device info
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check available controllers for this device
        available_controllers = []
        
        # Check AV controller
        av_controller = get_controller(device_id, 'av')
        if av_controller:
            available_controllers.append('av')
        
        # Check remote controller
        remote_controller = get_controller(device_id, 'remote')
        if remote_controller:
            available_controllers.append('remote')
        
        # Check verification controllers
        for verification_type in ['verification_image', 'verification_text', 'verification_adb']:
            controller = get_controller(device_id, verification_type)
            if controller:
                available_controllers.append(verification_type)
        
        print(f"[@route:verification_status] Available controllers for device {device_id}: {available_controllers}")
        
        return jsonify({
            'success': True,
            'status': 'ready',
            'controllers_available': available_controllers,
            'message': 'Verification system is ready',
            'host_connected': True,
            'device_id': device_id,
            'device_model': device.device_model,
            'device_name': device.device_name
        })
        
    except Exception as e:
        print(f"[@route:verification_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Verification status error: {str(e)}'
        }), 500

@host_verification_bp.route('/executeBatch', methods=['POST'])
def verification_execute_batch():
    """Execute batch of verifications using device's VerificationExecutor - always async"""
    try:
        print("[@route:host_verification:verification_execute_batch] Starting batch verification execution")
        
        # Get request data
        data = request.get_json() or {}
        verifications = data.get('verifications', [])
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        image_source_url = data.get('image_source_url')
        tree_id = data.get('tree_id')
        node_id = data.get('node_id')
        
        # Extract userinterface_name (MANDATORY for reference resolution)
        userinterface_name = verifications[0].get('userinterface_name') if verifications else None
        
        print(f"[@route:host_verification:verification_execute_batch] Processing {len(verifications)} verifications for device: {device_id}, team: {team_id}, userinterface: {userinterface_name}")
        
        # Validate
        if not verifications:
            return jsonify({'success': False, 'error': 'verifications are required'}), 400
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
            
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required for reference resolution'}), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has verification_executor
        if not hasattr(device, 'verification_executor') or not device.verification_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have VerificationExecutor initialized'
            }), 500
        
        # Always execute asynchronously to prevent HTTP timeouts
        # Generate execution ID
        import uuid
        import threading
        import time
        execution_id = str(uuid.uuid4())
        
        # Store execution state
        if not hasattr(device.verification_executor, '_executions'):
            device.verification_executor._executions = {}
            device.verification_executor._lock = threading.Lock()
        
        with device.verification_executor._lock:
            device.verification_executor._executions[execution_id] = {
                'execution_id': execution_id,
                'status': 'running',
                'result': None,
                'error': None,
                'start_time': time.time(),
                'progress': 0,
                'message': 'Verification execution starting...'
            }
        
        # Start execution in background thread
        thread = threading.Thread(
            target=_execute_verifications_thread,
            args=(device, execution_id, verifications, userinterface_name, image_source_url, team_id, tree_id, node_id),
            daemon=True
        )
        thread.start()
        
        print(f"[@route:host_verification:verification_execute_batch] Async execution started: {execution_id}")
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Verification execution started'
        })
        
    except Exception as e:
        print(f"[@route:host_verification:verification_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host verification execution failed: {str(e)}'
        }), 500

@host_verification_bp.route('/execution/<execution_id>/status', methods=['GET'])
def verification_execution_status(execution_id):
    """Get status of async verification execution"""
    try:
        # Get query parameters
        device_id = request.args.get('device_id', 'device1')
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has verification_executor
        if not hasattr(device, 'verification_executor') or not device.verification_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have VerificationExecutor initialized'
            }), 500
        
        # Get execution status
        status = device.verification_executor.get_execution_status(execution_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"[@route:host_verification:execution_status] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
        }), 500

# ========================================
# BACKGROUND EXECUTION THREAD
# ========================================

def _execute_verifications_thread(
    device,
    execution_id: str,
    verifications: list,
    userinterface_name: str,
    image_source_url: str,
    team_id: str,
    tree_id: str,
    node_id: str
):
    """Execute verifications in background thread with progress tracking"""
    import sys
    import io
    import time
    
    # Capture logs for verification execution
    log_buffer = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, data):
            for stream in self.streams:
                stream.write(data)
                stream.flush()
        def flush(self):
            for stream in self.streams:
                stream.flush()
    
    try:
        # Redirect stdout/stderr to BOTH terminal and buffer
        sys.stdout = Tee(old_stdout, log_buffer)
        sys.stderr = Tee(old_stderr, log_buffer)
        
        # Update status
        with device.verification_executor._lock:
            device.verification_executor._executions[execution_id]['message'] = 'Executing verifications...'
            device.verification_executor._executions[execution_id]['progress'] = 50
        
        # Execute verifications (synchronous call in background thread)
        result = device.verification_executor.execute_verifications(
            verifications=verifications,
            userinterface_name=userinterface_name,
            image_source_url=image_source_url,
            team_id=team_id,
            tree_id=tree_id,
            node_id=node_id
        )
        
        # Stop log capture and add logs to result
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        captured_logs = log_buffer.getvalue()
        if captured_logs:
            result['logs'] = captured_logs
        
        # Update with result
        with device.verification_executor._lock:
            if result.get('success'):
                device.verification_executor._executions[execution_id]['status'] = 'completed'
                device.verification_executor._executions[execution_id]['result'] = result
                device.verification_executor._executions[execution_id]['progress'] = 100
                device.verification_executor._executions[execution_id]['message'] = 'Verification execution completed'
            else:
                device.verification_executor._executions[execution_id]['status'] = 'error'
                device.verification_executor._executions[execution_id]['error'] = result.get('error', 'Verification execution failed')
                device.verification_executor._executions[execution_id]['result'] = result
                device.verification_executor._executions[execution_id]['progress'] = 100
                device.verification_executor._executions[execution_id]['message'] = 'Verification execution failed'
    
    except Exception as e:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Update with error
        with device.verification_executor._lock:
            device.verification_executor._executions[execution_id]['status'] = 'error'
            device.verification_executor._executions[execution_id]['error'] = str(e)
            device.verification_executor._executions[execution_id]['progress'] = 100
            device.verification_executor._executions[execution_id]['message'] = f'Verification execution error: {str(e)}'
    finally:
        # Always restore stdout/stderr
        if sys.stdout != old_stdout:
            sys.stdout = old_stdout
        if sys.stderr != old_stderr:
            sys.stderr = old_stderr
