#!/usr/bin/env python3
"""
Fullzap Script for VirtualPyTest

This script navigates to the live node and executes a zap action multiple times
using the unified script framework with motion detection validation.

Usage:
    python scripts/fullzap.py [userinterface_name] [--host <host>] [--device <device>] [--action <action>] [--max_iteration <count>]
    
Example:
    python scripts/fullzap.py
    python scripts/fullzap.py horizon_android_mobile
    python scripts/fullzap.py horizon_android_mobile --action live_chup --max_iteration 20
    python scripts/fullzap.py horizon_android_mobile --device device2 --action zap_chdown --max_iteration 5
"""

import sys
import os
import time

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, ScriptExecutionContext, handle_keyboard_interrupt, handle_unexpected_error
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path
from backend_core.src.controllers.verification.video import VideoVerificationController
from shared.lib.utils.script_utils import (
    find_node_by_label,
    execute_edge_actions,
    capture_validation_screenshot
)


def create_motion_detector(context: ScriptExecutionContext):
    """Create a video verification controller for motion detection"""
    try:
        # Get AV controller for the device
        from shared.lib.utils.host_utils import get_controller
        av_controller = get_controller(context.selected_device.device_id, 'av')
        
        if not av_controller:
            print(f"⚠️ [fullzap] No AV controller found for device {context.selected_device.device_id}")
            return None
        
        # Create video verification controller
        video_controller = VideoVerificationController(av_controller)
        print(f"✅ [fullzap] Motion detector created for device {context.selected_device.device_id}")
        return video_controller
            
    except Exception as e:
        print(f"⚠️ [fullzap] Error creating motion detector: {e}")
        return None


def detect_subtitles_ai_with_controller(motion_detector, context: ScriptExecutionContext, iteration: int, action_command: str):
    """Detect subtitles using AI after a zap action using the existing VideoVerificationController"""
    if not motion_detector:
        return {"success": False, "message": "No motion detector (VideoVerificationController) available"}
    
    try:
        print(f"🔍 [fullzap] Detecting AI subtitles after {action_command} (iteration {iteration})...")
        
        # Get the latest screenshot for subtitle analysis
        if not context.screenshot_paths:
            return {"success": False, "message": "No screenshots available for subtitle detection"}
        
        latest_screenshot = context.screenshot_paths[-1]
        print(f"🖼️ [fullzap] Analyzing screenshot: {latest_screenshot}")
        
        # Use the existing VideoVerificationController method directly
        result = motion_detector.execute_verification('DetectSubtitlesAI', {
            'extract_text': True
        }, [latest_screenshot])
        
        success = result.get('success', False)
        details = result.get('details', {})
        
        if success:
            has_subtitles = details.get('subtitles_detected', False)
            extracted_text = details.get('combined_extracted_text', '') or details.get('extracted_text', '')
            detected_language = details.get('detected_language')
            confidence = details.get('confidence', 0.9 if has_subtitles else 0.1)
            
            # Clean up language detection
            if detected_language == 'unknown' or not detected_language:
                detected_language = None
            
            subtitle_result = {
                "success": True,
                "subtitles_detected": has_subtitles,
                "extracted_text": extracted_text,
                "detected_language": detected_language,
                "confidence": confidence,
                "message": f"Subtitles {'detected' if has_subtitles else 'not detected'}"
            }
            
            if has_subtitles:
                lang_info = f" (Language: {detected_language})" if detected_language else ""
                print(f"✅ [fullzap] Subtitles detected{lang_info}")
                if extracted_text:
                    # Truncate text for display
                    display_text = extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
                    print(f"   📝 Text: {display_text}")
            else:
                print(f"⚠️ [fullzap] No subtitles detected")
            
            return subtitle_result
        else:
            error_msg = result.get('message', 'Unknown error')
            print(f"❌ [fullzap] Subtitle detection failed: {error_msg}")
            return {"success": False, "message": f"Detection failed: {error_msg}"}
        
    except Exception as e:
        error_msg = f"Subtitle detection error: {e}"
        print(f"❌ [fullzap] {error_msg}")
        return {"success": False, "message": error_msg}


