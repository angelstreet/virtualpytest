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
            "program_end_time": self.program_end_time
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
        match = re.search(r'capture_(\d+)\.jpg', latest_path)
        if not match:
            return latest_path
        
        num = int(match.group(1))
        base = latest_path.replace(f'capture_{num}.jpg', '')
        paths = [f"{base}capture_{num-i}.jpg" for i in range(count)]
        return ','.join(paths)
    
    def analyze_after_zap(self, iteration: int, action_command: str, context, action_start_time: float = None) -> ZapAnalysisResult:
        """Perform comprehensive analysis after a zap action - CLEAN ARCHITECTURE"""
        result = ZapAnalysisResult()
        
        try:
            print(f"🔍 [ZapExecutor] Analyzing zap results for {action_command} (iteration {iteration})...")
            
            # Get verification configurations
            verification_configs = self._get_zap_verification_configs(context, iteration, action_command, action_start_time)
            
            # Execute all verifications in one batch
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
            result = self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                target_node_label=live_node,
                team_id=context.team_id,
                context=context
            )
            
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
            result = self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                target_node_label=action_node,
                team_id=context.team_id,
                context=context
            )
            
            if result.get('success', False):
                # Perform zap-specific analysis and record zap step
                analysis_result = self.analyze_after_zap(iteration, action_node, context, action_start_time)
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
                    zapping_result_data = {
                        'success': True,
                        'zapping_duration': analysis_result.zapping_details.get('details', {}).get('zapping_duration', 0.0),
                        'blackscreen_duration': analysis_result.blackscreen_duration,
                        'channel_name': analysis_result.channel_name,
                        'channel_number': analysis_result.channel_number,
                        'program_name': analysis_result.program_name,
                        'program_start_time': analysis_result.program_start_time,
                        'program_end_time': analysis_result.program_end_time,
                        'channel_confidence': analysis_result.zapping_details.get('details', {}).get('channel_confidence', 0.0)
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
            result = self.device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                target_node_label=audio_menu_action,
                team_id=context.team_id,
                context=context
            )
            
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
    
    def _get_zap_verification_configs(self, context, iteration: int, action_command: str, action_start_time: float) -> List[Dict]:
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
        
        # Zapping detection (only for channel up actions)
        if 'chup' in action_command.lower():
            # Banner region for channel analysis (same as main branch)
            if 'android_mobile' in device_model:
                banner_region = {'x': 470, 'y': 230, 'width': 280, 'height': 70}
            else:
                banner_region = {'x': 245, 'y': 830, 'width': 1170, 'height': 120}
            
            configs.append({
                'command': 'DetectZapping',
                'verification_type': 'video',
                'params': {
                    'key_release_timestamp': action_start_time or time.time(),
                    'analysis_rectangle': {'x': 200, 'y': 0, 'width': 400, 'height': 200},
                    'banner_region': banner_region,
                    'max_images': self._get_max_images_for_device(device_model)
                },
                'analysis_type': 'zapping'
            })
        
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
        return verification_executor.execute_verifications(verification_configs, 
                                                         image_source_url=image_source_url,
                                                         team_id=context.team_id,
                                                         context=context)
    
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
            
            # DEBUG: Log the complete verification_result structure
            print(f"🔍 [ZapExecutor] DEBUG: Motion verification_result keys: {list(verification_result.keys())}")
            print(f"🔍 [ZapExecutor] DEBUG: Motion success: {success}")
            print(f"🔍 [ZapExecutor] DEBUG: Motion details type: {type(verification_result.get('details'))}")
            print(f"🔍 [ZapExecutor] DEBUG: Motion details content: {verification_result.get('details')}")
            
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
                print(f"🔍 [ZapExecutor] DEBUG: Motion details for thumbnails - type: {type(details)}, length: {len(details) if isinstance(details, list) else 'N/A'}")
                print(f"🔍 [ZapExecutor] DEBUG: Motion details content: {details}")
                
                if details and isinstance(details, list):
                    print(f"🔍 [ZapExecutor] DEBUG: Processing {len(details)} motion details for thumbnails")
                    from shared.src.lib.utils.device_utils import add_existing_image_to_context
                    
                    motion_images = []
                    # Reverse details to show chronologically (oldest first) in report
                    chronological_details = list(reversed(details[:3]))  # Take first 3, then reverse
                    
                    for i, detail in enumerate(chronological_details):
                        print(f"🔍 [ZapExecutor] DEBUG: Processing detail[{i}] (chronological): {detail}")
                        if isinstance(detail, dict):
                            filename = detail.get('filename', '')
                            
                            # Use centralized function - handles hot/cold, fails fast if missing
                            image_path = add_existing_image_to_context(self.device, filename, context)
                            
                            if image_path:
                                # Image found and added to context - create motion image entry
                                print(f"🔍 [ZapExecutor] DEBUG: Motion image found: {filename} -> {image_path}")
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
                    
                    print(f"🔍 [ZapExecutor] DEBUG: Created {len(motion_images)} motion_analysis_images (from {len(chronological_details)} analyzed)")
                    if motion_images:
                        result.motion_details['motion_analysis_images'] = motion_images
                        print(f"🔍 [ZapExecutor] DEBUG: Added motion_analysis_images to result.motion_details")
                    else:
                        print(f"⚠️ [ZapExecutor] No motion images found - motion_analysis_images not added")
                else:
                    print(f"🔍 [ZapExecutor] DEBUG: No valid details array for motion thumbnails")
            
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
            
        elif analysis_type == 'zapping':
            # Zapping results are in details, but also check direct fields for compatibility
            zapping_details = verification_result.get('details', {})
            
            # Extract duration first - check multiple possible field names
            # Note: freeze detection returns 'freeze_duration', blackscreen returns 'blackscreen_duration'
            # Use 'is not None' to properly handle 0.0 values
            duration = None
            for key in ['blackscreen_duration', 'freeze_duration', 'duration']:
                if duration is None and zapping_details.get(key) is not None:
                    duration = zapping_details.get(key)
                    break
            if duration is None:
                for key in ['blackscreen_duration', 'freeze_duration', 'duration']:
                    if verification_result.get(key) is not None:
                        duration = verification_result.get(key)
                        break
            
            result.blackscreen_duration = duration if duration is not None else 0.0
            
            # Zapping is only detected if success=True AND duration > 0
            # This ensures coherence: detected = True only when we have actual duration
            result.zapping_detected = (
                verification_result.get('success', False) and 
                result.blackscreen_duration > 0.0
            )
            # Extract channel info from details - channel info is nested under 'channel_info' key
            channel_info = zapping_details.get('channel_info', {}) if zapping_details else {}
            result.channel_name = channel_info.get('channel_name', '')
            result.channel_number = channel_info.get('channel_number', '')
            result.program_name = channel_info.get('program_name', '')
            result.program_start_time = channel_info.get('start_time', '')
            result.program_end_time = channel_info.get('end_time', '')
            
            # Create flattened structure for main branch compatibility
            result.zapping_details = {
                'success': verification_result.get('success', False),
                'zapping_detected': result.zapping_detected,
                'blackscreen_duration': result.blackscreen_duration,
                'zapping_duration': verification_result.get('zapping_duration', 0),
                'analyzed_images': verification_result.get('analyzed_images', 0),
                'channel_info': channel_info,
                'message': verification_result.get('message', '')
            }
            
            # Add zapping sequence images for main branch compatibility
            if result.zapping_detected:
                # Extract 4-image sequence from verification result details (nested structure)
                details = verification_result.get('details', {})
                result.zapping_details['first_image'] = details.get('first_image')
                result.zapping_details['blackscreen_start_image'] = details.get('blackscreen_start_image')
                result.zapping_details['blackscreen_end_image'] = details.get('blackscreen_end_image')
                result.zapping_details['first_content_after_blackscreen'] = details.get('first_content_after_blackscreen')
                
                # Add zapping images to R2 upload queue with full paths
                av_controller = self.device._get_controller('av')
                if av_controller and hasattr(av_controller, 'video_capture_path'):
                    capture_folder = f"{av_controller.video_capture_path}/captures"
                    
                    zapping_filenames = [
                        details.get('first_image'),
                        details.get('blackscreen_start_image'),
                        details.get('blackscreen_end_image'),
                        details.get('first_content_after_blackscreen')
                    ]
                    
                    if not hasattr(context, 'screenshot_paths'):
                        context.screenshot_paths = []
                    
                    for filename in zapping_filenames:
                        if filename:
                            full_path = f"{capture_folder}/{filename}"
                            if full_path not in context.screenshot_paths:
                                context.add_screenshot(full_path)  # Auto-copies to cold
                                print(f"🔍 [ZapExecutor] DEBUG: Added zapping image: {filename}")
            
    

    # Audio menu analysis integrated into ZapExecutor using VerificationExecutor
    
    def _analyze_zapping(self, context, iteration: int, action_command: str, action_start_time: float = None) -> Dict[str, Any]:
        """Smart zapping analysis - learn on first success, then stick with that method."""
        
        print(f"🔍 [ZapExecutor] Analyzing zapping sequence for {action_command} (iteration {iteration})...")
        
        # If we already learned the method, use it directly
        if self.learned_detection_method:
            print(f"🧠 [ZapExecutor] Using learned method: {self.learned_detection_method}")
            if self.learned_detection_method == 'freeze':
                zapping_result = self._try_freeze_detection(context, iteration, action_command, action_start_time)
                if not zapping_result.get('zapping_detected', False):
                    # Update error message to show which method failed
                    zapping_result['message'] = "Zapping Detection: ❌ NOT DETECTED"
                    zapping_result['details'] = "No freeze detected"
                return zapping_result
            else:
                zapping_result = self._try_blackscreen_detection(context, iteration, action_command, action_start_time)
                if not zapping_result.get('zapping_detected', False):
                    # Update error message to show which method failed
                    zapping_result['message'] = "Zapping Detection: ❌ NOT DETECTED"
                    zapping_result['details'] = "No blackscreen detected"
                return zapping_result
        
        # First time or no method learned yet - try blackscreen first
        print(f"🔍 [ZapExecutor] Learning phase - trying blackscreen first...")
        zapping_result = self._try_blackscreen_detection(context, iteration, action_command, action_start_time)
        
        # If blackscreen succeeds, learn it
        if zapping_result.get('zapping_detected', False):
            self.learned_detection_method = 'blackscreen'
            print(f"✅ [ZapExecutor] Learned method: blackscreen (will use for all future zaps)")
            return zapping_result
        
        # If blackscreen fails, try freeze as fallback
        print(f"🔄 [ZapExecutor] Blackscreen failed, trying freeze...")
        zapping_result = self._try_freeze_detection(context, iteration, action_command, action_start_time)
        
        # If freeze succeeds, learn it
        if zapping_result.get('zapping_detected', False):
            self.learned_detection_method = 'freeze'
            print(f"✅ [ZapExecutor] Learned method: freeze (will use for all future zaps)")
            return zapping_result
        
        # Both methods failed - provide detailed error message and verification images
        print(f"❌ [ZapExecutor] Both blackscreen and freeze detection failed")
        
        # For both methods failed, we need to get the images ourselves since no detection method succeeded
        av_controller = self.device._get_controller('av')
        analyzed_screenshots = []
        
        if av_controller:
            capture_folder = getattr(av_controller, 'video_capture_path', None)
            if capture_folder:
                # Get images using the same method as detection would use
                device_model = context.selected_device.device_model if context.selected_device else 'unknown'
                max_images = self._get_max_images_for_device(device_model)
                
                from backend_host.src.controllers.verification.video_content_helpers import VideoContentHelpers
                content_helpers = VideoContentHelpers(av_controller, "ZapExecutor")
                
                key_release_timestamp = action_start_time or time.time()
                image_data = content_helpers._get_images_after_timestamp(capture_folder, key_release_timestamp, max_count=max_images)
                
                if image_data:
                    analyzed_screenshots = [img['path'] for img in image_data]
                    print(f"🔍 [ZapExecutor] Using {len(analyzed_screenshots)} images for both methods failed mosaic")
                
                # Create failure mosaic for both methods failed
                mosaic_path = self._create_failure_mosaic(context, analyzed_screenshots, "both_failed")
                
                # Create combined analysis log for both methods
                analysis_log = create_combined_analysis_log(analyzed_screenshots, key_release_timestamp)
        
        return {
            "success": False,
            "zapping_detected": False,
            "detection_method": "both_failed",
            "transition_type": "none",
            "blackscreen_duration": 0.0,
            "message": "Zapping Detection: ❌ NOT DETECTED",
            "error": "Both blackscreen and freeze detection failed",
            "details": "No blackscreen or freeze transition detected",
            "analyzed_images": len(analyzed_screenshots),
            "failure_mosaic_path": mosaic_path,
            "mosaic_images_count": len(analyzed_screenshots),
            "analysis_log": analysis_log
        }
    
    def _try_blackscreen_detection(self, context, iteration: int, action_command: str, action_start_time: float) -> Dict[str, Any]:
        """Try blackscreen detection method - extracted existing logic."""
        try:
            print(f"⬛ [ZapExecutor] Trying blackscreen detection...")
            
            # Get video verification controller
            video_controller = self.device._get_controller('verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {self.device.device_id}"}
            
            # Get the folder path where images are captured
            av_controller = self.device._get_controller('av')
            if not av_controller:
                return {"success": False, "message": f"No AV controller found for device {self.device.device_id}"}
            
            capture_folder = getattr(av_controller, 'video_capture_path', None)
            if not capture_folder:
                return {"success": False, "message": "No capture folder available"}
            
            # Use action start time to catch blackscreen that happens during the action
            key_release_timestamp = action_start_time or time.time()
            
            # Get analysis areas (same as original)
            device_model = context.selected_device.device_model if context.selected_device else 'unknown'
            
            # Smaller uniform rectangle for all devices: 200,0, 400, 200 (80k pixels)
            analysis_rectangle = {'x': 200, 'y': 0, 'width': 400, 'height': 200}
            
            if device_model in ['android_mobile', 'ios_mobile']:
                banner_region = {'x': 470, 'y': 230, 'width': 280, 'height': 70}
            else:
                banner_region = {'x': 245, 'y': 830, 'width': 1170, 'height': 120}
            
            # Device-specific timeout using helper method
            max_images = self._get_max_images_for_device(device_model)
            
            # Call enhanced blackscreen zapping detection with device-specific timeout and threshold
            zapping_result = video_controller.detect_zapping(
                folder_path=capture_folder,
                key_release_timestamp=key_release_timestamp,
                analysis_rectangle=analysis_rectangle,
                banner_region=banner_region,
                max_images=max_images,
                device_model=device_model
            )
            
            if zapping_result.get('success', False) and zapping_result.get('zapping_detected', False):
                blackscreen_duration = zapping_result.get('blackscreen_duration', 0.0)
                print(f"✅ [ZapExecutor] Blackscreen zapping detected - Duration: {blackscreen_duration}s")
                
                # Add zapping images to context
                self._add_zapping_images_to_screenshots(context, zapping_result, capture_folder)
                
                result = {
                    "success": True,
                    "zapping_detected": True,
                    "detection_method": "blackscreen",
                    "transition_type": "blackscreen",
                    "blackscreen_duration": blackscreen_duration,
                    "zapping_duration": zapping_result.get('zapping_duration', 0.0),
                    "first_image": zapping_result.get('first_image'),
                    "blackscreen_start_image": zapping_result.get('blackscreen_start_image'),
                    "blackscreen_end_image": zapping_result.get('blackscreen_end_image'),
                    "first_content_after_blackscreen": zapping_result.get('first_content_after_blackscreen'),
                    "channel_detection_image": zapping_result.get('channel_detection_image'),
                    "last_image": zapping_result.get('last_image'),
                    "channel_info": zapping_result.get('channel_info', {}),
                    "analyzed_images": zapping_result.get('analyzed_images', 0),
                    "total_images_available": zapping_result.get('total_images_available', 0),
                    "debug_images": zapping_result.get('debug_images', []),
                    "early_stopped": zapping_result.get('early_stopped', False),
                    "coverage_seconds": 6,
                    "sub_second_precision": True,
                    "message": f"Enhanced blackscreen zapping detected (analyzed {zapping_result.get('analyzed_images', 0)} images, early_stopped={zapping_result.get('early_stopped', False)})",
                    "details": zapping_result
                }
                return result
            else:
                print(f"❌ [ZapExecutor] Blackscreen detection failed")
                
                # Use the debug_images from the detection result - these are the actual analyzed images
                debug_images = zapping_result.get('debug_images', [])
                captures_folder = os.path.join(capture_folder, 'captures')
                analyzed_screenshots = []
                
                for filename in debug_images:
                    image_path = os.path.join(captures_folder, filename)
                    if os.path.exists(image_path):
                        analyzed_screenshots.append(image_path)
                
                print(f"🔍 [ZapExecutor] Using {len(analyzed_screenshots)} actual analyzed images for blackscreen mosaic")
                
                # Create failure mosaic with blackscreen analysis data
                mosaic_path = self._create_failure_mosaic(context, analyzed_screenshots, "blackscreen", zapping_result)
                
                # Create detailed analysis log for modal display
                analysis_log = create_blackscreen_analysis_log(analyzed_screenshots, zapping_result, key_release_timestamp)
                
                return {
                    "success": False,
                    "zapping_detected": False,
                    "detection_method": "blackscreen",
                    "transition_type": "none",
                    "blackscreen_duration": 0.0,
                    "analyzed_images": len(analyzed_screenshots),
                    "message": "Blackscreen detection failed",
                    "error": "No blackscreen detected",
                    "details": f"No blackscreen transition detected (analyzed {len(analyzed_screenshots)} images)",
                    "failure_mosaic_path": mosaic_path,
                    "mosaic_images_count": len(analyzed_screenshots),
                    "analysis_log": analysis_log
                }
                
        except Exception as e:
            return {
                "success": False,
                "zapping_detected": False,
                "detection_method": "blackscreen",
                "transition_type": "none",
                "blackscreen_duration": 0.0,
                "message": "Blackscreen detection failed",
                "error": str(e),
                "details": f"Blackscreen detection error: {str(e)}"
            }
    
    def _try_freeze_detection(self, context, iteration: int, action_command: str, action_start_time: float) -> Dict[str, Any]:
        """Try freeze detection method - SAME workflow as blackscreen detection."""
        try:
            print(f"🧊 [ZapExecutor] Trying freeze detection...")
            
            # Get video verification controller (same as blackscreen)
            video_controller = self.device._get_controller('verification_video')
            if not video_controller:
                return {"success": False, "message": f"No video verification controller found for device {self.device.device_id}"}
            
            # Get AV controller for capture path (same as blackscreen)
            av_controller = self.device._get_controller('av')
            if not av_controller:
                return {"success": False, "message": f"No AV controller found for device {self.device.device_id}"}
            
            # Get the capture folder path (same as blackscreen)
            capture_folder = getattr(av_controller, 'video_capture_path', None)
            if not capture_folder:
                return {"success": False, "message": "No capture folder available"}
            
            # Use action start time (same as blackscreen)
            key_release_timestamp = action_start_time or time.time()
            
            # Use same areas as blackscreen detection
            device_model = context.selected_device.device_model if context.selected_device else 'unknown'
            
            # Smaller uniform rectangle for all devices: 200,0, 400, 200 (80k pixels)
            analysis_rectangle = {'x': 200, 'y': 0, 'width': 400, 'height': 200}
            
            if device_model in ['android_mobile', 'ios_mobile']:
                banner_region = {'x': 470, 'y': 230, 'width': 280, 'height': 70}
            else:
                banner_region = {'x': 245, 'y': 830, 'width': 1170, 'height': 120}
            
            # Device-specific timeout using helper method
            max_images = self._get_max_images_for_device(device_model)
            
            # Call freeze zapping detection using device-specific timeout
            freeze_result = video_controller.content_helpers.detect_freeze_zapping_sequence(
                folder_path=capture_folder,
                key_release_timestamp=key_release_timestamp,
                analysis_rectangle=analysis_rectangle,
                max_images=max_images,
                banner_region=banner_region
            )
            
            if freeze_result.get('success', False) and freeze_result.get('freeze_zapping_detected', False):
                freeze_duration = freeze_result.get('freeze_duration', 0.0)
                print(f"✅ [ZapExecutor] Freeze zapping detected - Duration: {freeze_duration}s")
                
                # Add zapping images to context (same as blackscreen)
                self._add_zapping_images_to_screenshots(context, freeze_result, capture_folder)
                
                result = {
                    "success": True,
                    "zapping_detected": True,
                    "detection_method": "freeze",
                    "transition_type": "freeze",
                    "blackscreen_duration": freeze_duration,  # Keep same field name for compatibility
                    "zapping_duration": freeze_result.get('zapping_duration', 0.0),
                    "first_image": freeze_result.get('first_image'),
                    # NOTE: freeze_result uses "blackscreen_*" field names for compatibility with reporting code
                    "blackscreen_start_image": freeze_result.get('blackscreen_start_image'),  # Actually freeze start image
                    "blackscreen_end_image": freeze_result.get('blackscreen_end_image'),      # Actually freeze end image
                    "first_content_after_blackscreen": freeze_result.get('first_content_after_blackscreen'),  # Actually first content after freeze
                    "channel_detection_image": freeze_result.get('channel_detection_image'),
                    "last_image": freeze_result.get('last_image'),
                    "channel_info": freeze_result.get('channel_info', {}),
                    "analyzed_images": freeze_result.get('analyzed_images', 0),
                    "total_images_available": freeze_result.get('total_images_available', 0),
                    "debug_images": freeze_result.get('debug_images', []),
                    "early_stopped": freeze_result.get('early_stopped', False),
                    "coverage_seconds": 6,
                    "sub_second_precision": True,
                    "message": f"Enhanced freeze zapping detected (analyzed {freeze_result.get('analyzed_images', 0)} images, early_stopped={freeze_result.get('early_stopped', False)})",
                    "details": freeze_result
                }
                return result
            else:
                print(f"❌ [ZapExecutor] Freeze detection failed")
                
                # Use the debug_images from the detection result - these are the actual analyzed images
                debug_images = freeze_result.get('debug_images', [])
                captures_folder = os.path.join(capture_folder, 'captures')
                analyzed_screenshots = []
                
                for filename in debug_images:
                    image_path = os.path.join(captures_folder, filename)
                    if os.path.exists(image_path):
                        analyzed_screenshots.append(image_path)
                
                print(f"🔍 [ZapExecutor] Using {len(analyzed_screenshots)} actual analyzed images for freeze mosaic")
                
                # Create failure mosaic with freeze analysis data (includes comparison results)
                mosaic_path = self._create_failure_mosaic(context, analyzed_screenshots, "freeze", freeze_result)
                
                # Create detailed analysis log for modal display
                analysis_log = create_freeze_analysis_log(analyzed_screenshots, freeze_result, key_release_timestamp)
                
                return {
                    "success": False,
                    "zapping_detected": False,
                    "detection_method": "freeze",
                    "transition_type": "none",
                    "blackscreen_duration": 0.0,
                    "analyzed_images": len(analyzed_screenshots),
                    "message": "Freeze detection failed",
                    "error": "No freeze detected",
                    "details": f"No freeze transition detected (analyzed {len(analyzed_screenshots)} images)",
                    "failure_mosaic_path": mosaic_path,
                    "mosaic_images_count": len(analyzed_screenshots),
                    "analysis_log": analysis_log
                }
                
        except Exception as e:
            return {
                "success": False,
                "zapping_detected": False,
                "detection_method": "freeze",
                "transition_type": "none",
                "blackscreen_duration": 0.0,
                "message": "Freeze detection failed",
                "error": str(e),
                "details": f"Freeze detection error: {str(e)}"
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
            
            # Add each key image to screenshot paths if it exists and has valid format
            for image_filename in key_images:
                if image_filename and validate_capture_filename(image_filename):
                    image_path = f"{captures_folder}/{image_filename}"
                    if image_path not in context.screenshot_paths:
                        context.add_screenshot(image_path)  # Auto-copies to cold
                        print(f"🖼️ [ZapExecutor] Added zapping image: {image_filename}")
            
            # Also add debug images for debugging failed zap detection
            debug_images = zapping_result.get('debug_images', [])
            if debug_images:
                for debug_filename in debug_images:
                    if debug_filename and validate_capture_filename(debug_filename):
                        debug_path = f"{captures_folder}/{debug_filename}"
                        if debug_path not in context.screenshot_paths:
                            context.add_screenshot(debug_path)  # Auto-copies to cold
                            print(f"🔧 [ZapExecutor] Added debug image: {debug_filename}")
            
        except Exception as e:
            print(f"⚠️ [ZapExecutor] Failed to add zapping images to screenshot collection: {e}")

    def _create_failure_mosaic(self, context, screenshots: List[str], detection_method: str, analysis_data: Dict[str, Any] = None) -> Optional[str]:
        """Create a mosaic image for zapping failure analysis instead of individual images"""
        try:
            if not screenshots or len(screenshots) == 0:
                print(f"❌ [ZapExecutor] No images available for {detection_method} failure mosaic")
                return None
            
            # Import simple mosaic generator
            from shared.src.lib.utils.image_mosaic_generator import create_zapping_failure_mosaic
            
            # Create mosaic with analysis data
            mosaic_path = create_zapping_failure_mosaic(
                image_paths=screenshots,
                detection_method=detection_method,
                analysis_info=analysis_data
            )
            
            if mosaic_path:
                print(f"🖼️ [ZapExecutor] Created {detection_method} failure mosaic: {os.path.basename(mosaic_path)}")
                print(f"   📊 Mosaic contains {len(screenshots)} analyzed images")
                
                # Add mosaic to screenshot collection for R2 upload
                if not hasattr(context, 'screenshot_paths'):
                    context.screenshot_paths = []
                
                if mosaic_path not in context.screenshot_paths:
                    context.add_screenshot(mosaic_path)  # Auto-copies to cold
                
                return mosaic_path
            else:
                print(f"❌ [ZapExecutor] Failed to create {detection_method} failure mosaic")
                return None
                
        except Exception as e:
            print(f"⚠️ [ZapExecutor] Exception creating {detection_method} failure mosaic: {e}")
            return None

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
                duration_info = f"duration: {analysis_result.blackscreen_duration:.2f}s" if analysis_result.blackscreen_duration > 0 else "duration: N/A"
                print(f"Details: Zapping detected ({duration_info})")
                if analysis_result.channel_name:
                    channel_info = analysis_result.channel_name
                    if analysis_result.channel_number:
                        channel_info += f" ({analysis_result.channel_number})"
                    if analysis_result.program_name:
                        channel_info += f" - {analysis_result.program_name}"
                    print(f"Channel: {channel_info}")
                    if analysis_result.program_start_time and analysis_result.program_end_time:
                        print(f"Program Time: {analysis_result.program_start_time}-{analysis_result.program_end_time}")
            else:
                # Show failure reason from zapping details
                zapping_message = analysis_result.zapping_details.get('message', 'Zapping not detected')
                print(f"Details: {zapping_message}")
        
        print()  # Add blank line after analysis results
