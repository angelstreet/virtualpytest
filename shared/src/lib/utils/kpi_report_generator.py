#!/usr/bin/env python3
"""
KPI Report Generator Utilities

Handles generation of both success and failure KPI reports.
Extracted from kpi_executor.py to reduce file size and improve maintainability.
"""

import os
import json
import time
import shutil
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def find_closest_thumbnail(thumb_dir: str, target_ts: float) -> Optional[str]:
    """Find thumbnail closest to target timestamp in directory"""
    if not os.path.isdir(thumb_dir):
        return None
    
    import glob
    thumbnails = glob.glob(os.path.join(thumb_dir, 'capture_*_thumbnail.jpg'))
    
    if not thumbnails:
        return None
    
    closest = None
    min_diff = float('inf')
    
    for thumb_path in thumbnails:
        try:
            mtime = os.path.getmtime(thumb_path)
            diff = abs(mtime - target_ts)
            if diff < min_diff:
                min_diff = diff
                closest = thumb_path
        except OSError:
            continue
    
    return closest


def generate_kpi_success_report(
    request,  # KPIMeasurementRequest object
    match_result: Dict,
    kpi_ms: int,
    working_dir: str,
    extra_before_filename: Optional[str]
) -> Optional[str]:
    """
    Generate KPI success report HTML with thumbnail evidence and upload to R2.
    
    Args:
        request: KPIMeasurementRequest object with all execution context
        match_result: Dict with match details (timestamp, capture_path, etc.)
        kpi_ms: KPI duration in milliseconds
        working_dir: Working directory containing copied images
        extra_before_filename: Filename of frame before scan window (if any)
        
    Returns:
        R2 URL to uploaded report, or None if failed
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_thumbnail_path_from_capture
        from shared.src.lib.utils.cloudflare_utils import upload_kpi_thumbnails, upload_kpi_report
        from shared.src.lib.utils.kpi_report_template import create_kpi_report_template
        
        logger.info(f"📊 Generating KPI success report for {request.execution_result_id[:8]}")
        
        # Find thumbnails from working directory
        logger.info(f"🔍 Searching for thumbnails in working directory: {working_dir}")
        
        if not os.path.isdir(working_dir):
            logger.warning(f"⚠️  Working directory not found: {working_dir}")
            return None
        
        # Get match capture using index-based selection
        match_index = match_result.get('capture_index')
        all_captures = match_result.get('all_captures', [])
        
        if match_index is None or not all_captures:
            logger.error(f"❌ No capture_index or all_captures in match_result")
            return None
        
        # Get match capture (the one that passed verification)
        match_capture = all_captures[match_index]
        match_capture_filename = os.path.basename(match_capture['path'])
        match_image = os.path.join(working_dir, match_capture_filename)
        
        # Use centralized function for thumbnail path
        match_thumb_filename = os.path.basename(get_thumbnail_path_from_capture(match_capture_filename))
        match_thumb = os.path.join(working_dir, match_thumb_filename)
        
        # Get before match capture (match - 1)
        before_index = match_index - 1
        if before_index < 0:
            # Match is first in scan window - use extra frame we copied before window
            if extra_before_filename:
                before_capture_filename = extra_before_filename
                before_thumb_filename = os.path.basename(get_thumbnail_path_from_capture(extra_before_filename))
                before_match_thumb = os.path.join(working_dir, before_thumb_filename)
                before_time_ts = os.path.getmtime(os.path.join(working_dir, extra_before_filename))
                logger.info(f"   • Before Match: {extra_before_filename} (extra frame before window) ✅")
            else:
                # No extra frame - use match as fallback
                logger.warning(f"⚠️  No extra frame found, using match as before")
                before_capture_filename = match_capture_filename
                before_thumb_filename = match_thumb_filename
                before_match_thumb = match_thumb
                before_time_ts = match_capture['timestamp']
        else:
            before_capture = all_captures[before_index]
            before_capture_filename = os.path.basename(before_capture['path'])
            before_thumb_filename = os.path.basename(get_thumbnail_path_from_capture(before_capture_filename))
            before_match_thumb = os.path.join(working_dir, before_thumb_filename)
            before_time_ts = before_capture['timestamp']
            logger.info(f"   • Before Match: {before_thumb_filename} (index {before_index})")
        
        # Get before action screenshot - taken BEFORE action pressed
        before_action_time_ts = None
        if request.before_action_screenshot_path and os.path.exists(request.before_action_screenshot_path):
            before_action_thumb_source = get_thumbnail_path_from_capture(request.before_action_screenshot_path)
            before_action_thumb = os.path.join(working_dir, os.path.basename(before_action_thumb_source))
            
            if os.path.exists(before_action_thumb_source):
                shutil.copy2(before_action_thumb_source, before_action_thumb)
                before_action_time_ts = os.path.getmtime(request.before_action_screenshot_path)
                logger.info(f"   • Before Action: {os.path.basename(before_action_thumb)} (thumbnail) ✅")
            else:
                before_action_thumb = None
                logger.warning(f"⚠️  Before action thumbnail not found: {before_action_thumb_source}")
        else:
            before_action_thumb = None
            logger.warning(f"⚠️  No before-action screenshot provided")
        
        # Get after action screenshot - taken AFTER action pressed
        after_action_time_ts = None
        if request.action_screenshot_path and os.path.exists(request.action_screenshot_path):
            after_action_thumb_source = get_thumbnail_path_from_capture(request.action_screenshot_path)
            after_action_thumb = os.path.join(working_dir, os.path.basename(after_action_thumb_source))
            
            if os.path.exists(after_action_thumb_source):
                shutil.copy2(after_action_thumb_source, after_action_thumb)
                after_action_time_ts = os.path.getmtime(request.action_screenshot_path)
                logger.info(f"   • After Action: {os.path.basename(after_action_thumb)} (thumbnail) ✅")
            else:
                after_action_thumb = None
                logger.warning(f"⚠️  After action thumbnail not found: {after_action_thumb_source}")
        else:
            # Fallback: Find closest thumbnail by timestamp
            after_action_thumb = find_closest_thumbnail(working_dir, request.action_timestamp)
            if after_action_thumb:
                after_action_time_ts = os.path.getmtime(after_action_thumb)
                logger.info(f"   • After Action: {os.path.basename(after_action_thumb)} (timestamp search - fallback)")
            else:
                after_action_thumb = None
                logger.warning(f"⚠️  No after-action screenshot provided")
        
        # Check if thumbnails exist (if not, will use placeholder later)
        if not os.path.exists(match_thumb):
            logger.warning(f"⚠️  Match thumbnail not found - will use placeholder")
            match_thumb = None
        
        if not os.path.exists(match_image):
            logger.warning(f"⚠️  Match original not found - will use placeholder")
            match_image = None
                
        if not os.path.exists(before_match_thumb):
            logger.warning(f"⚠️  Before match thumbnail not found - will use placeholder")
            before_match_thumb = None
        
        # Upload only images that exist
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        thumbnails = {}
        
        logger.info(f"📦 Preparing images for upload:")
        if before_action_thumb and os.path.exists(before_action_thumb):
            thumbnails['before_action'] = before_action_thumb
            logger.info(f"   ✓ before_action: {before_action_thumb}")
        else:
            logger.warning(f"   ✗ before_action: NOT FOUND")
            
        if after_action_thumb and os.path.exists(after_action_thumb):
            thumbnails['after_action'] = after_action_thumb
            logger.info(f"   ✓ after_action: {after_action_thumb}")
        else:
            logger.warning(f"   ✗ after_action: NOT FOUND")
            
        if before_match_thumb and os.path.exists(before_match_thumb):
            thumbnails['before_match'] = before_match_thumb
            logger.info(f"   ✓ before_match: {before_match_thumb}")
        else:
            logger.warning(f"   ✗ before_match: NOT FOUND at {before_match_thumb}")
            
        if match_thumb and os.path.exists(match_thumb):
            thumbnails['match'] = match_thumb
            logger.info(f"   ✓ match: {match_thumb}")
        else:
            logger.warning(f"   ✗ match: NOT FOUND at {match_thumb}")
            
        if match_image and os.path.exists(match_image):
            thumbnails['match_original'] = match_image
            logger.info(f"   ✓ match_original: {match_image}")
        else:
            logger.warning(f"   ✗ match_original: NOT FOUND at {match_image}")
        
        # Upload what we have
        if thumbnails:
            thumb_urls = upload_kpi_thumbnails(thumbnails, request.execution_result_id, timestamp)
            if not thumb_urls:
                thumb_urls = {}
        else:
            logger.warning(f"⚠️  No thumbnails to upload")
            thumb_urls = {}
        
        # Placeholder for missing images
        placeholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150'%3E%3Crect fill='%23ddd' width='200' height='150'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' fill='%23666'%3ENo Image%3C/text%3E%3C/svg%3E"
        thumb_urls.setdefault('before_action', placeholder)
        thumb_urls.setdefault('after_action', placeholder)
        thumb_urls.setdefault('before_match', placeholder)
        thumb_urls.setdefault('match', placeholder)
        thumb_urls.setdefault('match_original', placeholder)
        
        # Format timestamps for display
        before_action_time = datetime.fromtimestamp(before_action_time_ts).strftime('%H:%M:%S.%f')[:-3] if before_action_time_ts else 'N/A'
        after_action_time = datetime.fromtimestamp(after_action_time_ts).strftime('%H:%M:%S.%f')[:-3] if after_action_time_ts else 'N/A'
        before_time = datetime.fromtimestamp(before_time_ts).strftime('%H:%M:%S.%f')[:-3]
        match_time = datetime.fromtimestamp(match_result['timestamp']).strftime('%H:%M:%S.%f')[:-3]
        action_timestamp_full = datetime.fromtimestamp(request.action_timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        match_timestamp_full = datetime.fromtimestamp(match_result['timestamp']).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Calculate scan window
        scan_window = match_result['timestamp'] - request.action_timestamp
        
        # Upload verification evidence images and prepare data for template
        verification_cards_html = ""
        verification_count = 0
        
        if request.verification_evidence_list:
            from shared.src.lib.utils.cloudflare_utils import upload_kpi_thumbnails
            
            logger.info(f"📸 Processing {len(request.verification_evidence_list)} verification evidence items")
            
            # Collect all verification evidence images for upload
            verification_images = {}
            for i, evidence in enumerate(request.verification_evidence_list):
                ref_path = evidence.get('reference_image_path')
                src_path = evidence.get('source_image_path')
                
                logger.info(f"🔍 Evidence {i}:")
                logger.info(f"   • source_image_path: {src_path}")
                logger.info(f"   • source exists: {os.path.exists(src_path) if src_path else 'N/A'}")
                
                if ref_path and os.path.exists(ref_path):
                    verification_images[f'verif_{i}_reference'] = ref_path
                if src_path and os.path.exists(src_path):
                    verification_images[f'verif_{i}_source'] = src_path
                    logger.info(f"   ✅ Source added to upload queue")
            
            # Upload all verification images
            verif_urls = {}
            if verification_images:
                logger.info(f"📦 Uploading {len(verification_images)} verification evidence images to R2...")
                verif_urls = upload_kpi_thumbnails(verification_images, request.execution_result_id, timestamp)
                logger.info(f"✅ Upload complete! Got {len(verif_urls)} R2 URLs")
                
                # Log each uploaded URL
                for key, url in verif_urls.items():
                    logger.info(f"   • {key}: {url[:80]}..." if len(url) > 80 else f"   • {key}: {url}")
            
            # Generate HTML cards for each verification
            from shared.src.lib.utils.kpi_report_template import create_verification_card
            for i, evidence in enumerate(request.verification_evidence_list):
                # Build evidence data dict with R2 URLs
                evidence_with_urls = evidence.copy()
                evidence_with_urls['reference_url'] = verif_urls.get(f'verif_{i}_reference', '')
                evidence_with_urls['source_url'] = verif_urls.get(f'verif_{i}_source', '')
                
                logger.info(f"📄 Verification card {i+1}:")
                logger.info(f"   • reference_url: {evidence_with_urls['reference_url'][:60]}..." if len(evidence_with_urls.get('reference_url', '')) > 60 else f"   • reference_url: {evidence_with_urls.get('reference_url', 'N/A')}")
                logger.info(f"   • source_url: {evidence_with_urls['source_url'][:60]}..." if len(evidence_with_urls.get('source_url', '')) > 60 else f"   • source_url: {evidence_with_urls.get('source_url', 'N/A')}")
                
                # Generate card HTML
                card_html = create_verification_card(i + 1, evidence_with_urls)
                verification_cards_html += card_html
                verification_count += 1
        
        # Prepare action details for template
        action_command = request.action_details.get('command', 'N/A')
        action_type = request.action_details.get('action_type', 'N/A')
        action_params = json.dumps(request.action_details.get('params', {}))
        action_execution_time = request.action_details.get('execution_time_ms', 0)
        action_wait_time = request.action_details.get('wait_time_ms', 0)
        action_total_time = request.action_details.get('total_time_ms', 0)
        
        # Generate HTML
        html_template = create_kpi_report_template()
        html_content = html_template.format(
            kpi_ms=kpi_ms,
            device_name=f"{request.device_id}",
            navigation_path=request.userinterface_name,
            algorithm=match_result.get('algorithm', 'unknown'),
            captures_scanned=match_result.get('captures_scanned', 0),
            before_action_thumb=thumb_urls['before_action'],
            after_action_thumb=thumb_urls['after_action'],
            before_match_thumb=thumb_urls['before_match'],
            match_thumb=thumb_urls['match'],
            match_original=thumb_urls.get('match_original', thumb_urls['match']),
            before_action_time=before_action_time,
            after_action_time=after_action_time,
            before_time=before_time,
            match_time=match_time,
            execution_result_id=request.execution_result_id[:12],
            action_timestamp=action_timestamp_full,
            match_timestamp=match_timestamp_full,
            scan_window=f"{scan_window:.2f}",
            # Extended metadata
            host_name=request.host_name or 'N/A',
            device_model=request.device_model or 'N/A',
            tree_id=(request.tree_id[:8] if request.tree_id else 'N/A'),
            action_set_id=request.action_set_id or 'N/A',
            from_node_label=request.from_node_label or 'N/A',
            to_node_label=request.to_node_label or 'N/A',
            last_action=request.last_action or 'N/A',
            # Action details
            action_command=action_command,
            action_type=action_type,
            action_params=action_params,
            action_execution_time=action_execution_time,
            action_wait_time=action_wait_time,
            action_total_time=action_total_time,
            # Verification evidence
            verification_count=verification_count,
            verification_cards=verification_cards_html
        )
        
        # Upload HTML to R2
        upload_result = upload_kpi_report(html_content, request.execution_result_id, timestamp)
        
        if upload_result.get('success'):
            report_url = upload_result['report_url']
            logger.info(f"✅ KPI report generated: {report_url}")
            return report_url
        else:
            logger.error(f"❌ Failed to upload KPI report: {upload_result.get('error')}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error generating KPI success report: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_kpi_failure_report(
    request,  # KPIMeasurementRequest object
    match_result: Dict,
    working_dir: str
) -> Optional[str]:
    """
    Generate simple local HTML failure report in COLD storage for debugging.
    
    Args:
        request: KPIMeasurementRequest object with all execution context
        match_result: Dict with failure details (error, captures_scanned, etc.)
        working_dir: Working directory containing copied images (may not exist if early failure)
        
    Returns:
        Local path to report HTML file, or None if generation failed.
        Frontend will convert local path to HTTP URL using buildHostImageUrl().
    """
    try:
        from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
        
        # Get device folder from capture_dir (handles hot/cold paths automatically)
        device_folder = get_capture_folder(request.capture_dir)
        
        # Save report in COLD storage root (same level as captures/, thumbnails/)
        cold_base = get_cold_storage_path(device_folder, '')  # Empty subfolder = base dir
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_filename = f'kpi_failure_{request.execution_result_id[:8]}_{timestamp}.html'
        report_path = os.path.join(cold_base, report_filename)
        
        logger.info(f"📝 Generating failure report: {report_path}")
        
        # Build simple HTML
        html = ['<!DOCTYPE html><html><head><meta charset="UTF-8">']
        html.append('<style>body{font-family:monospace;padding:20px;background:#f5f5f5;max-width:1200px;margin:0 auto}')
        html.append('img{max-width:400px;border:2px solid #ddd;margin:10px;display:block;cursor:pointer}')
        html.append('img:hover{border-color:#2196F3}')
        html.append('h2{color:#d32f2f;margin-top:30px;border-bottom:2px solid #d32f2f;padding-bottom:5px}')
        html.append('.verif{background:white;padding:15px;margin:10px 0;border-left:4px solid #f44336;border-radius:4px}')
        html.append('pre{background:#f5f5f5;padding:10px;border-radius:4px;overflow-x:auto}')
        html.append('.meta{background:white;padding:15px;margin:10px 0;border-radius:4px}')
        html.append('</style></head><body>')
        
        html.append(f'<h1>❌ KPI Failure Report</h1>')
        html.append(f'<div class="meta">')
        html.append(f'<p><b>Execution ID:</b> {request.execution_result_id}</p>')
        html.append(f'<p><b>Error:</b> {match_result.get("error", "Unknown")}</p>')
        html.append(f'<p><b>Captures Scanned:</b> {match_result.get("captures_scanned", 0)}</p>')
        html.append(f'<p><b>Algorithm:</b> {match_result.get("algorithm", "unknown")}</p>')
        html.append(f'<p><b>UI:</b> {request.userinterface_name}</p>')
        html.append(f'<p><b>Device:</b> {request.device_id} ({request.device_model or "unknown"})</p>')
        html.append(f'<p><b>Host:</b> {request.host_name or "unknown"}</p>')
        html.append(f'</div>')
        
        # Show each verification reference that was checked
        html.append('<h2>Verification References Checked:</h2>')
        for i, kpi_ref in enumerate(request.kpi_references):
            command = kpi_ref.get('command', 'unknown')
            params = kpi_ref.get('params', {})
            
            html.append(f'<div class="verif">')
            html.append(f'<h3>#{i+1}: {command}</h3>')
            html.append(f'<pre>{json.dumps(params, indent=2)}</pre>')
            
            # Get reference image path using verification executor
            ref_filename = params.get('imageFileName') or params.get('filename')
            if ref_filename:
                from backend_host.src.lib.utils.host_utils import get_device_by_id
                device = get_device_by_id(request.device_id)
                if device and device.verification_executor:
                    try:
                        ref_path = device.verification_executor._resolve_reference_image_path(
                            ref_filename, 
                            request.userinterface_name, 
                            request.team_id
                        )
                        if os.path.exists(ref_path):
                            html.append(f'<p><b>Reference:</b> {ref_filename}</p>')
                            html.append(f'<img src="file://{ref_path}" alt="Reference" title="Click to open">')
                        else:
                            html.append(f'<p><b>Reference:</b> {ref_filename} (NOT FOUND: {ref_path})</p>')
                    except Exception as e:
                        html.append(f'<p><b>Reference:</b> {ref_filename} (Error resolving: {e})</p>')
            html.append('</div>')
        
        # Show sample source captures that were checked
        html.append('<h2>Sample Source Captures Checked:</h2>')
        all_captures = match_result.get('all_captures', [])
        
        if all_captures:
            # Sample 5 captures evenly distributed
            sample_captures = all_captures[::max(1, len(all_captures)//5)][:5]
            
            html.append(f'<p>Showing {len(sample_captures)} of {len(all_captures)} total captures scanned</p>')
            for cap in sample_captures:
                cap_path = cap['path']
                cap_name = os.path.basename(cap_path)
                cap_time = datetime.fromtimestamp(cap['timestamp']).strftime('%H:%M:%S.%f')[:-3]
                
                # Check if capture exists in working dir or original location
                if os.path.exists(cap_path):
                    html.append(f'<div><p><b>{cap_name}</b> at {cap_time}</p>')
                    html.append(f'<img src="file://{cap_path}" alt="{cap_name}" title="Click to open"></div>')
                else:
                    html.append(f'<p><b>{cap_name}</b> at {cap_time} (file not found)</p>')
        else:
            html.append('<p>No captures were scanned (early failure)</p>')
        
        html.append('</body></html>')
        
        # Write file
        with open(report_path, 'w') as f:
            f.write('\n'.join(html))
        
        logger.info(f"✅ Failure report generated: {report_path}")
        
        # Return local path only - frontend will convert to HTTP URL
        return report_path
        
    except Exception as e:
        logger.error(f"❌ Failed to generate failure report: {e}")
        import traceback
        traceback.print_exc()
        return None