def check_motion_after_zap(motion_detector, iteration, action_command, context: ScriptExecutionContext = None):
    """Check for motion after a zap action using JSON analysis and AI subtitle detection"""
    try:
        print(f"🔍 [fullzap] Checking motion after {action_command} (iteration {iteration})...")
        
        # 1. Check motion detection using JSON analysis
        motion_result = {"success": False, "message": "No motion detector available"}
        
        if motion_detector:
            # Wait a moment for analysis files to be generated
            time.sleep(2)
            
            # Use lenient mode and check last 3 JSON files
            result = motion_detector.detect_motion_from_json(json_count=3, strict_mode=False)
            
            success = result.get('success', False)
            message = result.get('message', 'Unknown result')
            video_ok = result.get('video_ok', False)
            audio_ok = result.get('audio_ok', False)
            total_analyzed = result.get('total_analyzed', 0)
            
            motion_result = {
                "success": success,
                "message": message,
                "video_ok": video_ok,
                "audio_ok": audio_ok,
                "total_analyzed": total_analyzed,
                "motion_detected": success
            }
            
            if success:
                print(f"✅ [fullzap] Motion detected after {action_command} - content changed successfully")
                print(f"   📊 Analysis: {total_analyzed} files, Video OK: {video_ok}, Audio OK: {audio_ok}")
            else:
                print(f"⚠️ [fullzap] No motion detected after {action_command} - content may not have changed")
                print(f"   📊 Analysis: {total_analyzed} files, Video OK: {video_ok}, Audio OK: {audio_ok}")
                print(f"   📝 Details: {message}")
        
        # 2. Check AI subtitle detection (if context is provided)
        subtitle_result = {"success": False, "message": "No context provided for subtitle detection"}
        
        if context:
            subtitle_result = detect_subtitles_ai_with_controller(motion_detector, context, iteration, action_command)
        
        # 3. Combine results
        combined_result = {
            **motion_result,
            "subtitle_analysis": subtitle_result,
            "subtitles_detected": subtitle_result.get("subtitles_detected", False),
            "detected_language": subtitle_result.get("detected_language"),
            "extracted_text": subtitle_result.get("extracted_text", "")
        }
        
        return combined_result
        
    except Exception as e:
        error_msg = f"Motion and subtitle detection error: {e}"
        print(f"❌ [fullzap] {error_msg}")
        return {"success": False, "message": error_msg}


def validate_and_find_action_edge(context: ScriptExecutionContext, action_command: str):
    """Validate that the action exists and return the action edge"""
    # Find the live node
    live_node = find_node_by_label(context.nodes, "live")
    if not live_node:
        return None, "Live node not found in navigation tree"
    
    live_node_id = live_node.get('node_id')
    print(f"🔍 [fullzap] Found live node with ID: '{live_node_id}'")
    
    # Validate action edge exists (including nested sub-trees)
    from shared.lib.utils.script_utils import find_action_in_nested_trees
    
    action_result = find_action_in_nested_trees(
        live_node_id, context.tree_id, context.nodes, context.edges, action_command, context.team_id
    )
    
    if not action_result.get('success'):
        from shared.lib.utils.script_utils import find_edges_from_node
        live_edges = find_edges_from_node(live_node_id, context.edges)
        available_actions = [
            next((n.get('label') for n in context.nodes if n.get('node_id') == e.get('target_node_id')), 'unknown') 
            for e in live_edges
        ]
        return None, f"Action '{action_command}' not found from live node. Available actions: {available_actions}"
    
    action_edge = action_result.get('edge')
    tree_type = action_result.get('tree_type')
    action_tree_id = action_result.get('tree_id')
    
    if tree_type == 'main':
        print(f"✅ [fullzap] Action '{action_command}' found in main tree - edge: {action_edge.get('edge_id')}")
    else:
        source_node_id = action_result.get('source_node_id')
        print(f"✅ [fullzap] Action '{action_command}' found in sub-tree {action_tree_id} - edge: {action_edge.get('edge_id')} (from node: {source_node_id})")
    
    return action_edge, None


