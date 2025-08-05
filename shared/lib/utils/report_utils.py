"""
Report Generation Utilities

This module provides functions for generating HTML validation reports with embedded screenshots.
Includes screenshot capture and upload functionality for consistent reporting across all controllers.
Reports include execution metrics, step-by-step results, and error analysis.
Enhanced for manager-friendly compact view with collapsible sections and theme support.
"""

import os
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from .report_template_utils import create_themed_html_template


def capture_and_upload_screenshot(host, device, step_name: str, script_context: str = "action") -> Dict[str, Any]:
    """
    Unified screenshot capture and upload function for reporting.
    Used by all controllers for consistent screenshot handling in reports.
    
    Args:
        host: Host instance
        device: Device instance  
        step_name: Name for the screenshot (e.g., "zap_iteration_1", "navigation_step_2")
        script_context: Context for organizing screenshots (e.g., "zap", "navigation", "validation")
        
    Returns:
        Dict with screenshot_path, screenshot_url, and success status
    """
    result = {
        'screenshot_path': '',
        'screenshot_url': None,
        'success': False,
        'error': None
    }
    
    try:
        # 1. Capture screenshot locally
        from .action_utils import capture_validation_screenshot
        screenshot_path = capture_validation_screenshot(host, device, step_name, script_context)
        result['screenshot_path'] = screenshot_path
        
        if screenshot_path:
            # 2. Upload to Cloudflare R2 for report display
            from .cloudflare_utils import get_cloudflare_utils
            uploader = get_cloudflare_utils()
            remote_path = f"{script_context}-screenshots/{device.device_id}/{step_name}.png"
            upload_result = uploader.upload_file(screenshot_path, remote_path)
            
            if upload_result.get('success'):
                result['screenshot_url'] = upload_result.get('url')
                result['success'] = True
                print(f"[@report_utils:capture_and_upload_screenshot] Screenshot uploaded: {result['screenshot_url']}")
            else:
                result['error'] = f"Upload failed: {upload_result.get('error', 'Unknown error')}"
                print(f"[@report_utils:capture_and_upload_screenshot] Upload failed: {result['error']}")
        else:
            result['error'] = "Screenshot capture failed"
            print(f"[@report_utils:capture_and_upload_screenshot] Capture failed: {result['error']}")
            
    except Exception as e:
        result['error'] = f"Screenshot handling error: {str(e)}"
        print(f"[@report_utils:capture_and_upload_screenshot] Error: {result['error']}")
        
    return result

def generate_validation_report(report_data: Dict) -> str:
    """
    Generate HTML validation report with embedded CSS and screenshots.
    
    Args:
        report_data: Dictionary containing all report information
        
    Returns:
        Complete HTML report as string
    """
    try:
        print(f"[@utils:report_utils:generate_validation_report] Generating report for {report_data.get('script_name')}")
        
        # Extract report data
        script_name = report_data.get('script_name', 'Unknown Script')
        device_info = report_data.get('device_info', {})
        host_info = report_data.get('host_info', {})
        execution_time = report_data.get('execution_time', 0)
        success = report_data.get('success', False)
        step_results = report_data.get('step_results', [])
        screenshots = report_data.get('screenshots', {})
        error_msg = report_data.get('error_msg', '')
        timestamp = report_data.get('timestamp', datetime.now().strftime('%Y%m%d%H%M%S'))
        start_time = report_data.get('start_time', timestamp)
        end_time = report_data.get('end_time', timestamp)
        
        # Calculate stats
        total_steps = len(step_results)
        passed_steps = sum(1 for step in step_results if step.get('success', False))
        failed_steps = total_steps - passed_steps
        
        # Generate HTML content
        html_template = create_themed_html_template()
        
        # Replace placeholders with actual content
        html_content = html_template.format(
            script_name=script_name,
            start_time=format_timestamp(start_time),
            end_time=format_timestamp(end_time),
            success_status="PASS" if success else "FAIL",
            success_class="success" if success else "failure",
            execution_time=format_execution_time(execution_time),
            device_name=device_info.get('device_name', 'Unknown Device'),
            device_model=device_info.get('device_model', 'Unknown Model'),
            host_name=host_info.get('host_name', 'Unknown Host'),
            total_steps=total_steps,
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            step_results_html=create_compact_step_results_section(step_results, screenshots),
            error_section=create_error_section(error_msg) if error_msg else '',
            execution_summary=format_console_summary_for_html(report_data.get('execution_summary', '')),
            initial_screenshot=get_thumbnail_screenshot_html(screenshots.get('initial')),
            final_screenshot=get_thumbnail_screenshot_html(screenshots.get('final')),
            test_video=get_video_thumbnail_html(report_data.get('test_video_url'), 'Test Execution')
        )
        
        print(f"[@utils:report_utils:generate_validation_report] Report generated successfully")
        return html_content
        
    except Exception as e:
        print(f"[@utils:report_utils:generate_validation_report] Error: {str(e)}")
        return create_error_report(str(e))

