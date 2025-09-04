"""
Report Formatting Utilities

This module handles HTML formatting, thumbnails, and utility functions for reports.
Contains functions for creating HTML sections, formatting data, and handling images.
"""

import json
from typing import Dict, List, Optional, Any
from .report_step_formatter import create_compact_step_results_section


def get_video_thumbnail_html(video_url: str, label: str = "Video") -> str:
    """Generate HTML for video thumbnail that opens video URL in modal (supports MP4 and HLS)"""
    if not video_url or video_url is None:
        return '<div class="video-placeholder" style="text-align: center; color: #888; font-style: italic; padding: 20px;">No video available</div>'
    
    # Escape quotes in the URL and label for JavaScript
    escaped_url = video_url.replace("'", "\\'").replace('"', '\\"')
    escaped_label = label.replace("'", "\\'").replace('"', '\\"')
    
    # Determine video type for appropriate source tag
    video_type = "video/mp4" if video_url.endswith('.mp4') else "application/x-mpegURL"
    video_format = "MP4" if video_url.endswith('.mp4') else "HLS"
    
    return f"""
    <div class="video-thumbnail" onclick="console.log('Video thumbnail clicked: {video_format}'); openVideoModal('{escaped_url}', '{escaped_label}')" style="cursor: pointer; position: relative; width: 100%; max-width: 200px;" title="Click to play {video_format} video">
        <video muted preload="metadata" style="width: 100%; height: auto; object-fit: contain; max-height: 150px;">
            <source src="{video_url}" type="{video_type}">
        </video>
        <div class="play-overlay" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 24px;">▶</div>
    </div>
    """


def format_console_summary_for_html(console_text: str) -> str:
    """Convert console summary text to HTML format."""
    if not console_text:
        return """<div class="summary-stats">
    <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0;">📊 Execution summary not available<br>ℹ️  This may be from an older script run<br>🔄 Run the script again to see detailed summary</pre>
</div>"""
    
    # Simple conversion - preserve line breaks and basic formatting
    html_text = console_text.replace('\n', '<br>')
    html_text = html_text.replace('=', '')  # Remove separator lines
    # Remove extra spacing - don't add additional <br> before bullets
    
    return f"""<div class="summary-stats">
    <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; margin: 0;">{html_text}</pre>
</div>"""


def create_error_section(error_msg: str) -> str:
    """Create HTML for error section."""
    return f"""<div class="section">
    <div class="error-section">
        <h3>Error Details</h3>
        <div class="error-message">{error_msg}</div>
    </div>
</div>"""


