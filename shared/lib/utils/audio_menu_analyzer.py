"""
Audio Menu Analyzer - Dedicated utility for analyzing audio/subtitle menus

This utility provides:
- Independent audio menu analysis functionality
- Device-specific menu handling (mobile vs desktop/TV)
- Clean separation from navigation and zap controllers
"""

import time
from typing import Dict, Any
from .navigation_utils import goto_node
from .host_utils import get_controller
from .report_utils import capture_and_upload_screenshot


def analyze_audio_menu(context, current_node: str = None) -> Dict[str, Any]:
    """
    Analyze audio/subtitle menu independently.
    
    Args:
        context: Script execution context
        current_node: Current node to return to after analysis (optional)
    
    Returns:
        Dict containing analysis results with menu_detected, audio_languages, etc.
    """
    try:
        device_model = context.selected_device.device_model if context.selected_device else 'unknown'
        device_id = context.selected_device.device_id
        
        # Determine the correct target node to return to
        if current_node:
            target_node = current_node
        elif device_model in ['android_mobile', 'ios_mobile']:
            target_node = "live_fullscreen"
        else:
            target_node = "live"
        
        # Get video verification controller
        video_controller = get_controller(device_id, 'verification_video')
        if not video_controller:
            return {"success": False, "message": f"No video verification controller found for device {device_id}"}
        
        if device_model in ['android_mobile', 'ios_mobile']:
            # Mobile devices: combined audio/subtitle menu
            print(f"🎧 [AudioMenuAnalyzer] Analyzing combined audio/subtitle menu for mobile...")
            
            # Use audio menu node provided by parent script, or fallback to default
            audio_menu_target = getattr(context, 'audio_menu_node', 'live_audiomenu')
            print(f"🎧 [AudioMenuAnalyzer] Using audio menu target: {audio_menu_target}")
            
            # Navigate to combined audio menu
            audio_menu_nav = goto_node(context.host, context.selected_device, audio_menu_target, 
                                     context.tree_id, context.team_id, context)
            
            if audio_menu_nav.get('success'):
                # Capture and analyze using unified approach
                screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "audio_menu_analysis", "analysis")
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
                
                # Navigate back to target node
                try:
                    print(f"🔄 [AudioMenuAnalyzer] Navigating back to {target_node}")
                    goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
                except Exception as nav_error:
                    print(f"⚠️ [AudioMenuAnalyzer] Navigation back to {target_node} failed: {nav_error}")
                    # Continue anyway - we have the analysis result
                
                print(f"🎧 [AudioMenuAnalyzer] Analysis complete: menu_detected = {result.get('menu_detected', False)}")
                return result
            else:
                # Even on navigation failure, try to capture screenshot for debugging
                screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "audio_menu_analysis_failed", "analysis")
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
            print(f"🎧 [AudioMenuAnalyzer] Analyzing separate audio and subtitle menus for desktop/TV...")
            
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
            print(f"🔊 [AudioMenuAnalyzer] Checking audio menu...")
            audio_nav = goto_node(context.host, context.selected_device, "live_menu_audio", 
                                context.tree_id, context.team_id, context)
            
            if audio_nav.get('success'):
                # Capture and analyze audio menu
                audio_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "audio_menu_analysis", "analysis")
                audio_screenshot_path = audio_screenshot_result['screenshot_path'] if audio_screenshot_result['success'] else ""
                audio_screenshot_url = audio_screenshot_result['screenshot_url'] if audio_screenshot_result['success'] else None
                if audio_screenshot_result['success']:
                    context.add_screenshot(audio_screenshot_path)
                
                audio_result = video_controller.analyze_language_menu_ai(audio_screenshot_path)
                combined_result["audio_analysis"] = audio_result
                combined_result["audio_detected"] = audio_result.get('menu_detected', False)
                
                # Add screenshot to audio analysis
                if audio_screenshot_url:
                    combined_result["audio_analysis"]['analyzed_screenshot'] = audio_screenshot_url
                elif audio_screenshot_path:
                    combined_result["audio_analysis"]['analyzed_screenshot'] = audio_screenshot_path
            
            # 2. Analyze subtitle menu
            print(f"📝 [AudioMenuAnalyzer] Checking subtitle menu...")
            subtitle_nav = goto_node(context.host, context.selected_device, "live_menu_subtitles", 
                                   context.tree_id, context.team_id, context)
            
            if subtitle_nav.get('success'):
                # Capture and analyze subtitle menu
                subtitle_screenshot_result = capture_and_upload_screenshot(context.host, context.selected_device, "subtitle_menu_analysis", "analysis")
                subtitle_screenshot_path = subtitle_screenshot_result['screenshot_path'] if subtitle_screenshot_result['success'] else ""
                subtitle_screenshot_url = subtitle_screenshot_result['screenshot_url'] if subtitle_screenshot_result['success'] else None
                if subtitle_screenshot_result['success']:
                    context.add_screenshot(subtitle_screenshot_path)
                
                subtitle_result = video_controller.analyze_language_menu_ai(subtitle_screenshot_path)
                combined_result["subtitle_analysis"] = subtitle_result
                combined_result["subtitles_detected"] = subtitle_result.get('menu_detected', False)
                
                # Add screenshot to subtitle analysis
                if subtitle_screenshot_url:
                    combined_result["subtitle_analysis"]['analyzed_screenshot'] = subtitle_screenshot_url
                elif subtitle_screenshot_path:
                    combined_result["subtitle_analysis"]['analyzed_screenshot'] = subtitle_screenshot_path
            
            # Navigate back to target node
            try:
                print(f"🔄 [AudioMenuAnalyzer] Navigating back to {target_node}")
                goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
            except Exception as nav_error:
                print(f"⚠️ [AudioMenuAnalyzer] Navigation back to {target_node} failed: {nav_error}")
            
            # Set overall menu detection and message
            combined_result["menu_detected"] = combined_result["audio_detected"] or combined_result["subtitles_detected"]
            
            # Flatten language results for report compatibility
            audio_languages = []
            subtitle_languages = []
            
            if combined_result["audio_analysis"].get('audio_languages'):
                audio_languages = combined_result["audio_analysis"]['audio_languages']
            if combined_result["subtitle_analysis"].get('subtitle_languages'):
                subtitle_languages = combined_result["subtitle_analysis"]['subtitle_languages']
            
            # Add flattened language arrays to top level for report formatter
            combined_result["audio_languages"] = audio_languages
            combined_result["subtitle_languages"] = subtitle_languages
            
            if combined_result["audio_detected"] and combined_result["subtitles_detected"]:
                combined_result["message"] = "Both audio and subtitle menus detected"
                # Use audio menu screenshot as primary
                if combined_result["audio_analysis"].get('analyzed_screenshot'):
                    combined_result["analyzed_screenshot"] = combined_result["audio_analysis"]['analyzed_screenshot']
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
            
            print(f"📊 [AudioMenuAnalyzer] Analysis complete: {combined_result['message']}")
            return combined_result
            
    except Exception as e:
        return {"success": False, "message": f"Audio menu analysis error: {e}"}


def add_audio_menu_analysis_to_step(context, step_index: int = None) -> bool:
    """
    Add audio menu analysis to a specific step in the context.
    
    Args:
        context: Script execution context
        step_index: Index of step to add analysis to (defaults to last step)
    
    Returns:
        bool: True if analysis was added successfully
    """
    try:
        if not context.step_results:
            return False
        
        # Use last step if no index specified
        if step_index is None:
            step_index = len(context.step_results) - 1
        
        if step_index < 0 or step_index >= len(context.step_results):
            return False
        
        # Perform analysis
        analysis_result = analyze_audio_menu(context)
        
        # Add to specified step
        context.step_results[step_index]['audio_menu_analysis'] = analysis_result
        
        print(f"🎧 [AudioMenuAnalyzer] Added analysis to step {step_index + 1}: menu_detected = {analysis_result.get('menu_detected', False)}")
        return True
        
    except Exception as e:
        print(f"❌ [AudioMenuAnalyzer] Error adding analysis to step: {e}")
        return False
