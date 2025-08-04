"""
ZapController - Handles zap action execution and comprehensive analysis

This controller manages:
- Zap action execution with motion detection
- Subtitle analysis using AI
- Audio menu analysis
- Statistics collection and reporting
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from .action_utils import execute_edge_actions, capture_validation_screenshot
from .navigation_utils import goto_node
from .host_utils import get_controller
from .report_utils import capture_and_upload_screenshot


class ZapAnalysisResult:
    """Container for zap analysis results"""
    
    def __init__(self):
        self.motion_detected = False
        self.subtitles_detected = False
        self.audio_menu_detected = False
        self.detected_language = None
        self.extracted_text = ""
        self.motion_details = {}
        self.subtitle_details = {}
        self.audio_menu_details = {}
        self.success = False
        self.message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility"""
        return {
            "success": self.success,
            "message": self.message,
            "motion_detected": self.motion_detected,
            "subtitles_detected": self.subtitles_detected,
            "audio_menu_detected": self.audio_menu_detected,
            "detected_language": self.detected_language,
            "extracted_text": self.extracted_text,
            "motion_details": self.motion_details,
            "subtitle_analysis": self.subtitle_details,
            "audio_menu_analysis": self.audio_menu_details
        }


class ZapStatistics:
    """Container for zap execution statistics"""
    
    def __init__(self):
        self.total_iterations = 0
        self.successful_iterations = 0
        self.motion_detected_count = 0
        self.subtitles_detected_count = 0
        self.audio_menu_detected_count = 0
        self.detected_languages = []
        self.total_execution_time = 0
        self.analysis_results = []
    
    @property
    def success_rate(self) -> float:
        return (self.successful_iterations / self.total_iterations * 100) if self.total_iterations > 0 else 0
    
    @property
    def motion_success_rate(self) -> float:
        return (self.motion_detected_count / self.total_iterations * 100) if self.total_iterations > 0 else 0
    
    @property
    def subtitle_success_rate(self) -> float:
        return (self.subtitles_detected_count / self.total_iterations * 100) if self.total_iterations > 0 else 0
    
    @property
    def average_execution_time(self) -> float:
        return self.total_execution_time / self.total_iterations if self.total_iterations > 0 else 0
    
    def add_language(self, language: str):
        """Add a detected language if not already present"""
        if language and language not in self.detected_languages:
            self.detected_languages.append(language)
    
    def print_summary(self, action_command: str):
        """Print formatted statistics summary"""
        print(f"📊 [ZapController] Action execution summary:")
        print(f"   • Total iterations: {self.total_iterations}")
        print(f"   • Successful: {self.successful_iterations}")
        print(f"   • Success rate: {self.success_rate:.1f}%")
        print(f"   • Average time per iteration: {self.average_execution_time:.0f}ms")
        print(f"   • Total action time: {self.total_execution_time}ms")
        print(f"   • Motion detected: {self.motion_detected_count}/{self.total_iterations} ({self.motion_success_rate:.1f}%)")
        print(f"   • Subtitles detected: {self.subtitles_detected_count}/{self.total_iterations} ({self.subtitle_success_rate:.1f}%)")
        
        if self.detected_languages:
            print(f"   🌐 Languages detected: {', '.join(self.detected_languages)}")
        
        no_motion_count = self.total_iterations - self.motion_detected_count
        if no_motion_count > 0:
            print(f"   ⚠️  {no_motion_count} zap(s) did not show content change")


