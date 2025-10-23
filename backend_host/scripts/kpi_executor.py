#!/usr/bin/env python3
"""
KPI Measurement Executor Service - Standalone Background Service

Measures actual time from navigation action to visual confirmation (node's KPI reference appearing).
Runs as separate systemd service, processes queued measurement requests via JSON files.

Architecture:
- NavigationExecutor writes KPI request JSON files to /tmp/kpi_queue/
- This service watches directory with inotify (zero CPU when idle)
- Processes requests and updates execution_results database
- No shared memory with Flask - completely decoupled!

Proven pattern: Same as capture_monitor.py and transcript_accumulator.py
"""

import os
import sys
import json
import time
import glob
import queue
import logging
import threading
import shutil
import uuid
from queue import Queue
from datetime import datetime
from typing import Dict, Optional

# Setup path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(backend_host_dir)
sys.path.insert(0, project_root)

import inotify.adapters

# Setup logging (systemd handles file output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# KPI request queue directory
KPI_QUEUE_DIR = '/tmp/kpi_queue'


class KPIMeasurementRequest:
    """KPI measurement request - loaded from JSON file"""
    def __init__(self, data: dict):
        # Validate required fields
        self.execution_result_id = data['execution_result_id']
        self.team_id = data['team_id']
        self.capture_dir = data['capture_dir']
        self.action_timestamp = data['action_timestamp']
        self.verification_timestamp = data['verification_timestamp']
        self.kpi_references = data['kpi_references']
        self.timeout_ms = data['timeout_ms']
        self.device_id = data['device_id']
        self.userinterface_name = data['userinterface_name']  # MANDATORY for reference resolution
        self.device_model = data.get('device_model')
        self.kpi_timestamp = data.get('kpi_timestamp')
        self.last_action_wait_ms = data.get('last_action_wait_ms', 0)
        self.request_file = data.get('_request_file')  # Track source file
        # Extended metadata for report
        self.host_name = data.get('host_name')
        self.device_name = data.get('device_name')
        self.tree_id = data.get('tree_id')
        self.action_set_id = data.get('action_set_id')
        self.from_node_label = data.get('from_node_label')
        self.to_node_label = data.get('to_node_label')
        self.last_action = data.get('last_action')
        self.action_screenshot_path = data.get('action_screenshot_path')  # ✅ NEW: Screenshot from action_executor


