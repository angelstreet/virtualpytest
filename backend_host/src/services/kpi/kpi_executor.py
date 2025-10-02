#!/usr/bin/env python3
"""
KPI Measurement Executor Service

Measures actual time from navigation action to visual confirmation (node's KPI reference appearing).
Runs as background service, processes queued measurement requests by scanning through 5 FPS FFmpeg captures.

Architecture:
- NavigationExecutor queues KPI measurements after each successful navigation step
- Background worker processes queue and scans captures
- Stops immediately when match found (minimal scanning)
- Updates execution_results with KPI timing
- No fallbacks - fail early if required data missing
"""

import os
import time
import glob
import queue
import threading
from typing import Dict, List, Optional, Any


class KPIMeasurementRequest:
    """
    KPI measurement request - all data required, no defaults, fail early
    """
    def __init__(
        self,
        execution_result_id: str,
        team_id: str,
        capture_dir: str,
        action_timestamp: float,
        verification_timestamp: float,
        kpi_references: List[Dict[str, Any]],
        timeout_ms: int,
        device_id: str,
        device_model: str = None,
        **kwargs
    ):
        # Validate required fields - fail early
        if not execution_result_id:
            raise ValueError("execution_result_id required")
        if not team_id:
            raise ValueError("team_id required")
        if not capture_dir:
            raise ValueError("capture_dir required")
        if not os.path.exists(capture_dir):
            raise ValueError(f"capture_dir does not exist: {capture_dir}")
        if not kpi_references:
            raise ValueError("kpi_references required")
        if timeout_ms <= 0:
            raise ValueError(f"timeout_ms must be > 0, got {timeout_ms}")
        if not device_id:
            raise ValueError("device_id required")
        if not verification_timestamp:
            raise ValueError("verification_timestamp required")
        if verification_timestamp < action_timestamp:
            raise ValueError(f"verification_timestamp ({verification_timestamp}) must be >= action_timestamp ({action_timestamp})")
        
        self.execution_result_id = execution_result_id
        self.team_id = team_id
        self.capture_dir = capture_dir
        self.action_timestamp = action_timestamp
        self.verification_timestamp = verification_timestamp
        self.kpi_references = kpi_references
        self.timeout_ms = timeout_ms
        self.device_id = device_id
        self.device_model = device_model
        self.kpi_timestamp = kwargs.get('kpi_timestamp')  # Pre-calculated KPI timestamp from verification


