"""
Report Step Formatting

Handles the formatting of individual step results for HTML reports.
"""

import os
import json
from typing import Dict, List
from datetime import datetime
from .cloudflare_utils import convert_to_signed_url


def ensure_signed_url(url: str) -> str:
    """Ensure URL is signed if it's an R2 URL."""
    if not url:
        return url
    if 'r2.dev' in url or 'r2.cloudflarestorage.com' in url or url.startswith('script-reports/') or url.startswith('navigation/'):
        return convert_to_signed_url(url)
    return url


def format_timestamp_to_hhmmss_ms(timestamp_str: str) -> str:
    """Format timestamp string to readable format like 21H25m26s.698ms."""
    if not timestamp_str:
        return 'N/A'
    
    try:
        # Parse ISO timestamp and format with milliseconds
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        # Format as 21H25m26s.698ms (more readable)
        ms = dt.microsecond // 1000
        return f"{dt.strftime('%H')}H{dt.strftime('%M')}m{dt.strftime('%S')}s.{ms:03d}ms"
    except (ValueError, AttributeError):
        return 'N/A'


def extract_capture_filename_from_url(url_or_path: str) -> str:
    """Extract capture filename from URL or path."""
    if not url_or_path:
        return 'unknown'
    
    try:
        # Extract filename from URL or path
        filename = os.path.basename(url_or_path)
        # Remove .jpg extension if present
        if filename.endswith('.jpg'):
            filename = filename[:-4]
        return filename
    except:
        return 'unknown'


def format_capture_display_name(capture_filename: str) -> str:
    """Format capture filename consistently across all analysis types."""
    if not capture_filename:
        return 'unknown'
    
    try:
        import re
        # Look for timestamp patterns in filename
        timestamp_match = re.search(r'(\d{8}_\d{6})', capture_filename)  # YYYYMMDD_HHMMSS
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            # Convert to readable format: YYYYMMDD_HHMMSS -> HH:MM:SS
            if len(timestamp_str) == 15:  # YYYYMMDD_HHMMSS
                time_part = timestamp_str[9:]  # Get HHMMSS
                formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                return f"{capture_filename} - {formatted_time}"
        else:
            # Check for numeric capture ID patterns
            # Pattern 1: Pure numbers (like "10149")
            pure_numeric_match = re.search(r'^(\d{4,5})$', capture_filename)
            if pure_numeric_match:
                return f"#{capture_filename}"
            
            # Pattern 2: capture_NNNNN format (like "capture_10096")
            capture_numeric_match = re.search(r'^capture_(\d{4,5})$', capture_filename)
            if capture_numeric_match:
                capture_id = capture_numeric_match.group(1)
                return f"#{capture_id}"
            
            # If no pattern found, just use filename as-is
            return capture_filename
    except Exception:
        # Fallback to just filename if formatting fails
        return capture_filename


def format_screenshot_display_name(screenshot_url_or_path: str) -> str:
    """
    Single function to format screenshot display names consistently.
    Combines extract_capture_filename_from_url + format_capture_display_name.
    
    Args:
        screenshot_url_or_path: URL or path to screenshot
        
    Returns:
        Formatted display name (e.g., "#10149", "screenshot_20250911_213045_21_30_45")
    """
    if not screenshot_url_or_path:
        return 'unknown'
    
    # Extract filename and format in one step
    filename = extract_capture_filename_from_url(screenshot_url_or_path)
    formatted_name = format_capture_display_name(filename)
    
    # Import sanitization function
    from .report_formatting import sanitize_for_json
    return sanitize_for_json(formatted_name)


def create_compact_step_results_section(step_results: List[Dict], screenshots: Dict) -> str:
    """Create HTML for compact step-by-step results."""
    if not step_results:
        return '<p>No steps executed</p>'
    
    steps_html = ['<div class="step-list">']
    
    for step_index, step in enumerate(step_results):
        step_html = format_single_step(step, step_index, screenshots)
        steps_html.append(step_html)
    
    steps_html.append('</div>')
    return ''.join(steps_html)


def format_single_step(step: Dict, step_index: int, screenshots: Dict) -> str:
    """Format a single step for display."""
    step_number = step.get('step_number', step_index + 1)
    success = step.get('success', False)
    message = step.get('message', 'No message')
    execution_time = step.get('execution_time_ms', 0)
    start_time = step.get('start_time', 'N/A')
    end_time = step.get('end_time', 'N/A')
    
    # Format execution time
    exec_time_str = format_execution_time(execution_time) if execution_time else "N/A"
    timing_header = f"Start: {start_time} End: {end_time} Duration: {exec_time_str}"
    
    # Format step content
    actions_html = format_step_actions(step)
    verifications_html = format_step_verifications(step)
    error_html = format_step_error(step)  # Error shown AFTER verifications
    script_output_html = format_script_output(step)
    analysis_html = format_analysis_results(step)
    screenshot_html = format_step_screenshots(step, step_index)
    
    return f"""
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
                 {error_html}
                 {script_output_html}
                 {analysis_html}
             </div>
             {screenshot_html}
         </div>
    </div>
    """