class KPIExecutorService:
    """Standalone KPI executor service with inotify-based queue"""
    
    def __init__(self):
        self.running = False
        self.work_queue = Queue(maxsize=100)
        self.worker_thread = None
        
        # Ensure queue directory exists
        os.makedirs(KPI_QUEUE_DIR, exist_ok=True)
        
        # Setup inotify
        self.inotify = inotify.adapters.Inotify()
        self.inotify.add_watch(KPI_QUEUE_DIR)
        
        logger.info(f"✓ Watching KPI queue directory: {KPI_QUEUE_DIR}")
    
    def start(self):
        """Start worker thread"""
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(self.work_queue,),
            daemon=True,
            name="KPI-Worker"
        )
        self.worker_thread.start()
        logger.info(f"✅ KPI worker thread started")
    
    def _worker_loop(self, work_queue):
        """Worker thread - processes KPI measurement requests"""
        logger.info("🔄 KPI worker loop started")
        
        iteration = 0
        while self.running:
            try:
                # Wait for measurement request
                try:
                    request_file, request = work_queue.get(timeout=1.0)
                except queue.Empty:
                    # Periodic heartbeat
                    iteration += 1
                    if iteration % 120 == 0:
                        logger.info(f"💓 KPI worker heartbeat (queue size: {work_queue.qsize()})")
                    continue
                
                # Log immediately
                logger.info(f"📥 KPI worker dequeued: {os.path.basename(request_file)}")
                
                # Process measurement
                try:
                    logger.info(f"🎬 KPI processing started: {request.execution_result_id[:8]}")
                    self._process_measurement(request)
                    logger.info(f"🏁 KPI processing finished")
                    
                    # Delete processed request file
                    try:
                        os.remove(request_file)
                        logger.debug(f"🗑️  Deleted processed request: {os.path.basename(request_file)}")
                    except Exception as e:
                        logger.warning(f"Could not delete request file: {e}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing KPI measurement: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    work_queue.task_done()
                    
            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
        
        logger.info("🛑 KPI worker loop exited")
    
    def _process_measurement(self, request: KPIMeasurementRequest):
        """Process single KPI measurement request"""
        logger.info(f"🔍 Processing KPI measurement")
        logger.info(f"   • Execution result: {request.execution_result_id[:8]}")
        
        # DEBUG: Show exact values received
        logger.info(f"   • verification_timestamp: {request.verification_timestamp}")
        logger.info(f"   • last_action_wait_ms: {request.last_action_wait_ms}ms")
        logger.info(f"   • action_timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        logger.info(f"   • timeout_ms: {request.timeout_ms}ms")
        logger.info(f"   • kpi_references: {len(request.kpi_references)}")
        
        # Check if KPI already calculated during verification
        if request.kpi_timestamp:
            kpi_ms = int((request.kpi_timestamp - request.action_timestamp) * 1000)
            logger.info(f"⚡ KPI already calculated during verification: {kpi_ms}ms")
            logger.info(f"   • Skipping post-processing scan")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
            return
        
        start_time = time.time()
        
        # CRITICAL: Copy images from hot storage to /tmp/ (RAM) to avoid race condition
        # Hot storage only keeps 150 images (30s at 5fps), they may be deleted during processing
        working_dir = self._copy_images_to_tmp(request)
        if not working_dir:
            self._update_result(request.execution_result_id, request.team_id, False, None, "Failed to copy images from hot storage")
            return
        
        try:
            # Scan captures from /tmp/ working directory
            match_result = self._scan_until_match(request, working_dir)
            
            logger.info(f"🔍 Scan completed, processing result: success={match_result.get('success')}")
            
            # Store result
            if match_result['success']:
                kpi_ms = int((match_result['timestamp'] - request.action_timestamp) * 1000)
                algorithm = match_result.get('algorithm', 'unknown')
                logger.info(f"✅ KPI match found!")
                logger.info(f"   • KPI duration: {kpi_ms}ms")
                logger.info(f"   • Algorithm: {algorithm}")
                logger.info(f"   • Captures scanned: {match_result['captures_scanned']}")
                
                # Generate KPI report with thumbnails (from working directory)
                report_url = self._generate_kpi_report(request, match_result, kpi_ms, working_dir)
                
                self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None, report_url)
            else:
                algorithm = match_result.get('algorithm', 'unknown')
                logger.error(f"❌ KPI measurement failed: {match_result['error']}")
                logger.info(f"   • Algorithm: {algorithm}")
                logger.info(f"   • Captures scanned: {match_result.get('captures_scanned', 0)}")
                self._update_result(request.execution_result_id, request.team_id, False, None, match_result['error'])
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"⏱️  KPI processing completed in {processing_time}ms")
        
        except Exception as e:
            logger.error(f"❌ Exception during KPI scan: {e}")
            import traceback
            traceback.print_exc()
            # Store failure result
            error_msg = f"Exception during scan: {str(e)}"
            self._update_result(request.execution_result_id, request.team_id, False, None, error_msg)
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"⏱️  KPI processing failed in {processing_time}ms")
        
        finally:
            # Cleanup: Delete working directory
            self._cleanup_working_dir(working_dir)
    
    def _copy_images_to_tmp(self, request: KPIMeasurementRequest) -> str:
        """
        Copy required images AND thumbnails from hot/cold storage to /tmp/ working directory (RAM).
        Avoids race condition where hot storage images are deleted during processing.
        
        Returns:
            Working directory path, or None if copy failed
        """
        
        # Create working directory in /tmp/ (RAM)
        working_id = str(uuid.uuid4())[:8]
        working_dir = f'/tmp/kpi_working/{request.execution_result_id[:8]}_{working_id}'
        os.makedirs(working_dir, exist_ok=True)
        
        logger.info(f"📂 Copying images to /tmp/ working directory...")
        logger.info(f"   • Source: {request.capture_dir}")
        logger.info(f"   • Working dir: {working_dir}")
        
        # Calculate scan window based on available information
        if request.verification_timestamp:
            # Case 1: Has verification - scan backwards from verification
            scan_end = request.verification_timestamp
            scan_start = max(request.action_timestamp, request.verification_timestamp - request.timeout_ms / 1000)
            logger.info(f"   • Scan mode: WITH verification (backwards from verification)")
        elif request.last_action_wait_ms > 0:
            # Case 2: No verification but has wait - scan backwards from wait end
            wait_end = request.action_timestamp + request.last_action_wait_ms / 1000
            scan_end = wait_end
            
            # For long waits (>60s), scan last 20s instead of timeout window
            if request.last_action_wait_ms > 60000:
                scan_window_s = 20.0  # Last 20 seconds
                logger.info(f"   • Scan mode: NO verification, WITH LONG wait ({request.last_action_wait_ms/1000:.1f}s) - scanning last 20s")
            else:
                scan_window_s = request.timeout_ms / 1000
                logger.info(f"   • Scan mode: NO verification, WITH wait (backwards from wait end)")
            
            scan_start = max(request.action_timestamp, wait_end - scan_window_s)
        else:
            # Case 3: No verification, no wait - scan FORWARD from action
            scan_start = request.action_timestamp
            scan_end = request.action_timestamp + request.timeout_ms / 1000
            logger.info(f"   • Scan mode: NO verification, NO wait (FORWARD from action)")
        
        logger.info(f"   • Scan window: {scan_end - scan_start:.2f}s (max {request.timeout_ms}ms)")
        
        # Copy captures in time window + 1 frame before (for "before" thumbnail)
        pattern = os.path.join(request.capture_dir, "capture_*.jpg")
        copied_captures = 0
        copied_capture_names = []  # Track which captures we copied
        
        # First pass: find all captures and get the one before scan window
        all_available_captures = []
        for source_path in glob.glob(pattern):
            if "_thumbnail" in source_path:
                continue
            try:
                ts = os.path.getmtime(source_path)
                filename = os.path.basename(source_path)
                all_available_captures.append({'path': source_path, 'ts': ts, 'filename': filename})
            except (OSError, IOError):
                continue
        
        # Sort by timestamp
        all_available_captures.sort(key=lambda x: x['ts'])
        
        # Find first capture in scan window
        first_in_window_idx = None
        for i, cap in enumerate(all_available_captures):
            if scan_start <= cap['ts'] <= scan_end:
                first_in_window_idx = i
                break
        
        # Copy the frame BEFORE first frame in window (if exists)
        if first_in_window_idx is not None and first_in_window_idx > 0:
            before_window_cap = all_available_captures[first_in_window_idx - 1]
            dest_path = os.path.join(working_dir, before_window_cap['filename'])
            try:
                shutil.copy2(before_window_cap['path'], dest_path)
                copied_captures += 1
                copied_capture_names.append(before_window_cap['filename'])
                logger.info(f"📸 Copied 1 extra frame BEFORE scan window: {before_window_cap['filename']}")
            except (OSError, IOError) as e:
                logger.warning(f"Could not copy before-window frame: {e}")
        
        # Copy all captures in scan window
        for source_path in glob.glob(pattern):
            if "_thumbnail" in source_path:
                continue
            
            try:
                ts = os.path.getmtime(source_path)
                # Copy images in time window: scan_start → scan_end
                if scan_start <= ts <= scan_end:
                    filename = os.path.basename(source_path)
                    if filename not in copied_capture_names:  # Don't copy twice
                        dest_path = os.path.join(working_dir, filename)
                        shutil.copy2(source_path, dest_path)  # copy2 preserves timestamps
                        copied_captures += 1
                        copied_capture_names.append(filename)
            except (OSError, IOError) as e:
                logger.warning(f"Could not copy {source_path}: {e}")
                continue
        
        if copied_captures == 0:
            logger.error(f"❌ No captures copied from {request.capture_dir}")
            return None
        
        logger.info(f"✅ Copied {copied_captures} captures to /tmp/ (RAM) - includes 1 before scan window")
        
        # Copy thumbnails for EACH capture we copied (not by mtime - ensures 1:1 mapping)
        # Use centralized path utilities (no manual path manipulation!)
        from shared.src.lib.utils.storage_path_utils import get_capture_folder, get_thumbnails_path
        
        device_folder = get_capture_folder(request.capture_dir)
        thumb_source_dir = get_thumbnails_path(device_folder)
        
        copied_thumbnails = 0
        missing_thumbnails = 0
        
        if os.path.isdir(thumb_source_dir):
            for capture_name in copied_capture_names:
                # For each capture, find its corresponding thumbnail
                thumb_name = capture_name.replace('.jpg', '_thumbnail.jpg')
                thumb_source = os.path.join(thumb_source_dir, thumb_name)
                thumb_dest = os.path.join(working_dir, thumb_name)
                
                if os.path.exists(thumb_source):
                    try:
                        shutil.copy2(thumb_source, thumb_dest)
                        copied_thumbnails += 1
                    except (OSError, IOError) as e:
                        logger.warning(f"Could not copy thumbnail {thumb_name}: {e}")
                        missing_thumbnails += 1
                else:
                    logger.debug(f"Thumbnail not found: {thumb_name}")
                    missing_thumbnails += 1
            
            if missing_thumbnails > 0:
                logger.warning(f"⚠️  {missing_thumbnails} thumbnails missing for copied captures")
            logger.info(f"✅ Copied {copied_thumbnails}/{copied_captures} thumbnails to /tmp/ (RAM)")
        else:
            logger.warning(f"⚠️  Thumbnail directory not found: {thumb_source_dir}")
            missing_thumbnails = copied_captures
        
        return working_dir
    
    def _cleanup_working_dir(self, working_dir: str):
        """Delete working directory and all its contents"""
        if not working_dir or not os.path.exists(working_dir):
            return
        
        try:
            shutil.rmtree(working_dir)
            logger.debug(f"🗑️  Cleaned up working directory: {working_dir}")
        except Exception as e:
            logger.warning(f"Could not cleanup working directory {working_dir}: {e}")
    
    def _scan_until_match(self, request: KPIMeasurementRequest, capture_dir: str) -> dict:
        """
        Scan captures using optimized quick check + backward scan algorithm.
        
        Args:
            request: KPI measurement request
            capture_dir: Directory to scan (usually /tmp/ working directory)
        """
        action_timestamp = request.action_timestamp
        verification_timestamp = request.verification_timestamp
        kpi_references = request.kpi_references
        
        logger.info(f"🔍 Scanning captures in: {capture_dir}")
        
        # Get device instance
        from backend_host.src.lib.utils.host_utils import get_device_by_id
        
        device = get_device_by_id(request.device_id)
        if not device:
            return {'success': False, 'error': f'Device {request.device_id} not found', 'captures_scanned': 0}
        
        # Use device's verification_executor
        verif_executor = device.verification_executor
        if not verif_executor:
            return {'success': False, 'error': f'No verification_executor for device {request.device_id}', 'captures_scanned': 0}
        
        # Calculate optimized time window (only if verification exists)
        if verification_timestamp:
            window_ms = int((verification_timestamp - action_timestamp) * 1000)
            timeout_s = request.timeout_ms / 1000
            window_s = window_ms / 1000
            logger.info(f"🎯 Optimized scan window: {window_s:.2f}s (action → verification) vs timeout: {timeout_s:.1f}s")
        else:
            logger.info(f"🎯 No verification - using timeout-based scan window")
        
        # Find all captures in time window
        pattern = os.path.join(capture_dir, "capture_*.jpg")
        all_captures = []
        
        # Calculate scan window based on available information (same logic as copy)
        if verification_timestamp:
            # Case 1: Has verification - scan backwards from verification
            logger.info(f"   • Case 1: Has verification - scan backwards from verification")
            scan_end = verification_timestamp
            scan_start = max(action_timestamp, verification_timestamp - request.timeout_ms / 1000)
        elif request.last_action_wait_ms > 0:
            # Case 2: No verification but has wait - scan backwards from wait end
            wait_end = action_timestamp + request.last_action_wait_ms / 1000
            scan_end = wait_end
            
            # For long waits (>60s), scan last 20s instead of timeout window
            if request.last_action_wait_ms > 60000:
                scan_window_s = 20.0  # Last 20 seconds
                logger.info(f"   • Case 2: No verification but has LONG wait ({request.last_action_wait_ms/1000:.1f}s) - scanning last 20s")
            else:
                scan_window_s = request.timeout_ms / 1000
                logger.info(f"   • Case 2: No verification but has wait - scan backwards from wait end")
            
            scan_start = max(action_timestamp, wait_end - scan_window_s)
        else:
            # Case 3: No verification, no wait - scan FORWARD from action
            logger.info(f"   • Case 3: No verification, no wait - scan FORWARD from action")
            scan_start = action_timestamp
            scan_end = action_timestamp + request.timeout_ms / 1000
        
        for path in glob.glob(pattern):
            if "_thumbnail" in path:
                continue
            try:
                ts = os.path.getmtime(path)
                if scan_start <= ts <= scan_end:
                    all_captures.append({'path': path, 'timestamp': ts})
            except OSError:
                continue
        
        # Sort by timestamp
        all_captures.sort(key=lambda x: x['timestamp'])
        
        if not all_captures:
            return {'success': False, 'error': 'No captures found in time window', 'captures_scanned': 0}
        
        total_captures = len(all_captures)
        
        # Calculate saved time only if verification exists
        if verification_timestamp:
            saved_ms = request.timeout_ms - int((verification_timestamp - action_timestamp) * 1000)
            saved_s = saved_ms / 1000
            logger.info(f"📸 Found {total_captures} captures in optimized window (saved ~{saved_s:.2f}s of scanning)")
        else:
            logger.info(f"📸 Found {total_captures} captures in window")
        
        # Convert kpi_references to verification format
        # CRITICAL: Force timeout=0 to check ONLY the provided image (no future frame scanning)
        verifications = []
        for kpi_ref in kpi_references:
            command = kpi_ref.get('command', 'waitForImageToAppear')
            params = dict(kpi_ref.get('params', {}))  # Copy params
            original_timeout = params.get('timeout', 0)
            params['timeout'] = 0  # Force single-image check (no waiting for future frames)
            verifications.append({
                'verification_type': kpi_ref.get('verification_type', 'image'),
                'command': command,
                'params': params
            })
            logger.info(f"   • Verification: {command} (timeout: {original_timeout}s → forced to 0s for single-image check)")
        
        logger.info(f"   • Total verifications configured: {len(verifications)}")
        
        # Helper to test a capture
        def test_capture(capture, label):
            logger.info(f"🔍 Quick check - {label}: {os.path.basename(capture['path'])}")
            try:
                result = verif_executor.execute_verifications(
                    verifications=verifications,
                    userinterface_name=request.userinterface_name,  # MANDATORY parameter
                    image_source_url=capture['path'],
                    team_id=request.team_id
                )
                success = result.get('success', False)
                logger.info(f"   ↳ Result: {success}")
                return success
            except Exception as e:
                logger.error(f"   ↳ ERROR in test_capture: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        captures_scanned = 0
        
        # PHASE 1: QUICK CHECK (early only - late check is useless for finding earliest)
        logger.info(f"⚡ Phase 1: Quick check (early only)")
        
        # Quick check: T0+200ms (early in the scan window)
        # If it matches here, we know it appeared very early (earliest or close to it)
        target_ts = scan_start + 0.2
        early_idx = min(range(total_captures), key=lambda i: abs(all_captures[i]['timestamp'] - target_ts))
        captures_scanned += 1
        
        if test_capture(all_captures[early_idx], f"early check (start+200ms, idx {early_idx}/{total_captures})"):
            return {
                'success': True,
                'timestamp': all_captures[early_idx]['timestamp'],
                'capture_path': all_captures[early_idx]['path'],
                'capture_index': early_idx,  # ✅ Return index for thumbnail selection
                'all_captures': all_captures,  # ✅ Return full list for before/match selection
                'captures_scanned': captures_scanned,
                'error': None,
                'algorithm': 'quick_check_early'
            }
        
        logger.info(f"⚡ Quick check: no early match, proceeding to backward scan")
        checked_indices = {early_idx}
        logger.info(f"   ↳ Early idx checked: {early_idx}")
        
        # PHASE 2: BACKWARD SCAN (optimized to find earliest match)
        logger.info(f"🔙 Phase 2: Backward scan from verification → action")
        logger.info(f"   ↳ Will scan {total_captures - len(checked_indices)} remaining captures")
        logger.info(f"   ↳ Strategy: Scan backward in steps of 2, fill gap when boundary found")
        
        earliest_match = None  # Track the earliest (closest to action) match found
        
        # Scan backward in steps of 2 (skip every other frame for speed)
        for i in range(total_captures - 1, -1, -2):
            if i in checked_indices:
                continue
            
            capture = all_captures[i]
            captures_scanned += 1
            
            logger.info(f"🔍 Backward scan {i+1}/{total_captures}: {os.path.basename(capture['path'])}")
            
            try:
                result = verif_executor.execute_verifications(
                    verifications=verifications,
                    userinterface_name=request.userinterface_name,  # MANDATORY parameter
                    image_source_url=capture['path'],
                    team_id=request.team_id
                )
                
                if result.get('success'):
                    # Found a match - keep scanning backward to find earliest
                    earliest_match = {
                        'timestamp': capture['timestamp'],
                        'capture_path': capture['path'],
                        'index': i
                    }
                    logger.info(f"   ↳ Match found! Continuing backward (step -2)...")
                elif earliest_match:
                    # No match after having matches - check the skipped frame (i+1) to fill the gap
                    gap_idx = i + 1
                    if gap_idx < total_captures and gap_idx not in checked_indices:
                        logger.info(f"   ↳ Checking skipped frame at idx {gap_idx} to confirm boundary...")
                        gap_capture = all_captures[gap_idx]
                        captures_scanned += 1
                        
                        gap_result = verif_executor.execute_verifications(
                            verifications=verifications,
                            userinterface_name=request.userinterface_name,
                            image_source_url=gap_capture['path'],
                            team_id=request.team_id
                        )
                        
                        if gap_result.get('success'):
                            # Gap frame matches, so earliest is the gap frame
                            earliest_match = {
                                'timestamp': gap_capture['timestamp'],
                                'capture_path': gap_capture['path'],
                                'index': gap_idx
                            }
                            logger.info(f"   ↳ Gap frame matches - earliest is at idx {gap_idx}")
                    
                    # Return the earliest match found
                    logger.info(f"   ↳ Boundary confirmed - earliest match at idx {earliest_match['index']}")
                    return {
                        'success': True,
                        'timestamp': earliest_match['timestamp'],
                        'capture_path': earliest_match['capture_path'],
                        'capture_index': earliest_match['index'],  # ✅ Return index for thumbnail selection
                        'all_captures': all_captures,  # ✅ Return full list for before/match selection
                        'captures_scanned': captures_scanned,
                        'error': None,
                        'algorithm': 'backward_scan_step2'
                    }
                else:
                    logger.debug(f"   ↳ No match")
            except Exception as e:
                logger.error(f"   ↳ ERROR in backward scan: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # If we have a match at the end (reached start while still matching)
        # Check if there's a skipped frame at index 0 that we need to verify
        if earliest_match:
            if earliest_match['index'] > 0 and 0 not in checked_indices:
                logger.info(f"   ↳ Checking first frame (idx 0) to confirm earliest...")
                first_capture = all_captures[0]
                captures_scanned += 1
                
                first_result = verif_executor.execute_verifications(
                    verifications=verifications,
                    userinterface_name=request.userinterface_name,
                    image_source_url=first_capture['path'],
                    team_id=request.team_id
                )
                
                if first_result.get('success'):
                    earliest_match = {
                        'timestamp': first_capture['timestamp'],
                        'capture_path': first_capture['path'],
                        'index': 0
                    }
                    logger.info(f"   ↳ First frame matches - earliest is at idx 0")
            
            logger.info(f"   ↳ Reached start of window - earliest match at idx {earliest_match['index']}")
            return {
                'success': True,
                'timestamp': earliest_match['timestamp'],
                'capture_path': earliest_match['capture_path'],
                'capture_index': earliest_match['index'],  # ✅ Return index for thumbnail selection
                'all_captures': all_captures,  # ✅ Return full list for before/match selection
                'captures_scanned': captures_scanned,
                'error': None,
                'algorithm': 'backward_scan_step2'
            }
        
        # No match found - backward scan completed without finding match
        logger.info(f"🔙 Backward scan completed: checked {captures_scanned} captures total")
        window_duration = scan_end - scan_start
        error_msg = f'No match found in {total_captures} captures ({window_duration:.2f}s window)'
        logger.warning(f"⚠️  {error_msg}")
        
        return {
            'success': False,
            'timestamp': None,
            'capture_index': None,  # ✅ Include for consistency
            'all_captures': all_captures,  # ✅ Include for consistency (even on failure)
            'captures_scanned': captures_scanned,
            'error': error_msg,
            'algorithm': 'exhaustive_search_failed'
        }
    
    def _find_closest_thumbnail(self, thumb_dir: str, target_ts: float) -> Optional[str]:
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
    
    def _generate_kpi_report(self, request: KPIMeasurementRequest, match_result: Dict, kpi_ms: int, working_dir: str) -> Optional[str]:
        """Generate KPI report HTML with thumbnail evidence and upload to R2"""
        try:
            from datetime import datetime
            from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, is_ram_mode, get_cold_storage_path
            from shared.src.lib.utils.cloudflare_utils import upload_kpi_thumbnails, upload_kpi_report
            from shared.src.lib.utils.kpi_report_template import create_kpi_report_template
            
            logger.info(f"📊 Generating KPI report for {request.execution_result_id[:8]}")
            
            # Find 3 thumbnails from working directory (already copied to /tmp/)
            logger.info(f"🔍 Searching for thumbnails in working directory: {working_dir}")
            
            if not os.path.isdir(working_dir):
                logger.warning(f"⚠️  Working directory not found: {working_dir}")
                return None
            
            # Find 3 thumbnails using INDEX-BASED selection (not timestamp search!)
            # This guarantees before ≠ match (unless match is first frame)
            match_index = match_result.get('capture_index')
            all_captures = match_result.get('all_captures', [])
            
            if match_index is None or not all_captures:
                logger.error(f"❌ No capture_index or all_captures in match_result")
                return None
            
            # Get match capture (the one that passed verification)
            match_capture = all_captures[match_index]
            match_capture_filename = os.path.basename(match_capture['path'])
            match_image = os.path.join(working_dir, match_capture_filename)  # Full-size original for click
            match_thumb_filename = match_capture_filename.replace('.jpg', '_thumbnail.jpg')
            match_thumb = os.path.join(working_dir, match_thumb_filename)  # Thumbnail for display
            
            # Get before capture (match - 1) - always exists now due to extra frame copied
            before_index = match_index - 1
            if before_index < 0:
                logger.error(f"❌ Match is at index 0 but no before frame available (should have been copied)")
                return None
            
            before_capture = all_captures[before_index]
            before_capture_filename = os.path.basename(before_capture['path'])
            before_thumb_filename = before_capture_filename.replace('.jpg', '_thumbnail.jpg')
            before_thumb = os.path.join(working_dir, before_thumb_filename)
            
            # Get action thumbnail - use provided screenshot from action_executor if available
            if request.action_screenshot_path and os.path.exists(request.action_screenshot_path):
                # Copy the provided action screenshot to working directory
                action_screenshot_filename = os.path.basename(request.action_screenshot_path)
                action_thumb = os.path.join(working_dir, action_screenshot_filename)
                shutil.copy2(request.action_screenshot_path, action_thumb)
                logger.info(f"   • Action: {action_screenshot_filename} (from action_executor) ✅")
            else:
                # Fallback: Find closest thumbnail by timestamp (old behavior)
                action_thumb = self._find_closest_thumbnail(working_dir, request.action_timestamp)
                if action_thumb:
                    logger.info(f"   • Action: {os.path.basename(action_thumb)} (timestamp search - fallback)")
                else:
                    logger.warning(f"⚠️  No action screenshot provided and timestamp search failed")
            
            # Verify all thumbnails exist (use full-size as fallback if thumbnail missing)
            if not os.path.exists(match_thumb):
                # Fallback: Use full-size capture if thumbnail missing
                if os.path.exists(match_image):
                    logger.warning(f"⚠️  Match thumbnail not found, using full-size capture as fallback for display")
                    match_thumb = match_image
                else:
                    logger.error(f"❌ Match capture not found: {match_capture_filename}")
                    return None
            
            # Verify match original exists (always needed for click zoom)
            if not os.path.exists(match_image):
                logger.error(f"❌ Match original not found: {match_capture_filename}")
                return None
                    
            if not os.path.exists(before_thumb):
                # Fallback: Use full-size capture if thumbnail missing
                before_thumb_fallback = before_thumb.replace('_thumbnail.jpg', '.jpg')
                if os.path.exists(before_thumb_fallback):
                    logger.warning(f"⚠️  Before thumbnail not found, using full-size capture as fallback")
                    before_thumb = before_thumb_fallback
                else:
                    logger.error(f"❌ Before capture not found: {before_capture_filename}")
                    return None
                    
            if not action_thumb or not os.path.exists(action_thumb):
                logger.warning(f"⚠️  Action screenshot not found - report will be incomplete")
                # Generate report anyway without action thumbnail
                action_thumb = None
            
            logger.info(f"✓ Found all 3 thumbnails + 1 original (index-based selection)")
            logger.info(f"   • Before: {before_thumb_filename} (index {before_index})")
            logger.info(f"   • Match: {match_thumb_filename} + original (index {match_index})")
            
            # Calculate timestamps for display
            before_time_ts = before_capture['timestamp']
            
            # Upload thumbnails + match original to R2
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            thumbnails = {}
            
            # Only include thumbnails that exist
            if action_thumb:
                thumbnails['action'] = action_thumb
            thumbnails['before'] = before_thumb
            thumbnails['match'] = match_thumb
            thumbnails['match_original'] = match_image  # Full-size for click zoom
            
            thumb_urls = upload_kpi_thumbnails(thumbnails, request.execution_result_id, timestamp)
            
            if not thumb_urls:
                logger.error(f"❌ Failed to upload thumbnails")
                return None
            
            # Ensure all required keys exist after deduplication
            # Deduplication can remove keys if files are identical
            if 'before' not in thumb_urls and 'match' in thumb_urls:
                thumb_urls['before'] = thumb_urls['match']
            if 'match' not in thumb_urls and 'before' in thumb_urls:
                thumb_urls['match'] = thumb_urls['before']
            if 'match_original' not in thumb_urls and 'match' in thumb_urls:
                thumb_urls['match_original'] = thumb_urls['match']
            
            # Ensure all required keys exist (use placeholder for missing action)
            if 'action' not in thumb_urls:
                # Action thumbnail missing - use before or match as placeholder
                thumb_urls['action'] = thumb_urls.get('before') or thumb_urls.get('match')
                logger.info(f"✓ Uploaded {len(thumb_urls)} unique images to R2 (action missing, using placeholder)")
            else:
                if len(thumb_urls) < len(thumbnails):
                    logger.info(f"✓ Uploaded {len(thumb_urls)} unique images to R2 (some deduplicated)")
                else:
                    logger.info(f"✓ Uploaded {len(thumb_urls)} images to R2 (3 thumbnails + 1 original)")
            
            # Format timestamps for display using actual capture timestamps
            action_time = datetime.fromtimestamp(request.action_timestamp).strftime('%H:%M:%S.%f')[:-3]
            before_time = datetime.fromtimestamp(before_time_ts).strftime('%H:%M:%S.%f')[:-3]
            match_time = datetime.fromtimestamp(match_result['timestamp']).strftime('%H:%M:%S.%f')[:-3]
            action_timestamp_full = datetime.fromtimestamp(request.action_timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            match_timestamp_full = datetime.fromtimestamp(match_result['timestamp']).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            # Calculate scan window
            scan_window = match_result['timestamp'] - request.action_timestamp
            
            # Generate HTML
            html_template = create_kpi_report_template()
            html_content = html_template.format(
                kpi_ms=kpi_ms,
                device_name=f"{request.device_id}",
                navigation_path=request.userinterface_name,
                algorithm=match_result.get('algorithm', 'unknown'),
                captures_scanned=match_result.get('captures_scanned', 0),
                action_thumb=thumb_urls['action'],
                before_thumb=thumb_urls['before'],
                match_thumb=thumb_urls['match'],
                match_original=thumb_urls.get('match_original', thumb_urls['match']),  # Fallback to thumb if original missing
                action_time=action_time,
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
                action_set_id=request.action_set_id or 'N/A',  # Don't truncate - it's a name, not UUID
                from_node_label=request.from_node_label or 'N/A',
                to_node_label=request.to_node_label or 'N/A',
                last_action=request.last_action or 'N/A'
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
            logger.error(f"❌ Error generating KPI report: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _update_result(self, execution_result_id: str, team_id: str, success: bool, kpi_ms: int, error: str, report_url: str = None):
        """Update execution_results with KPI measurement"""
        try:
            from shared.src.lib.supabase.execution_results_db import update_execution_result_with_kpi
            
            result = update_execution_result_with_kpi(
                execution_result_id=execution_result_id,
                team_id=team_id,
                kpi_measurement_success=success,
                kpi_measurement_ms=kpi_ms,
                kpi_measurement_error=error,
                kpi_report_url=report_url
            )
            
            if result:
                if report_url:
                    logger.info(f"💾 Stored KPI result: {kpi_ms}ms (success: {success}) - Report: {report_url}")
                else:
                    logger.info(f"💾 Stored KPI result: {kpi_ms}ms (success: {success})")
            else:
                logger.warning(f"⚠️  Failed to update execution_result_id: {execution_result_id[:8]}")
                
        except Exception as e:
            logger.error(f"❌ Error storing KPI result: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_existing_requests(self):
        """Process any existing request files on startup"""
        logger.info("Scanning for existing KPI requests...")
        
        request_files = sorted(glob.glob(os.path.join(KPI_QUEUE_DIR, 'kpi_request_*.json')))
        
        if request_files:
            logger.info(f"Found {len(request_files)} pending KPI requests")
            for request_file in request_files:
                try:
                    self._enqueue_request_file(request_file)
                except Exception as e:
                    logger.error(f"Error loading request {request_file}: {e}")
        else:
            logger.info("No pending KPI requests")
    
    def _enqueue_request_file(self, request_file: str):
        """Load and enqueue a request file"""
        with open(request_file, 'r') as f:
            data = json.load(f)
        
        data['_request_file'] = request_file
        request = KPIMeasurementRequest(data)
        
        try:
            self.work_queue.put_nowait((request_file, request))
            logger.info(f"📋 Queued KPI request: {os.path.basename(request_file)}")
        except queue.Full:
            logger.error(f"❌ Queue full! Dropping request: {os.path.basename(request_file)}")
    
    def run(self):
        """Main event loop - watch for new KPI request files"""
        logger.info("=" * 80)
        logger.info("Starting KPI executor inotify event loop")
        logger.info("Zero CPU when idle - event-driven processing")
        logger.info("=" * 80)
        
        # Process any existing requests first
        self._process_existing_requests()
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Only process files moved into watched directory (atomic writes)
                if 'IN_MOVED_TO' not in type_names:
                    continue
                
                # Check if it's a KPI request file
                if filename.startswith('kpi_request_') and filename.endswith('.json'):
                    request_file = os.path.join(path, filename)
                    logger.info(f"🆕 New KPI request detected: {filename}")
                    
                    try:
                        self._enqueue_request_file(request_file)
                    except Exception as e:
                        logger.error(f"Error enqueueing request {filename}: {e}")
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.inotify.remove_watch(KPI_QUEUE_DIR)


def main():
    """Main entry point"""
    
    # Kill any existing kpi_executor instances
    from shared.src.lib.utils.system_utils import kill_existing_script_instances
    killed = kill_existing_script_instances('kpi_executor.py')
    if killed:
        logger.info(f"Killed existing kpi_executor instances: {killed}")
        time.sleep(1)
    
    logger.info("=" * 80)
    logger.info("Starting KPI Measurement Executor Service")
    logger.info("Performance: Zero CPU when idle, event-driven processing")
    logger.info("Queue: JSON files in /tmp/kpi_queue/")
    logger.info("=" * 80)
    
    # Start service
    service = KPIExecutorService()
    service.start()
    service.run()


if __name__ == '__main__':
    main()