def create_compact_step_results_section(step_results: List[Dict], screenshots: Dict) -> str:
    """Create HTML for compact step-by-step results."""
    if not step_results:
        return '<p>No steps executed</p>'
    
    steps_html = ['<div class="step-list">']
    # steps now contains the full step results, not just screenshot paths
    step_data = screenshots.get('steps', step_results)
    
    for step_index, step in enumerate(step_results):
        step_number = step.get('step_number', step_index + 1)
        success = step.get('success', False)
        message = step.get('message', 'No message')
        execution_time = step.get('execution_time_ms', 0)
        start_time = step.get('start_time', 'N/A')
        end_time = step.get('end_time', 'N/A')
        from_node = step.get('from_node', 'Unknown')
        to_node = step.get('to_node', 'Unknown')
        actions = step.get('actions', [])
        retry_actions = step.get('retryActions', [])
        failure_actions = step.get('failureActions', [])
        verifications = step.get('verifications', [])
        
        # Format execution time
        exec_time_str = format_execution_time(execution_time) if execution_time else "N/A"
        
        # Format timing for header
        timing_header = f"Start: {start_time} End: {end_time} Duration: {exec_time_str}"
        
        # Format detailed actions and verifications
        actions_html = ""
        if actions:
            actions_html = "<div><strong>Actions:</strong></div>"
            for action_index, action in enumerate(actions, 1):
                command = action.get('command', 'unknown')
                params = action.get('params', {})
                
                # Format params as key=value pairs, excluding wait_time for cleaner display
                filtered_params = {k: v for k, v in params.items() if k != 'wait_time'}
                params_str = ", ".join([f"{k}='{v}'" for k, v in filtered_params.items()]) if filtered_params else ""
                
                # Create clean action line without labels
                action_line = f"{action_index}. {command}({params_str})" if params_str else f"{action_index}. {command}"
                
                actions_html += f'<div class="action-item">{action_line}</div>'
        
        # Add retry actions if they exist
        if retry_actions:
            actions_html += "<div style='margin-top: 10px;'><strong>Retry Actions:</strong> <span class='retry-status available'>AVAILABLE</span></div>"
            for retry_index, retry_action in enumerate(retry_actions, 1):
                command = retry_action.get('command', 'unknown')
                params = retry_action.get('params', {})
                
                # Format params as key=value pairs, excluding wait_time for cleaner display
                filtered_params = {k: v for k, v in params.items() if k != 'wait_time'}
                params_str = ", ".join([f"{k}='{v}'" for k, v in filtered_params.items()]) if filtered_params else ""
                
                # Create clean retry action line without labels
                retry_line = f"{retry_index}. {command}({params_str})" if params_str else f"{retry_index}. {command}"
                
                actions_html += f'<div class="retry-action-item available">{retry_line}</div>'
        
        # Add failure actions if they exist
        if failure_actions:
            actions_html += "<div style='margin-top: 10px;'><strong>Failure Actions:</strong> <span class='failure-status available'>AVAILABLE</span></div>"
            for failure_index, failure_action in enumerate(failure_actions, 1):
                command = failure_action.get('command', 'unknown')
                params = failure_action.get('params', {})
                
                # Format params as key=value pairs, excluding wait_time for cleaner display
                filtered_params = {k: v for k, v in params.items() if k != 'wait_time'}
                params_str = ", ".join([f"{k}='{v}'" for k, v in filtered_params.items()]) if filtered_params else ""
                
                # Create clean failure action line without labels
                failure_line = f"{failure_index}. {command}({params_str})" if params_str else f"{failure_index}. {command}"
                
                actions_html += f'<div class="failure-action-item available">{failure_line}</div>'
        
        verifications_html = ""
        verification_results = step.get('verification_results', [])
        
        if verifications:
            verifications_html = "<div><strong>Verifications:</strong></div>"
            for verification_index, verification in enumerate(verifications, 1):
                # Handle different verification formats
                if isinstance(verification, dict):
                    command = verification.get('command', verification.get('type', verification.get('verification_type', 'unknown')))
                    params = verification.get('params', verification.get('parameters', {}))
                    label = verification.get('label', '')
                    
                    # Format params, excluding common system params
                    filtered_params = {k: v for k, v in params.items() if k not in ['wait_time', 'timeout']}
                    params_str = ", ".join([f"{k}='{v}'" for k, v in filtered_params.items()]) if filtered_params else ""
                    
                    # Create verification line with label if available
                    if label:
                        verification_line = f"{verification_index}. {label}: {command}({params_str})" if params_str else f"{verification_index}. {label}: {command}"
                    else:
                        verification_line = f"{verification_index}. {command}({params_str})" if params_str else f"{verification_index}. {command}"
                else:
                    verification_line = f"{verification_index}. {str(verification)}"
                
                # Add verification result if available
                verification_result_html = ""
                if verification_index <= len(verification_results):
                    result = verification_results[verification_index-1]  # 0-indexed array
                    result_success = result.get('success', False)
                    result_message = result.get('message', '')
                    result_badge = f'<span class="verification-result-badge {"success" if result_success else "failure"}">{"PASS" if result_success else "FAIL"}</span>'
                    verification_result_html = f" {result_badge}"
                    if not result_success and result.get('error'):
                        verification_result_html += f" <span class='verification-error'>({result['error']})</span>"
                
                verifications_html += f'<div class="verification-item">{verification_line}{verification_result_html}</div>'
        elif verification_results:
            # Show verification results even if verification definitions are missing
            verifications_html = "<div><strong>Verification Results:</strong></div>"
            for verification_index, result in enumerate(verification_results, 1):
                result_success = result.get('success', False)
                result_message = result.get('message', 'Verification completed')
                verification_type = result.get('verification_type', 'unknown')
                result_badge = f'<span class="verification-result-badge {"success" if result_success else "failure"}">{"PASS" if result_success else "FAIL"}</span>'
                
                verification_line = f"{verification_index}. {verification_type}: {result_message}"
                if not result_success and result.get('error'):
                    verification_line += f" <span class='verification-error'>({result['error']})</span>"
                
                verifications_html += f'<div class="verification-item">{verification_line} {result_badge}</div>'
        
        # Add script output if available (for simple script execution)
        script_output_html = ""
        script_output = step.get('script_output', {})
        if script_output and (script_output.get('stdout') or script_output.get('stderr')):
            script_output_html = "<div><strong>Script Output:</strong></div>"
            
            if script_output.get('stdout'):
                script_output_html += f'<div class="script-output stdout"><strong>Output:</strong><pre>{script_output["stdout"]}</pre></div>'
            
            if script_output.get('stderr'):
                script_output_html += f'<div class="script-output stderr"><strong>Error:</strong><pre>{script_output["stderr"]}</pre></div>'
            
            exit_code = script_output.get('exit_code', 0)
            script_output_html += f'<div class="script-output exit-code"><strong>Exit Code:</strong> {exit_code}</div>'
        
        # Add analysis results if available (for zap actions)
        analysis_html = ""
        motion_analysis = step.get('motion_analysis', {})
        subtitle_analysis = step.get('subtitle_analysis', {})
        audio_menu_analysis = step.get('audio_menu_analysis', {})
        zapping_analysis = step.get('zapping_analysis', {})
        
        if motion_analysis or subtitle_analysis or audio_menu_analysis or zapping_analysis:
            analysis_html = "<div><strong>Analysis Results:</strong></div>"
            
            # Motion Detection Results
            if motion_analysis and motion_analysis.get('success') is not None:
                motion_success = motion_analysis.get('success', False)
                motion_status = "✅ DETECTED" if motion_success else "❌ NOT DETECTED"
                analysis_html += f'<div class="analysis-item motion"><strong>Motion Detection:</strong> {motion_status}</div>'
                
                if motion_analysis.get('total_analyzed'):
                    analysis_html += f'<div class="analysis-detail">Files analyzed: {motion_analysis.get("total_analyzed", 0)}</div>'
                if motion_analysis.get('message'):
                    analysis_html += f'<div class="analysis-detail">Details: {motion_analysis.get("message")}</div>'
            
            # Subtitle Analysis Results  
            if subtitle_analysis and subtitle_analysis.get('success') is not None:
                subtitle_detected = subtitle_analysis.get('subtitles_detected', False)
                subtitle_status = "✅ DETECTED" if subtitle_detected else "❌ NOT DETECTED"
                analysis_html += f'<div class="analysis-item subtitle"><strong>Subtitle Analysis:</strong> {subtitle_status}</div>'
                
                if subtitle_analysis.get('detected_language'):
                    analysis_html += f'<div class="analysis-detail">Language: {subtitle_analysis.get("detected_language")}</div>'
                if subtitle_analysis.get('extracted_text'):
                    text = subtitle_analysis.get('extracted_text', '')[:100] + ('...' if len(subtitle_analysis.get('extracted_text', '')) > 100 else '')
                    analysis_html += f'<div class="analysis-detail">Text: {text}</div>'
            
            # Audio Menu Analysis Results
            if audio_menu_analysis and audio_menu_analysis.get('success') is not None:
                menu_detected = audio_menu_analysis.get('menu_detected', False)
                menu_status = "✅ DETECTED" if menu_detected else "❌ NOT DETECTED"
                analysis_html += f'<div class="analysis-item audio-menu"><strong>Audio Menu Analysis:</strong> {menu_status}</div>'
                
                if audio_menu_analysis.get('audio_languages'):
                    languages = ', '.join(audio_menu_analysis.get('audio_languages', []))
                    analysis_html += f'<div class="analysis-detail">Audio Languages: {languages}</div>'
                if audio_menu_analysis.get('subtitle_languages'):
                    subtitles = ', '.join(audio_menu_analysis.get('subtitle_languages', []))
                    analysis_html += f'<div class="analysis-detail">Subtitle Options: {subtitles}</div>'
            
            # Zapping Analysis Results
            if zapping_analysis and zapping_analysis.get('success') is not None:
                zapping_detected = zapping_analysis.get('zapping_detected', False)
                zapping_status = "✅ DETECTED" if zapping_detected else "❌ NOT DETECTED"
                analysis_html += f'<div class="analysis-item zapping"><strong>Zapping Analysis:</strong> {zapping_status}</div>'
                
                if zapping_analysis.get('blackscreen_duration'):
                    duration = zapping_analysis.get('blackscreen_duration', 0.0)
                    analysis_html += f'<div class="analysis-detail">Blackscreen Duration: {duration:.2f}s</div>'
                if zapping_analysis.get('zapping_duration'):
                    zap_duration = zapping_analysis.get('zapping_duration', 0.0)
                    analysis_html += f'<div class="analysis-detail">Zap Duration: {zap_duration:.2f}s</div>'
                if zapping_analysis.get('channel_info', {}).get('channel_name'):
                    channel_info = zapping_analysis.get('channel_info', {})
                    channel_name = channel_info.get('channel_name', '')
                    analysis_html += f'<div class="analysis-detail">📺 Channel: {channel_name}</div>'
                    if channel_info.get('channel_number'):
                        channel_number = channel_info.get('channel_number', '')
                        analysis_html += f'<div class="analysis-detail">📺 Channel Number: {channel_number}</div>'
                    if channel_info.get('program_name'):
                        program_name = channel_info.get('program_name', '')
                        analysis_html += f'<div class="analysis-detail">🎬 Program: {program_name}</div>'
                    if channel_info.get('start_time') and channel_info.get('end_time'):
                        start_time = channel_info.get('start_time', '')
                        end_time = channel_info.get('end_time', '')
                        analysis_html += f'<div class="analysis-detail">⏰ Time: {start_time} - {end_time}</div>'
                # Key images in the zapping sequence (with clickable hyperlinks)
                def create_image_link(image_name, display_text):
                    """Create clickable hyperlink for image - will be converted to R2 URL by update_step_results_with_r2_urls"""
                    if image_name:
                        # The image_name might already be an R2 URL after URL mapping, or still a filename
                        if image_name.startswith('http'):
                            # Already an R2 URL
                            return f'<a href="{image_name}" target="_blank" style="color: #0066cc; text-decoration: underline;">{display_text}</a>'
                        else:
                            # Still a filename - will be converted to R2 URL later
                            return f'<a href="{image_name}" target="_blank" style="color: #0066cc; text-decoration: underline;">{display_text}</a>'
                    return display_text
                
                if zapping_analysis.get('first_image'):
                    first_image = zapping_analysis.get('first_image', '')
                    image_link = create_image_link(first_image, first_image)
                    analysis_html += f'<div class="analysis-detail">🎬 Start Image: {image_link}</div>'
                if zapping_analysis.get('blackscreen_start_image'):
                    start_image = zapping_analysis.get('blackscreen_start_image', '')
                    image_link = create_image_link(start_image, start_image)
                    analysis_html += f'<div class="analysis-detail">⚫ First Black: {image_link}</div>'
                if zapping_analysis.get('blackscreen_end_image'):
                    end_image = zapping_analysis.get('blackscreen_end_image', '')
                    image_link = create_image_link(end_image, end_image)
                    analysis_html += f'<div class="analysis-detail">⚫ Last Black: {image_link}</div>'
                if zapping_analysis.get('first_content_after_blackscreen'):
                    content_image = zapping_analysis.get('first_content_after_blackscreen', '')
                    image_link = create_image_link(content_image, content_image)
                    analysis_html += f'<div class="analysis-detail">📺 First Content: {image_link}</div>'
                if zapping_analysis.get('channel_detection_image'):
                    channel_image = zapping_analysis.get('channel_detection_image', '')
                    image_link = create_image_link(channel_image, channel_image)
                    analysis_html += f'<div class="analysis-detail">🔍 Channel Detection: {image_link}</div>'
                if zapping_analysis.get('analyzed_images'):
                    analyzed_count = zapping_analysis.get('analyzed_images', 0)
                    total_count = zapping_analysis.get('total_images_available', 0)
                    analysis_html += f'<div class="analysis-detail">Images analyzed: {analyzed_count}/{total_count}</div>'
        
        # Get all screenshots for this step (action screenshots + step screenshot)
        screenshot_html = ''
        screenshots_for_step = []
        
        # Add action screenshots with metadata
        action_screenshots = step.get('action_screenshots', [])
        actions = step.get('actions', [])
        for i, screenshot_path in enumerate(action_screenshots):
            action_cmd = actions[i].get('command', 'unknown') if i < len(actions) else 'unknown'
            action_params = actions[i].get('params', {}) if i < len(actions) else {}
            screenshots_for_step.append((f'Action {i+1}', screenshot_path, action_cmd, action_params))
        
        # Add step-level screenshot if available
        if step.get('screenshot_url'):
            screenshots_for_step.append(('Step', step.get('screenshot_url'), None, None))
        elif step.get('screenshot_path'):
            screenshots_for_step.append(('Step', step.get('screenshot_path'), None, None))
        
        if screenshots_for_step:
            step_id = step.get('step_number', step_index+1)
            # Use EXACT same logic as working preview
            from_node = step.get('from_node', 'Unknown')
            to_node = step.get('to_node', 'Unknown')
            step_title = f"Step {step_id}: {from_node} → {to_node}"
            
            # Show only the LAST screenshot as thumbnail
            last_screenshot = screenshots_for_step[-1]
            last_screenshot_path = last_screenshot[1]
            screenshot_count = len(screenshots_for_step)
            
            # Create single thumbnail that opens modal with all screenshots
            thumbnail_html = get_thumbnail_screenshot_html(
                last_screenshot_path, 
                f"{screenshot_count} screenshot{'s' if screenshot_count > 1 else ''}", 
                step_title, 
                screenshots_for_step, 
                len(screenshots_for_step) - 1  # Start at last screenshot
            )
            
            screenshot_html = f"""
            <div class="step-screenshot-container">
                <div class="screenshot-row">
                    {thumbnail_html}
                </div>
            </div>
            """
        
        step_html = f"""
        <div class="step-item {'success' if success else 'failure'}" onclick="toggleStep('step-details-{step_index}')">
            <div class="step-number">{step_number}</div>
            <div class="step-status">
                <span class="step-status-badge {'success' if success else 'failure'}">
                    {'PASS' if success else 'FAIL'}
                </span>
            </div>
            <div class="step-message">
                {message}
                <div class="step-timing-inline">{timing_header}</div>
            </div>
        </div>
        <div id="step-details-{step_index}" class="step-details">
             <div class="step-details-content">
                 <div class="step-info">
                     {actions_html}
                     {verifications_html}
                     {script_output_html}
                     {analysis_html}
                 </div>
                 {screenshot_html}
             </div>
        </div>
        """
        steps_html.append(step_html)
    
    steps_html.append('</div>')
    return ''.join(steps_html)

