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
    
    def execute_zap_iterations(self, context, action_edge, action_command: str, max_iterations: int, blackscreen_area: str = None) -> bool:
        """Execute multiple zap iterations with analysis"""
        print(f"🔄 [ZapController] Starting {max_iterations} iterations of '{action_command}'...")
        
        self.statistics = ZapStatistics()
        self.statistics.total_iterations = max_iterations
        self.blackscreen_area = blackscreen_area  # Store for later use
        
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
        
        # Store the action end time in context for zapping analysis
        context.last_action_end_time = end_time
        
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
        if analysis_result.zapping_detected:
            self.statistics.zapping_detected_count += 1
            # Add enhanced zapping result details
            self.statistics.add_zapping_result(analysis_result.zapping_details)
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
            
            # Use the actual action end time as key release timestamp
            key_release_timestamp = action_end_time if action_end_time else time.time() - 5
            
            # Get device model directly from context - always needed for screen dimensions
            device_model = context.selected_device.device_model if context.selected_device else 'unknown'
            
            # Simple resolution based on device model - only 2 cases
            if device_model in ['android_mobile', 'ios_mobile']:
                screen_width = 1024
                screen_height = 768
                print(f"🎯 [ZapController] Using mobile resolution for {device_model}: {screen_width}x{screen_height}")
            else:
                screen_width = 1920
                screen_height = 1080
                print(f"🎯 [ZapController] Using default resolution for {device_model}: {screen_width}x{screen_height}")
            
            # Parse blackscreen area from parameter or use default
            if blackscreen_area:
                try:
                    # Parse "x,y,width,height" format
                    x, y, width, height = map(int, blackscreen_area.split(','))
                    
                    # Validate that custom area fits within detected screen resolution
                    if (x + width > screen_width or y + height > screen_height or x < 0 or y < 0):
                        print(f"⚠️ [ZapController] Custom blackscreen area {x},{y},{width},{height} exceeds device resolution {screen_width}x{screen_height}, using device-appropriate default")
                        blackscreen_area = None  # Fall back to device-appropriate default
                    else:
                        analysis_rectangle = {'x': x, 'y': y, 'width': width, 'height': height}
                        print(f"🎯 [ZapController] Using validated custom blackscreen area: {analysis_rectangle}")
                except (ValueError, IndexError) as e:
                    print(f"⚠️ [ZapController] Invalid blackscreen_area format '{blackscreen_area}', using device-appropriate default. Error: {e}")
                    blackscreen_area = None
            
            if not blackscreen_area:
                # Standard banner height for all devices
                banner_height = 300
                
                # Calculate content area (exclude banner and bottom controls)
                content_height = screen_height - banner_height - 100  # Leave margin for bottom controls
                analysis_rectangle = {'x': 0, 'y': banner_height, 'width': screen_width, 'height': content_height}
                print(f"🎯 [ZapController] Using device-model-based blackscreen area: {analysis_rectangle}")
            
            # Calculate banner region as the remaining area below blackscreen area
            # This assumes full screen width and starts where blackscreen area ends
            detected_screen_width = analysis_rectangle['width']  # Use same width as blackscreen area
            detected_screen_height = screen_height  # Use the detected/default screen height
            banner_start_y = analysis_rectangle['y'] + analysis_rectangle['height']
            banner_height = detected_screen_height - banner_start_y
            banner_region = {'x': analysis_rectangle['x'], 'y': banner_start_y, 'width': detected_screen_width, 'height': banner_height}
            print(f"🎯 [ZapController] Calculated banner area: {banner_region}")
            
            # Call the new zapping detection method
            zapping_result = video_controller.detect_zapping(
                folder_path=capture_folder,
                key_release_timestamp=key_release_timestamp,
                analysis_rectangle=analysis_rectangle,
                banner_region=banner_region,
                max_images=8  # Analyze up to 8 images (8 seconds of capture)
            )
            
            if zapping_result.get('success', False):
                zapping_detected = zapping_result.get('zapping_detected', False)
                blackscreen_duration = zapping_result.get('blackscreen_duration', 0.0)
                channel_info = zapping_result.get('channel_info', {})
                
                if zapping_detected:
                    print(f"✅ [ZapController] Zapping detected - Duration: {blackscreen_duration}s")
                    if channel_info.get('channel_name'):
                        print(f"   📺 Channel: {channel_info['channel_name']}")
                    if channel_info.get('program_name'):
                        print(f"   📺 Program: {channel_info['program_name']}")
                else:
                    print(f"⚠️ [ZapController] No zapping sequence detected")
                
                return {
                    "success": True,
                    "zapping_detected": zapping_detected,
                    "blackscreen_duration": blackscreen_duration,
                    "channel_info": channel_info,
                    "message": f"Zapping {'detected' if zapping_detected else 'not detected'}",
                    "details": zapping_result
                }
            else:
                error_msg = zapping_result.get('error', 'Unknown error')
                print(f"❌ [ZapController] Zapping analysis failed: {error_msg}")
                return {
                    "success": False,
                    "zapping_detected": False,
                    "message": f"Zapping analysis failed: {error_msg}"
                }
                
        except Exception as e:
            print(f"❌ [ZapController] Zapping analysis error: {e}")
            return {"success": False, "message": f"Zapping analysis error: {e}"}

    
    def _record_step_result(self, context, iteration: int, max_iterations: int, action_command: str,
                          action_result: Dict, execution_time: int, start_time: float, end_time: float,
                          analysis_result: ZapAnalysisResult, screenshot_path: str, action_edge: Dict):
        """Record step result in context"""
        step_num = len(context.step_results) + 1
        
        # Extract real actions from edge
        real_actions, real_retry_actions, real_failure_actions = self._extract_edge_actions(action_edge)
        
        # Collect all screenshots for this zap iteration (align with navigation behavior)
        action_screenshots = []
        
        # 1. Main zap screenshot
        if screenshot_path:
            action_screenshots.append(screenshot_path)
        
        # 2. Analysis screenshots (if different from main screenshot)
        if analysis_result.subtitle_details.get('screenshot_path') and analysis_result.subtitle_details['screenshot_path'] != screenshot_path:
            action_screenshots.append(analysis_result.subtitle_details['screenshot_path'])
        
        if analysis_result.audio_menu_details.get('screenshot_path') and analysis_result.audio_menu_details['screenshot_path'] != screenshot_path:
            action_screenshots.append(analysis_result.audio_menu_details['screenshot_path'])
        
        step_result = {
            'step_number': step_num,
            'success': action_result.get('success', False),
            'screenshot_path': action_result.get('screenshot_path', ''),
            'screenshot_url': action_result.get('screenshot_url'),
            'action_screenshots': action_screenshots,  # Add this field to match navigation behavior
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
            'zapping_analysis': analysis_result.zapping_details,
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