class ZapController:
    """Controller for executing zap actions with comprehensive analysis"""
    
    def __init__(self):
        self.statistics = ZapStatistics()
    
    def analyze_after_zap(self, iteration: int, action_command: str, context) -> ZapAnalysisResult:
        """Perform comprehensive analysis after a zap action"""
        result = ZapAnalysisResult()
        
        try:
            print(f"🔍 [ZapController] Analyzing zap results for {action_command} (iteration {iteration})...")
            
            # 1. Motion detection first
            motion_result = self._detect_motion(context)
            result.motion_detected = motion_result.get('success', False)
            result.motion_details = motion_result
            
            if result.motion_detected:
                print(f"✅ [ZapController] Motion detected - content changed successfully")
                
                # 2. Only analyze subtitles if motion detected
                if context:
                    subtitle_result = self._analyze_subtitles(context, iteration, action_command)
                    result.subtitles_detected = subtitle_result.get('subtitles_detected', False)
                    result.detected_language = subtitle_result.get('detected_language')
                    result.extracted_text = subtitle_result.get('extracted_text', '')
                    result.subtitle_details = subtitle_result
                
                # 3. Only analyze audio menu if motion detected
                if context:
                    audio_result = self._analyze_audio_menu(context, iteration)
                    result.audio_menu_detected = audio_result.get('menu_detected', False)
                    result.audio_menu_details = audio_result
            else:
                print(f"⚠️ [ZapController] No motion detected - skipping additional analysis")
                result.subtitle_details = {"success": True, "message": "Skipped due to no motion"}
                result.audio_menu_details = {"success": True, "message": "Skipped due to no motion"}
            
            result.success = True
            result.message = f"Analysis completed for {action_command}"
            
        except Exception as e:
            result.success = False
            result.message = f"Analysis error: {e}"
            print(f"❌ [ZapController] {result.message}")
        
        return result
    
    def execute_zap_iterations(self, context, action_edge, action_command: str, max_iterations: int) -> bool:
        """Execute multiple zap iterations with analysis"""
        print(f"🔄 [ZapController] Starting {max_iterations} iterations of '{action_command}'...")
        
        self.statistics = ZapStatistics()
        self.statistics.total_iterations = max_iterations
        
        # Pre-action screenshot using unified approach
        from .report_utils import capture_and_upload_screenshot
        screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "pre_action", "zap")
        if screenshot_result['success']:
            context.add_screenshot(screenshot_result['screenshot_path'])
        
        for iteration in range(1, max_iterations + 1):
            success = self._execute_single_zap(context, action_edge, action_command, iteration, max_iterations)
            if success:
                self.statistics.successful_iterations += 1
        
        # Post-action screenshot using unified approach
        screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "post_action", "zap")
        if screenshot_result['success']:
            context.add_screenshot(screenshot_result['screenshot_path'])
        
        # Print statistics
        self.statistics.print_summary(action_command)
        
        # Store in context for reporting
        self._store_statistics_in_context(context, action_command)
        
        return self.statistics.successful_iterations == max_iterations
    
    def _execute_single_zap(self, context, action_edge, action_command: str, iteration: int, max_iterations: int) -> bool:
        """Execute a single zap iteration with timing and analysis"""
        print(f"🎬 [ZapController] Iteration {iteration}/{max_iterations}: {action_command}")
        
        # Execute action with timing
        start_time = time.time()
        action_result = execute_edge_actions(context.host, context.selected_device, action_edge, team_id=context.team_id)
        end_time = time.time()
        execution_time = int((end_time - start_time) * 1000)
        
        self.statistics.total_execution_time += execution_time
        
        # Use unified screenshot function from report_utils
        step_name = f"zap_iteration_{iteration}_{action_command}"
        screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, step_name, "zap")
        
        # Add screenshot info to action result for step recording
        action_result['screenshot_path'] = screenshot_result['screenshot_path']
        action_result['screenshot_url'] = screenshot_result['screenshot_url']
        
        # Analyze results
        analysis_result = self.analyze_after_zap(iteration, action_command, context)
        self.statistics.analysis_results.append(analysis_result)
        
        # Update statistics
        if analysis_result.motion_detected:
            self.statistics.motion_detected_count += 1
        if analysis_result.subtitles_detected:
            self.statistics.subtitles_detected_count += 1
        if analysis_result.audio_menu_detected:
            self.statistics.audio_menu_detected_count += 1
        if analysis_result.detected_language:
            self.statistics.add_language(analysis_result.detected_language)
        
        # Get screenshot path for context (maintain compatibility)
        screenshot_path = screenshot_result['screenshot_path']
        context.add_screenshot(screenshot_path)
        
        # Record step result
        self._record_step_result(context, iteration, max_iterations, action_command, action_result, 
                               execution_time, start_time, end_time, analysis_result, screenshot_path, action_edge)
        
        success = action_result.get('success', False)
        if success:
            print(f"✅ [ZapController] Iteration {iteration} completed in {execution_time}ms")
            if iteration < max_iterations:
                time.sleep(0.5)  # Brief pause between iterations
        else:
            print(f"❌ [ZapController] Iteration {iteration} failed: {action_result.get('error', 'Unknown error')}")
        
        return success
    
    def _detect_motion(self, context) -> Dict[str, Any]:
        """Detect motion using direct controller call - same as HTTP routes do"""
        try:
            time.sleep(2)  # Wait for analysis files
            
            device_id = context.selected_device.device_id
            
            # Get video verification controller - same as HTTP routes
            video_controller = get_controller(device_id, 'verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {device_id}"}
            
            # Call the same method that HTTP routes call
            result = video_controller.detect_motion_from_json(
                json_count=3, 
                strict_mode=False
            )
            
            success = result.get('success', False)
            if success:
                print(f"   📊 Motion analysis: {result.get('total_analyzed', 0)} files analyzed")
            else:
                print(f"   📝 Motion details: {result.get('message', 'No details')}")
            
            return result
        except Exception as e:
            return {"success": False, "message": f"Motion detection error: {e}"}
    
    def _analyze_subtitles(self, context, iteration: int, action_command: str) -> Dict[str, Any]:
        """Analyze subtitles using direct controller call - same as HTTP routes do"""
        if not context.screenshot_paths:
            return {"success": False, "message": "No screenshots available"}
        
        try:
            print(f"🔍 [ZapController] Analyzing subtitles...")
            
            latest_screenshot = context.screenshot_paths[-1]
            device_id = context.selected_device.device_id
            
            # Get video verification controller - same as HTTP routes
            video_controller = get_controller(device_id, 'verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {device_id}"}
            
            # Call the same method that HTTP routes call
            result = video_controller.detect_subtitles_ai([latest_screenshot], extract_text=True)
            
            if result.get('success'):
                has_subtitles = result.get('subtitles_detected', False)
                extracted_text = result.get('combined_extracted_text', '') or result.get('extracted_text', '')
                detected_language = result.get('detected_language')
                
                if detected_language == 'unknown' or not detected_language:
                    detected_language = None
                
                subtitle_result = {
                    "success": True,
                    "subtitles_detected": has_subtitles,
                    "extracted_text": extracted_text,
                    "detected_language": detected_language,
                    "message": f"Subtitles {'detected' if has_subtitles else 'not detected'}"
                }
                
                if has_subtitles:
                    lang_info = f" (Language: {detected_language})" if detected_language else ""
                    print(f"✅ [ZapController] Subtitles detected{lang_info}")
                else:
                    print(f"⚠️ [ZapController] No subtitles detected")
                
                # Add screenshot to context for reporting
                context.add_screenshot(latest_screenshot)
                
                return subtitle_result
            else:
                return {"success": False, "message": result.get('message', 'Subtitle analysis failed')}
                
        except Exception as e:
            return {"success": False, "message": f"Subtitle analysis error: {e}"}
    
    def _analyze_audio_menu(self, context, iteration: int) -> Dict[str, Any]:
        """Analyze audio menu using direct controller call - same as HTTP routes do"""
        try:
            print(f"🎧 [ZapController] Analyzing audio menu...")
            
            # Navigate to audio menu
            audio_menu_nav = goto_node(context.host, context.selected_device, "live_audiomenu", 
                                     context.tree_id, context.team_id, context)
            
            if audio_menu_nav.get('success'):
                # Capture and analyze using unified approach
                screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"audio_menu_{iteration}", "zap")
                screenshot_path = screenshot_result['screenshot_path'] if screenshot_result['success'] else ""
                if screenshot_result['success']:
                    context.add_screenshot(screenshot_path)
                device_id = context.selected_device.device_id
                
                # Get video verification controller - same as HTTP routes
                video_controller = get_controller(device_id, 'verification_video')
                if not video_controller:
                    return {"success": False, "message": f"No video verification controller found for device {device_id}"}
                
                # Call the same method that HTTP routes would call
                result = video_controller.analyze_language_menu_ai(screenshot_path)
                
                # Navigate back to live
                goto_node(context.host, context.selected_device, "live", context.tree_id, context.team_id, context)
                
                return result
            else:
                return {"success": False, "message": "Failed to navigate to audio menu"}
                
        except Exception as e:
            return {"success": False, "message": f"Audio menu analysis error: {e}"}
    

    
    def _record_step_result(self, context, iteration: int, max_iterations: int, action_command: str,
                          action_result: Dict, execution_time: int, start_time: float, end_time: float,
                          analysis_result: ZapAnalysisResult, screenshot_path: str, action_edge: Dict):
        """Record step result in context"""
        step_num = len(context.step_results) + 1
        
        # Extract real actions from edge
        real_actions, real_retry_actions, real_failure_actions = self._extract_edge_actions(action_edge)
        
        step_result = {
            'step_number': step_num,
            'success': action_result.get('success', False),
            'screenshot_path': action_result.get('screenshot_path', ''),
            'screenshot_url': action_result.get('screenshot_url'),
            'message': f"Zap iteration {iteration}: {action_command} ({iteration}/{max_iterations})",
            'execution_time_ms': execution_time,
            'start_time': datetime.fromtimestamp(start_time).strftime('%H:%M:%S'),
            'end_time': datetime.fromtimestamp(end_time).strftime('%H:%M:%S'),
            'step_category': 'action',
            'action_name': action_command,
            'iteration': iteration,
            'max_iterations': max_iterations,
            'motion_detection': analysis_result.to_dict(),
            # Individual analysis results for report display
            'motion_analysis': analysis_result.motion_details,
            'subtitle_analysis': analysis_result.subtitle_details,
            'audio_menu_analysis': analysis_result.audio_menu_details,
            'from_node': 'live',
            'to_node': 'live',
            'actions': real_actions,
            'retryActions': real_retry_actions,
            'failureActions': real_failure_actions,
            'verifications': [],
            'verification_results': []
        }
        
        if not action_result.get('success'):
            step_result['error_message'] = action_result.get('error', 'Unknown error')
        
        context.step_results.append(step_result)
    
    def _extract_edge_actions(self, action_edge: Dict) -> tuple:
        """Extract real actions from action edge"""
        real_actions = []
        real_retry_actions = []
        real_failure_actions = []
        
        action_sets = action_edge.get('action_sets', [])
        default_action_set_id = action_edge.get('default_action_set_id')
        
        if action_sets and default_action_set_id:
            default_action_set = next((s for s in action_sets if s.get('id') == default_action_set_id), 
                                    action_sets[0] if action_sets else None)
            
            if default_action_set:
                real_actions = default_action_set.get('actions', [])
                real_retry_actions = default_action_set.get('retry_actions') or []
                real_failure_actions = default_action_set.get('failure_actions') or []
        
        return real_actions, real_retry_actions, real_failure_actions
    
    def _store_statistics_in_context(self, context, action_command: str):
        """Store statistics in context for reporting"""
        context.custom_data.update({
            'action_command': action_command,
            'max_iteration': self.statistics.total_iterations,
            'successful_iterations': self.statistics.successful_iterations,
            'motion_detected_count': self.statistics.motion_detected_count,
            'subtitles_detected_count': self.statistics.subtitles_detected_count,
            'detected_languages': self.statistics.detected_languages,
            'motion_results': [r.to_dict() for r in self.statistics.analysis_results],
            'total_action_time': self.statistics.total_execution_time
        })