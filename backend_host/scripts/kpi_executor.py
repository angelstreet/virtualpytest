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
        self.request_file = data.get('_request_file')  # Track source file


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
                    if iteration % 30 == 0:
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
        
        # Check if KPI already calculated during verification
        if request.kpi_timestamp:
            kpi_ms = int((request.kpi_timestamp - request.action_timestamp) * 1000)
            logger.info(f"⚡ KPI already calculated during verification: {kpi_ms}ms")
            logger.info(f"   • Skipping post-processing scan")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
            return
        
        logger.info(f"   • Action timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        logger.info(f"   • Timeout: {request.timeout_ms}ms ({request.timeout_ms / 1000:.1f}s)")
        logger.info(f"   • KPI references: {len(request.kpi_references)}")
        
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
            
            # Store result
            if match_result['success']:
                kpi_ms = int((match_result['timestamp'] - request.action_timestamp) * 1000)
                algorithm = match_result.get('algorithm', 'unknown')
                logger.info(f"✅ KPI match found!")
                logger.info(f"   • KPI duration: {kpi_ms}ms")
                logger.info(f"   • Algorithm: {algorithm}")
                logger.info(f"   • Captures scanned: {match_result['captures_scanned']}")
                self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
            else:
                algorithm = match_result.get('algorithm', 'unknown')
                logger.error(f"❌ KPI measurement failed: {match_result['error']}")
                logger.info(f"   • Algorithm: {algorithm}")
                logger.info(f"   • Captures scanned: {match_result.get('captures_scanned', 0)}")
                self._update_result(request.execution_result_id, request.team_id, False, None, match_result['error'])
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"⏱️  KPI processing completed in {processing_time}ms")
        
        finally:
            # Cleanup: Delete working directory
            self._cleanup_working_dir(working_dir)
    
    def _copy_images_to_tmp(self, request: KPIMeasurementRequest) -> str:
        """
        Copy required images from hot/cold storage to /tmp/ working directory (RAM).
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
        
        # Find all captures in time window
        pattern = os.path.join(request.capture_dir, "capture_*.jpg")
        copied_count = 0
        
        for source_path in glob.glob(pattern):
            if "_thumbnail" in source_path:
                continue
            
            try:
                ts = os.path.getmtime(source_path)
                # Copy images in time window: action → verification
                if request.action_timestamp <= ts <= request.verification_timestamp:
                    filename = os.path.basename(source_path)
                    dest_path = os.path.join(working_dir, filename)
                    shutil.copy2(source_path, dest_path)  # copy2 preserves timestamps
                    copied_count += 1
            except (OSError, IOError) as e:
                logger.warning(f"Could not copy {source_path}: {e}")
                continue
        
        if copied_count == 0:
            logger.error(f"❌ No images copied from {request.capture_dir}")
            return None
        
        logger.info(f"✅ Copied {copied_count} images to /tmp/ (RAM)")
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
        
        # Calculate optimized time window
        window_ms = int((verification_timestamp - action_timestamp) * 1000)
        timeout_s = request.timeout_ms / 1000
        window_s = window_ms / 1000
        logger.info(f"🎯 Optimized scan window: {window_s:.2f}s (action → verification) vs timeout: {timeout_s:.1f}s")
        
        # Find all captures in time window
        pattern = os.path.join(capture_dir, "capture_*.jpg")
        all_captures = []
        
        for path in glob.glob(pattern):
            if "_thumbnail" in path:
                continue
            try:
                ts = os.path.getmtime(path)
                if action_timestamp <= ts <= verification_timestamp:
                    all_captures.append({'path': path, 'timestamp': ts})
            except OSError:
                continue
        
        # Sort by timestamp
        all_captures.sort(key=lambda x: x['timestamp'])
        
        if not all_captures:
            return {'success': False, 'error': 'No captures found in time window', 'captures_scanned': 0}
        
        total_captures = len(all_captures)
        saved_ms = request.timeout_ms - window_ms
        saved_s = saved_ms / 1000
        logger.info(f"📸 Found {total_captures} captures in optimized window (saved ~{saved_s:.2f}s of scanning)")
        
        # Convert kpi_references to verification format
        verifications = []
        for kpi_ref in kpi_references:
            verifications.append({
                'verification_type': kpi_ref.get('verification_type', 'image'),
                'command': kpi_ref.get('command', 'waitForImageToAppear'),
                'params': kpi_ref.get('params', {})
            })
        
        # Helper to test a capture
        def test_capture(capture, label):
            logger.info(f"🔍 Quick check - {label}: {os.path.basename(capture['path'])}")
            result = verif_executor.execute_verifications(
                verifications=verifications,
                userinterface_name=request.userinterface_name,  # MANDATORY parameter
                image_source_url=capture['path'],
                team_id=request.team_id
            )
            return result.get('success')
        
        captures_scanned = 0
        
        # PHASE 1: QUICK CHECK (2 checks)
        logger.info(f"⚡ Phase 1: Quick check")
        
        # Quick check 1: T0+200ms
        target_ts = action_timestamp + 0.2
        early_idx = min(range(total_captures), key=lambda i: abs(all_captures[i]['timestamp'] - target_ts))
        captures_scanned += 1
        
        if test_capture(all_captures[early_idx], f"early check (T0+200ms, idx {early_idx}/{total_captures})"):
            return {
                'success': True,
                'timestamp': all_captures[early_idx]['timestamp'],
                'capture_path': all_captures[early_idx]['path'],
                'captures_scanned': captures_scanned,
                'error': None,
                'algorithm': 'quick_check_early'
            }
        
        # Quick check 2: T1-200ms
        target_ts = verification_timestamp - 0.2
        late_idx = min(range(total_captures), key=lambda i: abs(all_captures[i]['timestamp'] - target_ts))
        
        if late_idx != early_idx:
            captures_scanned += 1
            if test_capture(all_captures[late_idx], f"late check (T1-200ms, idx {late_idx}/{total_captures})"):
                return {
                    'success': True,
                    'timestamp': all_captures[late_idx]['timestamp'],
                    'capture_path': all_captures[late_idx]['path'],
                    'captures_scanned': captures_scanned,
                    'error': None,
                    'algorithm': 'quick_check_late'
                }
        
        logger.info(f"⚡ Quick check: no immediate match, proceeding to backward scan")
        
        # PHASE 2: BACKWARD SCAN
        logger.info(f"🔙 Phase 2: Backward scan from verification → action")
        
        checked_indices = {early_idx, late_idx}
        
        for i in range(total_captures - 1, -1, -1):
            if i in checked_indices:
                continue
            
            capture = all_captures[i]
            captures_scanned += 1
            
            logger.info(f"🔍 Backward scan {i+1}/{total_captures}: {os.path.basename(capture['path'])}")
            
            result = verif_executor.execute_verifications(
                verifications=verifications,
                userinterface_name=request.userinterface_name,  # MANDATORY parameter
                image_source_url=capture['path'],
                team_id=request.team_id
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'timestamp': capture['timestamp'],
                    'capture_path': capture['path'],
                    'captures_scanned': captures_scanned,
                    'error': None,
                    'algorithm': 'backward_scan'
                }
        
        # No match found
        return {
            'success': False,
            'timestamp': None,
            'captures_scanned': captures_scanned,
            'error': f'No match found in {total_captures} captures ({window_s:.2f}s window)',
            'algorithm': 'exhaustive_search_failed'
        }
    
    def _update_result(self, execution_result_id: str, team_id: str, success: bool, kpi_ms: int, error: str):
        """Update execution_results with KPI measurement"""
        try:
            from shared.src.lib.supabase.execution_results_db import update_execution_result_with_kpi
            
            result = update_execution_result_with_kpi(
                execution_result_id=execution_result_id,
                team_id=team_id,
                kpi_measurement_success=success,
                kpi_measurement_ms=kpi_ms,
                kpi_measurement_error=error
            )
            
            if result:
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

