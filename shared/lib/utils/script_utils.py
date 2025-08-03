"""
Script execution utilities following existing patterns from adb_utils and appium_utils
"""
import os
import sys
import subprocess
import uuid
import time  # Add missing time import
from typing import Tuple, Dict, Any, Optional, List

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/lib/utils
lib_dir = os.path.dirname(current_dir)  # /shared/lib
shared_dir = os.path.dirname(lib_dir)  # /shared
project_root = os.path.dirname(shared_dir)  # /virtualpytest

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import existing utilities
from .app_utils import load_environment_variables
from .host_utils import get_host_instance, list_available_devices, get_controller
from .lock_utils import is_device_locked, lock_device, unlock_device


def load_navigation_tree(userinterface_name: str, script_name: str = "script") -> Dict[str, Any]:
    """
    Load navigation tree using direct database access (no HTTP requests).
    This populates the cache and is required before calling pathfinding functions.
    
    Args:
        userinterface_name: trface (e.g., 'horizon_android_mobile')
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with success status and tree data or error
    """
    try:
        team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        
        from shared.lib.supabase.userinterface_db import get_all_userinterfaces
        
        userinterfaces = get_all_userinterfaces(team_id)
        if not userinterfaces:
            return {'success': False, 'error': "No userinterfaces found"}
        
        userinterface = next((ui for ui in userinterfaces if ui['name'] == userinterface_name), None)
        if not userinterface:
            return {'success': False, 'error': f"User interface '{userinterface_name}' not found"}
        
        userinterface_id = userinterface['id']
        
        # Use the same approach as NavigationEditor - call the working API endpoint
        from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
        
        # Get the root tree for this user interface (same as navigation page)
        tree = get_root_tree_for_interface(userinterface_id, team_id)
        
        if not tree:
            return {'success': False, 'error': f"No root tree found for interface: {userinterface_id}"}
        
        # Get full tree data with nodes and edges (same as navigation page)
        tree_data = get_full_tree(tree['id'], team_id)
        
        if not tree_data['success']:
            return {'success': False, 'error': f"Failed to load tree data: {tree_data.get('error', 'Unknown error')}"}
        
        tree_id = tree['id']
        nodes = tree_data['nodes']
        edges = tree_data['edges']
        
        return {
            'success': True,
            'tree': {
                'id': tree_id,
                'name': tree.get('name', ''),
                'metadata': {
                    'nodes': nodes,
                    'edges': edges
                }
            },
            'tree_id': tree_id,
            'userinterface_id': userinterface_id,
            'nodes': nodes,
            'edges': edges
        }
        
    except Exception as e:
        return {'success': False, 'error': f"Error loading navigation tree: {str(e)}"}