def get_video_thumbnail_html(video_url: str, label: str = "Video") -> str:
    """Generate HTML for video thumbnail that opens video URL in modal"""
    if not video_url:
        return ""
    
    # Escape quotes in the URL and label for JavaScript
    escaped_url = video_url.replace("'", "\\'").replace('"', '\\"')
    escaped_label = label.replace("'", "\\'").replace('"', '\\"')
    
    return f"""
    <div class="video-thumbnail" onclick="console.log('Video thumbnail clicked'); openHLSVideoModal('{escaped_url}', '{escaped_label}')" style="cursor: pointer;" title="Click to play HLS video">
        <video muted preload="metadata">
            <source src="{video_url}" type="application/x-mpegURL">
        </video>
        <div class="play-overlay">▶</div>
        <div class="video-label">{label}</div>
    </div>
    """

def format_console_summary_for_html(console_text: str) -> str:
    """Convert console summary text to HTML format."""
    print(f"[@utils:report_utils:format_console_summary_for_html] Input text: '{console_text[:100] if console_text else 'EMPTY'}'...")
    
    if not console_text:
        print(f"[@utils:report_utils:format_console_summary_for_html] No console text provided, returning placeholder")
        # Return a placeholder when no summary is available
        return """
        <h3>Execution Summary</h3>
        <div class="summary-stats">
            <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0;">📊 Execution summary not available<br>ℹ️  This may be from an older script run<br>🔄 Run the script again to see detailed summary</pre>
        </div>
        """
    
    # Simple conversion - preserve line breaks and basic formatting
    html_text = console_text.replace('\n', '<br>')
    html_text = html_text.replace('=', '')  # Remove separator lines
    html_text = html_text.replace('  •', '<br>  •')  # Better bullet formatting
    
    result = f"""
    <h3>Execution Summary</h3>
    <div class="summary-stats">
        <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0;">{html_text}</pre>
    </div>
    """
    
    print(f"[@utils:report_utils:format_console_summary_for_html] Generated HTML length: {len(result)}")
    return result