def execute_zap_actions(context: ScriptExecutionContext, action_edge, action_command: str, max_iteration: int, motion_detector):
    """Execute zap actions multiple times with motion detection"""
    motion_results = []
    successful_iterations = 0
    total_action_time = 0
    
    # Capture pre-action screenshot
    pre_action_screenshot = capture_validation_screenshot(
        context.host, context.selected_device, "pre_action", "fullzap"
    )
    context.add_screenshot(pre_action_screenshot)
    
    print(f"🔄 [fullzap] Starting {max_iteration} iterations of action '{action_command}'...")
    
    for iteration in range(1, max_iteration + 1):
        step_num = len(context.step_results) + 1  # Continue step numbering
        print(f"🎬 [fullzap] Action step {iteration}: Execute {action_command} (iteration {iteration}/{max_iteration})")
        
        iteration_start_time = time.time()
        action_result = execute_edge_actions(context.host, context.selected_device, action_edge, team_id=context.team_id)
        iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
        total_action_time += iteration_execution_time
        
        # Check for motion and subtitles after each action
        motion_result = check_motion_after_zap(motion_detector, iteration, action_command, context)
        motion_results.append(motion_result)
        
        # Capture screenshot for this action step
        action_screenshot = capture_validation_screenshot(
            context.host, context.selected_device, f"action_step_{iteration}", "fullzap"
        )
        context.add_screenshot(action_screenshot)
        
        if action_result.get('success'):
            print(f"✅ [fullzap] Action step {iteration} completed successfully in {iteration_execution_time}ms")
            successful_iterations += 1
            
            # Record successful step result
            context.step_results.append({
                'step_number': step_num,
                'success': True,
                'screenshot_path': action_screenshot,
                'message': f"Action step {iteration}: Execute {action_command} (iteration {iteration}/{max_iteration})",
                'execution_time_ms': iteration_execution_time,
                'step_category': 'action',
                'action_name': action_command,
                'iteration': iteration,
                'max_iterations': max_iteration,
                'motion_detection': motion_result
            })
            
            # Brief pause between iterations
            if iteration < max_iteration:
                time.sleep(0.5)
        else:
            iteration_error = action_result.get('error', 'Unknown error')
            print(f"❌ [fullzap] Action step {iteration} failed: {iteration_error}")
            
            # Record failed step result
            context.step_results.append({
                'step_number': step_num,
                'success': False,
                'screenshot_path': action_screenshot,
                'message': f"Action step {iteration}: Execute {action_command} (iteration {iteration}/{max_iteration})",
                'execution_time_ms': iteration_execution_time,
                'step_category': 'action',
                'action_name': action_command,
                'iteration': iteration,
                'max_iterations': max_iteration,
                'error_message': iteration_error,
                'motion_detection': motion_result
            })
    
    # Capture post-action screenshot
    post_action_screenshot = capture_validation_screenshot(
        context.host, context.selected_device, "post_action", "fullzap"
    )
    context.add_screenshot(post_action_screenshot)
    
    # Calculate statistics
    motion_detected_count = sum(1 for result in motion_results if result.get('motion_detected', False))
    motion_success_rate = (motion_detected_count / len(motion_results) * 100) if motion_results else 0
    
    # Calculate subtitle statistics
    subtitles_detected_count = sum(1 for result in motion_results if result.get('subtitles_detected', False))
    subtitle_success_rate = (subtitles_detected_count / len(motion_results) * 100) if motion_results else 0
    
    # Collect detected languages
    detected_languages = []
    for result in motion_results:
        lang = result.get('detected_language')
        if lang and lang not in detected_languages:
            detected_languages.append(lang)
    
    average_time = total_action_time / max_iteration if max_iteration > 0 else 0
    success_rate = (successful_iterations / max_iteration * 100) if max_iteration > 0 else 0
    
    print(f"📊 [fullzap] Action execution summary:")
    print(f"   • Total iterations: {max_iteration}")
    print(f"   • Successful: {successful_iterations}")
    print(f"   • Success rate: {success_rate:.1f}%")
    print(f"   • Average time per iteration: {average_time:.0f}ms")
    print(f"   • Total action time: {total_action_time}ms")
    print(f"   • Motion detected: {motion_detected_count}/{len(motion_results)} ({motion_success_rate:.1f}%)")
    print(f"   • Subtitles detected: {subtitles_detected_count}/{len(motion_results)} ({subtitle_success_rate:.1f}%)")
    
    if detected_languages:
        print(f"   🌐 Languages detected: {', '.join(detected_languages)}")
    
    if motion_detected_count < len(motion_results):
        no_motion_count = len(motion_results) - motion_detected_count
        print(f"   ⚠️  {no_motion_count} zap(s) did not show content change")
    
    # Store summary in context for reporting
    context.custom_data.update({
        'action_command': action_command,
        'max_iteration': max_iteration,
        'successful_iterations': successful_iterations,
        'motion_detected_count': motion_detected_count,
        'subtitles_detected_count': subtitles_detected_count,
        'detected_languages': detected_languages,
        'motion_results': motion_results,
        'total_action_time': total_action_time
    })
    
    return successful_iterations == max_iteration