def get_thumbnail_screenshot_html(screenshot_path: Optional[str], label: str = None, step_title: str = None, all_screenshots: list = None, current_index: int = 0) -> str:
    """Get HTML for displaying a thumbnail screenshot that opens modal with navigation."""
    if not screenshot_path:
        return ''
    
    # Prepare screenshots for modal
    modal_screenshots = []
    if all_screenshots:
        for screenshot_data in all_screenshots:
            screenshot_label = screenshot_data[0]
            screenshot_working_path = screenshot_data[1]
            action_cmd = screenshot_data[2] if len(screenshot_data) > 2 else None
            action_params = screenshot_data[3] if len(screenshot_data) > 3 else None
            
            modal_screenshots.append({
                'label': screenshot_label,
                'url': screenshot_working_path,
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
    modal_data_json = json.dumps(modal_data).replace('"', '&quot;').replace("'", "&#x27;")
    
    display_url = screenshot_path if screenshot_path.startswith('http') else screenshot_path
    
    return f"""
    <div class="screenshot-container">
        <span class="screenshot-label">{label or 'Screenshot'}</span>
        <img src="{display_url}" alt="Screenshot" class="screenshot-thumbnail" 
             style="width: 100%; height: auto; object-fit: contain; max-height: 150px;" 
             onclick="openScreenshotModal('{modal_data_json}')">
    </div>
    """


def update_step_results_with_r2_urls(step_results: List[Dict], url_mapping: Dict[str, str]) -> List[Dict]:
    """Update step results to replace local screenshot paths with R2 URLs."""
    if not url_mapping:
        return step_results
    
    updated_results = []
    for step in step_results:
        updated_step = step.copy()
        
        # Update various screenshot fields
        for field in ['action_screenshots', 'verification_images']:
            if field in updated_step and updated_step[field]:
                updated_list = []
                for path in updated_step[field]:
                    if path and path.startswith('http'):
                        updated_list.append(path)
                    else:
                        r2_url = url_mapping.get(path, path)
                        updated_list.append(r2_url)
                updated_step[field] = updated_list
        
        # Update single path fields
        for field in ['screenshot_path', 'screenshot_url', 'step_start_screenshot_path', 'step_end_screenshot_path']:
            if field in updated_step and updated_step[field]:
                original_path = updated_step[field]
                if not original_path.startswith('http'):
                    r2_url = url_mapping.get(original_path, original_path)
                    updated_step[field] = r2_url
        
        # Update verification results with R2 URLs (for individual verification images)
        if 'verification_results' in updated_step and updated_step['verification_results']:
            updated_verification_results = []
            for verification_result in updated_step['verification_results']:
                updated_verification = verification_result.copy()
                
                # Update verification_images field if it exists
                if 'verification_images' in updated_verification and updated_verification['verification_images']:
                    updated_verification_images = []
                    for img_path in updated_verification['verification_images']:
                        if img_path and img_path.startswith('http'):
                            updated_verification_images.append(img_path)
                        else:
                            r2_url = url_mapping.get(img_path, img_path)
                            updated_verification_images.append(r2_url)
                    updated_verification['verification_images'] = updated_verification_images
                
                updated_verification_results.append(updated_verification)
            updated_step['verification_results'] = updated_verification_results
        
        # Update analysis results with R2 URLs (for zap controller analysis)
        for analysis_field in ['subtitle_analysis', 'audio_analysis', 'audio_menu_analysis', 'motion_analysis', 'zapping_analysis']:
            if analysis_field in updated_step and updated_step[analysis_field]:
                analysis = updated_step[analysis_field]
                # Update analyzed_screenshot field if it exists
                if 'analyzed_screenshot' in analysis and analysis['analyzed_screenshot']:
                    original_path = analysis['analyzed_screenshot']
                    if not original_path.startswith('http'):
                        r2_url = url_mapping.get(original_path, original_path)
                        analysis['analyzed_screenshot'] = r2_url
                
                # Update other potential image fields in analysis results
                for img_field in ['screenshot_path', 'image_path', 'first_image', 'blackscreen_start_image', 
                                  'blackscreen_end_image', 'first_content_after_blackscreen']:
                    if img_field in analysis and analysis[img_field]:
                        original_path = analysis[img_field]
                        if not original_path.startswith('http'):
                            r2_url = url_mapping.get(original_path, original_path)
                            analysis[img_field] = r2_url
                
                # Update motion analysis images array (for motion detection thumbnails)
                if 'motion_analysis_images' in analysis and analysis['motion_analysis_images']:
                    updated_motion_images = []
                    for motion_img in analysis['motion_analysis_images']:
                        updated_img = motion_img.copy()
                        if 'path' in updated_img and updated_img['path']:
                            original_path = updated_img['path']
                            if not original_path.startswith('http'):
                                r2_url = url_mapping.get(original_path, original_path)
                                updated_img['path'] = r2_url
                        updated_motion_images.append(updated_img)
                    analysis['motion_analysis_images'] = updated_motion_images
        
        updated_results.append(updated_step)
    
    return updated_results


def create_verification_image_modal_data(source_image: str, reference_image: str, overlay_image: str) -> str:
    """Create JSON data for verification image comparison modal."""
    modal_data = {
        'title': 'Image Verification Comparison',
        'images': []
    }
    
    # Add all available images
    if source_image:
        modal_data['images'].append({
            'url': source_image,
            'label': 'Source Image (Current)'
        })
    
    if reference_image:
        modal_data['images'].append({
            'url': reference_image,
            'label': 'Reference Image (Expected)'
        })
    
    if overlay_image:
        modal_data['images'].append({
            'url': overlay_image,
            'label': 'Overlay (Differences)'
        })
    
    # Convert to JSON and escape quotes for embedding in HTML
    return json.dumps(modal_data).replace('"', '&quot;').replace("'", "&#x27;")


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