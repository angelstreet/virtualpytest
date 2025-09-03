"""
Zap Summary Formatter for HTML Reports

Formats zap execution data into HTML table for reports.
"""

from typing import List, Dict, Any, Optional
from shared.lib.supabase.zap_results_db import get_zap_summary_for_script


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
        zap_data = get_zap_summary_for_script(script_result_id)
        
        if not zap_data or len(zap_data) == 0:
            return ""  # No zap data, return empty section
        
        # Generate the HTML table
        table_html = create_zap_summary_table(zap_data)
        
        return f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection('zap-summary-content')">
                    <h2>🎯 Zap Execution Summary ({len(zap_data)} iterations)</h2>
                    <button class="toggle-btn">▶</button>
                </div>
                <div id="zap-summary-content" class="collapsible-content">
                    <div class="zap-summary-container">
                        {table_html}
                    </div>
                </div>
            </div>
        """
        
    except Exception as e:
        print(f"[@utils:zap_summary_formatter:create_zap_summary_section] Error: {str(e)}")
        return ""  # Return empty section on error


def create_zap_summary_table(zap_data: List[Dict[str, Any]]) -> str:
    """
    Create the HTML table for zap summary data.
    
    Args:
        zap_data: List of zap iteration data from database
        
    Returns:
        HTML string for the zap summary table
    """
    if not zap_data:
        return "<p>No zap data available.</p>"
    
    # Create table header
    table_html = """
    <div class="zap-summary-table">
        <table class="zap-table">
            <thead>
                <tr>
                    <th>Iter</th>
                    <th>Action</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Duration</th>
                    <th>Motion</th>
                    <th>Subtitles</th>
                    <th>Audio</th>
                    <th>B/F</th>
                    <th>Channel Info</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add data rows
    for zap in zap_data:
        table_html += create_zap_table_row(zap)
    
    # Close table and add statistics
    table_html += """
            </tbody>
        </table>
    </div>
    """
    
    # Add summary statistics
    stats_html = create_zap_statistics(zap_data)
    table_html += stats_html
    
    return table_html


def create_zap_table_row(zap: Dict[str, Any]) -> str:
    """
    Create a single table row for zap data.
    
    Args:
        zap: Single zap iteration data
        
    Returns:
        HTML string for the table row
    """
    # Format detection results with icons
    motion_icon = "✅" if zap.get('motion_detected') else "❌"
    
    # Subtitle with language
    subtitle_result = ""
    if zap.get('subtitles_detected'):
        lang = zap.get('subtitle_language', '').upper()
        subtitle_result = f"✅ {lang}" if lang else "✅"
    else:
        subtitle_result = "❌"
    
    # Audio with language  
    audio_result = ""
    if zap.get('audio_speech_detected'):
        lang = zap.get('audio_language', '').upper()
        audio_result = f"✅ {lang}" if lang else "✅"
    else:
        audio_result = "❌"
    
    # Blackscreen/Freeze with duration
    bf_result = ""
    if zap.get('blackscreen_freeze_detected'):
        duration = zap.get('blackscreen_freeze_duration_seconds', 0)
        if duration and duration > 0:
            bf_result = f"⬛ {duration:.1f}s"
        else:
            bf_result = "⬛"
    else:
        bf_result = "❌"
    
    # Channel info
    channel_info = format_channel_info(zap)
    
    return f"""
                <tr>
                    <td>{zap.get('iteration_index', 'N/A')}</td>
                    <td>{zap.get('action_command', 'N/A')}</td>
                    <td>{zap.get('start_time', 'N/A')}</td>
                    <td>{zap.get('end_time', 'N/A')}</td>
                    <td>{zap.get('duration_seconds', 0):.1f}s</td>
                    <td>{motion_icon}</td>
                    <td>{subtitle_result}</td>
                    <td>{audio_result}</td>
                    <td>{bf_result}</td>
                    <td>{channel_info}</td>
                </tr>
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


def create_zap_statistics(zap_data: List[Dict[str, Any]]) -> str:
    """
    Create summary statistics for zap data.
    
    Args:
        zap_data: List of zap iteration data
        
    Returns:
        HTML string for statistics section
    """
    if not zap_data:
        return ""
    
    total_zaps = len(zap_data)
    motion_count = sum(1 for zap in zap_data if zap.get('motion_detected'))
    subtitle_count = sum(1 for zap in zap_data if zap.get('subtitles_detected'))
    audio_count = sum(1 for zap in zap_data if zap.get('audio_speech_detected'))
    bf_count = sum(1 for zap in zap_data if zap.get('blackscreen_freeze_detected'))
    
    # Calculate percentages
    motion_pct = (motion_count / total_zaps * 100) if total_zaps > 0 else 0
    subtitle_pct = (subtitle_count / total_zaps * 100) if total_zaps > 0 else 0
    audio_pct = (audio_count / total_zaps * 100) if total_zaps > 0 else 0
    bf_pct = (bf_count / total_zaps * 100) if total_zaps > 0 else 0
    
    return f"""
    <div class="zap-statistics">
        <h4>Summary Statistics</h4>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-label">Total Zaps:</span>
                <span class="stat-value">{total_zaps}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Motion Detection:</span>
                <span class="stat-value">{motion_pct:.0f}% ({motion_count}/{total_zaps})</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Subtitle Detection:</span>
                <span class="stat-value">{subtitle_pct:.0f}% ({subtitle_count}/{total_zaps})</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Audio Detection:</span>
                <span class="stat-value">{audio_pct:.0f}% ({audio_count}/{total_zaps})</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Blackscreen/Freeze:</span>
                <span class="stat-value">{bf_pct:.0f}% ({bf_count}/{total_zaps})</span>
            </div>
        </div>
    </div>
    """