def create_error_section(error_msg: str) -> str:
    """Create HTML for error section."""
    return f"""
    <div class="section">
        <div class="error-section">
            <h3>Error Details</h3>
            <div class="error-message">{error_msg}</div>
        </div>
    </div>
    """

def get_thumbnail_screenshot_html(screenshot_path: Optional[str], label: str = None, step_title: str = None, all_screenshots: list = None, current_index: int = 0) -> str:
    """Get HTML for displaying a thumbnail screenshot that opens modal with navigation."""
    # Return empty string if no screenshot path provided
    if not screenshot_path:
        return ''
    
    # Prepare screenshots for modal - use the SAME working URLs
    modal_screenshots = []
    if all_screenshots:
        for screenshot_data in all_screenshots:
            screenshot_label = screenshot_data[0]
            screenshot_working_path = screenshot_data[1]  # This is the working path
            action_cmd = screenshot_data[2] if len(screenshot_data) > 2 else None
            action_params = screenshot_data[3] if len(screenshot_data) > 3 else None
            
            modal_screenshots.append({
                'label': screenshot_label,
                'url': screenshot_working_path,  # Use the same working path
                'command': action_cmd,
                'params': action_params or {}
            })
    else:
        modal_screenshots.append({
            'label': label or 'Screenshot',
            'url': screenshot_path,
            'command': None,
            'params': {}
        })
    
    # Create modal data for navigation
    modal_data = {
        'step_title': step_title or 'Screenshot',
        'screenshots': modal_screenshots,
        'current_index': current_index
    }
    
    # Encode modal data as JSON for JavaScript
    import json
    modal_data_json = json.dumps(modal_data).replace('"', '&quot;').replace("'", "&#x27;")
    
    # Always use URLs for consistency and performance (no more base64 embedding)
    if screenshot_path.startswith('http'):
        # It's already an R2 URL - use directly
        display_url = screenshot_path
    else:
        # It's a local file path - this shouldn't happen after our URL mapping fix
        # But if it does, use the local path and let the browser handle it
        print(f"[@utils:report_utils:get_thumbnail_screenshot_html] Warning: Using local path instead of R2 URL: {screenshot_path}")
        display_url = screenshot_path
    
    return f"""
    <div class="screenshot-container">
        <span class="screenshot-label">{label or 'Screenshot'}</span>
        <img src="{display_url}" alt="Screenshot" class="screenshot-thumbnail" onclick="openScreenshotModal('{modal_data_json}')">
    </div>
    """



