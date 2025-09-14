"""
Report Generation Core

This module handles the main report generation logic and orchestration.
Contains the primary functions for generating validation reports and managing screenshots.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from .report_formatting import (
    create_compact_step_results_section,
    format_console_summary_for_html,
    get_thumbnail_screenshot_html,
    get_video_thumbnail_html,
    create_error_section,
    update_step_results_with_r2_urls,
    create_error_report
)
from .report_template_html import create_themed_html_template


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
            file_mappings = [{'local_path': screenshot_path, 'remote_path': remote_path}]
            upload_result = uploader.upload_files(file_mappings)
            
            # Convert to single file result format
            if upload_result['uploaded_files']:
                upload_result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url']
                }
            else:
                upload_result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
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
        
        # Extract report data with safe defaults
        script_name = report_data.get('script_name', 'Unknown Script')
        # For AI testcases, prefer human-friendly title if provided
        # Expect optional fields: ai_testcase_name, ai_display_name
        ai_display_name = report_data.get('ai_testcase_name') or report_data.get('ai_display_name')
        if ai_display_name:
            script_name = f"AI : {ai_display_name}"
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
        
        # Safely handle video URL - ensure it's either a valid URL or empty string
        test_video_url = report_data.get('test_video_url', '')
        if test_video_url is None:
            test_video_url = ''
        
        # Generate zap summary section using existing data from memory (no database read needed)
        zap_summary_section = ""
        custom_data = report_data.get('custom_data', {})
        print(f"[@utils:report_generation] DEBUG: custom_data keys = {list(custom_data.keys())}")
        if custom_data and 'motion_results' in custom_data:
            try:
                from .zap_summary_formatter import create_zap_summary_section_from_data
                print(f"[@utils:report_generation] DEBUG: Using existing zap data from memory (no DB read)")
                zap_summary_section = create_zap_summary_section_from_data(custom_data)
                print(f"[@utils:report_generation] DEBUG: Zap summary section length: {len(zap_summary_section)} characters")
            except Exception as e:
                print(f"[@utils:report_generation] Failed to generate zap summary from memory: {str(e)}")
                import traceback
                traceback.print_exc()
                zap_summary_section = ""
        else:
            print(f"[@utils:report_generation] DEBUG: No zap data found in custom_data, skipping zap summary")
        
        # Replace placeholders with actual content
        html_content = html_template.format(
            script_name=script_name,
            execution_date=format_execution_date(start_time),
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
            test_video=get_video_thumbnail_html(test_video_url, 'Test Execution'),
            zap_summary_section=zap_summary_section
        )
        
        print(f"[@utils:report_utils:generate_validation_report] Report generated successfully")
        return html_content
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[@utils:report_utils:generate_validation_report] Error: {str(e)}")
        print(f"[@utils:report_utils:generate_validation_report] Full traceback: {error_details}")
        return create_error_report(f"Report generation failed: {str(e)}")


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
    test_video_url: str = "",
    script_result_id: str = None,
    custom_data: Dict = None
) -> Dict[str, str]:
    """
    Generate HTML report and upload to R2 storage - extracted from validation.py
    Can be used by any script execution (validation, simple scripts, etc.)
    
    Returns:
        Dict with 'report_url', 'report_path', and 'success' keys
    """
    try:
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Starting report generation...")
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Parameters - script_name: {script_name}")
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Parameters - device_info: {device_info}")
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Parameters - screenshot_paths length: {len(screenshot_paths) if screenshot_paths else 0}")
        
        from .cloudflare_utils import upload_script_report, upload_validation_screenshots, upload_script_logs
        from datetime import datetime
        
        execution_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Timestamp generated: {execution_timestamp}")
        
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
                uploaded_screenshots = screenshot_result.get('uploaded_screenshots', [])
                
                for i, upload_info in enumerate(uploaded_screenshots):
                    try:
                        local_path = upload_info['local_path']
                        r2_url = upload_info['url']
                        url_mapping[local_path] = r2_url
                    except Exception as mapping_error:
                        print(f"[@utils:report_utils:generate_and_upload_script_report] ERROR: Failed to process mapping {i+1}: {mapping_error}")
                        print(f"[@utils:report_utils:generate_and_upload_script_report] ERROR: upload_info: {upload_info}")
                        import traceback
                        print(f"[@utils:report_utils:generate_and_upload_script_report] ERROR: Traceback: {traceback.format_exc()}")
                        # Continue with next mapping instead of crashing
                        continue
                        
            else:
                print(f"[@utils:report_utils:generate_and_upload_script_report] Screenshot upload failed: {screenshot_result.get('error', 'Unknown error')}")
        else:
            print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: No screenshots to upload")
        
        # Update step_results to use R2 URLs instead of local paths
        updated_step_results = update_step_results_with_r2_urls(step_results, url_mapping)
        
        # Upload script logs to R2 if stdout is provided
        logs_url = ""
        logs_path = ""
        if stdout and stdout.strip():
            print(f"[@utils:report_utils:generate_and_upload_script_report] Uploading script logs...")
            logs_upload_result = upload_script_logs(
                log_content=stdout,
                device_model=device_info.get('device_model', 'unknown'),
                script_name=script_name.replace('.py', ''),
                timestamp=execution_timestamp
            )
            
            if logs_upload_result['success']:
                logs_url = logs_upload_result['url']
                logs_path = logs_upload_result['path']
                print(f"[@utils:report_utils:generate_and_upload_script_report] Logs uploaded: {logs_url}")
            else:
                print(f"[@utils:report_utils:generate_and_upload_script_report] Logs upload failed: {logs_upload_result.get('error', 'Unknown error')}")
        else:
            print(f"[@utils:report_utils:generate_and_upload_script_report] No stdout provided, skipping log upload")
        
        # Calculate proper start and end times based on actual script execution
        # execution_timestamp is when report is generated (end time)
        # start_time should be execution_timestamp - execution_time
        execution_time_seconds = execution_time / 1000.0  # Convert ms to seconds
        
        # Parse execution_timestamp to datetime object
        end_datetime = datetime.strptime(execution_timestamp, '%Y%m%d%H%M%S')
        
        # Calculate start time by subtracting execution duration
        from datetime import timedelta
        start_datetime = end_datetime - timedelta(seconds=execution_time_seconds)
        
        # Format back to timestamp strings
        calculated_start_time = start_datetime.strftime('%Y%m%d%H%M%S')
        calculated_end_time = execution_timestamp  # This is already the end time
        
        print(f"[@utils:report_utils:generate_and_upload_script_report] DEBUG: Calculated timing:")
        print(f"  - Execution duration: {execution_time_seconds:.1f}s ({execution_time}ms)")
        print(f"  - Start time: {calculated_start_time} ({start_datetime.strftime('%H:%M:%S')})")
        print(f"  - End time: {calculated_end_time} ({end_datetime.strftime('%H:%M:%S')})")

        # Prepare report data (same structure as validation.py) - now with R2 URLs and correct timestamps
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
            'start_time': calculated_start_time,  # Proper start time
            'end_time': calculated_end_time,      # Proper end time
            'userinterface_name': userinterface_name or f'script_{script_name}',
            'total_steps': len(updated_step_results),
            'passed_steps': sum(1 for step in updated_step_results if step.get('success', False)),
            'failed_steps': sum(1 for step in updated_step_results if not step.get('success', True)),
            'total_verifications': total_verifications,
            'passed_verifications': passed_verifications,
            'failed_verifications': failed_verifications,
            'execution_summary': execution_summary,
            'test_video_url': test_video_url,
            'script_result_id': script_result_id,
            'custom_data': custom_data or {}  # Pass zap data from memory
        }
        
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
                'report_path': report_path,
                'logs_url': logs_url,
                'logs_path': logs_path
            }
        else:
            print(f"[@utils:report_utils:generate_and_upload_script_report] Upload failed: {upload_result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'report_url': '',
                'report_path': '',
                'logs_url': '',
                'logs_path': ''
            }
        
    except Exception as e:
        print(f"[@utils:report_utils:generate_and_upload_script_report] Error: {str(e)}")
        return {
            'success': False,
            'report_url': '',
            'report_path': '',
            'logs_url': '',
            'logs_path': ''
        }


def generate_and_upload_restart_report(
    host_info: Dict,
    device_info: Dict,
    video_url: str,
    analysis_data: Dict,
    processing_time: float,
    timestamp: str = None,
    local_video_path: str = None
) -> Dict[str, str]:
    """
    Generate HTML report for restart video using dedicated restart video template.
    Creates a clean video player interface with AI analysis results.
    
    Args:
        host_info: Dict with host_name
        device_info: Dict with device_name, device_model, device_id
        video_url: URL to the generated restart video (local host URL)
        analysis_data: Dict containing audio, subtitle, and video analysis results
        processing_time: Processing time in seconds
        timestamp: Optional timestamp, will generate if not provided
        local_video_path: Optional local path to video file for R2 upload
        
    Returns:
        Dict with 'report_url', 'report_path', and 'success' keys
    """
    try:
        print(f"[@utils:report_utils:generate_and_upload_restart_report] Starting restart report generation...")
        
        from .cloudflare_utils import upload_restart_report, upload_restart_video
        from .restart_video_template import create_restart_video_template
        from datetime import datetime
        import json
        
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Upload video to R2 if local path provided
        r2_video_url = video_url  # Default to original URL
        if local_video_path:
            print(f"[@utils:report_utils:generate_and_upload_restart_report] Uploading video to R2...")
            video_upload_result = upload_restart_video(local_video_path, timestamp)
            if video_upload_result.get('success'):
                r2_video_url = video_upload_result['video_url']
                print(f"[@utils:report_utils:generate_and_upload_restart_report] Video uploaded to R2: {r2_video_url}")
            else:
                print(f"[@utils:report_utils:generate_and_upload_restart_report] Video upload failed: {video_upload_result.get('error')}")
                # Continue with original URL as fallback
        
        # Extract analysis results for template with defensive checks
        audio_analysis = analysis_data.get('audio_analysis') or {}
        subtitle_analysis = analysis_data.get('subtitle_analysis') or {}
        video_analysis = analysis_data.get('video_analysis') or {}
        
        # Ensure all analysis results are dicts, not None
        if not isinstance(audio_analysis, dict):
            audio_analysis = {}
        if not isinstance(subtitle_analysis, dict):
            subtitle_analysis = {}
        if not isinstance(video_analysis, dict):
            video_analysis = {}
        
        # Prepare template data with R2 video URL
        template_data = {
            'host_name': host_info.get('host_name', 'Unknown Host'),
            'device_name': device_info.get('device_name', 'Unknown Device'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'video_url': r2_video_url,  # Use R2 URL instead of local host URL
            'audio_transcript': audio_analysis.get('combined_transcript', 'No audio transcript available'),
            'subtitle_text': subtitle_analysis.get('extracted_text', 'No subtitles detected'),
            'video_summary': video_analysis.get('video_summary', 'Video analysis pending'),
            'analysis_data_json': json.dumps(analysis_data) if analysis_data else '{}'
        }
        
        # Generate HTML using dedicated restart video template
        html_template = create_restart_video_template()
        html_content = html_template.format(**template_data)
        
        # Upload report to R2 using timestamp-based structure
        upload_result = upload_restart_report(
            html_content=html_content,
            host_name=host_info.get('host_name', 'unknown'),
            device_id=device_info.get('device_id', 'unknown'),
            timestamp=timestamp
        )
        
        if upload_result['success']:
            report_url = upload_result['report_url']
            report_path = upload_result['report_path']
            print(f"[@cloudflare_utils:upload_restart_report] INFO: Uploaded restart report: {report_path}")
            print(f"[@utils:report_utils:generate_and_upload_restart_report] Report uploaded: {report_url}")
            return {
                'success': True,
                'report_url': report_url,
                'report_path': report_path
            }
        else:
            print(f"[@utils:report_utils:generate_and_upload_restart_report] Upload failed: {upload_result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'report_url': '',
                'report_path': ''
            }
        
    except Exception as e:
        print(f"[@utils:report_utils:generate_and_upload_restart_report] Error: {str(e)}")
        return {
            'success': False,
            'report_url': '',
            'report_path': ''
        }


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        # Convert YYYYMMDDHHMMSS to readable format
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        return dt.strftime('%H:%M:%S')
    except:
        return timestamp


def format_execution_date(timestamp: str) -> str:
    """Format execution date for display in DD/MM/YYYY format."""
    try:
        # Convert YYYYMMDDHHMMSS to readable date format
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        return dt.strftime('%d/%m/%Y')
    except:
        # Fallback to current date if timestamp parsing fails
        return datetime.now().strftime('%d/%m/%Y')


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