class KPIExecutor:
    """
    Background KPI measurement executor (singleton)
    
    Processes KPI measurement requests in background thread.
    Scans 5 FPS captures to find when KPI reference appears.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize KPI executor"""
        # Skip if already initialized
        if hasattr(self, 'queue'):
            return
        
        self.queue = queue.Queue(maxsize=1000)
        self.running = False
        self.worker_thread = None
        print("🔧 [KPIExecutor] Initialized (queue capacity: 1000)")
    
    def start(self):
        """Start background worker thread"""
        import sys
        with self._lock:  # Thread-safe start
            if self.running:
                print("⚠️ [KPIExecutor] Already running", flush=True)
                sys.stdout.flush()
                return
            
            self.running = True
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="KPI-Worker"
            )
            self.worker_thread.start()
            print(f"✅ [KPIExecutor] Worker thread started (thread_id: {self.worker_thread.ident})", flush=True)
            sys.stdout.flush()
    
    def stop(self):
        """Stop background worker thread"""
        if not self.running:
            return
        
        print("🛑 [KPIExecutor] Stopping worker thread...")
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("✅ [KPIExecutor] Worker thread stopped")
    
    def enqueue_measurement(self, request: KPIMeasurementRequest) -> bool:
        """
        Add measurement request to queue
        
        Returns:
            True if enqueued successfully, False if queue full
        """
        import sys
        try:
            self.queue.put(request, block=False)
            thread_alive = self.worker_thread.is_alive() if self.worker_thread else False
            print(f"📋 [KPIExecutor] Queued KPI measurement (queue size: {self.queue.qsize()}, worker running: {self.running}, thread alive: {thread_alive})", flush=True)
            sys.stdout.flush()
            return True
        except queue.Full:
            print("❌ [KPIExecutor] Queue full! Dropping KPI measurement request", flush=True)
            sys.stdout.flush()
            return False
    
    def _worker_loop(self):
        """Background worker loop that processes measurement requests"""
        import sys
        print("🔄 [KPIExecutor] Worker loop started", flush=True)
        sys.stdout.flush()
        
        iteration = 0
        while self.running:
            try:
                # Wait for measurement request with timeout (allows clean shutdown)
                try:
                    request = self.queue.get(timeout=1.0)
                except queue.Empty:
                    # Periodic heartbeat every 30 iterations (~30 seconds)
                    iteration += 1
                    if iteration % 30 == 0:
                        print(f"💓 [KPIExecutor] Worker heartbeat (queue size: {self.queue.qsize()})", flush=True)
                        sys.stdout.flush()
                    continue
                
                # Got an item from queue - log IMMEDIATELY with explicit flush
                print(f"📥 [KPIExecutor] Worker dequeued item (type: {type(request).__name__})", flush=True)
                sys.stdout.flush()
                
                # Validate request object
                if not isinstance(request, KPIMeasurementRequest):
                    print(f"❌ [KPIExecutor] Invalid request type: {type(request)}", flush=True)
                    sys.stdout.flush()
                    self.queue.task_done()
                    continue
                
                # Process measurement request
                try:
                    print(f"🎬 [KPIExecutor] Starting processing for execution_result_id: {request.execution_result_id[:8]}", flush=True)
                    sys.stdout.flush()
                    self._process_measurement(request)
                    print(f"🏁 [KPIExecutor] Finished processing", flush=True)
                    sys.stdout.flush()
                except Exception as e:
                    print(f"❌ [KPIExecutor] Error processing measurement: {e}", flush=True)
                    sys.stdout.flush()
                    import traceback
                    traceback.print_exc()
                finally:
                    self.queue.task_done()
                    
            except Exception as e:
                print(f"❌ [KPIExecutor] Worker loop error: {e}", flush=True)
                sys.stdout.flush()
                import traceback
                traceback.print_exc()
                time.sleep(1)  # Prevent tight loop on errors
        
        print("🛑 [KPIExecutor] Worker loop exited", flush=True)
        sys.stdout.flush()
    
    def _process_measurement(self, request: KPIMeasurementRequest):
        """
        Process single KPI measurement request
        
        Scans captures from action_timestamp until match or timeout.
        Stops immediately when match found.
        """
        print("🔍 [KPIExecutor] Processing KPI measurement")
        print(f"   • Execution result: {request.execution_result_id[:8]}")
        
        # Check if KPI already calculated during verification (timeout polling found exact match)
        if request.kpi_timestamp:
            kpi_ms = int((request.kpi_timestamp - request.action_timestamp) * 1000)
            print(f"⚡ [KPIExecutor] KPI already calculated during verification: {kpi_ms}ms")
            print(f"   • Skipping post-processing scan (match found during timeout polling)")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
            return
        
        print(f"   • Action timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        print(f"   • Timeout: {request.timeout_ms}ms ({request.timeout_ms / 1000:.1f}s)")
        print(f"   • KPI references: {len(request.kpi_references)}")
        
        start_time = time.time()
        
        # Scan captures - stops at first match or timeout
        match_result = self._scan_until_match(request)
        
        # Store result
        if match_result['success']:
            kpi_ms = int((match_result['timestamp'] - request.action_timestamp) * 1000)
            algorithm = match_result.get('algorithm', 'unknown')
            print(f"✅ [KPIExecutor] KPI match found!")
            print(f"   • KPI duration: {kpi_ms}ms")
            print(f"   • Algorithm: {algorithm}")
            print(f"   • Captures scanned: {match_result['captures_scanned']}")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
        else:
            algorithm = match_result.get('algorithm', 'unknown')
            print(f"❌ [KPIExecutor] KPI measurement failed: {match_result['error']}")
            print(f"   • Algorithm: {algorithm}")
            print(f"   • Captures scanned: {match_result.get('captures_scanned', 0)}")
            self._update_result(request.execution_result_id, request.team_id, False, None, match_result['error'])
        
        processing_time = int((time.time() - start_time) * 1000)
        print(f"⏱️ [KPIExecutor] Processing completed in {processing_time}ms")
    
    def _scan_until_match(self, request: KPIMeasurementRequest) -> Dict[str, Any]:
        """
        Scan captures using optimized quick check + backward scan algorithm.
        
        Algorithm:
        1. Quick Check: Test T0+200ms and T1-200ms (80% hit rate)
        2. Backward Scan: If not found, scan from T1 backward to T0
        
        Uses device's existing verification_executor - zero code duplication!
        
        Args:
            request: KPI measurement request with all required data
        
        Returns:
            Dict with success, timestamp, captures_scanned, error
        """
        # Extract parameters from request for clarity
        capture_dir = request.capture_dir
        action_timestamp = request.action_timestamp
        verification_timestamp = request.verification_timestamp
        kpi_references = request.kpi_references
        
        # Get device instance from host (same host, same device, just post-processing)
        from backend_host.src.lib.utils.host_utils import get_device_by_id
        
        device = get_device_by_id(request.device_id)
        if not device:
            return {'success': False, 'error': f'Device {request.device_id} not found on host', 'captures_scanned': 0}
        
        # Use device's existing verification_executor (already has all controllers initialized)
        verif_executor = device.verification_executor
        if not verif_executor:
            return {'success': False, 'error': f'No verification_executor for device {request.device_id}', 'captures_scanned': 0}
        
        # Calculate optimized time window using verification timestamp (NOT timeout!)
        # We know KPI appeared by verification_timestamp, so no need to scan beyond it
        window_ms = int((verification_timestamp - action_timestamp) * 1000)
        timeout_s = request.timeout_ms / 1000
        window_s = window_ms / 1000
        print(f"🎯 [KPIExecutor] Optimized scan window: {window_s:.2f}s (action → verification) vs timeout: {timeout_s:.1f}s")
        
        # Find all captures in optimized time window
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
        
        # Sort by timestamp (oldest first for index-based access)
        all_captures.sort(key=lambda x: x['timestamp'])
        
        if not all_captures:
            return {'success': False, 'error': 'No captures found in time window', 'captures_scanned': 0}
        
        total_captures = len(all_captures)
        saved_ms = request.timeout_ms - window_ms
        saved_s = saved_ms / 1000
        print(f"📸 [KPIExecutor] Found {total_captures} captures in optimized window (saved ~{saved_s:.2f}s of scanning)")
        
        # Convert kpi_references to verification format (same structure as navigation)
        verifications = []
        for kpi_ref in kpi_references:
            verifications.append({
                'verification_type': kpi_ref.get('verification_type', 'image'),
                'command': kpi_ref.get('command', 'waitForImageToAppear'),
                'params': kpi_ref.get('params', {})
            })
        
        # Helper function to test a capture
        def test_capture(capture, label):
            print(f"🔍 [KPIExecutor] Quick check - {label}: {os.path.basename(capture['path'])}")
            result = verif_executor.execute_verifications(
                verifications=verifications,
                image_source_url=capture['path'],
                team_id=request.team_id
            )
            return result.get('success')
        
        captures_scanned = 0
        
        # ========================================
        # PHASE 1: QUICK CHECK (2 checks)
        # ========================================
        print(f"⚡ [KPIExecutor] Phase 1: Quick check")
        
        # Quick check 1: T0+200ms (immediate appearance)
        # Find capture closest to action_timestamp + 200ms
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
        
        # Quick check 2: T1-200ms (late appearance)
        # Find capture closest to verification_timestamp - 200ms
        target_ts = verification_timestamp - 0.2
        late_idx = min(range(total_captures), key=lambda i: abs(all_captures[i]['timestamp'] - target_ts))
        
        # Only test if different from early check
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
        
        print(f"⚡ [KPIExecutor] Quick check: no immediate match, proceeding to backward scan")
        
        # ========================================
        # PHASE 2: BACKWARD SCAN
        # ========================================
        print(f"🔙 [KPIExecutor] Phase 2: Backward scan from verification → action")
        
        # Scan backward from verification_timestamp to action_timestamp
        # Start from late_idx and go backward (skip captures already checked)
        checked_indices = {early_idx, late_idx}
        
        for i in range(total_captures - 1, -1, -1):
            if i in checked_indices:
                continue
            
            capture = all_captures[i]
            captures_scanned += 1
            
            print(f"🔍 [KPIExecutor] Backward scan {i+1}/{total_captures}: {os.path.basename(capture['path'])}")
            
            result = verif_executor.execute_verifications(
                verifications=verifications,
                image_source_url=capture['path'],
                team_id=request.team_id
            )
            
            # MATCH FOUND - this is the earliest appearance
            if result.get('success'):
                return {
                    'success': True,
                    'timestamp': capture['timestamp'],
                    'capture_path': capture['path'],
                    'captures_scanned': captures_scanned,
                    'error': None,
                    'algorithm': 'backward_scan'
                }
        
        # No match found after quick check + backward scan
        return {
            'success': False,
            'timestamp': None,
            'captures_scanned': captures_scanned,
            'error': f'No match found in {total_captures} captures ({window_s:.2f}s window)',
            'algorithm': 'exhaustive_search_failed'
        }
    
    def _update_result(
        self,
        execution_result_id: str,
        team_id: str,
        success: bool,
        kpi_ms: Optional[int],
        error: Optional[str]
    ):
        """
        Update execution_results with KPI measurement result using shared database function
        """
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
                print(f"💾 [KPIExecutor] Stored KPI result: {kpi_ms}ms (success: {success})")
            else:
                print(f"⚠️ [KPIExecutor] Failed to update execution_result_id: {execution_result_id[:8]}")
                
        except Exception as e:
            print(f"❌ [KPIExecutor] Error storing KPI result: {e}")
            import traceback
            traceback.print_exc()


# Module-level function to get service instance
def get_kpi_executor() -> KPIExecutor:
    """Get singleton KPI executor instance"""
    return KPIExecutor.get_instance()