def print_fullzap_summary(context: ScriptExecutionContext, userinterface_name: str):
    """Print fullzap-specific summary"""
    custom_data = context.custom_data
    
    print("\n" + "="*60)
    print(f"🎯 [FULLZAP] EXECUTION SUMMARY")
    print("="*60)
    print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    print(f"🖥️  Host: {context.host.host_name}")
    print(f"📋 Interface: {userinterface_name}")
    print(f"🗺️  Navigation: home → live ({len([s for s in context.step_results if s.get('step_category') != 'action'])} steps)")
    print(f"⚡ Action: {custom_data.get('action_command', 'unknown')} ({custom_data.get('max_iteration', 0)} iterations)")
    print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    print(f"✅ Success Rate: {custom_data.get('successful_iterations', 0)}/{custom_data.get('max_iteration', 0)} actions")
    print(f"🔄 Motion Detected: {custom_data.get('motion_detected_count', 0)}/{custom_data.get('max_iteration', 0)} zaps")
    print(f"📝 Subtitles Detected: {custom_data.get('subtitles_detected_count', 0)}/{custom_data.get('max_iteration', 0)} zaps")
    
    detected_languages = custom_data.get('detected_languages', [])
    if detected_languages:
        print(f"🌐 Languages: {', '.join(detected_languages)}")
    
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        print(f"❌ Error: {context.error_message}")
    
    print("="*60)


def main():
    """Main function to navigate to live and execute zap action multiple times"""
    script_name = "fullzap"
    executor = ScriptExecutor(script_name, "Navigate to live and execute zap action multiple times")
    
    # Create argument parser with custom fullzap arguments
    additional_args = [
        {
            'name': '--action',
            'kwargs': {
                'default': 'live_chup',
                'help': 'Action command to execute (default: live_chup)'
            }
        },
        {
            'name': '--max_iteration',
            'kwargs': {
                'type': int,
                'default': 5,
                'help': 'Number of times to execute the action (default: 5)'
            }
        }
    ]
    
    parser = executor.create_argument_parser(additional_args)
    args = parser.parse_args()
    
    print(f"🎯 [fullzap] Starting navigation to live and executing action '{args.action}' {args.max_iteration} times for: {args.userinterface_name}")
    
    # Setup execution context
    context = executor.setup_execution_context(args)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Create motion detector for zap validation
        print("🔧 [fullzap] Creating motion detector...")
        motion_detector = create_motion_detector(context)
        if motion_detector:
            print("✅ [fullzap] Motion detector ready for zap validation")
        else:
            print("⚠️ [fullzap] Motion detector unavailable - zap validation will be skipped")
        
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        # Validate action availability before navigation (fail fast)
        print(f"🔍 [fullzap] Validating action '{args.action}' availability before navigation...")
        action_edge, error_msg = validate_and_find_action_edge(context, args.action)
        if not action_edge:
            context.error_message = error_msg
            print(f"❌ [fullzap] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        # Find path to live node
        print("🗺️ [fullzap] Finding path to live...")
        navigation_path = find_shortest_path(context.tree_id, "live", context.team_id)
        
        if not navigation_path:
            context.error_message = "No path found to live node"
            print(f"❌ [fullzap] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [fullzap] Found path with {len(navigation_path)} steps")
        
        # Execute navigation sequence to reach live node
        nav_success = executor.execute_navigation_sequence(context, navigation_path)
        if not nav_success:
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print("🎉 [fullzap] Successfully navigated to live!")
        
        # Execute zap actions multiple times with motion detection
        print(f"⚡ [fullzap] Executing pre-validated action '{args.action}' from live node...")
        zap_success = execute_zap_actions(context, action_edge, args.action, args.max_iteration, motion_detector)
        
        context.overall_success = nav_success and zap_success
        
        if context.overall_success:
            print(f"✅ [fullzap] All {args.max_iteration} iterations of action '{args.action}' completed successfully!")
        else:
            context.error_message = f"Some zap actions failed"
        
        # Print custom fullzap summary
        print_fullzap_summary(context, args.userinterface_name)
        
        # Exit with proper code based on result
        if context.overall_success:
            print("✅ [fullzap] Fullzap execution completed successfully - exiting with code 0")
            sys.exit(0)
        else:
            print("❌ [fullzap] Fullzap execution failed - exiting with code 1")
            sys.exit(1)
            
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 