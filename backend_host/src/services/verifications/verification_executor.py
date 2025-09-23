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
from shared.src.lib.supabase.execution_results_db import record_node_execution


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
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Warn if creating instance outside of device initialization
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
        # Navigation context - REMOVED: Now using device.navigation_context
        
        # Get AV controller directly from device for screenshot capture
        self.av_controller = device._get_controller('av')
        if not self.av_controller:
            print(f"[@verification_executor] Warning: No AV controller found for device {self.device_id}")
        
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
            
            # Get verification actions from verification controllers - direct device access
            verification_types = ['image', 'text', 'adb', 'appium', 'video', 'audio']
            for v_type in verification_types:
                try:
                    controller = self.device._get_controller(f'verification_{v_type}')
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
    
    def execute_verifications(self, 
                            verifications: List[Dict[str, Any]], 
                            image_source_url: Optional[str] = None,
                            team_id: str = None
                           ) -> Dict[str, Any]:
        """
        Execute batch of verifications
        
        Args:
            verifications: List of verification dictionaries
            image_source_url: Optional source image URL for image/text verifications

            
        Returns:
            Dict with success status, results, and execution statistics
        """
        print(f"[@lib:verification_executor:execute_verifications] Starting batch verification execution")
        print(f"[@lib:verification_executor:execute_verifications] Processing {len(verifications)} verifications")
        print(f"[@lib:verification_executor:execute_verifications] Host: {self.host_name}")
        print(f"[@lib:verification_executor:execute_verifications] Source: {image_source_url}")
        

        
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
            
            print(f"[@lib:verification_executor:execute_verifications] Processing verification {i+1}/{len(valid_verifications)}: {verification_type}")
            
            start_time = time.time()
            result = self._execute_single_verification(verification, image_source_url)
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
                team_id=team_id
            )
        

        
        # Calculate overall success
        overall_success = passed_count == len(valid_verifications)
        
        print(f"[@lib:verification_executor:execute_verifications] Batch completed: {passed_count}/{len(valid_verifications)} passed")
        
        # Extract detailed error information from failed verifications
        error_info = None
        if not overall_success and results:
            # Get the first failed verification's message as the primary error
            for result in results:
                if not result.get('success', False):
                    error_info = result.get('message', 'Verification failed')
                    break
        
        result = {
            'success': overall_success,
            'total_count': len(valid_verifications),
            'passed_count': passed_count,
            'failed_count': len(valid_verifications) - passed_count,
            'results': results,
            'verification_screenshots': self.verification_screenshots,  # NEW: Include screenshots
            'message': f'Batch verification completed: {passed_count}/{len(valid_verifications)} passed'
        }
        
        # Add error information if verifications failed
        if error_info:
            result['error'] = error_info
            
        return result
    
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
    
    def _execute_single_verification(self, verification: Dict[str, Any], image_source_url: Optional[str]) -> Dict[str, Any]:
        """Execute a single verification and return standardized result"""
        try:
            verification_type = verification.get('verification_type', 'text')
            
            # Get verification controller directly from device
            controller = self.device._get_controller(f'verification_{verification_type}')
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
                'image_source_url': image_source_url
            }
            
            # Direct controller execution (same pattern as ActionExecutor)
            verification_result = controller.execute_verification(verification_config)
            
            # ALWAYS capture screenshot after verification - success OR failure
            screenshot_path = ""
            try:
                screenshot_path = self.av_controller.take_screenshot()
                if screenshot_path:
                    self.verification_screenshots.append(screenshot_path)
                    print(f"[@verification_executor] Screenshot captured: {screenshot_path}")
            except Exception as e:
                print(f"[@verification_executor] Screenshot failed: {e}")
            
            flattened_result = {
                'success': verification_result.get('success', False),
                'message': verification_result.get('message'),
                'error': verification_result.get('error'),
                'threshold': verification_result.get('threshold') or verification_result.get('confidence') or verification_result.get('userThreshold', 0.8),
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
                'screenshot_path': screenshot_path  # Always present
            }
            
            print(f"[@lib:verification_executor:_execute_single_verification] Verification result: success={flattened_result['success']}, type={flattened_result['verification_type']}")
            
            return flattened_result
            
        except Exception as e:
            print(f"[@lib:verification_executor:_execute_single_verification] Verification error: {str(e)}")
            
            # ALWAYS capture screenshot even on exception - success OR failure
            screenshot_path = ""
            try:
                screenshot_path = self.av_controller.take_screenshot()
                if screenshot_path:
                    self.verification_screenshots.append(screenshot_path)
                    print(f"[@verification_executor] Screenshot captured: {screenshot_path}")
            except Exception as screenshot_e:
                print(f"[@verification_executor] Screenshot failed: {screenshot_e}")
            
            return {
                'success': False,
                'message': f"Verification execution failed",
                'error': str(e),
                'verification_type': verification.get('verification_type', 'unknown'),
                'resultType': 'FAIL',
                'screenshot_path': screenshot_path  # Always present
            }
    
    def _record_verification_to_database(self, success: bool, execution_time_ms: int, message: str, error_details: Optional[Dict] = None, team_id: str = None):
        """Record single verification directly to database"""
        try:
            # Get navigation context from device
            nav_context = self.device.navigation_context
            tree_id = nav_context['current_tree_id']
            node_id = nav_context['current_node_id']
            
            # Only record if we have navigation context and team_id
            if tree_id is None or node_id is None:
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
                success=success,
                execution_time_ms=execution_time_ms,
                message=message,
                error_details=error_details,
                script_result_id=script_result_id,
                script_context=script_context
            )
            
        except Exception as e:
            print(f"[@lib:verification_executor:_record_verification_to_database] Database recording error: {e}") 