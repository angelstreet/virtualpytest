"""
Zap Summary Formatter for HTML Reports

Formats zap execution data into HTML table for reports.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.lib.supabase.zap_results_db import get_zap_summary_for_script


def format_time_from_timestamp(timestamp_str: str) -> str:
    """
    Format timestamp string to HH:MM:SS format.
    
    Args:
        timestamp_str: ISO timestamp string
        
    Returns:
        Time in HH:MM:SS format or 'N/A' if invalid
    """
    if not timestamp_str:
        return 'N/A'
    
    try:
        # Parse ISO timestamp and format as time only
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except (ValueError, AttributeError):
        return 'N/A'


def create_zap_summary_section_from_data(custom_data: Dict[str, Any]) -> str:
    """
    Create the zap summary section HTML for the report using existing data from memory.
    
    Args:
        custom_data: Dictionary containing zap statistics from context.custom_data
        
    Returns:
        HTML string for the zap summary section, or empty string if no data
    """
    try:
        # Check if we have zap data in custom_data
        if not custom_data or 'motion_results' not in custom_data:
            print(f"🔍 [ZapSummaryFormatter] DEBUG: No zap data found in custom_data")
            return ""  # No zap data, return empty section
        
        # Convert custom_data to the same format as database results
        motion_results = custom_data.get('motion_results', [])
        if not motion_results:
            print(f"🔍 [ZapSummaryFormatter] DEBUG: No motion_results found in custom_data")
            return ""
        
        # Convert motion_results to database-like format for compatibility
        zap_data = []
        for i, result in enumerate(motion_results, 1):
            # Extract data from the motion result
            zap_iteration = {
                'iteration_index': i,
                'action_command': custom_data.get('action_command', 'unknown'),
                'motion_detected': result.get('motion_detected', False),
                'subtitles_detected': result.get('subtitles_detected', False),
                'audio_speech_detected': result.get('audio_speech_detected', False),
                'blackscreen_freeze_detected': result.get('zapping_detected', False),
                'subtitle_language': result.get('detected_language'),
                'audio_language': result.get('audio_language'),
                'blackscreen_freeze_duration_seconds': result.get('zapping_analysis', {}).get('blackscreen_duration', 0.0) if result.get('zapping_detected') else None,
                'detection_method': result.get('zapping_analysis', {}).get('detection_method', 'blackscreen') if result.get('zapping_detected') else None,
                'channel_name': result.get('zapping_analysis', {}).get('channel_info', {}).get('channel_name') if result.get('zapping_detected') else None,
                'channel_number': result.get('zapping_analysis', {}).get('channel_info', {}).get('channel_number') if result.get('zapping_detected') else None,
                'program_name': result.get('zapping_analysis', {}).get('channel_info', {}).get('program_name') if result.get('zapping_detected') else None,
                'program_start_time': result.get('zapping_analysis', {}).get('channel_info', {}).get('start_time') if result.get('zapping_detected') else None,
                'program_end_time': result.get('zapping_analysis', {}).get('channel_info', {}).get('end_time') if result.get('zapping_detected') else None,
                'duration_seconds': 5.0,  # Approximate duration per iteration
                'started_at': '2025-01-01T00:00:00Z',  # Placeholder
                'completed_at': '2025-01-01T00:00:05Z',  # Placeholder
                'execution_date': '2025-01-01T00:00:00Z',  # Placeholder
                'host_name': 'unknown',
                'device_name': 'unknown',
                'device_model': 'unknown'
            }
            zap_data.append(zap_iteration)
        
        print(f"🔍 [ZapSummaryFormatter] DEBUG: Using existing data from memory:")
        print(f"  - motion_results count: {len(motion_results)}")
        print(f"  - converted zap_data count: {len(zap_data)}")
        
        if zap_data:
            for i, iteration in enumerate(zap_data):
                print(f"  - Iteration {iteration.get('iteration_index', i+1)}: blackscreen_freeze_detected = {iteration.get('blackscreen_freeze_detected')}")
        
        # Generate the text-based summary (like logs)
        text_html = create_zap_summary_text(zap_data)
        
        return f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection('zap-summary-content')">
                    <h2>🎯 Zap Execution Summary ({len(zap_data)} iterations)</h2>
                    <button class="toggle-btn">▶</button>
                </div>
                <div id="zap-summary-content" class="collapsible-content">
                    <div class="zap-summary-container">
                        {text_html}
                    </div>
                </div>
            </div>
        """
        
    except Exception as e:
        print(f"[@utils:zap_summary_formatter:create_zap_summary_section_from_data] Error: {str(e)}")
        return ""  # Return empty section on error


