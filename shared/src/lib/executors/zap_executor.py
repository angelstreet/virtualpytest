"""
ZapExecutor - Handles zap action execution and comprehensive analysis

This controller manages:
- Zap action execution with motion detection
- Subtitle analysis using AI
- Zapping detection and analysis
- Statistics collection and reporting
"""

import os
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from shared.src.lib.utils.zap_statistics import ZapStatistics
from shared.src.lib.utils.zap_utils import (
    create_blackscreen_analysis_log,
    create_freeze_analysis_log, 
    create_combined_analysis_log,
    validate_capture_filename,
    capture_fullzap_summary
)

class ZapAnalysisResult:
    """Container for zap analysis results"""
    
    def __init__(self):
        self.motion_detected = False
        self.subtitles_detected = False
        self.zapping_detected = False
        self.detected_language = None
        self.extracted_text = ""
        self.motion_details = {}
        self.subtitle_details = {}
        self.zapping_details = {}
        self.audio_speech_detected = False
        self.audio_transcript = ""
        self.audio_language = None
        self.audio_details = {}
        self.macroblocks_detected = False
        self.quality_score = 0.0
        self.macroblock_details = {}
        self.blackscreen_duration = 0.0
        self.channel_name = ""
        self.channel_number = ""
        self.program_name = ""
        self.program_start_time = ""
        self.program_end_time = ""
        self.audio_silence_duration = 0.0  # Audio silence duration during zapping
        
        # Zap timing information
        self.zap_start_timestamp = None  # Action execution timestamp
        self.zap_end_timestamp = None  # When content appeared after blackscreen
        self.total_zap_duration = 0.0  # Total duration in seconds (action → content)
        
        self.success = False
        self.message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility"""
        return {
            "success": self.success,
            "message": self.message,
            "motion_detected": self.motion_detected,
            "subtitles_detected": self.subtitles_detected,
            "zapping_detected": self.zapping_detected,
            "detected_language": self.detected_language,
            "extracted_text": self.extracted_text,
            "motion_details": self.motion_details,
            "subtitle_analysis": self.subtitle_details,
            "zapping_analysis": self.zapping_details,
            "audio_speech_detected": self.audio_speech_detected,
            "audio_transcript": self.audio_transcript,
            "audio_language": self.audio_language,
            "audio_analysis": self.audio_details,
            "macroblocks_detected": self.macroblocks_detected,
            "quality_score": self.quality_score,
            "macroblock_analysis": self.macroblock_details,
            "blackscreen_duration": self.blackscreen_duration,
            "channel_name": self.channel_name,
            "channel_number": self.channel_number,
            "program_name": self.program_name,
            "program_start_time": self.program_start_time,
            "program_end_time": self.program_end_time,
            "audio_silence_duration": self.audio_silence_duration,
            "zap_start_timestamp": self.zap_start_timestamp,
            "zap_end_timestamp": self.zap_end_timestamp,
            "total_zap_duration": self.total_zap_duration
        }


class ZapExecutor:
    """Controller for executing zap actions with comprehensive analysis"""
    
    def __init__(self, device, userinterface_name: str):
        """Initialize ZapExecutor with device instance and userinterface name"""
        self.device = device
        self.userinterface_name = userinterface_name
        self.statistics = ZapStatistics()
        self.learned_detection_method = None  # Learn on first success
    
    def _get_max_images_for_device(self, device_model: str) -> int:
        """Get device-specific max_images for analysis based on device capabilities"""
        if 'vnc' in device_model.lower():
            return 16
        elif 'stb' in device_model.lower():
            return 25
        elif 'android_mobile' in device_model.lower():
            return 40
        elif 'android_tv' in device_model.lower():
            return 40
        elif 'apple_tv' in device_model.lower():
            return 40
        else:
            return 40
    
    def _get_sequential_images(self, latest_path: str, count: int) -> str:
        """Get sequential capture images: current, -1, -2, etc."""
        import re
        import os
        match = re.search(r'capture_(\d+)\.jpg', latest_path)
        if not match:
            return latest_path
        
        num = int(match.group(1))
        # Extract directory and filename pattern correctly
        dir_path = os.path.dirname(latest_path)
        # Get the zero-padded width from the matched string
        matched_str = match.group(0)  # e.g., 'capture_000939633.jpg'
        num_str = match.group(1)  # e.g., '000939633'
        zero_padding = len(num_str)
        
        # Generate paths with proper zero padding
        paths = [os.path.join(dir_path, f"capture_{(num-i):0{zero_padding}d}.jpg") for i in range(count)]
        return ','.join(paths)
    
    def _detect_motion_from_json(self, context) -> Dict[str, Any]:
        """
        Simple motion detection: read last 3 JSON files, check freeze/blackscreen.
        Motion = no freeze AND no blackscreen.
        Reuses existing load_recent_analysis_data_from_path function.
        
        Returns:
            Same format as verification for compatibility with _map_verification_result
        """
        try:
            # Get AV controller
            av_controller = self.device._get_controller('av')
            if not av_controller:
                return {'success': False, 'message': 'No AV controller'}
            
            # REUSE existing function (already imported elsewhere in this file)
            from backend_host.src.lib.utils.analysis_utils import load_recent_analysis_data_from_path
            data_result = load_recent_analysis_data_from_path(
                av_controller.video_capture_path, 
                timeframe_minutes=5, 
                max_count=3
            )
            
            if not data_result['success'] or not data_result['analysis_data']:
                return {'success': False, 'message': 'No analysis data found'}
            
            # Reverse for chronological order (oldest first)
            analysis_data = list(reversed(data_result['analysis_data']))
            
            # Check motion: if any frame has NO freeze AND NO blackscreen → motion!
            motion_detected = False
            frame_data = []
            
            for file_item in analysis_data:
                analysis_json = file_item.get('analysis_json', {})
                freeze = analysis_json.get('freeze', False)
                blackscreen = analysis_json.get('blackscreen', False)
                
                # Simple: NOT frozen AND NOT blackscreen = motion
                if not freeze and not blackscreen:
                    motion_detected = True
                
                # Build frame data for thumbnail extraction (existing code expects this format)
                frame_data.append({
                    'filename': file_item['filename'],
                    'timestamp': file_item['timestamp'],
                    'freeze': freeze,
                    'blackscreen': blackscreen,
                    'audio': analysis_json.get('audio', True)
                })
            
            # Return in same format as verification for compatibility
            return {
                'success': True,
                'video_ok': motion_detected,
                'audio_ok': any(f.get('audio', True) for f in frame_data),
                'total_analyzed': len(frame_data),
                'details': {
                    'details': frame_data  # Nested for compatibility with _map_verification_result
                }
            }
            
        except Exception as e:
            print(f"❌ [ZapExecutor] Motion detection error: {e}")
            return {'success': False, 'message': f'Error: {e}'}
    
    def analyze_after_zap(self, iteration: int, action_command: str, context, action_completion_time: float = None) -> ZapAnalysisResult:
        """
        Perform comprehensive analysis after a zap action - CLEAN ARCHITECTURE
        
        Args:
            action_completion_time: Timestamp when action completed (used to match zapping detection)
        """
        result = ZapAnalysisResult()
        
        # Store action timestamp as zap start time
        if action_completion_time:
            result.zap_start_timestamp = action_completion_time
        
        try:
            print(f"🔍 [ZapExecutor] Analyzing zap results for {action_command} (iteration {iteration})...")
            
            # 1. MOTION: Read from JSON directly (fast, no verification needed)
            motion_result = self._detect_motion_from_json(context)
            self._map_verification_result(result, 'motion', motion_result, context)
            
            # 2. ZAPPING: Read recent zapping from last_zapping.json (simple recency check)
            if 'chup' in action_command.lower() and action_completion_time:
                av_controller = self.device._get_controller('av')
                if av_controller:
                    capture_folder = os.path.basename(av_controller.video_capture_path)
                    zapping_data = self._read_zapping_by_action_timestamp(action_completion_time, capture_folder)
                    self._map_zapping_from_json(result, zapping_data, context)
            
            # 3. Get verification configurations (subtitles, audio)
            verification_configs = self._get_zap_verification_configs(context, iteration, action_command, action_completion_time)
            
            # Remove motion from configs (already handled above)
            verification_configs = [c for c in verification_configs if c.get('analysis_type') != 'motion']
            
            # 4. Execute remaining verifications (subtitles, audio)
            if verification_configs:
                batch_result = self._execute_verification_batch(context, verification_configs)
                
                # Map results to ZapAnalysisResult
                if batch_result.get('results'):
                    for i, verification_result in enumerate(batch_result['results']):
                        config = verification_configs[i]
                        analysis_type = config.get('analysis_type')
                        self._map_verification_result(result, analysis_type, verification_result, context)
            
            result.success = True
            result.message = f"Analysis completed for {action_command}"
            
        except Exception as e:
            result.success = False
            result.message = f"Analysis error: {e}"
            print(f"❌ [ZapExecutor] {result.message}")
        
        return result
    
    def execute_zap_iterations(self, action: str, max_iterations: int, goto_live: bool = True, audio_analysis: bool = False) -> bool:
        """Execute complete zap workflow: goto_live → zap iterations → analysis"""
        from shared.src.lib.executors.script_decorators import get_context
        
        print(f"🔄 [ZapExecutor] Starting zap execution: {max_iterations} iterations of '{action}'")
        
        self.statistics = ZapStatistics()
        self.statistics.total_iterations = max_iterations
        context = get_context()
        
        # Set context values for database recording
        context.userinterface_name = self.userinterface_name
        context.custom_data['action_command'] = action
        
        # 1. Get navigation nodes
        live_node, action_node = self._get_navigation_nodes(action)
        
        # 2. Handle goto_live if required
        if goto_live:
            print(f"🎯 [ZapExecutor] Navigating to live: {live_node}")
            
            # Use NavigationExecutor directly
            # ✅ Wrap async call with asyncio.run for sync context
            import asyncio
            result = asyncio.run(self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=self.userinterface_name,  # MANDATORY parameter
                target_node_label=live_node,
                team_id=context.team_id,
                context=context
            ))
            
            if not result.get('success', False):
                print(f"❌ [ZapExecutor] Failed to navigate to {live_node}")
                return False
            print(f"✅ [ZapExecutor] Navigated to {live_node}")
        else:
            # goto_live=false: Set device context to live position without navigation
            print(f"🎯 [ZapExecutor] Setting device position to {live_node} (goto_live=false)")
            
            # Resolve label to actual node_id using loaded tree
            actual_node_id = self.device.navigation_executor.get_node_id(live_node)
            if actual_node_id:
                self.device.navigation_executor.update_current_position(
                    node_id=actual_node_id,
                    tree_id=context.tree_id,
                    node_label=live_node
                )
                print(f"✅ [ZapExecutor] Device position set to: {live_node}")
            else:
                print(f"⚠️ [ZapExecutor] Could not find node_id for label: {live_node}")
        
        print(f"🎬 [ZapExecutor] Zap action node: {action_node}")
        
        # 3. Execute zap iterations
        for iteration in range(1, max_iterations + 1):
            print(f"🎬 [ZapExecutor] Iteration {iteration}/{max_iterations}: {action_node}")
            
            action_start_time = time.time()
            
            # Use NavigationExecutor directly
            # ✅ Wrap async call with asyncio.run for sync context
            result = asyncio.run(self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=self.userinterface_name,  # MANDATORY parameter
                target_node_label=action_node,
                team_id=context.team_id,
                context=context
            ))
            
            # ✅ Use action timestamp from navigation context (written to last_action.json)
            # This ensures perfect sync with capture_monitor's zapping detection
            nav_context = self.device.navigation_context
            action_completion_time = nav_context.get('last_action_timestamp')
            if not action_completion_time:
                # Fallback: use current time if timestamp not available
                action_completion_time = time.time()
                print(f"⚠️ [ZapExecutor] No action_timestamp found, using current time as fallback")
            
            if result.get('success', False):
                # Perform zap-specific analysis and record zap step (use completion time for matching)
                analysis_result = self.analyze_after_zap(iteration, action_node, context, action_completion_time)
                if analysis_result.success:
                    self.statistics.successful_iterations += 1
                    
                    # Print detailed analysis results (restore main branch functionality)
                    self._print_analysis_results(analysis_result)
                
                # Store analysis result for reporting
                self.statistics.analysis_results.append(analysis_result)
                
                # Update statistics counters based on analysis results
                if analysis_result.motion_detected:
                    self.statistics.motion_detected_count += 1
                if analysis_result.subtitles_detected:
                    self.statistics.subtitles_detected_count += 1
                if analysis_result.audio_speech_detected:
                    self.statistics.audio_speech_detected_count += 1
                if analysis_result.zapping_detected:
                    self.statistics.zapping_detected_count += 1
                    # Create proper zapping result data structure for statistics
                    # Use total_zap_duration_ms from top-level zapping_details (not nested in details)
                    total_zap_duration_ms = analysis_result.zapping_details.get('total_zap_duration_ms', 0)
                    zapping_duration_s = total_zap_duration_ms / 1000.0 if total_zap_duration_ms else 0.0
                    
                    zapping_result_data = {
                        'success': True,
                        'zapping_duration': zapping_duration_s,  # Total zap duration in seconds
                        'blackscreen_duration': analysis_result.blackscreen_duration,
                        'channel_name': analysis_result.channel_name,
                        'channel_number': analysis_result.channel_number,
                        'program_name': analysis_result.program_name,
                        'program_start_time': analysis_result.program_start_time,
                        'program_end_time': analysis_result.program_end_time,
                        'channel_confidence': analysis_result.zapping_details.get('confidence', 0.0)
                    }
                    self.statistics.add_zapping_result(zapping_result_data)
                    
                    detection_method = analysis_result.zapping_details.get('detection_method', 'blackscreen')
                    self.statistics.detection_methods_used.append(detection_method)
                    
                    if detection_method == 'freeze':
                        self.statistics.freeze_detected_count += 1
                if analysis_result.detected_language:
                    self.statistics.add_language(analysis_result.detected_language)
                if analysis_result.audio_language and analysis_result.audio_language != 'unknown':
                    self.statistics.add_audio_language(analysis_result.audio_language)

                # Record iteration to database
                self.statistics.record_iteration_to_db(context, iteration, analysis_result, action_start_time, time.time())
                
                # Record zap analysis step (separate from navigation step)
                self._record_zap_step(context, iteration, action_node, analysis_result, max_iterations)
            else:
                print(f"❌ [ZapExecutor] Navigation to {action_node} failed: {result.get('error', 'Unknown error')}")
        
        # 4. Handle audio analysis if requested
        if audio_analysis and self.device.device_model != 'host_vnc':
            print(f"🎤 [ZapExecutor] Performing audio analysis...")
            self._analyze_audio_menu(context)
        
        self.statistics.print_summary(action_node)
        self.statistics.store_in_context(context, action_node)
        
        # Store comprehensive zap data for report generation (same as main branch)
        if not hasattr(context, 'custom_data'):
            context.custom_data = {}
        
        context.custom_data['zap_data'] = {
            'iterations': self.statistics.total_iterations,
            'successful_iterations': self.statistics.successful_iterations,
            'motion_detected_count': self.statistics.motion_detected_count,
            'subtitles_detected_count': self.statistics.subtitles_detected_count,
            'audio_speech_detected_count': self.statistics.audio_speech_detected_count,
            'zapping_detected_count': self.statistics.zapping_detected_count,
            'detected_languages': list(self.statistics.detected_languages),
            'audio_languages': list(self.statistics.audio_languages),
            'analysis_results': self.statistics.analysis_results
        }
        print(f"📊 [ZapExecutor] Stored zap data in custom_data for report generation")
        
        if self.learned_detection_method:
            method_emoji = "⬛" if self.learned_detection_method == "blackscreen" else "🧊"
            print(f"🧠 [ZapExecutor] Learned detection method: {method_emoji} {self.learned_detection_method}")
        
        # Generate zap execution summary for reporting (like goto_live.py does)
        self._generate_zap_summary(context, action, max_iterations)
        
        return self.statistics.successful_iterations == max_iterations
    
    def _generate_zap_summary(self, context, action: str, max_iterations: int):
        """Generate zap execution summary for reporting"""
        try:
            lines = []
            lines.append(f"🎯 [ZAP] EXECUTION SUMMARY")
            lines.append(f"📱 Device: {self.device.device_name} ({self.device.device_model})")
            lines.append(f"🎬 Action: {action}")
            lines.append(f"🔄 Iterations: {self.statistics.successful_iterations}/{max_iterations}")
            lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
            lines.append(f"📊 Success Rate: {(self.statistics.successful_iterations/max_iterations)*100:.1f}%")
            
            # Add zap duration metrics if available
            if self.statistics.zapping_durations:
                avg_zap = self.statistics.average_zapping_duration
                avg_bs = self.statistics.average_blackscreen_duration
                min_zap = min(self.statistics.zapping_durations)
                max_zap = max(self.statistics.zapping_durations)
                lines.append(f"⚡ Avg Zap Duration: {avg_zap:.2f}s (range: {min_zap:.2f}s - {max_zap:.2f}s)")
                lines.append(f"⬛ Avg Blackscreen: {avg_bs:.2f}s")
                
                # Add audio silence if we have that data
                audio_silence_durations = [result.audio_silence_duration for result in self.statistics.analysis_results 
                                          if hasattr(result, 'audio_silence_duration') and result.audio_silence_duration > 0]
                if audio_silence_durations:
                    avg_audio_silence = sum(audio_silence_durations) / len(audio_silence_durations)
                    lines.append(f"🔇 Avg Audio Silence: {avg_audio_silence:.2f}s")
            
            if self.learned_detection_method:
                method_emoji = "⬛" if self.learned_detection_method == "blackscreen" else "🧊"
                lines.append(f"🧠 Detection Method: {method_emoji} {self.learned_detection_method}")
            
            context.execution_summary = "\n".join(lines)
            
        except Exception as e:
            print(f"⚠️ [ZapExecutor] Failed to generate summary: {e}")
    
    def _get_navigation_nodes(self, action: str) -> tuple[str, str]:
        """Get live node and action node based on device type"""
        if "mobile" in self.device.device_model.lower():
            return "live_fullscreen", f"live_fullscreen_{action.split('_')[-1]}"
        return "live", action
    
    def _analyze_audio_menu(self, context):
        """Perform audio menu analysis using VerificationExecutor"""
        try:
            print(f"🎧 [ZapExecutor] Starting audio menu analysis...")
            
            # Use existing navigation logic - no duplication
            audio_menu_action = "live_fullscreen_audiomenu" if "mobile" in self.device.device_model.lower() else "live_audiomenu"
            
            # Navigate to audio menu
            # ✅ Wrap async call with asyncio.run for sync context
            import asyncio
            result = asyncio.run(self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=self.userinterface_name,  # MANDATORY parameter
                target_node_label=audio_menu_action,
                team_id=context.team_id,
                context=context
            ))
            
            if result.get('success', False):
                # Single verification config - minimal
                verification_configs = [{
                    'command': 'AnalyzeLanguageMenuAI',
                    'verification_type': 'video',
                    'params': {},
                    'analysis_type': 'audio_menu'
                }]
                
                # Execute using same batch system
                batch_result = self._execute_verification_batch(context, verification_configs)
                
                # Process result
                audio_result = {"success": False, "menu_detected": False}
                if batch_result.get('success') and batch_result.get('results'):
                    verification_result = batch_result['results'][0]
                    audio_result = {
                        "success": verification_result.get('success', False),
                        "menu_detected": verification_result.get('menu_detected', False),
                        "message": verification_result.get('message', 'Audio menu analyzed')
                    }
                    
                    # Add analyzed_screenshot for main branch compatibility
                    if hasattr(context, 'screenshot_paths') and context.screenshot_paths:
                        analyzed_screenshot = context.screenshot_paths[-1]  # Use latest screenshot
                        audio_result['analyzed_screenshot'] = analyzed_screenshot
                
                context.custom_data['audio_menu_analysis'] = audio_result
                print(f"✅ [ZapExecutor] Audio menu analysis: menu_detected = {audio_result.get('menu_detected', False)}")
            else:
                print(f"❌ [ZapExecutor] Failed to navigate to audio menu")
                context.custom_data['audio_menu_analysis'] = {"success": False, "menu_detected": False}
                
        except Exception as e:
            print(f"❌ [ZapExecutor] Audio analysis failed: {e}")
            context.custom_data['audio_menu_analysis'] = {"success": False, "menu_detected": False}
    
    def _record_zap_step(self, context, iteration: int, action_node: str, analysis_result, max_iterations: int):
        """Record zap analysis step using StepExecutor"""
        try:
            from shared.src.lib.executors.step_executor import StepExecutor
            step_executor = StepExecutor(context)
            
            # Get recent screenshots from context for ZAP step (same as navigation steps)
            screenshot_paths = {}
            if hasattr(context, 'screenshot_paths') and context.screenshot_paths:
                # Use the most recent screenshots as step start/end (like navigation steps)
                recent_screenshots = context.screenshot_paths[-3:] if len(context.screenshot_paths) >= 3 else context.screenshot_paths
                
                if len(recent_screenshots) >= 1:
                    screenshot_paths['step_start_screenshot_path'] = recent_screenshots[0]
                    screenshot_paths['screenshot_path'] = recent_screenshots[-1]  # Use last as main screenshot
                if len(recent_screenshots) >= 2:
                    screenshot_paths['step_end_screenshot_path'] = recent_screenshots[-1]
                    
                print(f"🔍 [ZapExecutor] Adding {len(screenshot_paths)} screenshot paths to zap step {iteration}")
            
            # Create zap step with analysis results and screenshots
            zap_step = step_executor.create_zap_step(
                iteration=iteration,
                action_command=action_node,
                analysis_result=analysis_result.to_dict(),
                max_iterations=max_iterations,
                screenshot_paths=screenshot_paths if screenshot_paths else None
            )
            
            # Record step in context
            context.record_step_dict(zap_step)
            
        except Exception as e:
            print(f"⚠️ [ZapExecutor] Failed to record zap step: {e}")
    
    def _get_zap_verification_configs(self, context, iteration: int, action_command: str, action_completion_time: float) -> List[Dict]:
        """Get all verification configurations for zap analysis"""
        device_model = context.selected_device.device_model if context.selected_device else 'unknown'
        configs = []
        
        # Motion detection (always run)
        configs.append({
            'command': 'DetectMotionFromJson',
            'verification_type': 'video',
            'params': {'json_count': 3, 'strict_mode': False},
            'analysis_type': 'motion'
        })
        
        # Subtitle detection (if screenshots available)
        if context.screenshot_paths:
            configs.append({
                'command': 'DetectSubtitlesAI',
                'verification_type': 'video',
                'params': {'extract_text': True},
                'analysis_type': 'subtitles'
            })
        
        # Audio analysis (skip for VNC devices) - use existing audio detection command
        if device_model != 'host_vnc':
            configs.append({
                'command': 'DetectAudioSpeech',
                'verification_type': 'audio',
                'params': {'json_count': 3, 'strict_mode': False},
                'analysis_type': 'audio_speech'
            })
        
        # Skip macroblock detection for now - no valid command available
        # TODO: Implement macroblock detection command if needed
        
        # Zapping detection removed - now reads from JSON using action timestamp
        # capture_monitor detects zapping asynchronously and writes to frame JSON
        
        return configs
    
    def _execute_verification_batch(self, context, verification_configs: List[Dict]) -> Dict[str, Any]:
        """Execute a batch of verifications using the standard VerificationExecutor"""
        verification_executor = self.device.verification_executor
        if not verification_executor:
            return {"success": False, "message": f"No VerificationExecutor found for device {self.device.device_id}"}
        
        # Pass context screenshot paths as image_source_url
        image_source_url = None
        if context.screenshot_paths:
            # Check if any verification needs multiple screenshots (subtitles only)
            has_subtitles = any(config.get('command') == 'DetectSubtitlesAI' for config in verification_configs)
            if has_subtitles:
                image_source_url = self._get_sequential_images(context.screenshot_paths[-1], 3)
                print(f"🔍 [ZapExecutor] DEBUG: Using 3 sequential screenshots for subtitle detection")
            else:
                image_source_url = context.screenshot_paths[-1]
                print(f"🔍 [ZapExecutor] DEBUG: Using latest context screenshot: {image_source_url}")
        else:
            print(f"🔍 [ZapExecutor] DEBUG: No context screenshots available - will fallback to take_screenshot")
        
        print(f"🔍 [ZapExecutor] DEBUG: Calling execute_verifications with image_source_url={image_source_url}")
        import asyncio
        return asyncio.run(verification_executor.execute_verifications(
            verifications=verification_configs,
            userinterface_name=self.userinterface_name,  # MANDATORY parameter
            image_source_url=image_source_url,
            team_id=context.team_id,
            context=context
        ))
    
    def _map_verification_result(self, result: ZapAnalysisResult, analysis_type: str, verification_result: Dict, context):
        """Map verification result to ZapAnalysisResult fields"""
        success = verification_result.get('success', False)
        details = verification_result.get('details', {})
        
        if analysis_type == 'motion':
            result.motion_detected = success
            result.motion_details = verification_result
            # Ensure motion_detected is never None
            if result.motion_detected is None:
                result.motion_detected = False
            
            if success:
                # Motion detection details are in the main verification_result, not nested in details
                analyzed_count = verification_result.get('total_analyzed', 0)
                video_ok = verification_result.get('video_ok', False)
                audio_ok = verification_result.get('audio_ok', False)
                if video_ok and audio_ok:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed - both video and audio content present")
                elif video_ok:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed - video motion detected")
                elif audio_ok:
                    print(f"   🎵 Motion detected: {analyzed_count} files analyzed - audio content present")
                else:
                    print(f"   📊 Motion detected: {analyzed_count} files analyzed")
                
                # Transform details array to motion_analysis_images for report thumbnails
                # Motion detection returns nested structure: verification_result['details']['details']
                motion_result = verification_result.get('details', {})
                details = motion_result.get('details', []) if isinstance(motion_result, dict) else []
                
                if details and isinstance(details, list):
                    from shared.src.lib.utils.device_utils import add_existing_image_to_context
                    
                    motion_images = []
                    # Reverse details to show chronologically (oldest first) in report
                    chronological_details = list(reversed(details[:3]))  # Take first 3, then reverse
                    
                    for i, detail in enumerate(chronological_details):
                        if isinstance(detail, dict):
                            filename = detail.get('filename', '')
                            
                            # Use centralized function - handles hot/cold, fails fast if missing
                            image_path = add_existing_image_to_context(self.device, filename, context)
                            
                            if image_path:
                                # Image found and added to context - create motion image entry
                                motion_images.append({
                                    'path': image_path,
                                    'filename': filename,
                                    'timestamp': detail.get('timestamp', ''),
                                    'analysis_data': {
                                        'freeze': detail.get('freeze', False),
                                        'blackscreen': detail.get('blackscreen', False),
                                        'audio': detail.get('audio', True)
                                    }
                                })
                            else:
                                # Image not found - fail fast, skip this image
                                print(f"⚠️ [ZapExecutor] Motion image missing, skipping: {filename}")
                    
                    if motion_images:
                        result.motion_details['motion_analysis_images'] = motion_images
                    else:
                        print(f"⚠️ [ZapExecutor] No motion images found - motion_analysis_images not added")
        elif analysis_type == 'subtitles':
            # Extract from details (where AI results are nested)
            subtitle_details = verification_result.get('details', {})
            # Use success flag when details indicate subtitles were detected
            result.subtitles_detected = (verification_result.get('success', False) and 
                                       subtitle_details.get('subtitles_detected', False))
            result.detected_language = subtitle_details.get('detected_language')
            result.extracted_text = subtitle_details.get('combined_extracted_text', '') or subtitle_details.get('extracted_text', '')
            
            # Create flattened structure for main branch compatibility
            result.subtitle_details = {
                'success': verification_result.get('success', False),
                'subtitles_detected': result.subtitles_detected,
                'detected_language': result.detected_language,
                'extracted_text': result.extracted_text,
                'message': verification_result.get('message', '')
            }
            
            # Add analyzed_screenshot with proper hot/cold handling
            analyzed_screenshot = None
            if subtitle_details.get('image_path'):
                # Verification returned the analyzed image filename
                from shared.src.lib.utils.device_utils import add_existing_image_to_context
                filename = subtitle_details['image_path']
                analyzed_screenshot = add_existing_image_to_context(self.device, filename, context)
                if analyzed_screenshot:
                    print(f"🔍 [ZapExecutor] Subtitle analyzed screenshot found: {filename}")
                else:
                    print(f"⚠️ [ZapExecutor] Subtitle analyzed screenshot missing: {filename}")
            
            if analyzed_screenshot:
                result.subtitle_details['analyzed_screenshot'] = analyzed_screenshot
            
        elif analysis_type == 'audio_speech':
            # Extract from details (where AI results are nested) same as subtitles
            audio_details = verification_result.get('details', {})
            result.audio_speech_detected = verification_result.get('success', False) and bool(audio_details.get('combined_transcript', '').strip())
            result.audio_transcript = audio_details.get('combined_transcript', '')
            result.audio_language = audio_details.get('detected_language', 'unknown')
            
            # Create flattened structure for main branch compatibility
            result.audio_details = {
                'success': verification_result.get('success', False),
                'speech_detected': result.audio_speech_detected,
                'detected_language': result.audio_language,
                'combined_transcript': result.audio_transcript,
                'message': verification_result.get('message', ''),
                'audio_urls': audio_details.get('audio_urls', [])  # Extract from details, not top level
            }
            
        elif analysis_type == 'macroblocks':
            result.macroblocks_detected = verification_result.get('macroblocks_detected', False)
            result.quality_score = verification_result.get('quality_score', 0.0)
            result.macroblock_details = verification_result
            
        # Zapping case removed - now handled by _read_zapping_by_action_timestamp    
    def _read_zapping_by_action_timestamp(self, action_timestamp: float, capture_folder: str) -> Dict[str, Any]:
        """
        Read recent zapping detection (simplified - no timestamp matching needed).
        
        ✅ SIMPLE: If last_zapping.json exists and is recent (< 30s), that's the zapping!
        ✅ INSTANT ACCESS: Single file read, no searching needed.
        ✅ SAME PATH AS METADATA: Uses get_metadata_path() - hot or cold based on mode.
        
        Path (RAM mode): /var/www/html/stream/{capture_folder}/hot/metadata/last_zapping.json
        Path (SD mode):  /var/www/html/stream/{capture_folder}/metadata/last_zapping.json
        Written by: zapping_detector_utils._write_last_zapping_json()
        
        Args:
            action_timestamp: Unix timestamp when action was executed (for recency check)
            capture_folder: Device capture folder name (e.g., 'capture1', 'capture4')
        
        Returns:
            Complete zapping data dict, or error dict if not found/too old
        """
        # 🔍 DEBUG: Log what we're looking for
        print(f"🔍 [ZapExecutor] _read_zapping_by_action_timestamp called:")
        print(f"    action_timestamp: {action_timestamp}")
        print(f"    capture_folder: {capture_folder}")
        
        try:
            # ✅ READ FROM SAME LOCATION AS METADATA (hot or cold based on mode)
            from shared.src.lib.utils.storage_path_utils import get_metadata_path
            metadata_path = get_metadata_path(capture_folder)
            last_zapping_path = os.path.join(metadata_path, 'last_zapping.json')
            
            # 🔍 DEBUG: Show exact path being checked
            print(f"🔍 [ZapExecutor] Looking for zapping file at: {last_zapping_path}")
            print(f"    metadata_path: {metadata_path}")
            print(f"    file exists: {os.path.exists(last_zapping_path)}")
            
            if os.path.exists(last_zapping_path):
                try:
                    # Read the zapping file
                    with open(last_zapping_path, 'r') as f:
                        zapping_data = json.load(f)
                    
                    # ✅ CHECK: Is detection in progress?
                    status = zapping_data.get('status')
                    if status == 'in_progress':
                        # ✅ TIMEOUT CHECK: Is marker stale (> 5 minutes old)?
                        started_at_unix = zapping_data.get('started_at_unix')
                        timeout_seconds = zapping_data.get('timeout_seconds', 300)  # Default 5 minutes
                        
                        if started_at_unix:
                            age_seconds = time.time() - started_at_unix
                            if age_seconds > timeout_seconds:
                                print(f"🗑️  [ZapExecutor] STALE marker detected (age: {age_seconds:.0f}s > {timeout_seconds}s) - treating as failed")
                                print(f"    Marker was likely left by crashed/stuck detection process")
                                return {'success': False, 'zapping_detected': False, 'error': f'Stale in_progress marker ({age_seconds:.0f}s old)'}
                            
                            print(f"⏳ [ZapExecutor] Zapping detection IN PROGRESS - started {age_seconds:.1f}s ago")
                            print(f"    Detection file: {last_zapping_path}")
                            print(f"    Polling every 1s for up to 15s...")
                        else:
                            print(f"⏳ [ZapExecutor] Zapping detection in progress (no timestamp) - polling...")
                        
                        # Poll more frequently and for less time: every 1s for up to 15s
                        # Zapping detection should be nearly instant since capture_monitor writes the JSON immediately
                        max_polls = 15
                        poll_interval = 1.0
                        
                        for poll_attempt in range(1, max_polls + 1):
                            time.sleep(poll_interval)
                            
                            # Read again
                            try:
                                with open(last_zapping_path, 'r') as f:
                                    zapping_data = json.load(f)
                                
                                current_status = zapping_data.get('status')
                                print(f"    Poll #{poll_attempt}: status={current_status}")
                                
                                # Check if completed
                                if current_status != 'in_progress':
                                    print(f"✅ [ZapExecutor] Detection completed after {poll_attempt}s - status: {current_status}")
                                    break
                                
                                # Show progress during polling
                                if poll_attempt % 5 == 0:
                                    print(f"    Still waiting... ({poll_attempt}s elapsed)")
                                
                                # ✅ RE-CHECK: Marker may have become stale during polling
                                if started_at_unix:
                                    age_seconds = time.time() - started_at_unix
                                    if age_seconds > timeout_seconds:
                                        print(f"🗑️  [ZapExecutor] Marker became STALE during polling (age: {age_seconds:.0f}s)")
                                        return {'success': False, 'zapping_detected': False, 'error': f'Detection timeout (marker stale)'}
                            except Exception as e:
                                print(f"⚠️ [ZapExecutor] Error during poll attempt {poll_attempt}: {e}")
                                break
                        else:
                            # Timeout after max_polls
                            print(f"⏰ [ZapExecutor] Timeout after {max_polls}s - detection still in progress")
                            print(f"    This indicates capture_monitor may not be running or is stuck")
                            print(f"    Last status: {zapping_data.get('status')}")
                            return {'success': False, 'zapping_detected': False, 'error': f'Detection timeout ({max_polls}s) - likely capture_monitor issue'}
                    
                    # ✅ ONLY CHECK: Does action_timestamp match THIS action?
                    zapping_action_timestamp = zapping_data.get('action_timestamp')
                    if not zapping_action_timestamp:
                        print(f"⚠️ [ZapExecutor] No action_timestamp in zapping file")
                        return {'success': False, 'zapping_detected': False, 'error': 'No action_timestamp in zapping file'}
                    
                    timestamp_diff = abs(action_timestamp - zapping_action_timestamp)
                    
                    # ✅ Try to find last action but some time get previous
                    if timestamp_diff > 10:
                        print(f"❌ [ZapExecutor] Timestamp mismatch: {timestamp_diff:.3f}s (expected <0.1s)")
                        print(f"    action_timestamp: {action_timestamp}")
                        print(f"    zapping_timestamp: {zapping_action_timestamp}")
                        return {'success': False, 'zapping_detected': False, 'error': f'Timestamp mismatch: {timestamp_diff:.3f}s'}
                    
                    zapping_detected = zapping_data.get('zapping_detected', False)
                    
                    if zapping_detected:
                        channel_name = zapping_data.get('channel_name', '')
                        channel_number = zapping_data.get('channel_number', '')
                        program_name = zapping_data.get('program_name', '')
                        detection_type = zapping_data.get('detection_type', 'unknown')
                        print(f"📺 [ZapExecutor] {detection_type.upper()} zapping detected: {channel_name} ({channel_number}) - {program_name}")
                    
                    # Extract sequence from frame filename
                    frame_filename = zapping_data.get('frame_filename', '')
                    try:
                        sequence = int(frame_filename.split('_')[1].split('.')[0])
                    except:
                        sequence = 0
                    
                    return {
                        'success': True,
                        'zapping_detected': zapping_detected,
                        'channel_name': channel_name,
                        'channel_number': channel_number,
                        'program_name': zapping_data.get('program_name', ''),
                        'blackscreen_duration': zapping_data.get('blackscreen_duration_ms', 0) / 1000.0,
                        'blackscreen_duration_ms': zapping_data.get('blackscreen_duration_ms', 0),  # ✅ ADD: Keep ms for consistency
                        'total_zap_duration_ms': zapping_data.get('total_zap_duration_ms'),  # ✅ NEW: Total zap duration
                        'time_since_action_ms': zapping_data.get('time_since_action_ms'),  # ✅ NEW: Time from action to blackscreen end
                        'detection_type': zapping_data.get('detection_type', 'unknown'),
                        'confidence': zapping_data.get('confidence', 0.0),
                        'detected_at': zapping_data.get('detected_at'),
                        'frame_filename': frame_filename,
                        'frame_sequence': sequence,
                        'action_timestamp': zapping_data.get('action_timestamp'),
                        'audio_silence_duration': zapping_data.get('audio_silence_duration', 0.0),
                        'transition_images': zapping_data.get('transition_images', {}),  # ✅ NEW: Transition images
                        'r2_images': zapping_data.get('r2_images', {}),  # ✅ NEW: R2 URLs for transition images
                        'details': {
                            'start_time': zapping_data.get('program_start_time', ''),
                            'end_time': zapping_data.get('program_end_time', '')
                        }
                    }
                
                except Exception as e:
                    print(f"❌ [ZapExecutor] Error reading last_zapping.json: {e}")
                    return {'success': False, 'zapping_detected': False, 'error': f'Failed to read last_zapping.json: {e}'}
            
            # ❌ File not found - CLEAR FAILURE MESSAGE
            print(f"❌ [ZapExecutor] ZAP DETECTION FAILED: last_zapping.json not found at {last_zapping_path}")
            print(f"    This means capture_monitor is NOT detecting zapping events.")
            print(f"    Check if capture_monitor is running and processing frames for {capture_folder}")
            return {'success': False, 'zapping_detected': False, 'error': f'ZAP DETECTION FAILED: last_zapping.json not found at {last_zapping_path}'}
            
        except Exception as e:
            print(f"❌ [ZapExecutor] Error reading zapping detection: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'zapping_detected': False, 'error': str(e)}
    
    def _map_zapping_from_json(self, result: ZapAnalysisResult, zapping_data: Dict[str, Any], context):
        """Map zapping data from JSON to ZapAnalysisResult"""
        result.zapping_detected = zapping_data.get('zapping_detected', False)
        result.channel_name = zapping_data.get('channel_name', '')
        result.channel_number = zapping_data.get('channel_number', '')
        result.program_name = zapping_data.get('program_name', '')
        result.blackscreen_duration = zapping_data.get('blackscreen_duration', 0.0)
        result.audio_silence_duration = zapping_data.get('audio_silence_duration', 0.0)
        result.program_start_time = zapping_data.get('details', {}).get('start_time', '')
        result.program_end_time = zapping_data.get('details', {}).get('end_time', '')
        
        # Calculate and store zap timing information
        total_zap_duration_ms = zapping_data.get('total_zap_duration_ms', 0)
        if total_zap_duration_ms:
            result.total_zap_duration = total_zap_duration_ms / 1000.0  # Convert to seconds
            
            # Calculate end timestamp: start + duration
            action_timestamp = zapping_data.get('action_timestamp')
            if action_timestamp and result.zap_start_timestamp:
                result.zap_end_timestamp = result.zap_start_timestamp + result.total_zap_duration
        
        # ✅ NEW: Process transition images and R2 URLs
        transition_images = zapping_data.get('transition_images', {})
        r2_images = zapping_data.get('r2_images', {})
        transition_image_paths = []
        
        # Map to report formatter expected field names
        first_image = None  # Before blackscreen
        blackscreen_start_image = None  # First blackscreen
        blackscreen_end_image = None  # Last blackscreen
        first_content_after_blackscreen = None  # After
        
        if transition_images or r2_images:
            print(f"📸 [ZapExecutor] Processing zapping transition images...")
            
            # Map before image
            if r2_images.get('before_url'):
                first_image = r2_images['before_url']
                print(f"   📸 Before: {transition_images.get('before_frame', 'unknown')} (R2)")
            elif transition_images.get('before_thumbnail_path'):
                first_image = transition_images['before_thumbnail_path']
                if first_image not in context.screenshot_paths:
                    context.add_screenshot(first_image)
                print(f"   📸 Before: {transition_images.get('before_frame', 'unknown')} (local)")
            
            # Map first blackscreen image
            if r2_images.get('first_blackscreen_url'):
                blackscreen_start_image = r2_images['first_blackscreen_url']
                print(f"   📸 First Blackscreen: {transition_images.get('first_blackscreen_frame', 'unknown')} (R2)")
            elif transition_images.get('first_blackscreen_thumbnail_path'):
                blackscreen_start_image = transition_images['first_blackscreen_thumbnail_path']
                if blackscreen_start_image not in context.screenshot_paths:
                    context.add_screenshot(blackscreen_start_image)
                print(f"   📸 First Blackscreen: {transition_images.get('first_blackscreen_frame', 'unknown')} (local)")
            
            # Map last blackscreen image
            if r2_images.get('last_blackscreen_url'):
                blackscreen_end_image = r2_images['last_blackscreen_url']
                print(f"   📸 Last Blackscreen: {transition_images.get('last_blackscreen_frame', 'unknown')} (R2)")
            elif transition_images.get('last_blackscreen_thumbnail_path'):
                blackscreen_end_image = transition_images['last_blackscreen_thumbnail_path']
                if blackscreen_end_image not in context.screenshot_paths:
                    context.add_screenshot(blackscreen_end_image)
                print(f"   📸 Last Blackscreen: {transition_images.get('last_blackscreen_frame', 'unknown')} (local)")
            
            # Map after image
            if r2_images.get('after_url'):
                first_content_after_blackscreen = r2_images['after_url']
                print(f"   📸 After: {transition_images.get('after_frame', 'unknown')} (R2)")
            elif transition_images.get('after_thumbnail_path'):
                first_content_after_blackscreen = transition_images['after_thumbnail_path']
                if first_content_after_blackscreen not in context.screenshot_paths:
                    context.add_screenshot(first_content_after_blackscreen)
                print(f"   📸 After: {transition_images.get('after_frame', 'unknown')} (local)")
            
            # Build transition_image_paths for backward compatibility
            image_order = [
                (first_image, 'before_frame', 'Before'),
                (blackscreen_start_image, 'first_blackscreen_frame', 'First Blackscreen'),
                (blackscreen_end_image, 'last_blackscreen_frame', 'Last Blackscreen'),
                (first_content_after_blackscreen, 'after_frame', 'After')
            ]
            
            for image_url, filename_key, display_name in image_order:
                if image_url:
                    transition_image_paths.append({
                        'type': display_name,
                        'url': image_url,
                        'filename': transition_images.get(filename_key, 'unknown')
                    })
            
            # Debug log mapped fields for report formatter
            print(f"🔍 [ZapExecutor] Mapped zapping images for report:")
            print(f"   first_image: {first_image}")
            print(f"   blackscreen_start_image: {blackscreen_start_image}")
            print(f"   blackscreen_end_image: {blackscreen_end_image}")
            print(f"   first_content_after_blackscreen: {first_content_after_blackscreen}")
        
        # Calculate total zap duration for display
        total_zap_duration_ms = zapping_data.get('total_zap_duration_ms')
        time_since_action_ms = zapping_data.get('time_since_action_ms')
        
        # Create details structure for compatibility
        result.zapping_details = {
            'success': zapping_data.get('success', False),
            'zapping_detected': result.zapping_detected,
            'blackscreen_duration': result.blackscreen_duration,
            'blackscreen_duration_ms': zapping_data.get('blackscreen_duration_ms', 0),  # ✅ Keep ms
            'total_zap_duration_ms': total_zap_duration_ms,  # ✅ NEW: Total duration
            'time_since_action_ms': time_since_action_ms,  # ✅ NEW: Action delay
            'audio_silence_duration': result.audio_silence_duration,  # ✅ NEW: Audio silence duration for report
            'detection_type': zapping_data.get('detection_type', 'unknown'),
            'confidence': zapping_data.get('confidence', 0.0),
            'channel_info': {
                'channel_name': result.channel_name,
                'channel_number': result.channel_number,
                'program_name': result.program_name,
                'start_time': result.program_start_time,
                'end_time': result.program_end_time,
                'confidence': zapping_data.get('confidence', 0.0)
            },
            'frame_filename': zapping_data.get('frame_filename', ''),
            'transition_images': transition_image_paths,  # ✅ NEW: Transition images for display
            # ✅ ADD: Report formatter expected field names for thumbnails/modal
            'first_image': first_image,  # Before blackscreen
            'blackscreen_start_image': blackscreen_start_image,  # First blackscreen
            'blackscreen_end_image': blackscreen_end_image,  # Last blackscreen
            'first_content_after_blackscreen': first_content_after_blackscreen,  # After
            'message': 'Zapping detected from capture_monitor' if result.zapping_detected else zapping_data.get('error', 'No zapping detected'),
            'error': zapping_data.get('error')  # ✅ Propagate error for clear failure messages
        }
        
        # Add R2 images (transition images uploaded when zapping confirmed)
        if r2_images:
            result.zapping_details['r2_images'] = r2_images
        # Legacy: Keep compatibility with old format
        elif zapping_data.get('images'):
            result.zapping_details['r2_images'] = zapping_data['images']

    # Audio menu analysis integrated into ZapExecutor using VerificationExecutor
    
    # OLD ZAPPING DETECTION METHODS REMOVED - Now reads from JSON via _read_zapping_by_action_timestamp()
    # Deleted methods: _analyze_zapping, _try_blackscreen_detection, _try_freeze_detection,
    # _add_zapping_images_to_screenshots, _create_failure_mosaic
    
    def _add_motion_analysis_images_to_screenshots(self, context, iteration: int):
        """Add the 3 most recent motion analysis images to context screenshot collection for R2 upload"""
        motion_images = []
        try:
            if not hasattr(context, 'screenshot_paths'):
                context.screenshot_paths = []
            
            # Get the capture path from AV controller
            av_controller = self.device._get_controller('av')
            if not av_controller:
                print(f"⚠️ [ZapExecutor] No AV controller found for motion image collection")
                return motion_images
                
            capture_folder = f"{av_controller.video_capture_path}/captures"
            
            # Load the 3 most recent analysis files using the same method as motion detection
            from  backend_host.src.lib.utils.analysis_utils import load_recent_analysis_data_from_path
            data_result = load_recent_analysis_data_from_path(av_controller.video_capture_path, timeframe_minutes=5, max_count=3)
            
            if data_result['success'] and data_result['analysis_data']:
                print(f"🖼️ [ZapExecutor] Found {len(data_result['analysis_data'])} motion analysis images")
                
                # Reverse for chronological order (oldest first) in reports
                analysis_data_chronological = list(reversed(data_result['analysis_data']))
                
                # Add the corresponding image files to screenshot collection
                for i, file_item in enumerate(analysis_data_chronological, 1):
                    image_filename = file_item['filename']  # e.g., "capture_0001.jpg"
                    image_path = f"{capture_folder}/{image_filename}"
                    # Validate filename format before adding to prevent FileNotFoundError on malformed files
                    if not validate_capture_filename(image_filename):
                        print(f"🔍 [ZapExecutor] Skipped motion analysis image with invalid format: {image_filename}")
                        continue
                    
                    if image_path not in context.screenshot_paths:
                        context.add_screenshot(image_path)  # Auto-copies to cold
                        print(f"🖼️ [ZapExecutor] Added motion analysis image {i}/3: {image_filename}")
                    
                    # Store image info for result (for thumbnails in reports)
                    motion_images.append({
                        'filename': image_filename,
                        'path': image_path,
                        'timestamp': file_item['timestamp'],
                        'analysis_data': file_item.get('analysis_json', {})
                    })
            else:
                print(f"⚠️ [ZapExecutor] No motion analysis images found: {data_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"⚠️ [ZapExecutor] Failed to add motion analysis images to screenshot collection: {e}")
        
        return motion_images
    
    def _print_analysis_results(self, analysis_result):
        """Print detailed analysis results to console (restore main branch functionality)"""
        print("\nAnalysis Results:")
        
        # Motion Detection
        motion_status = "✅ DETECTED" if analysis_result.motion_detected else "❌ NOT DETECTED"
        print(f"Motion Detection: {motion_status}")
        if analysis_result.motion_details.get('message'):
            print(f"Details: {analysis_result.motion_details.get('message')}")
        
        # Subtitle Detection
        subtitle_status = "✅ DETECTED" if analysis_result.subtitles_detected else "❌ NOT DETECTED"
        print(f"Subtitle Detection: {subtitle_status}")
        if analysis_result.subtitles_detected:
            if analysis_result.detected_language:
                print(f"Language: {analysis_result.detected_language}")
            if analysis_result.extracted_text:
                text_preview = analysis_result.extracted_text[:100] + "..." if len(analysis_result.extracted_text) > 100 else analysis_result.extracted_text
                print(f"Text: {text_preview}")
        else:
            print("Details: AI Subtitles not detected")
        
        # Audio Speech Detection
        audio_status = "✅ DETECTED" if analysis_result.audio_speech_detected else "❌ NOT DETECTED"
        print(f"Audio Speech Detection: {audio_status}")
        if analysis_result.audio_speech_detected:
            if analysis_result.audio_transcript:
                transcript_preview = analysis_result.audio_transcript[:50] + "..." if len(analysis_result.audio_transcript) > 50 else analysis_result.audio_transcript
                language_info = f" ({analysis_result.audio_language})" if analysis_result.audio_language and analysis_result.audio_language != 'unknown' else ""
                print(f"Details: Speech detected: '{transcript_preview}'{language_info}")
        else:
            # Check if there's a message from audio analysis
            audio_message = analysis_result.audio_details.get('message', 'Audio analysis completed: 0/1 segments with speech')
            print(f"Details: {audio_message}")
        
        # Zapping Detection (only for chup actions)
        if 'chup' in analysis_result.message.lower():
            zapping_status = "✅ DETECTED" if analysis_result.zapping_detected else "❌ NOT DETECTED"
            print(f"Zapping Detection: {zapping_status}")
            if analysis_result.zapping_detected:
                # ✅ NEW: Display comprehensive duration information
                details = analysis_result.zapping_details
                
                # Total zap duration (action → after blackscreen)
                total_zap_duration_ms = details.get('total_zap_duration_ms')
                if total_zap_duration_ms:
                    print(f"   📊 Total Zap Duration: {total_zap_duration_ms}ms ({total_zap_duration_ms/1000:.2f}s)")
                
                # Timing information (start/end timestamps)
                if analysis_result.zap_start_timestamp and analysis_result.zap_end_timestamp:
                    from datetime import datetime
                    start_dt = datetime.fromtimestamp(analysis_result.zap_start_timestamp)
                    end_dt = datetime.fromtimestamp(analysis_result.zap_end_timestamp)
                    print(f"   ⏰ Start: {start_dt.strftime('%H:%M:%S.%f')[:-3]} | End: {end_dt.strftime('%H:%M:%S.%f')[:-3]}")
                
                # Blackscreen duration
                blackscreen_duration_ms = details.get('blackscreen_duration_ms', 0)
                if blackscreen_duration_ms > 0:
                    print(f"   ⬛ Blackscreen Duration: {blackscreen_duration_ms}ms ({blackscreen_duration_ms/1000:.2f}s)")
                
                # Audio silence duration
                if analysis_result.audio_silence_duration > 0:
                    print(f"   🔇 Audio Silence: {analysis_result.audio_silence_duration:.2f}s")
                
                # Time from action to blackscreen end
                time_since_action_ms = details.get('time_since_action_ms')
                if time_since_action_ms:
                    print(f"   ⏱️  Action Delay: {time_since_action_ms}ms (action → blackscreen end)")
                
                # Channel info
                if analysis_result.channel_name:
                    channel_info = analysis_result.channel_name
                    if analysis_result.channel_number:
                        channel_info += f" ({analysis_result.channel_number})"
                    if analysis_result.program_name:
                        channel_info += f" - {analysis_result.program_name}"
                    print(f"   📺 Channel: {channel_info}")
                    if analysis_result.program_start_time and analysis_result.program_end_time:
                        print(f"   🕐 Program Time: {analysis_result.program_start_time}-{analysis_result.program_end_time}")
                
                # Transition images
                transition_images = details.get('transition_images', [])
                if transition_images:
                    print(f"   📸 Transition Images: {len(transition_images)} frames captured")
                    for img in transition_images:
                        img_type = img.get('type', 'Unknown')
                        filename = img.get('filename', 'unknown')
                        print(f"      - {img_type}: {filename}")
            else:
                # Show failure reason from zapping details - highlight if actual error
                zapping_error = analysis_result.zapping_details.get('error')
                zapping_message = analysis_result.zapping_details.get('message', 'Zapping not detected')
                if zapping_error:
                    print(f"❌ ERROR: {zapping_error}")
                else:
                    print(f"Details: {zapping_message}")
        
        print()  # Add blank line after analysis results
