#!/usr/bin/env python3
"""
Verification Failure Report Generator

Generates minimal HTML debug reports for failed verifications.
Shows side-by-side images (source, cropped, reference) and processing details.

Pattern: Same as KPI report generator (minimal, HTTP-served, clickable from logs)
"""
import os
import json
import time
import shutil
from typing import Dict, Optional
from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder


def generate_verification_failure_report(
    verification_config: Dict,
    verification_result: Dict,
    device_folder: str
) -> Optional[str]:
    """
    Generate HTML report for verification failure with images and processing details.
    
    Args:
        verification_config: Verification config (command, params, type, source_image_path)
        verification_result: Verification result (success, threshold, matching_score, etc.)
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Local path to report HTML file, or None if generation failed.
        Frontend will convert local path to HTTP URL using buildHostImageUrl().
        
    Example:
        report_path = generate_verification_failure_report(config, result, 'capture1')
        if report_path:
            logger.error(f"🔍 DEBUG REPORT (local): {report_path}")
    """
    try:
        # Get verification failures directory (COLD storage)
        failures_base = get_cold_storage_path(device_folder, 'verification_failures')
        
        # Create timestamped report directory
        timestamp = str(int(time.time() * 1000))
        report_dir = os.path.join(failures_base, timestamp)
        os.makedirs(report_dir, exist_ok=True)
        
        # Copy images to report directory
        details = verification_result.get('details', {})
        
        # Source image (original screenshot)
        source_image_path = verification_config.get('source_image_path') or details.get('source_image_path')
        if source_image_path and os.path.exists(source_image_path):
            shutil.copy2(source_image_path, os.path.join(report_dir, 'source_image.jpg'))
        
        # Reference image (expected image)
        reference_image_path = details.get('reference_image_path')
        if reference_image_path and os.path.exists(reference_image_path):
            shutil.copy2(reference_image_path, os.path.join(report_dir, 'reference_image.jpg'))
        
        # Result overlay (if available - shows match regions)
        result_overlay_path = details.get('result_overlay_path')
        if result_overlay_path and os.path.exists(result_overlay_path):
            shutil.copy2(result_overlay_path, os.path.join(report_dir, 'result_overlay.jpg'))
        
        # Save processing details as JSON
        processing_info = {
            'command': verification_config.get('command'),
            'verification_type': verification_config.get('verification_type'),
            'params': verification_config.get('params', {}),
            'threshold': verification_result.get('threshold'),
            'matching_score': verification_result.get('matching_result'),
            'success': verification_result.get('success'),
            'message': verification_result.get('message'),
            'error': verification_result.get('error'),
            'extracted_text': verification_result.get('extractedText'),
            'searched_text': verification_result.get('searchedText'),
            'image_filter': verification_result.get('imageFilter'),
            'detected_language': verification_result.get('detected_language'),
            'language_confidence': verification_result.get('language_confidence'),
            'timestamp': timestamp
        }
        
        with open(os.path.join(report_dir, 'details.json'), 'w') as f:
            json.dump(processing_info, f, indent=2)
        
        # Generate minimal HTML report
        html_content = _generate_html_report(processing_info, verification_config, verification_result)
        
        html_path = os.path.join(report_dir, 'index.html')
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        # Return local path only - frontend will convert to HTTP URL
        return html_path
        
    except Exception as e:
        print(f"❌ Failed to generate verification failure report: {e}")
        import traceback
        traceback.print_exc()
        return None


def _generate_html_report(
    processing_info: Dict,
    verification_config: Dict,
    verification_result: Dict
) -> str:
    """Generate minimal HTML report with side-by-side images"""
    
    verification_type = verification_config.get('verification_type', 'unknown')
    command = verification_config.get('command', 'unknown')
    success = verification_result.get('success', False)
    
    # Build image row
    images_html = '<tr>'
    
    # Source image
    if os.path.exists('source_image.jpg'):
        images_html += '<td><img src="source_image.jpg" style="max-width:400px"/><br/><b>Source Screenshot</b></td>'
    
    # Reference image
    if os.path.exists('reference_image.jpg'):
        images_html += '<td><img src="reference_image.jpg" style="max-width:400px"/><br/><b>Reference Image</b></td>'
    
    # Result overlay (if available)
    if os.path.exists('result_overlay.jpg'):
        images_html += '<td><img src="result_overlay.jpg" style="max-width:400px"/><br/><b>Result Overlay</b></td>'
    
    images_html += '</tr>'
    
    # Build processing details based on type
    details_html = '<h3>Processing Details</h3><ul>'
    
    if verification_type == 'image':
        threshold = processing_info.get('threshold')
        matching_score = processing_info.get('matching_score')
        match_symbol = '✅' if success else '❌'
        
        # Handle None values gracefully
        if threshold is not None:
            details_html += f'<li><b>Threshold:</b> {threshold:.2f} (required)</li>'
        else:
            details_html += f'<li><b>Threshold:</b> N/A (required)</li>'
        
        if matching_score is not None:
            details_html += f'<li><b>Match Score:</b> {matching_score:.2f} (found) {match_symbol}</li>'
        else:
            details_html += f'<li><b>Match Score:</b> N/A (found) {match_symbol}</li>'
        
        details_html += f'<li><b>Image Filter:</b> {processing_info.get("image_filter", "none")}</li>'
        
        params = verification_config.get('params', {})
        if params.get('area'):
            details_html += f'<li><b>Search Area:</b> {params["area"]}</li>'
    
    elif verification_type == 'text':
        extracted_text = processing_info.get('extracted_text', '')
        searched_text = processing_info.get('searched_text', '')
        
        details_html += f'<li><b>Searched Text:</b> "{searched_text}"</li>'
        details_html += f'<li><b>Extracted Text:</b> "{extracted_text}"</li>'
        details_html += f'<li><b>Detected Language:</b> {processing_info.get("detected_language", "unknown")}</li>'
        
        # Handle None confidence
        lang_confidence = processing_info.get("language_confidence")
        if lang_confidence is not None:
            details_html += f'<li><b>Language Confidence:</b> {lang_confidence:.2f}</li>'
        else:
            details_html += f'<li><b>Language Confidence:</b> N/A</li>'
    
    details_html += f'<li><b>Result:</b> {"PASS ✅" if success else "FAIL ❌"}</li>'
    
    if processing_info.get('error'):
        details_html += f'<li><b>Error:</b> {processing_info["error"]}</li>'
    
    if processing_info.get('message'):
        details_html += f'<li><b>Message:</b> {processing_info["message"]}</li>'
    
    details_html += '</ul>'
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Verification Failure Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 1400px; margin: 0 auto; }}
        h2 {{ color: #d32f2f; }}
        table {{ width: 100%; margin: 20px 0; }}
        td {{ text-align: center; vertical-align: top; padding: 10px; }}
        img {{ border: 2px solid #ddd; border-radius: 4px; }}
        ul {{ text-align: left; }}
        li {{ margin: 8px 0; }}
        .status-fail {{ color: #d32f2f; font-weight: bold; }}
        .status-pass {{ color: #388e3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>❌ Verification Failure: {command}</h2>
        <p><b>Type:</b> {verification_type}</p>
        <p><b>Timestamp:</b> {processing_info.get("timestamp")}</p>
        
        <h3>Images</h3>
        <table>
            {images_html}
        </table>
        
        {details_html}
        
        <hr/>
        <p style="color: #666; font-size: 12px;">
            Generated by verification_report_generator.py<br/>
            Report directory: verification_failures/{processing_info.get("timestamp")}
        </p>
    </div>
</body>
</html>'''
    
    return html