def setup_script_environment(script_name: str = "script") -> Dict[str, Any]:
    """
    Setup script environment by loading configuration and creating host instance.
    Reuses existing host_utils and app_utils infrastructure.
    
    Args:
        script_name: Name of the script for logging
        
    Returns:
        Dictionary containing host, team_id, and other configuration
    """
    print(f"[@script_utils:setup_script_environment] Setting up environment for {script_name}...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate to project root and then to backend_host/src/.env
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    env_path = os.path.join(project_root, 'backend_host', 'src', '.env')
    
    print(f"[@script_utils:setup_script_environment] Looking for .env at: {env_path}")
    
    if os.path.exists(env_path):
        print(f"[@script_utils:setup_script_environment] Found .env file, loading environment variables")
        load_environment_variables(mode='host', calling_script_dir=os.path.dirname(env_path))
    else:
        print(f"[@script_utils:setup_script_environment] ERROR: .env file not found at {env_path}")
        return {'success': False, 'error': f'.env file not found at {env_path}'}
    
    # Check if critical environment variables are set
    host_name = os.getenv('HOST_NAME')
    print(f"[@script_utils:setup_script_environment] HOST_NAME from environment: {host_name}")
    
    device1_name = os.getenv('DEVICE1_NAME')
    print(f"[@script_utils:setup_script_environment] DEVICE1_NAME from environment: {device1_name}")
    
    try:
        print(f"[@script_utils:setup_script_environment] Creating host instance...")
        host = get_host_instance()
        
        device_count = host.get_device_count()
        print(f"[@script_utils:setup_script_environment] Host created with {device_count} devices")
        
        if device_count == 0:
            return {'success': False, 'error': 'No devices configured'}
        
        # List available devices for debugging
        devices = host.get_devices()
        for device in devices:
            print(f"[@script_utils:setup_script_environment] Found device: {device.device_name} ({device.device_model})")
        
    except Exception as e:
        import traceback
        print(f"[@script_utils:setup_script_environment] ERROR: Failed to create host: {e}")
        traceback.print_exc()
        return {'success': False, 'error': f'Failed to create host: {e}'}
    
    team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    
    return {
        'success': True,
        'host': host,
        'team_id': team_id,
        'script_name': script_name
    }


def select_device(host, device_id: Optional[str] = None, script_name: str = "script") -> Dict[str, Any]:
    """
    Select a device from the host, either specified or first available.
    
    Args:
        host: Host instance
        device_id: Optional specific device ID to select
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with selected device or error
    """
    print(f"[@script_utils:select_device] Selecting device for {script_name}...")
    available_devices = [d.device_id for d in host.get_devices()]
    print(f"[@script_utils:select_device] Available devices: {available_devices}")
    
    if device_id:
        print(f"[@script_utils:select_device] Requested device: {device_id}")
        selected_device = next((d for d in host.get_devices() if d.device_id == device_id), None)
        if not selected_device:
            error_msg = f"Device {device_id} not found. Available: {available_devices}"
            print(f"[@script_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
    else:
        devices = host.get_devices()
        if not devices:
            error_msg = "No devices available"
            print(f"[@script_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
        selected_device = devices[0]
        print(f"[@script_utils:select_device] No device specified, using first available: {selected_device.device_id}")
    
    print(f"[@script_utils:select_device] Selected device: {selected_device.device_name} ({selected_device.device_model}) [{selected_device.device_id}]")
    return {'success': True, 'device': selected_device}


def take_device_control(host, device, script_name: str = "script") -> Dict[str, Any]:
    """
    Take control of a device using existing lock_utils.
    
    Args:
        host: Host instance
        device: Device instance
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with session_id or error
    """
    device_key = f"{host.host_name}:{device.device_id}"
    
    if is_device_locked(device_key):
        return {'success': False, 'error': f"Device {device.device_id} is locked by another process"}
    
    session_id = str(uuid.uuid4())
    
    if not lock_device(device_key, session_id):
        return {'success': False, 'error': f"Failed to take control of device {device.device_id}"}
    
    return {'success': True, 'session_id': session_id, 'device_key': device_key}


def release_device_control(device_key: str, session_id: str, script_name: str = "script") -> bool:
    """
    Release control of a device using existing lock_utils.
    
    Args:
        device_key: Device key in format "hostname:device_id"
        session_id: Session ID from take_device_control
        script_name: Name of the script for logging
        
    Returns:
        True if successful, False otherwise
    """
    try:
        unlock_device(device_key, session_id)
        return True
    except Exception:
        return False


def execute_action_directly(host, device, action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an action directly using controller-specific abstraction.
    
    Args:
        host: Host instance
        device: Device instance
        action: Action dictionary with 'command' and 'params'
        
    Returns:
        Dictionary with success status and execution details
    """
    try:
        command = action.get('command')
        params = action.get('params', {})
        
        remote_controller = get_controller(device.device_id, 'remote')
        if not remote_controller:
            return {
                'success': False,
                'error': f'No remote controller found for device {device.device_id}'
            }
        
        success = remote_controller.execute_command(command, params)
        
        return {
            'success': success,
            'message': f'{"Successfully executed" if success else "Failed to execute"} {command}'
        }
            
    except Exception as e:
        return {'success': False, 'error': f'Action execution error: {str(e)}'}


def execute_verification_directly(host, device, verification: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a verification directly using controller-specific abstraction.
    
    Args:
        host: Host instance
        device: Device instance
        verification: Verification dictionary with 'verification_type' and other params
        
    Returns:
        Dictionary with success status and verification results
    """
    try:
        verification_type = verification.get('verification_type', 'adb')
        
        verification_controller = get_controller(device.device_id, f'verification_{verification_type}')
        if not verification_controller:
            return {
                'success': False,
                'error': f'No {verification_type} verification controller found for device {device.device_id}'
            }
        
        result = verification_controller.execute_verification(verification)
        
        return {
            'success': result.get('success', False),
            'message': result.get('message', 'Verification completed'),
            'verification_type': verification_type,
            'resultType': 'PASS' if result.get('success') else 'FAIL'
        }
            
    except Exception as e:
        import traceback
        print(f"[@script_utils:execute_verification_directly] ERROR: {str(e)}")
        print(f"[@script_utils:execute_verification_directly] TRACEBACK: {traceback.format_exc()}")
        return {'success': False, 'error': f'Verification execution error: {str(e)}'}


def execute_navigation_with_verifications(host, device, transition: Dict[str, Any], team_id: str, tree_id: str = None, script_result_id: str = None, script_context: str = 'script') -> Dict[str, Any]:
    """
    Execute a single navigation step with verifications following NavigationExecutor pattern.
    
    This function mimics the NavigationExecutor.execute_navigation() behavior:
    1. Execute navigation actions using ActionExecutor pattern
    2. Execute target node verifications using VerificationExecutor pattern
    3. Record execution results to database (same as server-side NavigationExecutor)
    
    Args:
        host: Host instance
        device: Device instance
        transition: Navigation transition with actions and verifications
        team_id: Team ID for database recording
        tree_id: Tree ID for database recording (should be UUID)
        
    Returns:
        Dictionary with execution results including verification results
    """
    try:
        start_time = time.time()
        
        actions = transition.get('actions', [])
        retry_actions = transition.get('retryActions', [])
        
        remote_controller = get_controller(device.device_id, 'remote')
        if not remote_controller:
            return {
                'success': False,
                'error': f'No remote controller found for device {device.device_id}',
                'verification_results': []
            }
        
        action_start_time = time.time()
        actions_success = remote_controller.execute_sequence(actions, retry_actions)
        action_execution_time = int((time.time() - action_start_time) * 1000)
        
        if tree_id and actions:
            try:
                from shared.lib.supabase.execution_results_db import record_edge_execution
                edge_id = transition.get('edge_id', 'unknown')
                record_edge_execution(
                    team_id=team_id,
                    tree_id=tree_id,
                    edge_id=edge_id,
                    host_name=host.host_name,
                    device_model=device.device_model,
                    success=actions_success,
                    execution_time_ms=action_execution_time,
                    message='Navigation actions completed' if actions_success else 'Navigation actions failed',
                    error_details={'error': 'Action execution failed'} if not actions_success else None,
                    script_result_id=script_result_id,
                    script_context=script_context
                )
            except Exception:
                pass  # Silent fail as per optimization
        
        if not actions_success:
            return {
                'success': False,
                'error': 'Navigation actions failed',
                'message': 'Navigation step failed during action execution',
                'verification_results': []
            }
        
        verifications = transition.get('verifications', [])
        verification_results = []
        
        for i, verification in enumerate(verifications):
            verification_start_time = time.time()
            verify_result = execute_verification_directly(host, device, verification)
            verification_execution_time = int((time.time() - verification_start_time) * 1000)
            
            if tree_id:
                try:
                    from shared.lib.supabase.execution_results_db import record_node_execution
                    node_id = transition.get('to_node_id', 'unknown')
                    record_node_execution(
                        team_id=team_id,
                        tree_id=tree_id,
                        node_id=node_id,
                        host_name=host.host_name,
                        success=verify_result.get('success', False),
                        execution_time_ms=verification_execution_time,
                        message=verify_result.get('message', 'Verification completed'),
                        error_details={'error': verify_result.get('error')} if verify_result.get('error') else None,
                        script_result_id=script_result_id,
                        script_context=script_context
                    )
                except Exception:
                    pass
            
            verification_result = {
                'verification_number': i + 1,
                'verification_type': verification.get('verification_type', 'adb'),
                'success': verify_result.get('success', False),
                'message': verify_result.get('message', 'Verification completed'),
                'resultType': 'PASS' if verify_result.get('success') else 'FAIL',
                'error': verify_result.get('error') if not verify_result.get('success') else None
            }
            verification_results.append(verification_result)
            
            if not verify_result['success']:
                return {
                    'success': False,
                    'error': f'Verification {i+1} failed: {verify_result.get("error", "Unknown error")}',
                    'message': 'Navigation step failed during verification',
                    'verification_results': verification_results
                }
        
        execution_time = time.time() - start_time
        
        return {
            'success': True,
            'message': 'Navigation step with verifications completed successfully',
            'verification_results': verification_results,
            'verifications_executed': len(verifications),
            'execution_time': execution_time
        }
        
    except Exception as e:
        import traceback
        print(f"[@script_utils:execute_navigation_with_verifications] ERROR: {str(e)}")
        print(f"[@script_utils:execute_navigation_with_verifications] TRACEBACK: {traceback.format_exc()}")
        return {
            'success': False, 
            'error': f'Navigation step with verifications execution error: {str(e)}',
            'verification_results': []
        }

def capture_validation_screenshot(host, device: Any, step_name: str, script_name: str = "validation") -> str:
    """
    Capture screenshot for validation reporting using AV controller directly.
    No HTTP requests needed - uses controller abstraction.
    
    Args:
        host: Host instance (not dict)
        device: Device object
        step_name: Name of the step (e.g., "initial_state", "step_1", "final_state")
        script_name: Name of the script for logging
        
    Returns:
        Local path to captured screenshot or empty string if failed
    """
    try:
        av_controller = get_controller(device.device_id, 'av')
        
        screenshot_path = av_controller.take_screenshot()
        
        
        return screenshot_path
            
    except Exception:
        return "" 

# Script folder configuration - single source of truth
def get_scripts_directory() -> str:
    """Get the scripts directory path - single source of truth"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/lib/utils
    lib_dir = os.path.dirname(current_dir)  # /shared/lib
    shared_dir = os.path.dirname(lib_dir)  # /shared
    project_root = os.path.dirname(shared_dir)  # /virtualpytest
    
    # Use test_scripts folder as the primary scripts location
    return os.path.join(project_root, 'test_scripts')

def get_script_path(script_name: str) -> str:
    """Get full path to a script file"""
    scripts_dir = get_scripts_directory()
    script_path = os.path.join(scripts_dir, f'{script_name}.py')
    
    if not os.path.exists(script_path):
        raise ValueError(f'Script not found: {script_path}')
    
    return script_path

def list_available_scripts() -> list:
    """List all available Python scripts in the scripts directory"""
    import glob
    
    scripts_dir = get_scripts_directory()
    
    if not os.path.exists(scripts_dir):
        return []
    
    # Find all Python files in the scripts directory
    script_pattern = os.path.join(scripts_dir, '*.py')
    script_files = glob.glob(script_pattern)
    
    # Extract just the filenames without path and extension
    available_scripts = []
    for script_file in script_files:
        filename = os.path.basename(script_file)
        script_name = os.path.splitext(filename)[0]  # Remove .py extension
        available_scripts.append(script_name)
    
    # Sort alphabetically
    available_scripts.sort()
    
    return available_scripts

# Add back simplified execute_command
def execute_command(command: str, timeout: int = 30) -> Tuple[bool, str, str, int]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode
        
        return success, stdout, stderr, exit_code
        
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out", -1
    except Exception as e:
        return False, "", str(e), -1

# Enhanced execute_script with report generation using shared report_utils function
def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    start_time = time.time()
    
    try:
        script_path = get_script_path(script_name)
        
        hostname = os.getenv('HOST_NAME', 'localhost')
        
        # Build command with parameters
        base_command = f"bash -c 'source /home/{hostname}/myvenv/bin/activate && python {script_path}"
        
        if parameters and parameters.strip():
            # Add parameters to the command
            command = f"{base_command} {parameters.strip()}'"
        else:
            command = f"{base_command}'"
        
        success, stdout, stderr, exit_code = execute_command(command, timeout=300)  # Increased timeout
        
        total_execution_time = int((time.time() - start_time) * 1000)
        
        # Generate and upload report using shared function
        report_url = ""
        try:
            # Get device and host info
            device_info = get_device_info_for_report(device_id)
            host_info = get_host_info_for_report()
            
            # Use shared report generation function (same as validation.py)
            from .report_utils import generate_and_upload_script_report
            
            report_url = generate_and_upload_script_report(
                script_name=f'{script_name}.py',
                device_info=device_info,
                host_info=host_info,
                execution_time=total_execution_time,
                success=success,
                step_results=None,  # Simple script execution, no steps
                screenshot_paths=None,  # No screenshots for simple scripts
                error_message=stderr if not success else "",
                userinterface_name="",
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                parameters=parameters
            )
            
        except Exception as e:
            print(f"[@utils:script_utils:execute_script] Report generation error: {str(e)}")
        
        return {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'script_name': script_name,
            'device_id': device_id,
            'script_path': script_path,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': report_url  # Add report URL to response
        }
        
    except Exception as e:
        total_execution_time = int((time.time() - start_time) * 1000)
        
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': ""
        }

def get_device_info_for_report(device_id: str) -> Dict[str, Any]:
    """Get device information for report generation"""
    try:
        from .host_utils import get_device_by_id
        device = get_device_by_id(device_id)
        
        if device:
            return {
                'device_name': device.device_name,
                'device_model': device.device_model,
                'device_id': device.device_id
            }
        else:
            return {
                'device_name': f'Device {device_id}',
                'device_model': 'Unknown Model',
                'device_id': device_id
            }
    except Exception:
        return {
            'device_name': f'Device {device_id}',
            'device_model': 'Unknown Model', 
            'device_id': device_id
        }

def get_host_info_for_report() -> Dict[str, Any]:
    """Get host information for report generation"""
    try:
        from .host_utils import get_host_instance
        host = get_host_instance()
        
        if host:
            return {
                'host_name': host.host_name
            }
        else:
            hostname = os.getenv('HOST_NAME', 'localhost')
            return {
                'host_name': hostname
            }
    except Exception:
        hostname = os.getenv('HOST_NAME', 'localhost')
        return {
            'host_name': hostname
        }


def find_action_edges_from_node(node_id: str, edges: List[Dict]) -> List[Dict]:
    """
    Find all edges from a specific node (simple filter).
    
    Args:
        node_id: Source node ID to find edges from
        edges: List of edge dictionaries from loaded tree data
        
    Returns:
        List of edges originating from the specified node
    """
    return [edge for edge in edges if edge.get('source_node_id') == node_id]


def find_node_by_label(nodes: List[Dict], label: str) -> Dict:
    """
    Find node by its label in a generic way.
    
    Args:
        nodes: List of node dictionaries
        label: Node label to search for
        
    Returns:
        Node dictionary with the matching label, or None if not found
    """
    for node in nodes:
        if node.get('label') == label:
            return node
    return None


def find_edges_from_node(source_node_id: str, edges: List[Dict]) -> List[Dict]:
    """
    Find all edges originating from a specific node (generic version).
    
    Args:
        source_node_id: Source node ID
        edges: List of edge dictionaries
        
    Returns:
        List of edges originating from the specified node
    """
    return [edge for edge in edges if edge.get('source_node_id') == source_node_id]


def find_edge_by_target_label(source_node_id: str, edges: List[Dict], nodes: List[Dict], target_label: str) -> Dict:
    """
    Find edge from source node to a target node with specific label.
    This is the proper generic way to find action edges.
    
    Args:
        source_node_id: Source node ID
        edges: List of edge dictionaries
        nodes: List of node dictionaries  
        target_label: Label of target node to find
        
    Returns:
        Edge dictionary going to target node with specified label, or None if not found
    """
    # First find the target node by label
    target_node = find_node_by_label(nodes, target_label)
    if not target_node:
        return None
    
    target_node_id = target_node.get('node_id')
    if not target_node_id:
        return None
    
    # Find edge from source to target
    source_edges = find_edges_from_node(source_node_id, edges)
    for edge in source_edges:
        if edge.get('target_node_id') == target_node_id:
            return edge
    
    return None


def find_edge_with_action_command(node_id: str, edges: List[Dict], action_command: str) -> Dict:
    """
    Find edge from node_id that contains the specified action command in its action sets.
    
    Args:
        node_id: Source node ID
        edges: List of edge dictionaries 
        action_command: Action command to search for (e.g., 'tap_coordinates', 'press_key')
        
    Returns:
        Edge dictionary containing the action, or None if not found
    """
    source_edges = find_edges_from_node(node_id, edges)
    
    for edge in source_edges:
        action_sets = edge.get('action_sets', [])
        for action_set in action_sets:
            actions = action_set.get('actions', [])
            for action in actions:
                if action.get('command') == action_command:
                    return edge
    
    return None


def get_node_sub_trees_with_actions(node_id: str, tree_id: str, team_id: str) -> Dict:
    """Get all sub-trees for a node and return their nodes and edges for action checking."""
    from shared.lib.supabase.navigation_trees_db import get_node_sub_trees, get_full_tree
    
    # Get sub-trees for this node
    sub_trees_result = get_node_sub_trees(tree_id, node_id, team_id)
    if not sub_trees_result.get('success'):
        return {'success': False, 'error': sub_trees_result.get('error'), 'sub_trees': [], 'all_nodes': [], 'all_edges': []}
    
    sub_trees = sub_trees_result.get('sub_trees', [])
    all_nodes = []
    all_edges = []
    
    # Load nodes and edges from all sub-trees
    for sub_tree in sub_trees:
        sub_tree_id = sub_tree.get('id')
        if sub_tree_id:
            tree_data = get_full_tree(sub_tree_id, team_id)
            if tree_data.get('success'):
                all_nodes.extend(tree_data.get('nodes', []))
                all_edges.extend(tree_data.get('edges', []))
    
    return {
        'success': True,
        'sub_trees': sub_trees,
        'all_nodes': all_nodes,
        'all_edges': all_edges
    }

def find_action_in_nested_trees(source_node_id: str, tree_id: str, nodes: List[Dict], edges: List[Dict], action_command: str, team_id: str) -> Dict:
    """Find action in main tree and sub-trees of the specific source node only."""
    
    # First check in the main tree
    action_edge = find_edge_by_target_label(source_node_id, edges, nodes, action_command)
    if action_edge:
        return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
    
    action_edge = find_edge_with_action_command(source_node_id, edges, action_command)
    if action_edge:
        return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
    
    # Check sub-trees for this specific node only
    print(f"🔍 [script_utils] Checking sub-trees for node: {source_node_id}")
    sub_trees_data = get_node_sub_trees_with_actions(source_node_id, tree_id, team_id)
    
    if not sub_trees_data.get('success') or not sub_trees_data.get('sub_trees'):
        print(f"🔍 [script_utils] Node {source_node_id} has no sub-trees")
        return {'success': False, 'error': f"Action '{action_command}' not found in main tree and node has no sub-trees"}
    
    sub_nodes = sub_trees_data.get('all_nodes', [])
    sub_edges = sub_trees_data.get('all_edges', [])
    sub_trees = sub_trees_data.get('sub_trees', [])
    
    print(f"🔍 [script_utils] Found {len(sub_trees)} sub-trees with {len(sub_nodes)} nodes and {len(sub_edges)} edges")
    
    # Simple search: try to find action in any sub-tree node
    for node in sub_nodes:
        node_id = node.get('node_id')
        if node_id:
            # Check by target label
            sub_action_edge = find_edge_by_target_label(node_id, sub_edges, sub_nodes, action_command)
            if sub_action_edge:
                return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
            
            # Check by action command
            sub_action_edge = find_edge_with_action_command(node_id, sub_edges, action_command)
            if sub_action_edge:
                return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
    
    return {'success': False, 'error': f"Action '{action_command}' not found in main tree or sub-trees"}

def execute_edge_actions(host, device, edge: Dict, action_set_id: str = None, team_id: str = 'default') -> Dict:
    """
    Execute edge actions using ActionExecutor - same as frontend useAction hook.
    
    Args:
        host: Host instance 
        device: Device instance
        edge: Edge dictionary with action_sets
        action_set_id: Optional specific action set ID to execute (uses default if None)
        team_id: Team ID for database recording
        
    Returns:
        Execution result dictionary with success status and details
    """
    try:
        from backend_core.src.services.actions.action_executor import ActionExecutor
        
        # Get action set (specific or default)
        action_sets = edge.get('action_sets', [])
        default_action_set_id = edge.get('default_action_set_id')
        
        if action_set_id:
            # Find specific action set by ID
            action_set = next((s for s in action_sets if s.get('id') == action_set_id), None)
        else:
            # Use default action set
            action_set = next((s for s in action_sets if s.get('id') == default_action_set_id), 
                            action_sets[0] if action_sets else None)
        
        if not action_set:
            return {
                'success': False, 
                'error': f'Action set not found (looking for: {action_set_id or default_action_set_id})'
            }
        
        print(f"[@script_utils:execute_edge_actions] Executing action set: {action_set.get('label', action_set.get('id'))}")
        print(f"[@script_utils:execute_edge_actions] Actions: {len(action_set.get('actions', []))}, Retry actions: {len(action_set.get('retry_actions', []))}")
        
        # Convert host to dict format if needed (ActionExecutor expects dict)
        host_dict = host.__dict__ if hasattr(host, '__dict__') else host
        
        # Use ActionExecutor exactly like the API route does
        action_executor = ActionExecutor(
            host=host_dict,
            device_id=device.device_id,
            tree_id=None,  # Not needed for direct action execution
            edge_id=edge.get('edge_id'),
            team_id=team_id
        )
        
        result = action_executor.execute_actions(
            actions=action_set.get('actions', []),
            retry_actions=action_set.get('retry_actions', [])
        )
        
        print(f"[@script_utils:execute_edge_actions] Execution completed: success={result.get('success')}")
        return result
        
    except Exception as e:
        error_msg = f'Edge action execution failed: {str(e)}'
        print(f"[@script_utils:execute_edge_actions] ERROR: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }