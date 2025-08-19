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
        self.zapping_detected = False
        self.detected_language = None
        self.extracted_text = ""
        self.motion_details = {}
        self.subtitle_details = {}
        self.audio_menu_details = {}
        self.zapping_details = {}
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
            "zapping_detected": self.zapping_detected,
            "detected_language": self.detected_language,
            "extracted_text": self.extracted_text,
            "motion_details": self.motion_details,
            "subtitle_analysis": self.subtitle_details,
            "audio_menu_analysis": self.audio_menu_details,
            "zapping_analysis": self.zapping_details
        }


class ZapStatistics:
    """Container for zap execution statistics"""
    
    def __init__(self):
        self.total_iterations = 0
        self.successful_iterations = 0
        self.motion_detected_count = 0
        self.subtitles_detected_count = 0
        self.audio_menu_detected_count = 0
        self.zapping_detected_count = 0
        self.detected_languages = []
        self.total_execution_time = 0
        self.analysis_results = []
        
        # Enhanced zapping statistics
        self.zapping_durations = []        # List of zapping durations
        self.blackscreen_durations = []    # List of blackscreen durations  
        self.detected_channels = []        # List of detected channel names
        self.channel_info_results = []     # List of complete channel info results
    
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
    def zapping_success_rate(self) -> float:
        return (self.zapping_detected_count / self.total_iterations * 100) if self.total_iterations > 0 else 0
    
    @property
    def average_execution_time(self) -> float:
        return self.total_execution_time / self.total_iterations if self.total_iterations > 0 else 0
    
    def add_language(self, language: str):
        """Add a detected language if not already present"""
        if language and language not in self.detected_languages:
            self.detected_languages.append(language)
    
    def add_zapping_result(self, zapping_details: Dict[str, Any]):
        """Add enhanced zapping analysis results"""
        if zapping_details.get('success', False):
            # Add duration information
            zapping_duration = zapping_details.get('zapping_duration', 0.0)
            blackscreen_duration = zapping_details.get('blackscreen_duration', 0.0)
            
            if zapping_duration > 0:
                self.zapping_durations.append(zapping_duration)
            if blackscreen_duration > 0:
                self.blackscreen_durations.append(blackscreen_duration)
            
            # Add channel information
            channel_name = zapping_details.get('channel_name', '').strip()
            if channel_name and channel_name not in self.detected_channels:
                self.detected_channels.append(channel_name)
            
            # Store complete channel info result
            channel_info = {
                'channel_name': zapping_details.get('channel_name', ''),
                'channel_number': zapping_details.get('channel_number', ''),
                'program_name': zapping_details.get('program_name', ''),
                'program_start_time': zapping_details.get('program_start_time', ''),
                'program_end_time': zapping_details.get('program_end_time', ''),
                'channel_confidence': zapping_details.get('channel_confidence', 0.0),
                'zapping_duration': zapping_duration,
                'blackscreen_duration': blackscreen_duration
            }
            self.channel_info_results.append(channel_info)
    
    @property
    def average_zapping_duration(self) -> float:
        """Average zapping duration in seconds"""
        return sum(self.zapping_durations) / len(self.zapping_durations) if self.zapping_durations else 0.0
    
    @property
    def average_blackscreen_duration(self) -> float:
        """Average blackscreen duration in seconds"""
        return sum(self.blackscreen_durations) / len(self.blackscreen_durations) if self.blackscreen_durations else 0.0
    
    def print_summary(self, action_command: str):
        """Print formatted statistics summary with enhanced zapping information"""
        print(f"📊 [ZapController] Action execution summary:")
        print(f"   • Total iterations: {self.total_iterations}")
        print(f"   • Successful: {self.successful_iterations}")
        print(f"   • Success rate: {self.success_rate:.1f}%")
        print(f"   • Average time per iteration: {self.average_execution_time:.0f}ms")
        print(f"   • Total action time: {self.total_execution_time}ms")
        print(f"   • Motion detected: {self.motion_detected_count}/{self.total_iterations} ({self.motion_success_rate:.1f}%)")
        print(f"   • Subtitles detected: {self.subtitles_detected_count}/{self.total_iterations} ({self.subtitle_success_rate:.1f}%)")
        print(f"   • Zapping detected: {self.zapping_detected_count}/{self.total_iterations} ({self.zapping_success_rate:.1f}%)")
        
        # Enhanced zapping duration information
        if self.zapping_durations:
            print(f"   ⚡ Average zapping duration: {self.average_zapping_duration:.2f}s")
            print(f"   ⬛ Average blackscreen duration: {self.average_blackscreen_duration:.2f}s")
            min_zap = min(self.zapping_durations)
            max_zap = max(self.zapping_durations)
            print(f"   📊 Zapping duration range: {min_zap:.2f}s - {max_zap:.2f}s")
        
        # Channel information
        if self.detected_channels:
            print(f"   📺 Channels detected: {', '.join(self.detected_channels)}")
            
            # Show detailed channel info for successful zaps
            successful_channel_info = [info for info in self.channel_info_results if info.get('channel_name')]
            if successful_channel_info:
                print(f"   🎬 Channel details:")
                for i, info in enumerate(successful_channel_info, 1):
                    channel_display = info['channel_name']
                    if info.get('channel_number'):
                        channel_display += f" ({info['channel_number']})"
                    if info.get('program_name'):
                        channel_display += f" - {info['program_name']}"
                    if info.get('program_start_time') and info.get('program_end_time'):
                        channel_display += f" [{info['program_start_time']}-{info['program_end_time']}]"
                    
                    print(f"      {i}. {channel_display} (zap: {info['zapping_duration']:.2f}s, confidence: {info['channel_confidence']:.1f})")
        
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
            # Set current iteration for screenshot naming
            context.current_iteration = iteration
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
                
                # 4. Only analyze zapping if motion detected and it's a channel up action
                if context and 'chup' in action_command.lower():
                    # Get the action end time from context if available
                    action_end_time = getattr(context, 'last_action_end_time', None)
                    zapping_result = self._analyze_zapping(context, iteration, action_command, self.blackscreen_area, action_end_time)
                    result.zapping_detected = zapping_result.get('zapping_detected', False)
                    result.zapping_details = zapping_result
                else:
                    result.zapping_details = {"success": True, "message": "Skipped - not a channel up action"}
            else:
                print(f"⚠️ [ZapController] No motion detected - skipping additional analysis")
                result.subtitle_details = {"success": True, "message": "Skipped due to no motion"}
                result.audio_menu_details = {"success": True, "message": "Skipped due to no motion"}
                result.zapping_details = {"success": True, "message": "Skipped due to no motion"}
            
            result.success = True
            result.message = f"Analysis completed for {action_command}"
            
        except Exception as e:
            result.success = False
            result.message = f"Analysis error: {e}"
            print(f"❌ [ZapController] {result.message}")
        
        return result
    
    def execute_zap_iterations(self, context, action_edge, action_command: str, max_iterations: int, blackscreen_area: str = None, goto_live: bool = True) -> bool:
        """Execute multiple zap iterations with analysis - simple sequential recording"""
        print(f"🔄 [ZapController] Starting {max_iterations} iterations of '{action_command}'...")
        
        self.statistics = ZapStatistics()
        self.statistics.total_iterations = max_iterations
        self.blackscreen_area = blackscreen_area  # Store for later use
        self.goto_live = goto_live  # Store for audio menu analysis logic
        
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
        
        # RECORD ZAP STEP IMMEDIATELY WHEN IT STARTS
        start_time = time.time()
        
        # Step start screenshot - capture BEFORE action execution
        step_name = f"zap_iteration_{iteration}_{action_command}"
        step_start_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"{step_name}_start", "zap")
        step_start_screenshot_path = step_start_screenshot_result.get('screenshot_path', '')
        
        if step_start_screenshot_path:
            print(f"📸 [ZapController] Step-start screenshot captured: {step_start_screenshot_path}")
            context.add_screenshot(step_start_screenshot_path)
        
        # Execute action with timing
        action_result = execute_edge_actions(context.host, context.selected_device, action_edge, team_id=context.team_id)
        end_time = time.time()
        execution_time = int((end_time - start_time) * 1000)
        
        # Store action times for analysis
        context.last_action_start_time = start_time
        context.last_action_end_time = end_time
        self.statistics.total_execution_time += execution_time
        
        # Main action screenshot
        screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, step_name, "zap")
        action_result['screenshot_path'] = screenshot_result['screenshot_path']
        action_result['screenshot_url'] = screenshot_result['screenshot_url']
        action_result['step_start_screenshot_path'] = step_start_screenshot_path
        
        # RECORD STEP IMMEDIATELY - not during analysis
        zap_step_index = len(context.step_results)  # Store index before recording
        self._record_zap_step_immediately(context, iteration, max_iterations, action_command, action_result, 
                                         execution_time, start_time, end_time, screenshot_result['screenshot_path'], action_edge)
        
        # Wait for banner to disappear before analysis
        print(f"⏰ [ZapController] Waiting 4 seconds for banner to disappear...")
        time.sleep(4)
        
        # Capture a clean screenshot after banner disappears for analysis
        analysis_step_name = f"zap_analysis_{iteration}_{action_command}"
        analysis_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, analysis_step_name, "zap")
        print(f"📸 [ZapController] Captured clean screenshot for analysis: {analysis_screenshot_result['screenshot_path']}")
        
        # Analyze results (this may trigger navigation steps)
        analysis_result = self.analyze_after_zap(iteration, action_command, context)
        self.statistics.analysis_results.append(analysis_result)
        
        # Update statistics
        if analysis_result.motion_detected:
            self.statistics.motion_detected_count += 1
        if analysis_result.subtitles_detected:
            self.statistics.subtitles_detected_count += 1
        if analysis_result.audio_menu_detected:
            self.statistics.audio_menu_detected_count += 1
        if analysis_result.zapping_detected:
            self.statistics.zapping_detected_count += 1
            self.statistics.add_zapping_result(analysis_result.zapping_details)
        if analysis_result.detected_language:
            self.statistics.add_language(analysis_result.detected_language)
        
        # Update the ZAP step (not the last step) with analysis results
        if context.step_results and zap_step_index < len(context.step_results):
            zap_step = context.step_results[zap_step_index]
            zap_step['motion_detection'] = analysis_result.to_dict()
            zap_step['motion_analysis'] = analysis_result.motion_details
            zap_step['subtitle_analysis'] = analysis_result.subtitle_details
            zap_step['audio_menu_analysis'] = analysis_result.audio_menu_details
            zap_step['zapping_analysis'] = analysis_result.zapping_details
            
            # Collect all screenshots for this zap iteration (like original)
            action_screenshots = []
            if screenshot_result['screenshot_path']:
                action_screenshots.append(screenshot_result['screenshot_path'])
            
            # Add analysis screenshots if different from main screenshot
            if analysis_result.subtitle_details.get('analyzed_screenshot') and analysis_result.subtitle_details['analyzed_screenshot'] != screenshot_result['screenshot_path']:
                action_screenshots.append(analysis_result.subtitle_details['analyzed_screenshot'])
            
            if analysis_result.audio_menu_details.get('analyzed_screenshot') and analysis_result.audio_menu_details['analyzed_screenshot'] != screenshot_result['screenshot_path']:
                action_screenshots.append(analysis_result.audio_menu_details['analyzed_screenshot'])
            
            zap_step['action_screenshots'] = action_screenshots
        
        context.add_screenshot(screenshot_result['screenshot_path'])
        
        # Step end screenshot
        step_end_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"{step_name}_end", "zap")
        step_end_screenshot_path = step_end_screenshot_result.get('screenshot_path', '')
        
        if step_end_screenshot_path:
            context.add_screenshot(step_end_screenshot_path)
            
        # Update the ZAP step with the step_end_screenshot_path
        if context.step_results and zap_step_index < len(context.step_results):
            zap_step = context.step_results[zap_step_index]
            zap_step['step_end_screenshot_path'] = step_end_screenshot_path
        
        success = action_result.get('success', False)
        if success:
            print(f"✅ [ZapController] Iteration {iteration} completed in {execution_time}ms")
            if iteration < max_iterations:
                time.sleep(0.5)
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
            
            # Capture screenshot for motion analysis reporting
            iteration = getattr(context, 'current_iteration', 1)
            screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"motion_analysis_{iteration}", "zap")
            
            # Call the same method that HTTP routes call
            result = video_controller.detect_motion_from_json(
                json_count=3, 
                strict_mode=False
            )
            
            # Collect the 3 motion analysis images for thumbnails and add paths to result (similar to zapping detection)
            motion_images = self._add_motion_analysis_images_to_screenshots(context, device_id, iteration)
            if motion_images:
                result['motion_analysis_images'] = motion_images
            
            # Add screenshot information to the result for reporting
            if screenshot_result['success']:
                context.add_screenshot(screenshot_result['screenshot_path'])
                if screenshot_result['screenshot_url']:
                    result['analyzed_screenshot'] = screenshot_result['screenshot_url']
                elif screenshot_result['screenshot_path']:
                    result['analyzed_screenshot'] = screenshot_result['screenshot_path']
            
            success = result.get('success', False)
            if success:
                # Enhanced logging to show what triggered the motion detection
                video_ok = result.get('video_ok', False)
                audio_ok = result.get('audio_ok', False)
                analyzed_count = result.get('total_analyzed', 0)
                
                if video_ok and audio_ok:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed - both video and audio content present")
                elif video_ok:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed - video motion detected")
                elif audio_ok:
                    print(f"   🎵 Motion detected: {analyzed_count} files analyzed - audio content present (video motion minimal)")
                else:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed")
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
            
            # Use the latest screenshot (which should be the clean analysis screenshot)
            latest_screenshot = context.screenshot_paths[-1]
            print(f"🔍 [ZapController] Using clean screenshot for subtitle analysis: {latest_screenshot}")
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
                    "analyzed_screenshot": latest_screenshot,
                    "message": f"Subtitles {'detected' if has_subtitles else 'not detected'}"
                }
                
                if has_subtitles:
                    lang_info = f" (Language: {detected_language})" if detected_language else ""
                    text_info = f", Text: '{extracted_text[:50]}...'" if extracted_text and len(extracted_text) > 0 else ""
                    print(f"✅ [ZapController] Subtitles detected{lang_info}{text_info}")
                else:
                    print(f"⚠️ [ZapController] No subtitles detected in {latest_screenshot}")
                
                # Add screenshot to context for reporting (for R2 upload)
                context.add_screenshot(latest_screenshot)
                
                return subtitle_result
            else:
                error_msg = result.get('message', 'Subtitle analysis failed')
                print(f"❌ [ZapController] Subtitle analysis failed: {error_msg} (image: {latest_screenshot})")
                # Add screenshot to context for reporting even when failed (for debugging)
                context.add_screenshot(latest_screenshot)
                return {
                    "success": False, 
                    "analyzed_screenshot": latest_screenshot,
                    "message": error_msg
                }
                
        except Exception as e:
            error_msg = f"Subtitle analysis error: {e}"
            image_info = f" (image: {latest_screenshot})" if 'latest_screenshot' in locals() else ""
            print(f"❌ [ZapController] {error_msg}{image_info}")
            # Add screenshot to context for reporting even when exception occurs (for debugging)
            if 'latest_screenshot' in locals():
                context.add_screenshot(latest_screenshot)
            return {
                "success": False,
                "analyzed_screenshot": latest_screenshot if 'latest_screenshot' in locals() else None,
                "message": error_msg
            }
    
    def _analyze_audio_menu(self, context, iteration: int) -> Dict[str, Any]:
        """Analyze audio/subtitle menu using direct controller call - handles mobile (combined) and desktop/TV (separate) menus"""
        try:
            device_model = context.selected_device.device_model if context.selected_device else 'unknown'
            device_id = context.selected_device.device_id
            
            # Determine the correct target node to return to
            if device_model in ['android_mobile', 'ios_mobile']:
                target_node = "live_fullscreen"
            else:
                target_node = "live"
            
            # Get video verification controller - same as HTTP routes
            video_controller = get_controller(device_id, 'verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {device_id}"}
            
            if device_model in ['android_mobile', 'ios_mobile']:
                # Mobile devices: combined audio/subtitle menu
                print(f"🎧 [ZapController] Analyzing combined audio/subtitle menu for mobile...")
                
                # Use audio menu node provided by parent script, or fallback to default
                audio_menu_target = getattr(context, 'audio_menu_node', 'live_audiomenu')
                print(f"🎧 [ZapController] Using audio menu target: {audio_menu_target}")
                
                # Navigate to combined audio menu
                audio_menu_nav = goto_node(context.host, context.selected_device, audio_menu_target, 
                                         context.tree_id, context.team_id, context)
                
                if audio_menu_nav.get('success'):
                    # Capture and analyze using unified approach
                    screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"audio_menu_{iteration}", "zap")
                    screenshot_path = screenshot_result['screenshot_path'] if screenshot_result['success'] else ""
                    screenshot_url = screenshot_result['screenshot_url'] if screenshot_result['success'] else None
                    if screenshot_result['success']:
                        context.add_screenshot(screenshot_path)
                    
                    # Call the same method that HTTP routes would call
                    result = video_controller.analyze_language_menu_ai(screenshot_path)
                    
                    # Add screenshot information to the result for reporting
                    if screenshot_url:
                        result['analyzed_screenshot'] = screenshot_url
                    elif screenshot_path:
                        result['analyzed_screenshot'] = screenshot_path
                    
                    # Navigate back to correct target node (live_fullscreen for mobile, live for desktop)
                    try:
                        print(f"🔄 [ZapController] Navigating back to {target_node}")
                        goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
                    except Exception as nav_error:
                        print(f"⚠️ [ZapController] Navigation back to {target_node} failed: {nav_error}")
                        # Continue anyway - we have the analysis result
                    
                    return result
                else:
                    # Even on navigation failure, try to capture screenshot for debugging
                    screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"audio_menu_{iteration}_failed", "zap")
                    result = {"success": False, "message": f"Failed to navigate to {audio_menu_target}"}
                    
                    # Include screenshot even on failure for debugging
                    if screenshot_result['success']:
                        context.add_screenshot(screenshot_result['screenshot_path'])
                        if screenshot_result['screenshot_url']:
                            result['analyzed_screenshot'] = screenshot_result['screenshot_url']
                        elif screenshot_result['screenshot_path']:
                            result['analyzed_screenshot'] = screenshot_result['screenshot_path']
                    
                    return result
            
            else:
                # Desktop/TV devices: separate audio and subtitle menus
                print(f"🎧 [ZapController] Analyzing separate audio and subtitle menus for desktop/TV...")
                
                combined_result = {
                    "success": True,
                    "menu_detected": False,
                    "audio_detected": False,
                    "subtitles_detected": False,
                    "audio_analysis": {},
                    "subtitle_analysis": {},
                    "message": ""
                }
                
                # 1. Analyze audio menu
                print(f"🔊 [ZapController] Checking audio menu...")
                audio_nav = goto_node(context.host, context.selected_device, "live_menu_audio", 
                                    context.tree_id, context.team_id, context)
                
                if audio_nav.get('success'):
                    # Capture and analyze audio menu
                    audio_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"audio_menu_{iteration}", "zap")
                    audio_screenshot_path = audio_screenshot_result['screenshot_path'] if audio_screenshot_result['success'] else ""
                    audio_screenshot_url = audio_screenshot_result['screenshot_url'] if audio_screenshot_result['success'] else None
                    if audio_screenshot_result['success']:
                        context.add_screenshot(audio_screenshot_path)
                    
                    audio_result = video_controller.analyze_language_menu_ai(audio_screenshot_path)
                    
                    # Add screenshot information to the audio result for reporting
                    if audio_screenshot_url:
                        audio_result['analyzed_screenshot'] = audio_screenshot_url
                    elif audio_screenshot_path:
                        audio_result['analyzed_screenshot'] = audio_screenshot_path
                    
                    combined_result["audio_analysis"] = audio_result
                    if audio_result.get('menu_detected', False):
                        combined_result["audio_detected"] = True
                        combined_result["menu_detected"] = True
                        print(f"✅ [ZapController] Audio menu detected")
                    else:
                        print(f"⚠️ [ZapController] No audio menu detected")
                else:
                    # Even on navigation failure, try to capture screenshot for debugging
                    audio_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"audio_menu_{iteration}_failed", "zap")
                    audio_analysis_result = {"success": False, "message": "Failed to navigate to audio menu"}
                    
                    # Include screenshot even on failure for debugging
                    if audio_screenshot_result['success']:
                        context.add_screenshot(audio_screenshot_result['screenshot_path'])
                        if audio_screenshot_result['screenshot_url']:
                            audio_analysis_result['analyzed_screenshot'] = audio_screenshot_result['screenshot_url']
                        elif audio_screenshot_result['screenshot_path']:
                            audio_analysis_result['analyzed_screenshot'] = audio_screenshot_result['screenshot_path']
                    
                    combined_result["audio_analysis"] = audio_analysis_result
                    print(f"❌ [ZapController] Failed to navigate to audio menu")
                
                # 2. Analyze subtitle menu
                print(f"📝 [ZapController] Checking subtitle menu...")
                subtitle_nav = goto_node(context.host, context.selected_device, "live_menu_subtitles", 
                                       context.tree_id, context.team_id, context)
                
                if subtitle_nav.get('success'):
                    # Capture and analyze subtitle menu
                    subtitle_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, f"subtitle_menu_{iteration}", "zap")
                    subtitle_screenshot_path = subtitle_screenshot_result['screenshot_path'] if subtitle_screenshot_result['success'] else ""
                    subtitle_screenshot_url = subtitle_screenshot_result['screenshot_url'] if subtitle_screenshot_result['success'] else None
                    if subtitle_screenshot_result['success']:
                        context.add_screenshot(subtitle_screenshot_path)
                    
                    subtitle_result = video_controller.analyze_language_menu_ai(subtitle_screenshot_path)
                    
                    # Add screenshot information to the subtitle result for reporting
                    if subtitle_screenshot_url:
                        subtitle_result['analyzed_screenshot'] = subtitle_screenshot_url
                    elif subtitle_screenshot_path:
                        subtitle_result['analyzed_screenshot'] = subtitle_screenshot_path
                    
                    combined_result["subtitle_analysis"] = subtitle_result
                    if subtitle_result.get('menu_detected', False):
                        combined_result["subtitles_detected"] = True
                        combined_result["menu_detected"] = True
                        print(f"✅ [ZapController] Subtitle menu detected")
                    else:
                        print(f"⚠️ [ZapController] No subtitle menu detected")
                else:
                    combined_result["subtitle_analysis"] = {"success": False, "message": "Failed to navigate to subtitle menu"}
                    print(f"❌ [ZapController] Failed to navigate to subtitle menu")
                
                # Navigate back to correct target node (best effort - don't fail if navigation fails)
                try:
                    print(f"🔄 [ZapController] Navigating back to {target_node}")
                    goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
                except Exception as nav_error:
                    print(f"⚠️ [ZapController] Navigation back to {target_node} failed: {nav_error}")
                    # Continue anyway - we have the analysis results
                
                # Set combined message and analyzed_screenshot
                if combined_result["audio_detected"] and combined_result["subtitles_detected"]:
                    combined_result["message"] = "Both audio and subtitle menus detected"
                    # Prioritize audio menu screenshot if both detected
                    if combined_result["audio_analysis"].get('analyzed_screenshot'):
                        combined_result["analyzed_screenshot"] = combined_result["audio_analysis"]['analyzed_screenshot']
                    elif combined_result["subtitle_analysis"].get('analyzed_screenshot'):
                        combined_result["analyzed_screenshot"] = combined_result["subtitle_analysis"]['analyzed_screenshot']
                elif combined_result["audio_detected"]:
                    combined_result["message"] = "Only audio menu detected"
                    if combined_result["audio_analysis"].get('analyzed_screenshot'):
                        combined_result["analyzed_screenshot"] = combined_result["audio_analysis"]['analyzed_screenshot']
                elif combined_result["subtitles_detected"]:
                    combined_result["message"] = "Only subtitle menu detected"
                    if combined_result["subtitle_analysis"].get('analyzed_screenshot'):
                        combined_result["analyzed_screenshot"] = combined_result["subtitle_analysis"]['analyzed_screenshot']
                else:
                    combined_result["message"] = "No audio or subtitle menus detected"
                
                print(f"📊 [ZapController] Menu analysis complete: {combined_result['message']}")
                return combined_result
                
        except Exception as e:
            return {"success": False, "message": f"Audio menu analysis error: {e}"}
    
    def _analyze_zapping(self, context, iteration: int, action_command: str, blackscreen_area: str = None, action_end_time: float = None) -> Dict[str, Any]:
        """Analyze zapping sequence using the new zapping detection functionality"""
        try:
            print(f"🔍 [ZapController] Analyzing zapping sequence for {action_command} (iteration {iteration})...")
            
            device_id = context.selected_device.device_id
            
            # Get video verification controller
            video_controller = get_controller(device_id, 'verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {device_id}"}
            
            # Get the folder path where images are captured
            # Use the AV controller's capture path
            av_controller = get_controller(device_id, 'av')
            if not av_controller:
                return {"success": False, "message": f"No AV controller found for device {device_id}"}
            
            # Get the capture folder path
            capture_folder = getattr(av_controller, 'video_capture_path', None)
            if not capture_folder:
                return {"success": False, "message": "No capture folder available"}
            
            # Use action start time to catch blackscreen that happens during the action
            key_release_timestamp = context.last_action_start_time
            
            # Simple hardcoded areas - no more over-engineering!
            device_model = context.selected_device.device_model if context.selected_device else 'unknown'
            
            if device_model in ['android_mobile', 'ios_mobile']:
                # Mobile: blackscreen area 475,50 to 800,215 and banner area 470,230 to 750,300
                analysis_rectangle = {'x': 475, 'y': 50, 'width': 325, 'height': 165}  # 800-475=325, 215-50=165
                banner_region = {'x': 470, 'y': 230, 'width': 280, 'height': 70}  # 750-470=280, 300-230=70
                print(f"🎯 [ZapController] Using hardcoded mobile areas:")
                print(f"    Blackscreen: {analysis_rectangle}")
                print(f"    Banner: {banner_region}")
            else:
                # Desktop/TV: blackscreen area 300,130 to 1600,700 and banner area 245,830 to 1415,950
                analysis_rectangle = {'x': 300, 'y': 130, 'width': 1300, 'height': 570}  # 1600-300=1300, 700-130=570
                banner_region = {'x': 245, 'y': 830, 'width': 1170, 'height': 120}  # 1415-245=1170, 950-830=120
                print(f"🎯 [ZapController] Using hardcoded desktop/TV areas:")
                print(f"    Blackscreen: {analysis_rectangle}")
                print(f"    Banner: {banner_region}")
            
            # Call the new zapping detection method
            # Analyze more images since we start 2 seconds earlier to catch early blackscreen
            zapping_result = video_controller.detect_zapping(
                folder_path=capture_folder,
                key_release_timestamp=key_release_timestamp,
                analysis_rectangle=analysis_rectangle,
                banner_region=banner_region,
                max_images=10  # Analyze up to 10 images (10 seconds of capture) to account for earlier start
            )
            
            if zapping_result.get('success', False):
                # Analysis completed and zapping was detected
                zapping_detected = zapping_result.get('zapping_detected', False)
                blackscreen_duration = zapping_result.get('blackscreen_duration', 0.0)
                channel_info = zapping_result.get('channel_info', {})
                analyzed_images = zapping_result.get('analyzed_images', 0)
                
                if zapping_detected:
                    print(f"✅ [ZapController] Zapping detected - Duration: {blackscreen_duration}s")
                    if channel_info.get('channel_name'):
                        print(f"   📺 Channel: {channel_info['channel_name']}")
                    if channel_info.get('program_name'):
                        print(f"   📺 Program: {channel_info['program_name']}")
                    
                    # Add zapping images to context screenshot collection for R2 upload
                    self._add_zapping_images_to_screenshots(context, zapping_result, capture_folder)
                    
                    return {
                        "success": True,
                        "zapping_detected": True,
                        "blackscreen_duration": blackscreen_duration,
                        "zapping_duration": zapping_result.get('zapping_duration', 0.0),  # Total zapping duration
                        "first_image": zapping_result.get('first_image'),
                        "blackscreen_start_image": zapping_result.get('blackscreen_start_image'),
                        "blackscreen_end_image": zapping_result.get('blackscreen_end_image'),
                        "first_content_after_blackscreen": zapping_result.get('first_content_after_blackscreen'),
                        "channel_detection_image": zapping_result.get('channel_detection_image'),
                        "last_image": zapping_result.get('last_image'),
                        "channel_info": channel_info,
                        "analyzed_images": analyzed_images,
                        "total_images_available": zapping_result.get('total_images_available', 0),
                        "debug_images": zapping_result.get('debug_images', []),  # Include debug images
                        "message": f"Zapping detected (analyzed {analyzed_images} images)",
                        "details": zapping_result
                    }
                else:
                    # Analysis completed but no blackscreen detected - this is an error for zapping tests
                    print(f"❌ [ZapController] No blackscreen detected (analyzed {analyzed_images} images)")
                    
                    # Still add images for debugging
                    self._add_zapping_images_to_screenshots(context, zapping_result, capture_folder)
                    
                    return {
                        "success": False,
                        "zapping_detected": False,
                        # Include image paths even on failure so they show in reports
                        "first_image": zapping_result.get('first_image'),
                        "blackscreen_start_image": zapping_result.get('blackscreen_start_image'),
                        "blackscreen_end_image": zapping_result.get('blackscreen_end_image'),
                        "first_content_after_blackscreen": zapping_result.get('first_content_after_blackscreen'),
                        "last_image": zapping_result.get('last_image'),
                        "analyzed_images": analyzed_images,
                        "total_images_available": zapping_result.get('total_images_available', 0),
                        "debug_images": zapping_result.get('debug_images', []),
                        "message": "No blackscreen detected",
                        "error": "No blackscreen detected"
                    }
            else:
                # Analysis actually failed (couldn't load images, configuration error, etc.)
                error_msg = zapping_result.get('error', f'Analysis could not be performed - no images were analyzed (folder: {capture_folder})')
                print(f"❌ [ZapController] Zapping analysis failed: {error_msg}")
                
                # Still include debug images if available for debugging
                debug_images = zapping_result.get('debug_images', [])
                total_available = zapping_result.get('total_images_available', 0)
                analyzed_count = zapping_result.get('analyzed_images', 0)
                
                # Still add images for debugging even on complete failure
                self._add_zapping_images_to_screenshots(context, zapping_result, capture_folder)
                
                detailed_message = f"Zapping analysis failed: {error_msg}"
                if total_available > 0:
                    detailed_message += f" (found {total_available} images, analyzed {analyzed_count})"
                
                return {
                    "success": False,
                    "zapping_detected": False,
                    # Include image paths even on complete failure so they show in reports
                    "first_image": zapping_result.get('first_image'),
                    "blackscreen_start_image": zapping_result.get('blackscreen_start_image'),
                    "blackscreen_end_image": zapping_result.get('blackscreen_end_image'),
                    "first_content_after_blackscreen": zapping_result.get('first_content_after_blackscreen'),
                    "last_image": zapping_result.get('last_image'),
                    "debug_images": debug_images,
                    "analyzed_images": analyzed_count,
                    "total_images_available": total_available,
                    "message": detailed_message,
                    "error": error_msg
                }
                
        except Exception as e:
            import traceback
            error_details = f"{str(e)} | Traceback: {traceback.format_exc()}"
            print(f"❌ [ZapController] Zapping analysis exception: {error_details}")
            return {
                "success": False, 
                "zapping_detected": False,
                "debug_images": [],
                "message": f"Zapping analysis exception: {str(e)}",
                "error": str(e),
                "error_details": error_details
            }
    
    def _add_zapping_images_to_screenshots(self, context, zapping_result: Dict[str, Any], capture_folder: str):
        """Add key zapping images to context screenshot collection for R2 upload"""
        try:
            if not hasattr(context, 'screenshot_paths'):
                context.screenshot_paths = []
            
            # Get the captures subfolder where images are stored
            captures_folder = f"{capture_folder}/captures"
            
            # List of key images to upload (in order of importance)
            key_images = [
                zapping_result.get('first_image'),
                zapping_result.get('blackscreen_start_image'),
                zapping_result.get('blackscreen_end_image'),
                zapping_result.get('first_content_after_blackscreen'),
                zapping_result.get('last_image')
            ]
            
            # Add each key image to screenshot paths if it exists
            for image_filename in key_images:
                if image_filename:
                    image_path = f"{captures_folder}/{image_filename}"
                    if image_path not in context.screenshot_paths:
                        context.screenshot_paths.append(image_path)
                        print(f"🖼️ [ZapController] Added zapping image for R2 upload: {image_filename}")
            
            # Also add debug images for debugging failed zap detection
            debug_images = zapping_result.get('debug_images', [])
            if debug_images:
                for debug_filename in debug_images:
                    if debug_filename:
                        debug_path = f"{captures_folder}/{debug_filename}"
                        if debug_path not in context.screenshot_paths:
                            context.screenshot_paths.append(debug_path)
                            print(f"🔧 [ZapController] Added debug image for R2 upload: {debug_filename}")
            
        except Exception as e:
            print(f"⚠️ [ZapController] Failed to add zapping images to screenshot collection: {e}")

    def _add_motion_analysis_images_to_screenshots(self, context, device_id: str, iteration: int):
        """Add the 3 most recent motion analysis images to context screenshot collection for R2 upload"""
        motion_images = []
        try:
            if not hasattr(context, 'screenshot_paths'):
                context.screenshot_paths = []
            
            # Get the capture path from AV controller
            av_controller = get_controller(device_id, 'av')
            if not av_controller:
                print(f"⚠️ [ZapController] No AV controller found for motion image collection")
                return motion_images
                
            capture_folder = f"{av_controller.video_capture_path}/captures"
            
            # Load the 3 most recent analysis files using the same method as motion detection
            from shared.lib.utils.analysis_utils import load_recent_analysis_data_from_path
            data_result = load_recent_analysis_data_from_path(av_controller.video_capture_path, timeframe_minutes=5, max_count=3)
            
            if data_result['success'] and data_result['analysis_data']:
                print(f"🖼️ [ZapController] Found {len(data_result['analysis_data'])} motion analysis images")
                
                # Add the corresponding image files to screenshot collection
                for i, file_item in enumerate(data_result['analysis_data'], 1):
                    image_filename = file_item['filename']  # e.g., "capture_20240101120000.jpg"
                    image_path = f"{capture_folder}/{image_filename}"
                    
                    if image_path not in context.screenshot_paths:
                        context.screenshot_paths.append(image_path)
                        print(f"🖼️ [ZapController] Added motion analysis image {i}/3 for R2 upload: {image_filename}")
                    
                    # Store image info for result (for thumbnails in reports)
                    motion_images.append({
                        'filename': image_filename,
                        'path': image_path,
                        'timestamp': file_item['timestamp'],
                        'analysis_data': file_item.get('analysis_json', {})
                    })
            else:
                print(f"⚠️ [ZapController] No motion analysis images found: {data_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"⚠️ [ZapController] Failed to add motion analysis images to screenshot collection: {e}")
        
        return motion_images

    
    def _record_zap_step_immediately(self, context, iteration: int, max_iterations: int, action_command: str,
                                    action_result: Dict, execution_time: int, start_time: float, end_time: float,
                                    screenshot_path: str, action_edge: Dict):
        """Record zap step immediately when executed - simple sequential recording"""
        # Extract real actions from edge
        real_actions, real_retry_actions, real_failure_actions = self._extract_edge_actions(action_edge)
        
        step_result = {
            'success': action_result.get('success', False),
            'screenshot_path': screenshot_path,
            'screenshot_url': action_result.get('screenshot_url'),
            'step_start_screenshot_path': action_result.get('step_start_screenshot_path', ''),
            'message': f"Zap iteration {iteration}: {action_command} ({iteration}/{max_iterations})",  # Will be updated with step number
            'execution_time_ms': execution_time,
            'start_time': datetime.fromtimestamp(start_time).strftime('%H:%M:%S'),
            'end_time': datetime.fromtimestamp(end_time).strftime('%H:%M:%S'),
            'step_category': 'zap_action',
            'action_name': action_command,
            'iteration': iteration,
            'max_iterations': max_iterations,
            'from_node': 'live',
            'to_node': 'live',
            'actions': real_actions,
            'retryActions': real_retry_actions,
            'failureActions': real_failure_actions,
            'verifications': [],
            'verification_results': []
        }
        
        if not action_result.get('success'):
            step_result['error'] = action_result.get('error', 'Unknown error')
        
        # Record step immediately - step number shown in table
        context.record_step_immediately(step_result)
        # Simple message without redundant step number
        step_result['message'] = f"Zap iteration {iteration}: {action_command} ({iteration}/{max_iterations})"
    
    # Legacy step recording removed - using immediate recording only
    
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
            'zapping_detected_count': self.statistics.zapping_detected_count,
            'detected_languages': self.statistics.detected_languages,
            'motion_results': [r.to_dict() for r in self.statistics.analysis_results],
            'total_action_time': self.statistics.total_execution_time,
            
            # Enhanced zapping statistics
            'zapping_durations': self.statistics.zapping_durations,
            'blackscreen_durations': self.statistics.blackscreen_durations,
            'detected_channels': self.statistics.detected_channels,
            'channel_info_results': self.statistics.channel_info_results
        })