def create_zap_summary_section(script_result_id: str) -> str:
    """
    Create the zap summary section HTML for the report.
    
    Args:
        script_result_id: The script result ID to get zap data for
        
    Returns:
        HTML string for the zap summary section, or empty string if no data
    """
    try:
        # Get zap data from database
        zap_response = get_zap_summary_for_script(script_result_id)
        
        # Check if we got a valid response
        if not zap_response or not zap_response.get('success'):
            return ""  # No zap data or error, return empty section
        
        # Extract the actual zap iterations list
        zap_data = zap_response.get('zap_iterations', [])
        
        if not zap_data or len(zap_data) == 0:
            return ""  # No zap iterations, return empty section
        
        # Generate the text-based summary (like logs)
        text_html = create_zap_summary_text(zap_data)
        
        return f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection('zap-summary-content')">
                    <h2>🎯 Zap Execution Summary ({len(zap_data)} iterations)</h2>
                    <button class="toggle-btn">▶</button>
                </div>
                <div id="zap-summary-content" class="collapsible-content">
                    <div class="zap-summary-container">
                        {text_html}
                    </div>
                </div>
            </div>
        """
        
    except Exception as e:
        print(f"[@utils:zap_summary_formatter:create_zap_summary_section] Error: {str(e)}")
        return ""  # Return empty section on error


def generate_zap_summary_text(zap_data: List[Dict[str, Any]]) -> str:
    """
    Generate the exact same zap summary text that appears in logs.
    This is the shared function used by both logs and reports.
    
    Args:
        zap_data: List of zap iteration data from database
        
    Returns:
        Plain text string matching log format exactly
    """
    if not zap_data:
        return "No zap data available."
    
    lines = []
    
    # Header with separators
    lines.append("=" * 120)
    lines.append("🎯 ZAP EXECUTION SUMMARY")
    lines.append("=" * 120)
    
    # Header info
    first_iteration = zap_data[0]
    formatted_date = first_iteration['execution_date'][:19] if first_iteration.get('execution_date') else 'Unknown'
    lines.append(f"Host: {first_iteration['host_name']} | Device: {first_iteration['device_name']} ({first_iteration['device_model']}) | Date: {formatted_date}")
    lines.append("")
    
    # Table header
    lines.append(f"{'Iter':<4} | {'Action':<12} | {'Start':<8} | {'End':<8} | {'Duration':<8} | {'Motion':<6} | {'Subtitles':<10} | {'Audio':<8} | {'B/F':<6} | {'Channel Info':<40}")
    lines.append("-" * 120)
    
    # Table rows
    motion_count = subtitle_count = audio_count = bf_count = 0
    for iteration in zap_data:
        # Format detection results (exact same logic as zap_controller)
        motion_icon = "✅" if iteration['motion_detected'] else "❌"
        subtitle_result = "✅" if iteration['subtitles_detected'] else "❌"
        if iteration['subtitles_detected'] and iteration['subtitle_language']:
            subtitle_result += f" {iteration['subtitle_language'][:2].upper()}"
        
        audio_result = "✅" if iteration['audio_speech_detected'] else "❌"
        if iteration['audio_speech_detected'] and iteration['audio_language']:
            audio_result += f" {iteration['audio_language'][:2].upper()}"
        
        bf_result = "❌"
        if iteration['blackscreen_freeze_detected']:
            duration = iteration['blackscreen_freeze_duration_seconds'] or 0
            method = iteration['detection_method'] or 'B'
            method_icon = "⬛" if method == 'blackscreen' else "🧊"
            bf_result = f"{method_icon} {duration:.1f}s"
        
        # Format channel info (exact same logic as zap_controller)
        channel_info = ""
        if iteration['channel_name']:
            channel_info = iteration['channel_name']
            if iteration['channel_number']:
                channel_info += f" ({iteration['channel_number']})"
            if iteration['program_name']:
                channel_info += f" - {iteration['program_name']}"
            if iteration['program_start_time'] and iteration['program_end_time']:
                channel_info += f" [{iteration['program_start_time']}-{iteration['program_end_time']}]"
        
        # Truncate channel info if too long
        if len(channel_info) > 40:
            channel_info = channel_info[:37] + "..."
        
        # Format timestamps to HH:MM:SS
        start_time_str = format_time_from_timestamp(iteration.get('started_at', ''))
        end_time_str = format_time_from_timestamp(iteration.get('completed_at', ''))
        
        lines.append(f"{iteration['iteration_index']:<4} | {iteration['action_command']:<12} | {start_time_str:<8} | {end_time_str:<8} | {iteration['duration_seconds']:<8.1f}s | {motion_icon:<6} | {subtitle_result:<10} | {audio_result:<8} | {bf_result:<6} | {channel_info:<40}")
        
        # Count successes
        if iteration['motion_detected']:
            motion_count += 1
        if iteration['subtitles_detected']:
            subtitle_count += 1
        if iteration['audio_speech_detected']:
            audio_count += 1
        if iteration['blackscreen_freeze_detected']:
            bf_count += 1
    
    # Summary totals
    total_iterations = len(zap_data)
    lines.append("-" * 120)
    lines.append(f"TOTALS: {total_iterations}/{total_iterations} successful | Motion: {motion_count}/{total_iterations} ({motion_count/total_iterations*100:.0f}%) | Subtitles: {subtitle_count}/{total_iterations} ({subtitle_count/total_iterations*100:.0f}%) | Audio: {audio_count}/{total_iterations} ({audio_count/total_iterations*100:.0f}%) | Blackscreen/Freeze: {bf_count}/{total_iterations} ({bf_count/total_iterations*100:.0f}%)")
    
    # Calculate mean durations
    mean_zap_duration = sum(iteration['duration_seconds'] for iteration in zap_data) / total_iterations
    bf_durations = [iteration['blackscreen_freeze_duration_seconds'] for iteration in zap_data if iteration['blackscreen_freeze_detected'] and iteration['blackscreen_freeze_duration_seconds']]
    mean_bf_duration = sum(bf_durations) / len(bf_durations) if bf_durations else 0
    
    lines.append(f"MEANS: Zap Duration: {mean_zap_duration:.1f}s | Blackscreen/Freeze Duration: {mean_bf_duration:.1f}s")
    lines.append("=" * 120)
    
    return "\n".join(lines)


def create_zap_summary_text(zap_data: List[Dict[str, Any]]) -> str:
    """
    Create HTML wrapper for zap summary text for reports.
    
    Args:
        zap_data: List of zap iteration data from database
        
    Returns:
        HTML string with preformatted text matching log style
    """
    if not zap_data:
        return "<p>No zap data available.</p>"
    
    # Get the exact same text as logs
    text_content = generate_zap_summary_text(zap_data)
    
    return f"""
    <div class="zap-summary-text" style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 10px 0;">
        <pre style="font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.4; margin: 0; white-space: pre; overflow-x: auto;">{text_content}</pre>
    </div>
    """





def format_channel_info(zap: Dict[str, Any]) -> str:
    """
    Format channel information for display.
    
    Args:
        zap: Single zap iteration data
        
    Returns:
        Formatted channel info string
    """
    channel_name = zap.get('channel_name', '')
    channel_number = zap.get('channel_number', '')
    program_name = zap.get('program_name', '')
    program_start = zap.get('program_start_time', '')
    program_end = zap.get('program_end_time', '')
    
    # Build channel info string
    parts = []
    
    if channel_name:
        if channel_number:
            parts.append(f"{channel_name} ({channel_number})")
        else:
            parts.append(channel_name)
    
    if program_name:
        parts.append(program_name)
    
    if program_start and program_end:
        parts.append(f"[{program_start}-{program_end}]")
    
    return " - ".join(parts) if parts else "N/A"