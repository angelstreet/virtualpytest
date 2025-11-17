"""
Standardized Verification Executor

This module provides a standardized way to execute verifications that can be used by:
- Python code directly (navigation execution, scripts, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The core logic is the same as /server/verification/executeBatch but available as a reusable class.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from shared.src.lib.database.execution_results_db import record_node_execution


class VerificationExecutor:
    """
    Standardized verification executor that provides consistent verification execution
    across Python code and API endpoints.
    
    CRITICAL: Do not create new instances directly! Use device.verification_executor instead.
    Each device has a singleton VerificationExecutor that preserves navigation context.
    """
    
    @classmethod
    def get_for_device(cls, device):
        """
        Factory method to get the device's existing VerificationExecutor.
        
        RECOMMENDED: Use device.verification_executor directly instead of this method.
        
        Args:
            device: Device instance
            
        Returns:
            The device's existing VerificationExecutor instance
            
        Raises:
            ValueError: If device doesn't have a verification_executor
        """
        if not hasattr(device, 'verification_executor') or not device.verification_executor:
            raise ValueError(f"Device {device.device_id} does not have a VerificationExecutor. "
                           "VerificationExecutors are created during device initialization.")
        return device.verification_executor
    
    def __init__(self, device, tree_id: str = None, node_id: str = None, _from_device_init: bool = False):
        """
        Initialize VerificationExecutor
        
        Args:
            device: Device instance (mandatory, contains host_name and device_id)
            tree_id: Tree ID for navigation context
            node_id: Node ID for navigation context
            _from_device_init: Internal flag to indicate creation from device initialization
        """
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        if not _from_device_init:
            import traceback
            print(f"⚠️ [VerificationExecutor] WARNING: Creating new VerificationExecutor instance for device {device.device_id}")
            print(f"⚠️ [VerificationExecutor] This may cause state loss! Use device.verification_executor instead.")
            print(f"⚠️ [VerificationExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:  # Show last 2 stack frames
                print(f"⚠️ [VerificationExecutor]   {line.strip()}")
        
        # Store instances directly
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        self.device_name = device.device_name

        # Get AV controller directly from device for screenshot capture
        self.av_controller = device._get_controller('av')
        if not self.av_controller:
            print(f"[@verification_executor] Warning: No AV controller found for device {self.device_id}")
        
        # Get verification controllers directly by type
        verification_controllers = device.get_controllers('verification')
        
        # ALSO get web and desktop controllers (they have built-in verification methods)
        web_controllers = device.get_controllers('web')
        desktop_controllers = device.get_controllers('desktop')
        
        # Combine all controllers that support verifications
        all_controllers = verification_controllers + web_controllers + desktop_controllers
        
        self.video_controller = None
        self.image_controller = None
        self.text_controller = None
        self.audio_controller = None
        self.adb_controller = None
        self.appium_controller = None
        self.web_controller = None
        self.desktop_controller = None
        
        for ctrl in all_controllers:
            class_name = ctrl.__class__.__name__.lower()
            if 'video' in class_name:
                self.video_controller = ctrl
            elif 'image' in class_name:
                self.image_controller = ctrl
            elif 'text' in class_name:
                self.text_controller = ctrl
            elif 'audio' in class_name:
                self.audio_controller = ctrl
            elif 'adb' in class_name:
                self.adb_controller = ctrl
            elif 'appium' in class_name:
                self.appium_controller = ctrl
            elif 'playwright' in class_name or 'web' in class_name:
                self.web_controller = ctrl
            elif 'desktop' in class_name or 'bash' in class_name or 'pyautogui' in class_name:
                self.desktop_controller = ctrl
        
        # Initialize screenshot tracking
        self.verification_screenshots = []
        
        # Initialized for device: {self.device_id}, model: {self.device_model}
    
    def take_screenshot(self) -> Tuple[bool, str, str]:
        """
        Take a screenshot and return base64 data for AI analysis.
        
        Returns:
            tuple: (success, base64_screenshot_data, error_message)
        """
        try:
            # Use remote controller for base64 screenshot data
            remote_controller = self.device._get_controller('remote')
            if not remote_controller:
                return False, "", "No remote controller available"
            
            if not hasattr(remote_controller, 'take_screenshot'):
                return False, "", "Remote controller does not support screenshots"
            
            print(f"[@verification_executor] Taking screenshot using remote controller: {type(remote_controller).__name__}")
            return remote_controller.take_screenshot()
            
        except Exception as e:
            error_msg = f"Screenshot error: {str(e)}"
            print(f"[@verification_executor] {error_msg}")
            return False, "", error_msg
    
    def get_available_context(self, userinterface_name: str = None) -> Dict[str, Any]:
        """
        Get available verification context for AI based on user interface
        
        Args:
            userinterface_name: User interface name for context
            
        Returns:
            Dict with available verifications and their descriptions
        """
        try:
            device_verifications = []
            
            print(f"[@verification_executor] Loading verification context for device: {self.device_id}, model: {self.device_model}")
            
            # Get verification actions from verification controllers AND web controller
            verification_types = ['image', 'text', 'adb', 'appium', 'video', 'audio', 'web', 'desktop']
            for v_type in verification_types:
                try:
                    controller = getattr(self, f'{v_type}_controller', None)
                    if controller and hasattr(controller, 'get_available_verifications'):
                        verifications = controller.get_available_verifications()
                        if isinstance(verifications, list):
                            for verification in verifications:
                                device_verifications.append({
                                    'command': verification.get('command', ''),
                                    'action_type': f'verification_{v_type}',
                                    'params': verification.get('params', {}),
                                    'description': verification.get('description', '')
                                })
                except Exception as e:
                    print(f"[@verification_executor] Could not load verification_{v_type} verifications: {e}")
                    continue
            
            print(f"[@verification_executor] Loaded {len(device_verifications)} verifications from controllers")
            
            return {
                'service_type': 'verifications',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'available_verifications': device_verifications
            }
            
        except Exception as e:
            print(f"[@verification_executor] Error loading verification context: {e}")
            return {
                'service_type': 'verifications',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'available_verifications': []
            }
    
    async def execute_verifications(self, 
                            verifications: List[Dict[str, Any]],
                            userinterface_name: str,  # MANDATORY for reference resolution
                            image_source_url: Optional[str] = None,
                            team_id: str = None,
                            context = None,
                            tree_id: Optional[str] = None,
                            node_id: Optional[str] = None,
                            verification_pass_condition: str = None  # Auto-detect if not provided
                           ) -> Dict[str, Any]:
        """
        Execute batch of verifications (PURE - no log capture)
        
        Args:
            verifications: List of verification dictionaries
            userinterface_name: User interface name (REQUIRED for reference resolution, e.g., 'horizon_android_tv')
            image_source_url: Optional source image URL for image/text verifications
            team_id: Team ID for database recording
            context: Optional execution context
            tree_id: Navigation tree ID for database recording
            node_id: Navigation node ID for database recording
            verification_pass_condition: Condition for passing ('all' or 'any'). If None, auto-detects from verifications data.
            
        Returns:
            Dict with success status, results, and execution statistics
        """
        # Auto-detect verification_pass_condition from verifications if not explicitly provided
        if verification_pass_condition is None:
            if verifications and isinstance(verifications[0], dict) and 'verification_pass_condition' in verifications[0]:
                verification_pass_condition = verifications[0]['verification_pass_condition']
                print(f"[@lib:verification_executor:execute_verifications] Auto-detected pass_condition from verification data: '{verification_pass_condition}'")
            else:
                verification_pass_condition = 'all'  # Default
                print(f"[@lib:verification_executor:execute_verifications] Using default pass_condition: 'all' (not found in verification data)")
        
        # Reduced logging for cleaner output during KPI scans
        
        # Clear screenshots from previous verification batch (VerificationExecutor is a singleton per device)
        self.verification_screenshots = []
        
        # Validate inputs
        if not verifications:
            return {
                'success': True,
                'message': 'No verifications to execute',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        # Filter valid verifications
        valid_verifications = self._filter_valid_verifications(verifications)
        
        if not valid_verifications:
            return {
                'success': False,
                'error': 'All verifications were invalid and filtered out',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        results = []
        passed_count = 0
        
        # Execute each verification
        for i, verification in enumerate(valid_verifications):
            verification_type = verification.get('verification_type', 'text')
            
            start_time = time.time()
            result = await self._execute_single_verification(verification, userinterface_name, image_source_url, context, team_id)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Add execution time to result
            result['execution_time_ms'] = execution_time
            results.append(result)
            
            # Count successful verifications
            if result.get('success'):
                passed_count += 1
            
            # Record execution directly to database
            self._record_verification_to_database(
                success=result.get('success', False),
                execution_time_ms=execution_time,
                message=result.get('message', ''),
                error_details={'error': result.get('error')} if result.get('error') else None,
                team_id=team_id,
                tree_id=tree_id,
                node_id=node_id
            )


        
        # Calculate overall success based on verification_pass_condition
        if verification_pass_condition == 'any':
            # Pass if ANY verification passed (at least one)
            overall_success = passed_count > 0
            print(f"[@lib:verification_executor:execute_verifications] 'any can pass' mode: {passed_count}/{len(valid_verifications)} passed → {'✅ PASS' if overall_success else '❌ FAIL'}")
        else:
            # Default: Pass only if ALL verifications passed
            overall_success = passed_count == len(valid_verifications)
            print(f"[@lib:verification_executor:execute_verifications] 'all must pass' mode: {passed_count}/{len(valid_verifications)} passed → {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        # Generate debug report ONLY if BATCH failed (not for individual failures)
        # This prevents unnecessary reports when "any can pass" mode allows batch to succeed
        debug_report_path = None
        debug_report_url = None
        if not overall_success:
            # Find first failed verification that has report config stored
            for result in results:
                if not result.get('success', False) and '_report_config' in result:
                    print(f"[@lib:verification_executor] " + "=" * 80)
                    print(f"[@lib:verification_executor] 🔍 BATCH FAILED - GENERATING DEBUG REPORT FOR FIRST FAILURE")
                    print(f"[@lib:verification_executor] " + "=" * 80)
                    try:
                        from shared.src.lib.utils.verification_report_generator import generate_verification_failure_report
                        from shared.src.lib.utils.storage_path_utils import get_capture_folder
                        from backend_host.src.lib.utils.host_utils import get_host_instance
                        
                        verification_config = result['_report_config']
                        details = result.get('details', {})
                        
                        # Get device folder from AV controller
                        device_folder = get_capture_folder(self.av_controller.video_capture_path)
                        print(f"[@lib:verification_executor] Device folder from AV controller: {device_folder}")
                        
                        # Get host info for URL building
                        host = get_host_instance()
                        host_info = {
                            'host_name': host.host_name,
                            'host_url': host.host_url
                        }
                        print(f"[@lib:verification_executor] Host info for report: {host_info}")
                        
                        # Get source_image_path from result details
                        source_path = None
                        print(f"[@lib:verification_executor] Details dict has {len(details)} keys: {list(details.keys())}")
                        
                        if 'source_image_path' in details:
                            source_path = details['source_image_path']
                            print(f"[@lib:verification_executor] ✅ Found source_image_path in details: {source_path}")
                        elif 'source_image_path' in verification_config:
                            source_path = verification_config['source_image_path']
                            print(f"[@lib:verification_executor] ✅ Found source_image_path in config: {source_path}")
                        else:
                            print(f"[@lib:verification_executor] ❌ source_image_path not found!")
                        
                        if source_path and device_folder:
                            # Add source_image_path to verification_config for report generator
                            verification_config_with_path = {**verification_config, 'source_image_path': source_path}
                            
                            # Generate report
                            report_path = generate_verification_failure_report(
                                verification_config=verification_config_with_path,
                                verification_result=result,
                                device_folder=device_folder,
                                host_info=host_info
                            )
                            if report_path:
                                debug_report_path = report_path
                                print(f"[@lib:verification_executor] " + "-" * 80)
                                print(f"[@lib:verification_executor] 🔍 DEBUG REPORT (local): {report_path}")
                                
                                # Convert local path to URL for frontend
                                from shared.src.lib.utils.build_url_utils import buildHostImageUrl
                                debug_report_url = buildHostImageUrl(host_info, report_path)
                                
                                print(f"[@lib:verification_executor] 🔍 DEBUG REPORT (URL): {debug_report_url}")
                                print(f"[@lib:verification_executor] " + "-" * 80)
                                
                                # Store in result for later use
                                result['debug_report_path'] = report_path
                                result['debug_report_url'] = debug_report_url
                            else:
                                print(f"[@lib:verification_executor] ⚠️ Report generation returned None")
                        else:
                            if not source_path:
                                print(f"[@lib:verification_executor] ⚠️ Source path not found - cannot generate report")
                            if not device_folder:
                                print(f"[@lib:verification_executor] ⚠️ Device folder is None - cannot generate report")
                        
                        print(f"[@lib:verification_executor] " + "=" * 80)
                    except Exception as report_error:
                        print(f"[@lib:verification_executor] ❌ Failed to generate debug report: {report_error}")
                        import traceback
                        traceback.print_exc()
                        print(f"[@lib:verification_executor] " + "=" * 80)
                    
                    # Only generate report for first failure
                    break
        
        # Extract detailed error information from failed verifications
        error_info = None
        if not overall_success and results:
            # Get the first failed verification's message as the primary error
            for result in results:
                if not result.get('success', False):
                    error_info = result.get('message', 'Verification failed')
                    # Debug report paths already set above (lines 311-395)
                    break
        
        # Collect all verification evidence for KPI report
        verification_evidence_list = []
        for result in results:
            if 'verification_evidence' in result:
                verification_evidence_list.append(result['verification_evidence'])
        
        result = {
            'success': overall_success,
            'total_count': len(valid_verifications),
            'passed_count': passed_count,
            'failed_count': len(valid_verifications) - passed_count,
            'results': results,
            'verification_screenshots': self.verification_screenshots,  # NEW: Include screenshots
            'verification_evidence_list': verification_evidence_list,  # ✅ NEW: All verification evidence for KPI
            'message': f'Batch verification completed: {passed_count}/{len(valid_verifications)} passed'
        }
        
        # Add error information if verifications failed
        if error_info:
            result['error'] = error_info
            # ✅ Include debug report path and URL if available
            if debug_report_path:
                result['debug_report_path'] = debug_report_path
            if debug_report_url:
                result['debug_report_url'] = debug_report_url
            
        return result
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of async verification execution (called by route polling).
        
        Returns:
            {
                'success': bool,
                'execution_id': str,
                'status': 'running' | 'completed' | 'error',
                'result': dict (if completed),
                'error': str (if error),
                'progress': int,
                'message': str
            }
        """
        import threading
        if not hasattr(self, '_executions'):
            return {
                'success': False,
                'error': f'Execution {execution_id} not found'
            }
        
        if not hasattr(self, '_lock'):
            self._lock = threading.Lock()
        
        with self._lock:
            if execution_id not in self._executions:
                return {
                    'success': False,
                    'error': f'Execution {execution_id} not found'
                }
            
            execution = self._executions[execution_id].copy()
        
        return {
            'success': True,
            'execution_id': execution['execution_id'],
            'status': execution['status'],
            'result': execution.get('result'),
            'error': execution.get('error'),
            'progress': execution.get('progress', 0),
            'message': execution.get('message', ''),
            'elapsed_time_ms': int((time.time() - execution['start_time']) * 1000)
        }
    
    async def verify_node(self, node_id: str, userinterface_name: str, team_id: str, tree_id: str = None, image_source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute verifications for a specific node during navigation.
        
        Args:
            node_id: Node ID to verify
            userinterface_name: User interface name (REQUIRED for reference resolution)
            team_id: Team ID
            tree_id: Optional tree ID (will fall back to navigation context if not provided)
            image_source_url: Optional image source URL
            
        Returns:
            Dict with success status and verification results
        """
        print(f"[@lib:verification_executor:verify_node] 🔍 Called with node_id={node_id}, userinterface_name={userinterface_name}, tree_id={tree_id}, team_id={team_id}")
        
        try:
            # Get tree_id from navigation context if not provided (use root tree for unified graph)
            if not tree_id:
                nav_context = self.device.navigation_context
                tree_id = nav_context.get('tree_id')  # Use root tree_id, not current_tree_id
                print(f"[@lib:verification_executor:verify_node] Tree ID from context: {tree_id}")
            
            # ✅ USE ALREADY-LOADED UNIFIED GRAPH (zero database calls, zero cache calls!)
            # NavigationExecutor already loaded the unified graph during navigation
            if not hasattr(self.device, 'navigation_executor') or not self.device.navigation_executor:
                raise ValueError(f"Device {self.device_id} has no NavigationExecutor - cannot verify")
            
            unified_graph = self.device.navigation_executor.unified_graph
            if not unified_graph:
                raise ValueError(f"NavigationExecutor has no unified graph loaded - call load_navigation_tree() first")
            
            print(f"[@lib:verification_executor:verify_node] ✅ Using unified graph from NavigationExecutor ({len(unified_graph.nodes)} nodes)")
            
            # Get node data from unified graph
            if node_id not in unified_graph.nodes:
                print(f"[@lib:verification_executor:verify_node] ⚠️ Node {node_id} not in graph - skipping verification")
                return {'success': False, 'has_verifications': False, 'message': 'Node not found in graph', 'results': []}
            
            node_data = unified_graph.nodes[node_id]
            
            if not node_data:
                print(f"[@lib:verification_executor:verify_node] ⚠️ Node {node_id} has no data - skipping verification")
                return {'success': False, 'has_verifications': False, 'message': 'Node not found in graph', 'results': []}
            
            print(f"[@lib:verification_executor:verify_node] ✅ Node data from graph: {node_data.get('label')} (tree: {node_data.get('tree_name')})")
            
            # Extract verifications from node
            verifications = node_data.get('verifications', [])
            
            if not verifications:
                print(f"[@lib:verification_executor:verify_node] No verifications for node {node_id}")
                return {'success': False, 'has_verifications': False, 'message': 'No verifications defined - cannot verify position', 'results': []}
            
            # Extract verification_pass_condition from node (defaults to 'all')
            # Priority: 1) first verification's pass_condition, 2) node's pass_condition, 3) default 'all'
            if verifications and isinstance(verifications[0], dict) and 'verification_pass_condition' in verifications[0]:
                verification_pass_condition = verifications[0]['verification_pass_condition']
                print(f"[@lib:verification_executor:verify_node] Using pass_condition from verification data: '{verification_pass_condition}'")
            else:
                verification_pass_condition = node_data.get('verification_pass_condition', 'all')
                print(f"[@lib:verification_executor:verify_node] Using pass_condition from node data: '{verification_pass_condition}' (not embedded in verifications)")
            
            print(f"[@lib:verification_executor:verify_node] Executing {len(verifications)} verifications for node {node_id} with condition '{verification_pass_condition}'")
            
            # Use actual node's tree_id for database recording (nested tree)
            actual_tree_id = node_data.get('tree_id')
            
            # Execute verifications with proper tree_id and node_id for database recording
            return await self.execute_verifications(
                verifications=verifications,
                userinterface_name=userinterface_name,  # MANDATORY parameter
                image_source_url=image_source_url,
                team_id=team_id,
                tree_id=actual_tree_id,  # Use node's actual tree_id for recording
                node_id=node_id,
                verification_pass_condition=verification_pass_condition  # NEW: Pass condition from node
            )
            
        except Exception as e:
            print(f"[@lib:verification_executor:verify_node] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'results': []}
    
    def _filter_valid_verifications(self, verifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out invalid verifications"""
        valid_verifications = []
        
        for i, verification in enumerate(verifications):
            verification_type = verification.get('verification_type', 'text')
            
            if not verification.get('command') or verification.get('command', '').strip() == '':
                print(f"[@lib:verification_executor:_filter_valid_verifications] Removing verification {i}: No command specified")
                continue
            
            # Type-specific validation
            if verification_type == 'image':
                if not verification.get('params', {}).get('image_path'):
                    print(f"[@lib:verification_executor:_filter_valid_verifications] Removing verification {i}: No image reference specified")
                    continue
            elif verification_type == 'text':
                if not verification.get('params', {}).get('text'):
                    print(f"[@lib:verification_executor:_filter_valid_verifications] Removing verification {i}: No text specified")
                    continue
            elif verification_type == 'adb':
                if not verification.get('params', {}).get('search_term'):
                    print(f"[@lib:verification_executor:_filter_valid_verifications] Removing verification {i}: No search term specified")
                    continue
            
            valid_verifications.append(verification)
        
        return valid_verifications
    
    async def _execute_single_verification(self, verification: Dict[str, Any], userinterface_name: str, image_source_url: Optional[str], context = None, team_id: str = None) -> Dict[str, Any]:
        """Execute a single verification and return standardized result"""
        try:
            verification_type = verification.get('verification_type', 'text')
            
            # Get verification controller directly
            controller = getattr(self, f'{verification_type}_controller', None)
            if not controller:
                return {
                    'success': False,
                    'error': f'No {verification_type} verification controller found for device {self.device_id}',
                    'verification_type': verification_type,
                    'resultType': 'FAIL'
                }
            
            # Execute verification directly using controller
            verification_config = {
                'command': verification.get('command'),
                'params': verification.get('params', {}),
                'verification_type': verification_type,
                'team_id': team_id,  # Pass team_id for database operations
                'userinterface_name': userinterface_name  # Use mandatory parameter (no fallback)
            }
            
            # Add source_image_path to config if provided (for offline/post-processing)
            if image_source_url:
                import os
                from shared.src.lib.utils.build_url_utils import convertHostUrlToLocalPath
                
                # Helper function to check if path needs conversion
                def needs_conversion(path):
                    """Check if path is a URL that needs conversion (vs already a local path)"""
                    # Only convert HTTP URLs - all local file paths (including /tmp/) should pass through
                    return path.startswith(('http://', 'https://'))
                
                # Handle comma-separated paths (for multiple images in subtitle/audio detection)
                if isinstance(image_source_url, str) and ',' in image_source_url:
                    # Split comma-separated paths and convert each if needed
                    paths = [path.strip() for path in image_source_url.split(',')]
                    processed_paths = []
                    for path in paths:
                        if needs_conversion(path):
                            try:
                                converted_path = convertHostUrlToLocalPath(path)
                                processed_paths.append(converted_path)
                                print(f"[@lib:verification_executor:_execute_single_verification] Converted URL: {path} -> {converted_path}")
                            except Exception as e:
                                print(f"[@lib:verification_executor:_execute_single_verification] Warning: Failed to convert path {path}: {e}")
                        else:
                            # Already a local path, use as-is
                            processed_paths.append(path)
                    
                    if processed_paths:
                        source_image_path = ','.join(processed_paths)
                        verification_config['source_image_path'] = source_image_path
                        print(f"[@lib:verification_executor:_execute_single_verification] Using {len(processed_paths)} image path(s)")
                    else:
                        print(f"[@lib:verification_executor:_execute_single_verification] Warning: No valid paths available")
                else:
                    # Single path
                    if needs_conversion(image_source_url):
                        source_image_path = convertHostUrlToLocalPath(image_source_url)
                        verification_config['source_image_path'] = source_image_path
                    else:
                        # Already a local path, use as-is
                        verification_config['source_image_path'] = image_source_url
            
            # Set context on controller so helpers can access it (for motion image collection)
            if context:
                controller._current_context = context
            
            # Direct controller execution - handle both async (Playwright) and sync (ADB, Image, Text) controllers
            import inspect
            import asyncio
            
            if inspect.iscoroutinefunction(controller.execute_verification):
                # Async controller (e.g., Playwright)
                verification_result = await controller.execute_verification(verification_config)
            else:
                # Sync controller (e.g., ADB, Image, Text)
                verification_result = controller.execute_verification(verification_config)
            
            # Build URLs from file paths if verification generated images
            # Frontend will process these paths using buildVerificationResultUrl from buildUrlUtils.ts
            details = verification_result.get('details', {})
            if details.get('source_image_path'):
                verification_result['sourceUrl'] = details['source_image_path']  # Local path - frontend converts to URL
            if details.get('reference_image_url'):
                verification_result['referenceUrl'] = details['reference_image_url']  # Already R2 URL
            if details.get('result_overlay_path'):
                verification_result['overlayUrl'] = details['result_overlay_path']  # Local path - frontend converts to URL
            
            # Capture screenshot (no upload)
            from shared.src.lib.utils.device_utils import capture_screenshot
            screenshot_path = capture_screenshot(self.device, context) or ""
            
            # Add screenshot to collection for report
            if screenshot_path:
                self.verification_screenshots.append(screenshot_path)
            
            # Build verification evidence for KPI report (NEW)
            verification_evidence = {
                'type': verification_type,
                'command': verification.get('command'),
                'success': verification_result.get('success', False),
                'params': verification.get('params', {}),
            }
            
            # Add type-specific evidence
            if verification_type == 'image':
                verification_evidence.update({
                    'reference_image_path': details.get('reference_image_path'),  # Local cropped reference
                    'source_image_path': details.get('source_image_path'),  # Local cropped source
                    'threshold': verification_result.get('threshold', 0.8),
                    'matching_score': verification_result.get('matching_result', 0.0),
                    'search_area': verification.get('params', {}).get('area'),
                    'image_filter': verification_result.get('imageFilter', 'none'),
                })
            elif verification_type == 'text':
                verification_evidence.update({
                    'source_image_path': details.get('source_image_path'),
                    'searched_text': verification_result.get('searchedText', ''),
                    'extracted_text': verification_result.get('extractedText', ''),
                    'language': verification_result.get('detected_language', 'unknown'),
                    'confidence': verification_result.get('language_confidence', 0),
                })
            
            flattened_result = {
                'success': verification_result.get('success', False),
                'message': verification_result.get('message'),
                'error': verification_result.get('error'),
                'threshold': verification_result.get('threshold') or verification_result.get('confidence') or verification_result.get('userThreshold', 0.8),
                'matching_result': verification_result.get('matching_result'),  # ✅ Add for report generator
                'resultType': 'PASS' if verification_result.get('success', False) else 'FAIL',
                'sourceImageUrl': verification_result.get('sourceUrl'),
                'referenceImageUrl': verification_result.get('referenceUrl'),
                'resultOverlayUrl': verification_result.get('overlayUrl'),
                'extractedText': verification_result.get('extractedText', ''),
                'searchedText': verification_result.get('searchedText', ''),
                'imageFilter': verification_result.get('imageFilter', 'none'),
                'detectedLanguage': verification_result.get('detected_language'),
                'languageConfidence': verification_result.get('language_confidence'),
                # ADB-specific fields
                'search_term': verification_result.get('search_term'),
                'wait_time': verification_result.get('wait_time'),
                'total_matches': verification_result.get('total_matches'),
                'matches': verification_result.get('matches'),
                # Appium-specific fields
                'platform': verification_result.get('platform'),
                # Audio/Video-specific fields  
                'motion_threshold': verification_result.get('motion_threshold'),
                'duration': verification_result.get('duration'),
                'frequency': verification_result.get('frequency'),
                'audio_level': verification_result.get('audio_level'),
                # General fields
                'verification_type': verification_result.get('verification_type', verification_type),
                'execution_time_ms': verification_result.get('execution_time_ms'),
                'details': verification_result.get('details', {}),
                'screenshot_path': screenshot_path,  # Always present
                'verification_evidence': verification_evidence,  # ✅ NEW: Evidence data for KPI report
                'output_data': verification_result.get('output_data', {})  # ✅ Include output_data from controller (getMenuInfo, etc.)
            }
            
            # Clean up context reference to avoid memory leaks
            if hasattr(controller, '_current_context'):
                delattr(controller, '_current_context')
            
            # Store failure details for potential debug report generation later (after batch evaluation)
            # Debug reports will only be generated if the BATCH fails
            if not flattened_result.get('success') and verification_type in ['image', 'text']:
                # Store config and result for potential report generation
                flattened_result['_report_config'] = verification_config
                flattened_result['_report_details'] = flattened_result.get('details', {})
            
            return flattened_result
            
        except Exception as e:
            # EXCEPTION HANDLER: This should only trigger for unexpected crashes, not normal verification failures
            # Normal failures should return {'success': False} from the controller, not throw exceptions
            print(f"[@lib:verification_executor:_execute_single_verification] ⚠️ UNEXPECTED EXCEPTION in verification:")
            print(f"[@lib:verification_executor:_execute_single_verification]   Verification type: {verification.get('verification_type', 'unknown')}")
            print(f"[@lib:verification_executor:_execute_single_verification]   Command: {verification.get('command', 'unknown')}")
            print(f"[@lib:verification_executor:_execute_single_verification]   Exception: {str(e)}")
            print(f"[@lib:verification_executor:_execute_single_verification]   Full traceback:")
            import traceback
            traceback.print_exc()
            
            # Capture error screenshot but DON'T add to validation context (use context=None)
            # This screenshot is for debugging the exception, not for the validation report
            from shared.src.lib.utils.device_utils import capture_screenshot
            screenshot_path = capture_screenshot(self.device, context=None) or ""
            
            # Add to internal collection for debugging, but it won't appear in validation report
            if screenshot_path:
                self.verification_screenshots.append(screenshot_path)
                print(f"[@lib:verification_executor:_execute_single_verification] 📸 Exception screenshot captured (for debugging, not validation report): {screenshot_path}")
            
            return {
                'success': False,
                'message': f"Verification execution failed with exception",
                'error': str(e),
                'verification_type': verification.get('verification_type', 'unknown'),
                'resultType': 'FAIL',
                'screenshot_path': screenshot_path  # Always present
            }
    
    def _record_verification_to_database(self, success: bool, execution_time_ms: int, message: str, error_details: Optional[Dict] = None, team_id: str = None, tree_id: Optional[str] = None, node_id: Optional[str] = None):
        """Record single verification directly to database"""
        try:
            # Get navigation context from device
            nav_context = self.device.navigation_context
            
            # Use provided tree_id/node_id if available, otherwise fall back to navigation context
            if not tree_id:  # Handles None and empty string
                tree_id = nav_context.get('current_tree_id')
            if not node_id:  # Handles None and empty string
                node_id = nav_context.get('current_node_id')
            
            # Only record if we have valid tree_id, node_id, and team_id (not None or empty string)
            if not tree_id or not node_id:
                print(f"[@lib:verification_executor:_record_verification_to_database] Skipping database recording - missing navigation context (tree_id: {tree_id}, node_id: {node_id})")
                return
            
            if team_id is None:
                print(f"[@lib:verification_executor:_record_verification_to_database] Skipping database recording - missing team_id")
                return
            
            # Get script context from device navigation_context - single source of truth
            script_result_id = nav_context.get('script_id')
            script_context = nav_context.get('script_context', 'direct')
            
            record_node_execution(
                team_id=team_id,
                tree_id=tree_id,
                node_id=node_id,
                host_name=self.host_name,
                device_model=self.device_model,
                device_name=self.device_name,
                success=success,
                execution_time_ms=execution_time_ms,
                message=message,
                error_details=error_details,
                script_result_id=script_result_id,
                script_context=script_context
            )
            
        except Exception as e:
            print(f"[@lib:verification_executor:_record_verification_to_database] Database recording error: {e}") 