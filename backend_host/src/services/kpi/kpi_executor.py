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
        kpi_references: List[Dict[str, Any]],
        timeout_ms: int,
        device_id: str,
        device_model: str = None
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
        
        self.execution_result_id = execution_result_id
        self.team_id = team_id
        self.capture_dir = capture_dir
        self.action_timestamp = action_timestamp
        self.kpi_references = kpi_references
        self.timeout_ms = timeout_ms
        self.device_id = device_id
        self.device_model = device_model


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
        if self.running:
            print("⚠️ [KPIExecutor] Already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="KPI-Worker"
        )
        self.worker_thread.start()
        print("✅ [KPIExecutor] Worker thread started")
    
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
        try:
            self.queue.put(request, block=False)
            print(f"📋 [KPIExecutor] Queued KPI measurement (queue size: {self.queue.qsize()}, worker running: {self.running})")
            return True
        except queue.Full:
            print("❌ [KPIExecutor] Queue full! Dropping KPI measurement request")
            return False
    
    def _worker_loop(self):
        """Background worker loop that processes measurement requests"""
        print("🔄 [KPIExecutor] Worker loop started")
        
        iteration = 0
        while self.running:
            try:
                # Wait for measurement request with timeout (allows clean shutdown)
                try:
                    request = self.queue.get(timeout=1.0)
                    print(f"📥 [KPIExecutor] Worker received KPI request from queue")
                except queue.Empty:
                    # Periodic heartbeat every 30 iterations (~30 seconds)
                    iteration += 1
                    if iteration % 30 == 0:
                        print(f"💓 [KPIExecutor] Worker heartbeat (queue size: {self.queue.qsize()})")
                    continue
                
                # Process measurement request
                try:
                    self._process_measurement(request)
                except Exception as e:
                    print(f"❌ [KPIExecutor] Error processing measurement: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.queue.task_done()
                    
            except Exception as e:
                print(f"❌ [KPIExecutor] Worker loop error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)  # Prevent tight loop on errors
        
        print("🛑 [KPIExecutor] Worker loop exited")
    
    def _process_measurement(self, request: KPIMeasurementRequest):
        """
        Process single KPI measurement request
        
        Scans captures from action_timestamp until match or timeout.
        Stops immediately when match found.
        """
        print("🔍 [KPIExecutor] Processing KPI measurement")
        print(f"   • Execution result: {request.execution_result_id[:8]}")
        print(f"   • Action timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        print(f"   • Timeout: {request.timeout_ms}ms")
        print(f"   • KPI references: {len(request.kpi_references)}")
        
        start_time = time.time()
        
        # Scan captures - stops at first match or timeout
        match_result = self._scan_until_match(request)
        
        # Store result
        if match_result['success']:
            kpi_ms = int((match_result['timestamp'] - request.action_timestamp) * 1000)
            print(f"✅ [KPIExecutor] KPI match found!")
            print(f"   • KPI duration: {kpi_ms}ms")
            print(f"   • Captures scanned: {match_result['captures_scanned']}")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
        else:
            print(f"❌ [KPIExecutor] KPI measurement failed: {match_result['error']}")
            print(f"   • Captures scanned: {match_result.get('captures_scanned', 0)}")
            self._update_result(request.execution_result_id, request.team_id, False, None, match_result['error'])
        
        processing_time = int((time.time() - start_time) * 1000)
        print(f"⏱️ [KPIExecutor] Processing completed in {processing_time}ms")
    
    def _scan_until_match(self, request: KPIMeasurementRequest) -> Dict[str, Any]:
        """
        Scan captures from action_timestamp until match or timeout.
        Stops immediately when match found - minimal scanning.
        
        Uses device's existing verification_executor - zero code duplication!
        
        Args:
            request: KPI measurement request with all required data
        
        Returns:
            Dict with success, timestamp, captures_scanned, error
        """
        # Extract parameters from request for clarity
        capture_dir = request.capture_dir
        action_timestamp = request.action_timestamp
        timeout_ms = request.timeout_ms
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
        
        # Calculate time window
        end_timestamp = action_timestamp + (timeout_ms / 1000.0)
        
        # Find all captures in time window
        pattern = os.path.join(capture_dir, "capture_*.jpg")
        all_captures = []
        
        for path in glob.glob(pattern):
            if "_thumbnail" in path:
                continue
            try:
                ts = os.path.getmtime(path)
                if action_timestamp <= ts <= end_timestamp:
                    all_captures.append({'path': path, 'timestamp': ts})
            except OSError:
                continue
        
        # Sort by timestamp (oldest first - scan forward from action time)
        all_captures.sort(key=lambda x: x['timestamp'])
        
        if not all_captures:
            return {'success': False, 'error': 'No captures found in time window', 'captures_scanned': 0}
        
        print(f"📸 [KPIExecutor] Found {len(all_captures)} captures in time window")
        
        # Convert kpi_references to verification format (same structure as navigation)
        verifications = []
        for kpi_ref in kpi_references:
            verifications.append({
                'verification_type': kpi_ref.get('verification_type', 'image'),
                'command': kpi_ref.get('command', 'waitForImageToAppear'),
                'params': kpi_ref.get('params', {})
            })
        
        # Scan captures sequentially - STOP at first match
        for i, capture in enumerate(all_captures):
            print(f"🔍 [KPIExecutor] Testing capture {i+1}/{len(all_captures)}: {os.path.basename(capture['path'])}")
            
            # Execute verifications using device's verification_executor
            # This gives us the SAME detailed logs as normal navigation verification!
            result = verif_executor.execute_verifications(
                verifications=verifications,
                image_source_url=capture['path'],  # Use this specific capture
                team_id=request.team_id
            )
            
            # MATCH FOUND - stop immediately
            if result.get('success'):
                return {
                    'success': True,
                    'timestamp': capture['timestamp'],
                    'capture_path': capture['path'],
                    'captures_scanned': i + 1,
                    'error': None
                }
        
        # No match found after scanning all captures
        return {
            'success': False,
            'timestamp': None,
            'captures_scanned': len(all_captures),
            'error': f'No match found in {len(all_captures)} captures (timeout {timeout_ms}ms)'
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