def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        # Convert YYYYMMDDHHMMSS to readable format
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        return dt.strftime('%H:%M:%S')
    except:
        return timestamp

def format_execution_time(execution_time_ms: int) -> str:
    """Format execution time for display."""
    if execution_time_ms < 1000:
        return f"{execution_time_ms}ms"
    elif execution_time_ms < 60000:
        return f"{execution_time_ms / 1000:.1f}s"
    else:
        minutes = execution_time_ms // 60000
        seconds = (execution_time_ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"

def update_step_results_with_r2_urls(step_results: List[Dict], url_mapping: Dict[str, str]) -> List[Dict]:
    """
    Update step results to replace local screenshot paths with R2 URLs.
    
    Args:
        step_results: List of step result dictionaries
        url_mapping: Dictionary mapping local paths to R2 URLs
        
    Returns:
        Updated step results with R2 URLs
    """
    if not url_mapping:
        return step_results
    
    updated_results = []
    for step in step_results:
        updated_step = step.copy()  # Shallow copy
        
        # Update action_screenshots (list of local paths)
        if 'action_screenshots' in updated_step:
            updated_action_screenshots = []
            for screenshot_path in updated_step['action_screenshots']:
                # For thumbnails, we want to use the thumbnail R2 URL if available
                # Check if there's a thumbnail version of this screenshot
                thumbnail_path = screenshot_path.replace('.jpg', '_thumbnail.jpg')
                r2_url = url_mapping.get(thumbnail_path, url_mapping.get(screenshot_path, screenshot_path))
                updated_action_screenshots.append(r2_url)
                if r2_url != screenshot_path:
                    print(f"[@utils:report_utils:update_step_results_with_r2_urls] Updated action screenshot: {screenshot_path} -> {r2_url}")
            updated_step['action_screenshots'] = updated_action_screenshots
        
        # Update screenshot_path (single path)
        if 'screenshot_path' in updated_step and updated_step['screenshot_path']:
            original_path = updated_step['screenshot_path']
            r2_url = url_mapping.get(original_path, original_path)
            updated_step['screenshot_path'] = r2_url
            if r2_url != original_path:
                print(f"[@utils:report_utils:update_step_results_with_r2_urls] Updated step screenshot: {original_path} -> {r2_url}")
        
        # Update screenshot_url (if it exists and is a local path)
        if 'screenshot_url' in updated_step and updated_step['screenshot_url']:
            original_url = updated_step['screenshot_url']
            # Only update if it's not already a URL (doesn't start with http)
            if not original_url.startswith('http'):
                r2_url = url_mapping.get(original_url, original_url)
                updated_step['screenshot_url'] = r2_url
                if r2_url != original_url:
                    print(f"[@utils:report_utils:update_step_results_with_r2_urls] Updated screenshot URL: {original_url} -> {r2_url}")
        
        # Update zapping analysis image filenames to R2 URLs
        if 'zapping_analysis' in updated_step and updated_step['zapping_analysis']:
            zapping_analysis = updated_step['zapping_analysis'].copy()
            
            # List of image fields to update
            image_fields = [
                'first_image', 'blackscreen_start_image', 'blackscreen_end_image',
                'first_content_after_blackscreen', 'channel_detection_image', 'last_image'
            ]
            
            for field in image_fields:
                if field in zapping_analysis and zapping_analysis[field]:
                    filename = zapping_analysis[field]
                    # Construct the full path that would have been added to screenshot_paths
                    # Format: /path/to/captures/capture_YYYYMMDDHHMMSS.jpg
                    for local_path, r2_url in url_mapping.items():
                        if filename in local_path:  # If the filename appears in the local path
                            zapping_analysis[field] = r2_url
                            print(f"[@utils:report_utils:update_step_results_with_r2_urls] Updated zapping {field}: {filename} -> {r2_url}")
                            break
            
            updated_step['zapping_analysis'] = zapping_analysis
        
        updated_results.append(updated_step)
    
    return updated_results

def generate_and_upload_script_report(
    script_name: str,
    device_info: Dict,
    host_info: Dict,
    execution_time: int,
    success: bool,
    step_results: List[Dict] = None,
    screenshot_paths: List[str] = None,
    error_message: str = "",
    userinterface_name: str = "",
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    parameters: str = "",
    execution_summary: str = "",
    test_video_url: str = ""
) -> Dict[str, str]:
    """
    Generate HTML report and upload to R2 storage - extracted from validation.py
    Can be used by any script execution (validation, simple scripts, etc.)
    
    Returns:
        Dict with 'report_url', 'report_path', and 'success' keys
    """
    try:
        from .cloudflare_utils import upload_script_report, upload_validation_screenshots
        from datetime import datetime
        
        execution_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Handle simple script execution (no step_results)
        if not step_results:
            step_results = [{
                'step_number': 1,
                'success': success,
                'screenshot_path': None,
                'message': f'Script execution: {script_name}',
                'execution_time_ms': execution_time,
                'start_time': 'N/A',
                'end_time': 'N/A',
                'from_node': 'Script Start',
                'to_node': 'Script End',
                'actions': [{
                    'command': f'python {script_name}',
                    'params': {'parameters': parameters} if parameters else {},
                    'label': f'Execute {script_name} script'
                }],
                'verifications': [],
                'verification_results': [],
                'script_output': {
                    'stdout': stdout[:2000] if stdout else '',
                    'stderr': stderr[:2000] if stderr else '',
                    'exit_code': exit_code
                }
            }]
        
        # Calculate verification statistics
        total_verifications = sum(len(step.get('verification_results', [])) for step in step_results)
        passed_verifications = sum(
            sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
            for step in step_results
        )
        failed_verifications = total_verifications - passed_verifications
        
        # Upload screenshots FIRST to get R2 URLs
        url_mapping = {}  # Map local paths to R2 URLs
        if screenshot_paths:
            screenshot_result = upload_validation_screenshots(
                screenshot_paths=screenshot_paths,
                device_model=device_info.get('device_model', 'unknown'),
                script_name=script_name.replace('.py', ''),
                timestamp=execution_timestamp
            )
            
            if screenshot_result['success']:
                print(f"[@utils:report_utils:generate_and_upload_script_report] Screenshots uploaded: {screenshot_result['uploaded_count']} files")
                # Create mapping from local paths to R2 URLs
                for upload_info in screenshot_result.get('uploaded_screenshots', []):
                    local_path = upload_info['local_path']
                    r2_url = upload_info['url']
                    url_mapping[local_path] = r2_url
                    print(f"[@utils:report_utils:generate_and_upload_script_report] Mapped: {local_path} -> {r2_url}")
            else:
                print(f"[@utils:report_utils:generate_and_upload_script_report] Screenshot upload failed: {screenshot_result.get('error', 'Unknown error')}")
        
        # Update step_results to use R2 URLs instead of local paths
        updated_step_results = update_step_results_with_r2_urls(step_results, url_mapping)
        
        # Debug execution summary
        print(f"[@utils:report_utils:generate_and_upload_script_report] Execution summary received: '{execution_summary[:100] if execution_summary else 'EMPTY'}'...")
        
        # Prepare report data (same structure as validation.py) - now with R2 URLs
        report_data = {
            'script_name': script_name,
            'device_info': device_info,
            'host_info': host_info,
            'execution_time': execution_time,
            'success': success,
            'step_results': updated_step_results,  # Use updated step results with R2 URLs
            'screenshots': {
                'initial': url_mapping.get(screenshot_paths[0], screenshot_paths[0]) if screenshot_paths and len(screenshot_paths) > 0 else None,
                'steps': [url_mapping.get(path, path) for path in screenshot_paths[1:-1]] if screenshot_paths and len(screenshot_paths) > 2 else [],
                'final': url_mapping.get(screenshot_paths[-1], screenshot_paths[-1]) if screenshot_paths and len(screenshot_paths) > 1 else None
            },
            'error_msg': error_message,
            'timestamp': execution_timestamp,
            'userinterface_name': userinterface_name or f'script_{script_name}',
            'total_steps': len(updated_step_results),
            'passed_steps': sum(1 for step in updated_step_results if step.get('success', False)),
            'failed_steps': sum(1 for step in updated_step_results if not step.get('success', True)),
            'total_verifications': total_verifications,
            'passed_verifications': passed_verifications,
            'failed_verifications': failed_verifications,
            'execution_summary': execution_summary,
            'test_video_url': test_video_url
        }
        
        # Generate HTML content using existing function - now with R2 URLs
        html_content = generate_validation_report(report_data)
        
        # Upload report to R2
        upload_result = upload_script_report(
            html_content=html_content,
            device_model=device_info.get('device_model', 'unknown'),
            script_name=script_name.replace('.py', ''),
            timestamp=execution_timestamp
        )
        
        if upload_result['success']:
            report_url = upload_result['report_url']
            report_path = upload_result['report_path']
            print(f"[@utils:report_utils:generate_and_upload_script_report] Report uploaded: {report_url}")
            return {
                'success': True,
                'report_url': report_url,
                'report_path': report_path
            }
        else:
            print(f"[@utils:report_utils:generate_and_upload_script_report] Upload failed: {upload_result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'report_url': '',
                'report_path': ''
            }
        
    except Exception as e:
        print(f"[@utils:report_utils:generate_and_upload_script_report] Error: {str(e)}")
        return {
            'success': False,
            'report_url': '',
            'report_path': ''
        }

def create_error_report(error_message: str) -> str:
    """Create a minimal error report when report generation fails."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Report Generation Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        .error {{ color: red; background: #ffe6e6; padding: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Report Generation Error</h1>
    <div class="error">
        <h3>Error occurred while generating the report:</h3>
        <p>{error_message}</p>
    </div>
</body>
</html>"""

