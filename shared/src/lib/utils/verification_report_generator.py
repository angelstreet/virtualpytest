#!/usr/bin/env python3
"""
Verification Failure Report Generator

Generates minimal HTML debug reports for failed verifications.
Pattern: Same as KPI failure report (simple HTML with file:// URLs)
"""
import os
import time
from typing import Dict, Optional


def generate_verification_failure_report(
    verification_config: Dict,
    verification_result: Dict,
    device_folder: str,
    host_info: Dict
) -> Optional[str]:
    """
    Generate HTML report for verification failure with images and processing details.
    
    Args:
        verification_config: Verification config (command, params, type, source_image_path)
        verification_result: Verification result (success, threshold, matching_score, etc.)
        device_folder: Device folder name (e.g., 'capture4')
        host_info: Host information dict for URL building (from get_host_info_for_report)
        
    Returns:
        Local path to report HTML file, or None if generation failed.
        Frontend will convert local path to HTTP URL using buildHostImageUrl().
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
        from shared.src.lib.utils.build_url_utils import buildHostImageUrl
        
        # Save report in COLD storage root (same level as captures/, thumbnails/) - SAME AS KPI
        cold_base = get_cold_storage_path(device_folder, '')  # Empty subfolder = base dir
        timestamp = str(int(time.time() * 1000))
        report_filename = f'verification_failure_{timestamp}.html'
        report_path = os.path.join(cold_base, report_filename)
        
        print(f"[@verification_report_generator] Generating failure report: {report_path}")
        
        # Get details
        details = verification_result.get('details', {})
        verification_type = verification_config.get('verification_type', 'unknown')
        command = verification_config.get('command', 'unknown')
        
        # Get image paths and convert to HTTP URLs
        source_image_path = verification_config.get('source_image_path') or details.get('source_image_path')
        source_image_url = buildHostImageUrl(host_info, source_image_path) if source_image_path else None
        
        # Reference image URL is already R2 URL - use as is
        reference_image_url = details.get('reference_image_url')
        print(f"[@verification_report_generator] Reference image URL from details: {reference_image_url}")
        
        # Overlay image - convert local path to HTTP URL
        result_overlay_path = details.get('result_overlay_path')
        result_overlay_url = buildHostImageUrl(host_info, result_overlay_path) if result_overlay_path else None
        
        # Build simple HTML (same pattern as KPI failure report)
        html = ['<!DOCTYPE html><html><head><meta charset="UTF-8">']
        html.append('<style>body{font-family:monospace;padding:20px;background:#f5f5f5;max-width:1200px;margin:0 auto}')
        html.append('img{max-width:400px;border:2px solid #ddd;margin:10px;display:block;cursor:pointer}')
        html.append('img:hover{border-color:#2196F3}')
        html.append('h2{color:#d32f2f;margin-top:30px;border-bottom:2px solid #d32f2f;padding-bottom:5px}')
        html.append('.meta{background:white;padding:15px;margin:10px 0;border-radius:4px}')
        html.append('.details{background:white;padding:15px;margin:10px 0;border-radius:4px}')
        html.append('pre{background:#f5f5f5;padding:10px;border-radius:4px;overflow-x:auto}')
        html.append('</style></head><body>')
        
        html.append(f'<h1>Verification Failure Report</h1>')
        html.append(f'<div class="meta">')
        html.append(f'<p><b>Command:</b> {command}</p>')
        html.append(f'<p><b>Type:</b> {verification_type}</p>')
        html.append(f'<p><b>Timestamp:</b> {timestamp}</p>')
        html.append(f'<p><b>Message:</b> {verification_result.get("message", "N/A")}</p>')
        html.append(f'</div>')
        
        # Images section
        html.append('<h2>Images</h2>')
        if source_image_url:
            html.append(f'<div><p><b>Source Screenshot</b></p>')
            html.append(f'<a href="{source_image_url}" target="_blank"><img src="{source_image_url}" alt="Source"></a></div>')
        
        if reference_image_url:
            html.append(f'<div><p><b>Reference Image</b></p>')
            html.append(f'<a href="{reference_image_url}" target="_blank"><img src="{reference_image_url}" alt="Reference"></a></div>')
        
        if result_overlay_url:
            html.append(f'<div><p><b>Result Overlay</b></p>')
            html.append(f'<a href="{result_overlay_url}" target="_blank"><img src="{result_overlay_url}" alt="Overlay"></a></div>')
        
        # Processing details
        html.append('<h2>Processing Details</h2>')
        html.append('<div class="details">')
        
        if verification_type == 'image':
            threshold = verification_result.get('threshold')
            matching_score = verification_result.get('matching_result')
            
            if threshold is not None:
                html.append(f'<p><b>Threshold:</b> {threshold:.2f} (required)</p>')
            if matching_score is not None:
                html.append(f'<p><b>Match Score:</b> {matching_score:.2f} (found)</p>')
            
            html.append(f'<p><b>Image Filter:</b> {details.get("image_filter", "none")}</p>')
            
            params = verification_config.get('params', {})
            if params.get('area'):
                html.append(f'<p><b>Search Area:</b> {params["area"]}</p>')
        
        elif verification_type == 'text':
            html.append(f'<p><b>Searched Text:</b> "{verification_result.get("searchedText", "")}"</p>')
            html.append(f'<p><b>Extracted Text:</b> "{verification_result.get("extractedText", "")}"</p>')
            html.append(f'<p><b>Detected Language:</b> {verification_result.get("detected_language", "unknown")}</p>')
            
            lang_confidence = verification_result.get("language_confidence")
            if lang_confidence is not None:
                html.append(f'<p><b>Language Confidence:</b> {lang_confidence:.2f}</p>')
        
        html.append('</div>')
        html.append('</body></html>')
        
        # Write file
        with open(report_path, 'w') as f:
            f.write('\n'.join(html))
        
        # Build HTTP URL for the report (for logging)
        report_url = buildHostImageUrl(host_info, report_path)
        
        print(f"[@verification_report_generator] Failure report generated: {report_path}")
        print(f"[@verification_report_generator] Report URL: {report_url}")
        
        # Return local path only - frontend will convert to HTTP URL
        return report_path
        
    except Exception as e:
        print(f"[@verification_report_generator] Failed to generate verification failure report: {e}")
        import traceback
        traceback.print_exc()
        return None