def format_step_error(step: Dict) -> str:
    """Format error details section for a step."""
    error = step.get('error')
    success = step.get('success', False)
    
    # Only show error section for failed steps with error details
    if success or not error:
        return ""
    
    # Clean and format the error message
    error_html = "<div><strong>❌ Error Details:</strong></div>"
    error_html += '<div class="error-details-container" style="background-color: #fff5f5; border-left: 4px solid #e53e3e; padding: 12px; margin: 8px 0; border-radius: 4px;">'
    
    # Split error message by common delimiters to make it more readable
    error_text = str(error)
    
    # Handle specific error patterns for better formatting
    if "Actions failed:" in error_text:
        # Parse action failure details
        parts = error_text.split("Actions failed:")
        if len(parts) > 1:
            main_error = parts[0].strip()
            failed_actions = parts[1].strip()
            
            if main_error:
                error_html += f'<div class="error-summary" style="font-weight: bold; color: #e53e3e; margin-bottom: 8px;">{main_error}</div>'
            
            error_html += f'<div class="failed-actions" style="color: #a0a0a0; font-size: 14px;">Failed Actions: <span style="color: #e53e3e; font-weight: bold;">{failed_actions}</span></div>'
    
    elif "Detailed selector attempts:" in error_text:
        # Handle Playwright detailed selector failures
        parts = error_text.split("Detailed selector attempts:")
        if len(parts) > 1:
            main_error = parts[0].strip()
            selector_details = parts[1].strip()
            
            error_html += f'<div class="error-summary" style="font-weight: bold; color: #e53e3e; margin-bottom: 8px;">🔍 {main_error}</div>'
            
            # Format selector attempts in a collapsible section
            error_html += '<div class="selector-attempts" style="margin-top: 12px;">'
            error_html += '<div style="font-weight: bold; color: #666; margin-bottom: 6px; cursor: pointer;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === \'none\' ? \'block\' : \'none\'">📋 View All Selector Attempts ▼</div>'
            error_html += '<div style="display: none; background-color: #f8f8f8; padding: 8px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;">'
            
            # Format each selector attempt
            attempt_lines = selector_details.split('\n')
            for line in attempt_lines:
                if line.strip():
                    # Color-code the attempts
                    if "failed" in line.lower():
                        error_html += f'<div style="color: #e53e3e; margin: 2px 0;">{line.strip()}</div>'
                    else:
                        error_html += f'<div style="color: #666; margin: 2px 0;">{line.strip()}</div>'
            
            error_html += '</div></div>'
        else:
            # Fallback if parsing fails
            error_html += f'<div style="color: #e53e3e; font-size: 14px;">{error_text}</div>'
    
    elif "Timeout" in error_text or "timeout" in error_text:
        # Format timeout errors with better structure
        error_html += f'<div class="timeout-error" style="color: #e53e3e;">'
        error_html += f'<div style="font-weight: bold;">⏱️ Timeout Error</div>'
        error_html += f'<div style="margin-top: 4px; font-size: 14px;">{error_text}</div>'
        error_html += f'</div>'
        
    elif "element not found" in error_text.lower():
        # Format element not found errors
        error_html += f'<div class="element-error" style="color: #e53e3e;">'
        error_html += f'<div style="font-weight: bold;">🔍 Element Not Found</div>'
        error_html += f'<div style="margin-top: 4px; font-size: 14px;">{error_text}</div>'
        error_html += f'</div>'
        
    else:
        # Generic error formatting with better line break handling
        error_html += f'<div class="generic-error" style="color: #e53e3e; font-size: 14px; line-height: 1.4;">'
        
        # Handle multiline errors better
        if '\n' in error_text:
            lines = error_text.split('\n')
            for line in lines:
                if line.strip():
                    # Preserve indentation for structured error messages
                    formatted_line = line.replace('  ', '&nbsp;&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
                    error_html += f'<div style="margin: 2px 0;">{formatted_line}</div>'
        else:
            # Single line error
            error_html += error_text
        
        error_html += f'</div>'
    
    # Add debug report link if available (verification failure reports)
    # Check both direct step field and error_details (different code paths may use either)
    debug_report_url = step.get('debug_report_url') or step.get('error_details', {}).get('debug_report_url')
    if debug_report_url:
        error_html += '<div class="debug-report-link" style="margin-top: 12px; padding: 8px; background-color: #e8f4fd; border-left: 4px solid #3182ce; border-radius: 4px;">'
        error_html += f'<a href="{debug_report_url}" target="_blank" style="color: #3182ce; text-decoration: none; font-size: 14px; display: inline-flex; align-items: center; gap: 4px;">'
        error_html += '📊 View Detailed Comparison Report'
        error_html += '<span style="font-size: 12px;">↗</span>'
        error_html += '</a>'
        error_html += '</div>'
    
    error_html += '</div>'
    return error_html


def format_step_actions(step: Dict) -> str:
    """Format actions section for a step with execution status."""
    # Check if this is an "already at destination" step
    if step.get('already_at_destination'):
        return '''<div class="already-at-destination" style="background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 12px; margin: 8px 0; border-radius: 4px;">
            <div style="font-weight: bold; color: #1e40af; margin-bottom: 4px;">✓ Already at Destination</div>
            <div style="color: #64748b; font-size: 14px;">No navigation needed - device was already verified at the target node.</div>
        </div>'''
    
    actions = step.get('actions', [])
    retry_actions = step.get('retry_actions', [])
    failure_actions = step.get('failure_actions', [])
    action_results = step.get('action_results', [])
    
    actions_html = ""
    
    # Determine which actions were executed based on action_results
    executed_categories = set()
    if action_results:
        for result in action_results:
            executed_categories.add(result.get('action_category', 'main'))
    
    # Regular actions
    if actions:
        actions_html = "<div><strong>Actions:</strong></div>"
        for action_index, action in enumerate(actions, 1):
            command = action.get('command', 'unknown')
            params = action.get('params', {})
            
            # Format params as key=value pairs
            params_str = ", ".join([f"{k}='{v}'" for k, v in params.items()]) if params else ""
            
            action_line = f"{action_index}. {command}({params_str})" if params_str else f"{action_index}. {command}"
            
            # Show result if available
            if action_results and action_index <= len([r for r in action_results if r.get('action_category') == 'main']):
                main_results = [r for r in action_results if r.get('action_category') == 'main']
                if action_index - 1 < len(main_results):
                    result = main_results[action_index - 1]
                    success = result.get('success', False)
                    status_badge = f'<span class="action-result-badge {"success" if success else "failure"}">{"✓" if success else "✗"}</span>'
                    action_line += f" {status_badge}"
            
            actions_html += f'<div class="action-item">{action_line}</div>'
    
    # Retry actions
    if retry_actions:
        was_executed = 'retry' in executed_categories
        status_label = 'EXECUTED' if was_executed else 'AVAILABLE'
        status_class = 'executed' if was_executed else 'available'
        
        actions_html += f"<div><strong>Retry Actions:</strong> <span class='retry-status {status_class}'>{status_label}</span></div>"
        for retry_index, retry_action in enumerate(retry_actions, 1):
            command = retry_action.get('command', 'unknown')
            params = retry_action.get('params', {})
            
            # Format params as key=value pairs
            params_str = ", ".join([f"{k}='{v}'" for k, v in params.items()]) if params else ""
            
            retry_line = f"{retry_index}. {command}({params_str})" if params_str else f"{retry_index}. {command}"
            
            # Show result if retry was executed
            if was_executed and action_results:
                retry_results = [r for r in action_results if r.get('action_category') == 'retry']
                if retry_index - 1 < len(retry_results):
                    result = retry_results[retry_index - 1]
                    success = result.get('success', False)
                    status_badge = f'<span class="action-result-badge {"success" if success else "failure"}">{"✓" if success else "✗"}</span>'
                    retry_line += f" {status_badge}"
            
            actions_html += f'<div class="retry-action-item {status_class}">{retry_line}</div>'
    
    # Failure actions
    if failure_actions:
        was_executed = 'failure' in executed_categories
        status_label = 'EXECUTED' if was_executed else 'AVAILABLE'
        status_class = 'executed' if was_executed else 'available'
        
        actions_html += f"<div><strong>Failure Actions:</strong> <span class='failure-status {status_class}'>{status_label}</span></div>"
        for failure_index, failure_action in enumerate(failure_actions, 1):
            command = failure_action.get('command', 'unknown')
            params = failure_action.get('params', {})
            
            # Format params as key=value pairs
            params_str = ", ".join([f"{k}='{v}'" for k, v in params.items()]) if params else ""
            
            failure_line = f"{failure_index}. {command}({params_str})" if params_str else f"{failure_index}. {command}"
            
            # Show result if failure action was executed
            if was_executed and action_results:
                failure_results = [r for r in action_results if r.get('action_category') == 'failure']
                if failure_index - 1 < len(failure_results):
                    result = failure_results[failure_index - 1]
                    success = result.get('success', False)
                    status_badge = f'<span class="action-result-badge {"success" if success else "failure"}">{"✓" if success else "✗"}</span>'
                    failure_line += f" {status_badge}"
            
            actions_html += f'<div class="failure-action-item {status_class}">{failure_line}</div>'
    
    return actions_html


def format_step_verifications(step: Dict) -> str:
    """Format verifications section for a step."""
    verifications = step.get('verifications', [])
    verification_results = step.get('verification_results', [])
    
    if not verifications and not verification_results:
        return ""
    
    verifications_html = ""
    
    if verifications:
        verifications_html = "<div><strong>Verifications:</strong></div>"
        for verification_index, verification in enumerate(verifications, 1):
            verification_line = format_verification_item(verification, verification_index)
            
            # Add verification result if available
            verification_result_html = ""
            if verification_index <= len(verification_results):
                result = verification_results[verification_index-1]
                verification_result_html = format_verification_result(result, step)
            
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
            verification_result_html = f" {result_badge}"
            
            if not result_success and result.get('error'):
                verification_result_html += f" <span class='verification-error'>({result['error']})</span>"
            
            verification_result_html += format_image_verification_extras(result, step)
            
            verifications_html += f'<div class="verification-item">{verification_line}{verification_result_html}</div>'
    
    return verifications_html


def format_verification_item(verification: Dict, verification_index: int) -> str:
    """Format a single verification item."""
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
    
    return verification_line


def format_verification_result(result: Dict, step: Dict) -> str:
    """Format verification result with badges and extras."""
    result_success = result.get('success', False)
    
    # Use tick marks like actions (✓/✗) with percentage for image verifications
    badge_text = "✓" if result_success else "✗"
    if result.get('verification_type') == 'image':
        details = result.get('details', {})
        match_score = details.get('match_score') or details.get('matching_result')
        if match_score is not None:
            badge_text += f" <strong>{match_score*100:.0f}%</strong>"
    
    result_badge = f'<span class="verification-result-badge {"success" if result_success else "failure"}">{badge_text}</span>'
    verification_result_html = f" {result_badge}"
    
    if not result_success and result.get('error'):
        verification_result_html += f" <span class='verification-error'>({result['error']})</span>"
    
    # Add image verification extras (thumbnails only now)
    verification_result_html += format_image_verification_extras(result, step)
    
    return verification_result_html


def format_image_verification_extras(result: Dict, step: Dict) -> str:
    """Format thumbnails for image verifications."""
    if result.get('verification_type') != 'image':
        return ""
    
    extras_html = ""
    details = result.get('details', {})
    
    # Add small thumbnails
    source_image = None
    reference_image = None
    overlay_image = None
    
    # Find source and overlay images from verification_images
    # First try to get from individual verification result, then fall back to step level
    verification_images = result.get('verification_images', []) or step.get('verification_images', [])
    for img_path in verification_images:
        if img_path:
            filename = os.path.basename(img_path).lower()
            if 'source' in filename:
                source_image = img_path
            elif 'overlay' in filename or 'result_overlay' in filename:
                overlay_image = img_path
    
    # Get reference image from details
    reference_image = details.get('reference_image_url')
    
    # Debug logging to help diagnose missing images
    print(f"[@report_step_formatter:format_image_verification_extras] Debug verification images:")
    print(f"  verification_images array: {verification_images}")
    print(f"  source_image found: {source_image}")
    print(f"  overlay_image found: {overlay_image}")
    print(f"  reference_image from details: {reference_image}")
    
    # Create small thumbnails if we have images
    if source_image or reference_image or overlay_image:
        from .report_formatting import create_verification_image_modal_data
        modal_data = create_verification_image_modal_data(source_image, reference_image, overlay_image)
        
        thumbnails_html = "<div class='verification-thumbnails' style='margin-top: 4px; display: flex; gap: 10px;'>"
        
        # Order: Source → Reference → Overlay (logical flow)
        if source_image:
            signed_source = ensure_signed_url(source_image)
            thumbnails_html += f"""
            <div style='text-align: center;'>
                <div style='font-size: 11px; color: #666; margin-bottom: 2px;'>Source</div>
                <img src='{signed_source}' style='width: 60px; height: 40px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                     onclick='openVerificationImageModal({modal_data})' title='Click to compare all images'>
            </div>
            """
        
        if reference_image:
            signed_reference = ensure_signed_url(reference_image)
            thumbnails_html += f"""
            <div style='text-align: center;'>
                <div style='font-size: 11px; color: #666; margin-bottom: 2px;'>Reference</div>
                <img src='{signed_reference}' style='width: 60px; height: 40px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                     onclick='openVerificationImageModal({modal_data})' title='Click to compare all images'>
            </div>
            """
        
        if overlay_image:
            signed_overlay = ensure_signed_url(overlay_image)
            thumbnails_html += f"""
            <div style='text-align: center;'>
                <div style='font-size: 11px; color: #666; margin-bottom: 2px;'>Overlay</div>
                <img src='{signed_overlay}' style='width: 60px; height: 40px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                     onclick='openVerificationImageModal({modal_data})' title='Click to compare all images'>
            </div>
            """
        
        thumbnails_html += "</div>"
        extras_html += thumbnails_html
    
    return extras_html


def format_script_output(step: Dict) -> str:
    """Format script output section for a step."""
    script_output = step.get('script_output', {})
    if not script_output or not (script_output.get('stdout') or script_output.get('stderr')):
        return ""
    
    script_output_html = "<div><strong>Script Output:</strong></div>"
    
    if script_output.get('stdout'):
        script_output_html += f'<div class="script-output stdout"><strong>Output:</strong><pre>{script_output["stdout"]}</pre></div>'
    
    if script_output.get('stderr'):
        script_output_html += f'<div class="script-output stderr"><strong>Error:</strong><pre>{script_output["stderr"]}</pre></div>'
    
    exit_code = script_output.get('exit_code', 0)
    script_output_html += f'<div class="script-output exit-code"><strong>Exit Code:</strong> {exit_code}</div>'
    
    return script_output_html


def format_analysis_results(step: Dict) -> str:
    """Format analysis results section for a step."""
    motion_analysis = step.get('motion_analysis', {})
    subtitle_analysis = step.get('subtitle_analysis', {})
    audio_analysis = step.get('audio_analysis', {})
    audio_menu_analysis = step.get('audio_menu_analysis', {})
    zapping_analysis = step.get('zapping_analysis', {})
    
    if not (motion_analysis or subtitle_analysis or audio_analysis or audio_menu_analysis or zapping_analysis):
        return ""
    
    analysis_html = "<div><strong>Analysis Results:</strong></div>"
    
    # Motion Detection Results
    if motion_analysis and motion_analysis.get('success') is not None:
        motion_success = motion_analysis.get('success', False)
        motion_status = "✅ DETECTED" if motion_success else "❌ NOT DETECTED"
        analysis_html += f'<div class="analysis-item motion"><strong>Motion Detection:</strong> {motion_status}</div>'
        
        # Motion analysis thumbnails (3 analyzed images) - similar to zapping detection
        motion_images = motion_analysis.get('motion_analysis_images', [])
        if motion_images:
            import json
            
            # DEBUG: Log motion_images structure
            print(f"🔍 [ReportFormatter] DEBUG: Processing {len(motion_images)} motion_analysis_images")
            for i, img in enumerate(motion_images):
                print(f"🔍 [ReportFormatter] DEBUG: motion_image[{i}]: path={img.get('path')}, filename={img.get('filename')}")
            
            # Convert motion images to modal format
            images = []
            for motion_img in motion_images:
                image_url = ensure_signed_url(motion_img.get('path', ''))  # Sign R2 URLs
                # Extract analysis info for label with improved formatting
                analysis_data = motion_img.get('analysis_data', {})
                
                # Format capture name and timestamp
                filename = motion_img.get('filename', 'unknown')
                timestamp_str = motion_img.get('timestamp', '')
                
                # Extract readable timestamp
                formatted_time = format_timestamp_to_hhmmss_ms(timestamp_str)
                
                # First line: capture name - time
                first_line = f"{filename} - {formatted_time}"
                
                # Second line: status indicators with proper Yes/No format and color coding
                freeze_val = analysis_data.get('freeze', False)
                blackscreen_val = analysis_data.get('blackscreen', False)
                audio_val = analysis_data.get('audio', True)
                
                freeze_status = "Yes" if freeze_val else "No"
                blackscreen_status = "Yes" if blackscreen_val else "No"
                # FIXED: Audio field semantics - invert display to match user expectation
                # Display "Yes" when audio is present (good), "No" when no audio (bad)
                # This makes audio consistent with freeze/blackscreen where the status indicates presence
                audio_status = "No" if audio_val else "Yes"
                
                # Color logic: issues = freeze present OR blackscreen present OR no audio
                # If audio_val is inverted in source data, adjust color logic accordingly
                has_issues = freeze_val or blackscreen_val or audio_val
                color = "#ff4444" if has_issues else "#44ff44"  # Red for issues, green for good
                
                # Create HTML-formatted second line with color
                second_line_html = f'<span style="color: {color};">Freeze:{freeze_status}, Blackscreen:{blackscreen_status}, Audio:{audio_status}</span>'
                
                # Use actual newline character and HTML formatting
                label = f"{first_line}<br>{second_line_html}"
                images.append({'url': image_url, 'label': label})
                print(f"🔍 [ReportFormatter] DEBUG: Added image to modal: url={image_url}, filename={filename}")
            
            modal_data = {
                'title': 'Motion Analysis - 3 Recent Captures',
                'images': images
            }
            # Encode modal data as JSON for JavaScript with proper escaping
            json_str = json.dumps(modal_data, ensure_ascii=True)
            modal_data_json = json_str.replace('"', '&quot;').replace("'", "&#x27;")
            
            thumbnails_html = "<div class='motion-analysis-thumbnails' style='margin-top: 4px; display: flex; gap: 8px;'>"
            
            for i, image in enumerate(images):
                # Show first 3 images as thumbnails
                if i < 3:
                    # Extract capture name and time from label (first line before <br> or newline)
                    label_first_line = image['label'].split('<br>')[0] if '<br>' in image['label'] else image['label'].split('\n')[0] if '\n' in image['label'] else image['label']
                    thumbnails_html += f"""
                    <div style='text-align: center;'>
                        <img src='{image['url']}' style='width: 120px; height: 80px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                             onclick='openVerificationImageModal({modal_data_json})' title='Click to view motion analysis images'>
                    </div>
                    """
            
            thumbnails_html += "</div>"
            analysis_html += thumbnails_html
    
    # Subtitle Analysis Results
    if subtitle_analysis and subtitle_analysis.get('success') is not None:
        analysis_html += '<div style="margin: 8px 0; border-top: 1px solid #555; opacity: 0.6;"></div>'
        

        subtitle_detected = subtitle_analysis.get('subtitles_detected', False)
        subtitle_status = "✅ DETECTED" if subtitle_detected else "❌ NOT DETECTED"
        analysis_html += f'<div class="analysis-item subtitle"><strong>Subtitle Detection:</strong> {subtitle_status}</div>'
        
        if subtitle_detected:
            if subtitle_analysis.get('detected_language'):
                analysis_html += f'<div class="analysis-detail">Language: {subtitle_analysis.get("detected_language")}</div>'
            if subtitle_analysis.get('extracted_text'):
                text_preview = subtitle_analysis.get('extracted_text')[:100] + ('...' if len(subtitle_analysis.get('extracted_text', '')) > 100 else '')
                analysis_html += f'<div class="analysis-detail">Text: {text_preview}</div>'
        elif subtitle_analysis.get('message'):
            analysis_html += f'<div class="analysis-detail">Details: {subtitle_analysis.get("message")}</div>'
            
        # Show analyzed screenshot thumbnail for debugging (with modal like zapping images)
        analyzed_screenshot = ensure_signed_url(subtitle_analysis.get('analyzed_screenshot'))
        if analyzed_screenshot:
            import json
            # Create single image modal data
            modal_data = {
                'title': 'Subtitle Analysis Screenshot',
                'images': [{'url': analyzed_screenshot, 'label': 'Analyzed for Subtitles'}]
            }
            # Encode modal data as JSON for JavaScript with proper escaping
            json_str = json.dumps(modal_data, ensure_ascii=True)
            modal_data_json = json_str.replace('"', '&quot;').replace("'", "&#x27;")
            
            # Use single function to format screenshot display name
            formatted_display = format_screenshot_display_name(analyzed_screenshot)
            
            analysis_html += f"""
            <div class='subtitle-screenshot' style='margin-top: 4px;'>
                <div>
                    <img src='{analyzed_screenshot}' style='width: 120px; height: 80px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                         onclick='openVerificationImageModal({modal_data_json})' title='Click to view subtitle analysis screenshot'>
                </div>
            </div>
            """
    
    # Audio Speech Analysis Results
    if audio_analysis and audio_analysis.get('success') is not None:
        analysis_html += '<div style="margin: 8px 0; border-top: 1px solid #555; opacity: 0.6;"></div>'
        
        speech_detected = audio_analysis.get('speech_detected', False)
        was_skipped = audio_analysis.get('skipped', False)
        
        if was_skipped:
            speech_status = "⏭️ SKIPPED"
        else:
            speech_status = "✅ DETECTED" if speech_detected else "❌ NOT DETECTED"
        
        analysis_html += f'<div class="analysis-item audio"><strong>Audio Speech Detection:</strong> {speech_status}</div>'
        
        if was_skipped:
            # Show skip reason for skipped analysis
            if audio_analysis.get('details'):
                analysis_html += f'<div class="analysis-detail">Details: {audio_analysis.get("details")}</div>'
        elif speech_detected:
            # Add details on separate lines for better readability
            if audio_analysis.get('detected_language'):
                analysis_html += f'<div class="analysis-detail">Language: {audio_analysis.get("detected_language")}</div>'
            if audio_analysis.get('combined_transcript'):
                transcript_preview = audio_analysis.get('combined_transcript')[:100] + ('...' if len(audio_analysis.get('combined_transcript', '')) > 100 else '')
                analysis_html += f'<div class="analysis-detail">Transcript: {transcript_preview}</div>'
            if audio_analysis.get('confidence'):
                analysis_html += f'<div class="analysis-detail">Confidence: {audio_analysis.get("confidence"):.2f}</div>'
        
            # Show R2 audio URLs if available for traceability (only for actual analysis, not skipped)
            audio_urls = audio_analysis.get('audio_urls', [])
            if audio_urls:
                analysis_html += '<div class="analysis-detail">Audio files:'
                for i, url in enumerate(audio_urls, 1):
                    if url:
                        analysis_html += f' <a href="{url}" target="_blank" style="font-size: 10px; margin-left: 4px;">Segment {i}</a>'
                analysis_html += '</div>'
        else:
            # Show failure details for failed (not skipped) analysis
            if audio_analysis.get('message'):
                analysis_html += f'<div class="analysis-detail">Details: {audio_analysis.get("message")}</div>'
    
    # Audio Menu Analysis Results
    if audio_menu_analysis and audio_menu_analysis.get('success') is not None:
        analysis_html += '<div style="margin: 8px 0; border-top: 1px solid #555; opacity: 0.6;"></div>'
        
        menu_detected = audio_menu_analysis.get('menu_detected', False)
        menu_status = "✅ DETECTED" if menu_detected else "❌ NOT DETECTED"
        analysis_html += f'<div class="analysis-item audio-menu"><strong>Audio Menu Detection:</strong> {menu_status}</div>'
        
        if menu_detected:
            audio_languages = audio_menu_analysis.get('audio_languages', [])
            subtitle_languages = audio_menu_analysis.get('subtitle_languages', [])
            selected_audio = audio_menu_analysis.get('selected_audio', -1)
            selected_subtitle = audio_menu_analysis.get('selected_subtitle', -1)
            
            if audio_languages:
                # Show available audio languages with selected indicator
                audio_display = []
                for i, lang in enumerate(audio_languages):
                    if i == selected_audio:
                        audio_display.append(f"<strong>{lang}</strong> (selected)")
                    else:
                        audio_display.append(lang)
                analysis_html += f'<div class="analysis-detail">Audio Languages: {", ".join(audio_display)}</div>'
            
            if subtitle_languages:
                # Show available subtitle languages with selected indicator
                subtitle_display = []
                for i, lang in enumerate(subtitle_languages):
                    if i == selected_subtitle:
                        subtitle_display.append(f"<strong>{lang}</strong> (selected)")
                    else:
                        subtitle_display.append(lang)
                analysis_html += f'<div class="analysis-detail">Subtitle Languages: {", ".join(subtitle_display)}</div>'
        elif audio_menu_analysis.get('message'):
            analysis_html += f'<div class="analysis-detail">Details: {audio_menu_analysis.get("message")}</div>'

        # Add screenshot display for audio menu analysis (similar to subtitle analysis)
        analyzed_screenshot = ensure_signed_url(audio_menu_analysis.get('analyzed_screenshot'))
        if analyzed_screenshot:
            import json
            # Create single image modal data
            modal_data = {
                'title': 'Audio Menu Analysis Screenshot',
                'images': [{'url': analyzed_screenshot, 'label': 'Analyzed for Audio Menu'}]
            }
            # Encode modal data as JSON for JavaScript with proper escaping
            json_str = json.dumps(modal_data, ensure_ascii=True)
            modal_data_json = json_str.replace('"', '&quot;').replace("'", "&#x27;")
            
            # Use single function to format screenshot display name
            formatted_display = format_screenshot_display_name(analyzed_screenshot)
            
            analysis_html += f"""
            <div class='audio-menu-screenshot' style='margin-top: 4px;'>
                <div style='text-align: center;'>
                    <img src='{analyzed_screenshot}' style='width: 120px; height: 80px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                         onclick='openVerificationImageModal({modal_data_json})' title='Click to view audio menu analysis screenshot'>
                </div>
            </div>
            """
    
    # Zapping Analysis Results  
    if zapping_analysis and zapping_analysis.get('success') is not None:
        # Add discrete separator before zapping section
        analysis_html += '<div style="margin: 8px 0; border-top: 1px solid #555; opacity: 0.6;"></div>'
        
        zapping_detected = zapping_analysis.get('zapping_detected', False)
        zapping_status = "✅ DETECTED" if zapping_detected else "❌ NOT DETECTED"
        analysis_html += f'<div class="analysis-item zapping"><strong>Zapping Detection:</strong> {zapping_status}</div>'
        
        if zapping_detected:
            blackscreen_duration = zapping_analysis.get('blackscreen_duration', 0)
            blackscreen_duration_ms = zapping_analysis.get('blackscreen_duration_ms', 0)
            total_zap_duration_ms = zapping_analysis.get('total_zap_duration_ms', 0)
            audio_silence_duration = zapping_analysis.get('audio_silence_duration', 0)
            zapping_duration = zapping_analysis.get('zapping_duration', 0)  # Legacy field
            channel_info = zapping_analysis.get('channel_info', {})
            analyzed_images = zapping_analysis.get('analyzed_images', 0)
            
            # Combine zapping details with comprehensive timing information
            zap_details = []
            
            # Show total zap duration (action → after blackscreen)
            if total_zap_duration_ms > 0:
                zap_details.append(f"Total Zap Duration: {total_zap_duration_ms/1000:.2f}s")
            elif zapping_duration > 0:  # Legacy fallback
                zap_details.append(f"Total Zap Duration: {zapping_duration:.1f}s")
            
            # Show blackscreen/freeze duration
            if blackscreen_duration_ms > 0:
                zap_details.append(f"Blackscreen Duration: {blackscreen_duration_ms/1000:.2f}s")
            elif blackscreen_duration > 0:  # Legacy fallback
                zap_details.append(f"Blackscreen Duration: {blackscreen_duration:.1f}s")
            
            # Show audio silence duration
            if audio_silence_duration > 0:
                zap_details.append(f"Audio Silence: {audio_silence_duration:.2f}s")
            
            if analyzed_images > 0:
                zap_details.append(f"Images Analyzed: {analyzed_images}")
            
            if zap_details:
                analysis_html += f'<div class="analysis-detail" style="margin-bottom: 6px;">{" | ".join(zap_details)}</div>'
                
            # Channel information with spacing
            if channel_info.get('channel_name'):
                channel_display = channel_info['channel_name']
                if channel_info.get('channel_number'):
                    channel_display += f" ({channel_info['channel_number']})"
                if channel_info.get('program_name'):
                    channel_display += f" - {channel_info['program_name']}"
                
                # Combine channel and program time on single line
                channel_info_line = f"Channel info: {channel_display}"
                if channel_info.get('start_time') and channel_info.get('end_time'):
                    channel_info_line += f" Program Time - {channel_info['start_time']}-{channel_info['end_time']}"
                
                analysis_html += f'<div class="analysis-detail" style="word-wrap: break-word; max-width: none; margin-bottom: 8px;">{channel_info_line}</div>'
            
            # Complete zapping sequence thumbnails (4 key images) - sign all URLs
            before_blackscreen = ensure_signed_url(zapping_analysis.get('first_image'))
            blackscreen_start = ensure_signed_url(zapping_analysis.get('blackscreen_start_image'))
            blackscreen_end = ensure_signed_url(zapping_analysis.get('blackscreen_end_image'))
            first_content = ensure_signed_url(zapping_analysis.get('first_content_after_blackscreen'))
            
            # Debug logging for missing images
            print(f"[@report_step_formatter:format_analysis_results] Zapping images debug:")
            print(f"  before_blackscreen: {before_blackscreen}")
            print(f"  blackscreen_start: {blackscreen_start}")
            print(f"  blackscreen_end: {blackscreen_end}")
            print(f"  first_content: {first_content}")
            
            if before_blackscreen or blackscreen_start or blackscreen_end or first_content:
                from .report_formatting import create_verification_image_modal_data
                
                # Create modal data for complete zapping sequence (4 images)
                images = []
                if before_blackscreen:
                    formatted_display = format_screenshot_display_name(before_blackscreen)
                    images.append({'url': before_blackscreen, 'label': f'{formatted_display}\nBefore Transition'})
                if blackscreen_start:
                    formatted_display = format_screenshot_display_name(blackscreen_start)
                    images.append({'url': blackscreen_start, 'label': f'{formatted_display}\nFirst Transition'})
                if blackscreen_end:
                    formatted_display = format_screenshot_display_name(blackscreen_end)
                    images.append({'url': blackscreen_end, 'label': f'{formatted_display}\nLast Transition'})  
                if first_content:
                    formatted_display = format_screenshot_display_name(first_content)
                    images.append({'url': first_content, 'label': f'{formatted_display}\nFirst Content After'})
                
                if images:
                    import json
                    modal_data = {
                        'title': 'Complete Zapping Sequence Analysis',
                        'images': images
                    }
                    # Encode modal data as JSON for JavaScript with proper escaping
                    json_str = json.dumps(modal_data, ensure_ascii=True)
                    modal_data_json = json_str.replace('"', '&quot;').replace("'", "&#x27;")
                    
                    thumbnails_html = "<div class='zapping-sequence-thumbnails' style='margin-top: 4px; display: flex; gap: 8px;'>"
                    
                    for image in images:
                        thumbnails_html += f"""
                        <div style='text-align: center;'>
                            <img src='{image['url']}' style='width: 120px; height: 80px; object-fit: contain; border: 1px solid #ddd; border-radius: 3px; cursor: pointer;' 
                                 onclick='openVerificationImageModal({modal_data_json})' title='Click to view complete zapping sequence'>
                        </div>
                        """
                    
                    thumbnails_html += "</div>"
                    analysis_html += thumbnails_html
        else:
            if zapping_analysis.get('message'):
                analysis_html += f'<div class="analysis-detail">Details: {zapping_analysis.get("message")}</div>'
            
            # Show analyzed images count for failed detection (same as success case)
            analyzed_images = zapping_analysis.get('analyzed_images', 0)
            if analyzed_images > 0:
                analysis_html += f'<div class="analysis-detail">Images Analyzed: {analyzed_images}</div>'
            
            # Show failure mosaic with detailed analysis - sign URL
            failure_mosaic_path = ensure_signed_url(zapping_analysis.get('failure_mosaic_path'))
            analysis_log = zapping_analysis.get('analysis_log', [])
            
            if failure_mosaic_path:
                import json
                
                # Create modal data with mosaic and detailed analysis log
                modal_data = {
                    'title': f'Zapping Detection Failure Analysis - {zapping_analysis.get("detection_method", "Unknown").title()} Method',
                    'images': [{'url': failure_mosaic_path, 'label': f'Analysis Mosaic ({zapping_analysis.get("mosaic_images_count", 0)} images)'}],
                    'analysis_log': analysis_log
                }
                # Encode modal data as JSON for JavaScript with proper escaping
                json_str = json.dumps(modal_data, ensure_ascii=True)
                modal_data_json = json_str.replace('"', '&quot;').replace("'", "&#x27;")
                
                thumbnails_html = "<div class='zapping-failure-mosaic' style='margin-top: 4px;'>"
                thumbnails_html += f"""
                <div style='text-align: center;'>
                    <div style='font-size: 11px; color: #666; margin-bottom: 2px;'>Failure Analysis Mosaic</div>
                    <img src='{failure_mosaic_path}' style='width: 120px; height: 80px; object-fit: contain; border: 2px solid #e53e3e; border-radius: 4px; cursor: pointer;' 
                         onclick='openZappingAnalysisModal({modal_data_json})' title='Click to view detailed failure analysis'>
                </div>
                """
                thumbnails_html += "</div>"
                analysis_html += thumbnails_html
    
    return analysis_html


def format_step_screenshots(step: Dict, step_index: int) -> str:
    """Format screenshots section for a step."""
    screenshots_for_step = []
    
    # Debug logging to see what screenshot fields are available
    step_num = step.get('step_number', step_index + 1)
    print(f"[@report_step_formatter:format_step_screenshots] Step {step_num} screenshot fields:")
    print(f"  success: {step.get('success')}")
    error_msg = step.get('error', 'No error')
    error_preview = error_msg[:100] + "..." if error_msg and len(str(error_msg)) > 100 else (error_msg or 'No error')
    print(f"  error: {error_preview}")
    print(f"  step_start_screenshot_path: {step.get('step_start_screenshot_path')}")
    print(f"  step_end_screenshot_path: {step.get('step_end_screenshot_path')}")
    print(f"  screenshot_url: {step.get('screenshot_url')}")
    print(f"  screenshot_path: {step.get('screenshot_path')}")
    print(f"  action_screenshots: {step.get('action_screenshots', [])}")
    print(f"  verification_screenshots: {step.get('verification_screenshots', [])}")
    
    # Collect all screenshots in chronological order
    if step.get('step_start_screenshot_path'):
        # Use enhanced formatting for navigation step screenshots
        start_screenshot_path = step.get('step_start_screenshot_path')
        start_formatted_display = format_screenshot_display_name(start_screenshot_path)
        screenshots_for_step.append((f'{start_formatted_display}_step_start', start_screenshot_path, None, None))
    
    # Action screenshots - use action_results to get correct command and category
    # Actions provide their own screenshots, no need for separate "main action screenshot"
    action_screenshots = step.get('action_screenshots', [])
    action_results = step.get('action_results', [])
    
    # If we have action_results (new format with categories), use them
    if action_results:
        for i, screenshot_path in enumerate(action_screenshots):
            if i < len(action_results):
                result = action_results[i]
                action_cmd = result.get('message', 'unknown').split('(')[0].strip()  # Extract command from message
                action_category = result.get('action_category', 'main')  # main, retry, or failure
                action_params = {}  # Results don't include params, but we have the command
                
                # Create label with category indicator
                category_label = {
                    'main': '',
                    'retry': 'retry_',
                    'failure': 'failure_'
                }.get(action_category, '')
                
                # Use enhanced formatting for action screenshots
                # Don't include action_cmd in label - JavaScript will add it with ": cmd"
                action_formatted_display = format_screenshot_display_name(screenshot_path)
                label_suffix = f'{category_label}action' if category_label else ''
                screenshots_for_step.append((f'{action_formatted_display}_{label_suffix}' if label_suffix else action_formatted_display, screenshot_path, action_cmd, action_params))
            else:
                # Fallback if screenshot has no matching result
                action_formatted_display = format_screenshot_display_name(screenshot_path)
                screenshots_for_step.append((f'{action_formatted_display}_action_{i+1}', screenshot_path, 'unknown', {}))
    else:
        # Fallback to old method: combine all actions (main + retry + failure)
        all_actions = []
        all_actions.extend(step.get('actions', []))
        all_actions.extend(step.get('retry_actions', []))
        all_actions.extend(step.get('failure_actions', []))
        
        for i, screenshot_path in enumerate(action_screenshots):
            action_cmd = all_actions[i].get('command', 'unknown') if i < len(all_actions) else 'unknown'
            action_params = all_actions[i].get('params', {}) if i < len(all_actions) else {}
            # Use enhanced formatting for action screenshots
            action_formatted_display = format_screenshot_display_name(screenshot_path)
            screenshots_for_step.append((f'{action_formatted_display}_action_{i+1}', screenshot_path, action_cmd, action_params))
    
    # Verification screenshots - use verification_results to get correct command and type
    verification_screenshots = step.get('verification_screenshots', [])
    verification_results = step.get('verification_results', [])
    verifications = step.get('verifications', [])
    
    if verification_screenshots:
        for i, screenshot_path in enumerate(verification_screenshots):
            if i < len(verification_results):
                result = verification_results[i]
                verification_cmd = result.get('verification_type', 'unknown')
                verification_params = {}
                
                if i < len(verifications):
                    verification = verifications[i]
                    verification_cmd = verification.get('command', verification_cmd)
                    # Extract verification parameters
                    verification_params = verification.get('params', {})
                
                # Use enhanced formatting for verification screenshots
                verification_formatted_display = format_screenshot_display_name(screenshot_path)
                screenshots_for_step.append((f'{verification_formatted_display}_verification_{i+1}', screenshot_path, verification_cmd, verification_params))
            else:
                # Fallback if screenshot has no matching result
                verification_formatted_display = format_screenshot_display_name(screenshot_path)
                screenshots_for_step.append((f'{verification_formatted_display}_verification_{i+1}', screenshot_path, 'unknown', {}))
    
    # Check if this is a dummy "Script Start → Script End" step (no actual navigation)
    is_dummy_step = (step.get('from_node') == 'Script Start' and step.get('to_node') == 'Script End')
    
    # Step end screenshot
    if step.get('step_end_screenshot_path'):
        # Use enhanced formatting for navigation step screenshots
        end_screenshot_path = step.get('step_end_screenshot_path')
        end_formatted_display = format_screenshot_display_name(end_screenshot_path)
        screenshots_for_step.append((f'{end_formatted_display}_step_end', end_screenshot_path, None, None))
        print(f"[@report_step_formatter:format_step_screenshots] ✅ Step {step_num} end screenshot included")
    elif not is_dummy_step:
        # Only warn about missing screenshots for real navigation steps
        expected_filename = f"step_{step_num}_{step.get('from_node', 'unknown')}_{step.get('to_node', 'unknown')}_end"
        print(f"[@report_step_formatter:format_step_screenshots] ⚠️ Step {step_num} end screenshot NOT found - expected: {expected_filename}")
    
    print(f"[@report_step_formatter:format_step_screenshots] Step {step_num} total screenshots for modal: {len(screenshots_for_step)}")
    for i, (label, path, cmd, params) in enumerate(screenshots_for_step):
        print(f"  [{i+1}] {label}: {path}")
    
    if not screenshots_for_step:
        if not is_dummy_step:
            # Only warn for real steps - dummy steps are expected to have no screenshots
            print(f"[@report_step_formatter:format_step_screenshots] ⚠️ Step {step_num} has no screenshots - this may be a failed action")
        return ""
    
    step_id = step.get('step_number', step_index+1)
    from_node = step.get('from_node', 'Unknown')
    to_node = step.get('to_node', 'Unknown')
    step_title = f"Step {step_id}: {from_node} → {to_node}"
    
    # Show the FIRST screenshot as thumbnail (prioritize step start, then main action)
    first_screenshot = screenshots_for_step[0]
    first_screenshot_path = first_screenshot[1]
    screenshot_count = len(screenshots_for_step)
    
    # For failed steps, emphasize that screenshots are available for debugging
    step_success = step.get('success', False)
    if not step_success and screenshot_count > 0:
        print(f"[@report_step_formatter:format_step_screenshots] 🔍 Failed step {step_num} has {screenshot_count} screenshot(s) for debugging")
    
    from .report_formatting import get_thumbnail_screenshot_html
    thumbnail_html = get_thumbnail_screenshot_html(
        first_screenshot_path, 
        f"{screenshot_count} screenshot{'s' if screenshot_count > 1 else ''}", 
        step_title, 
        screenshots_for_step, 
        0
    )
    
    return f"""
    <div class="step-screenshot-container">
        <div class="screenshot-row">
            {thumbnail_html}
        </div>
    </div>
    """


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