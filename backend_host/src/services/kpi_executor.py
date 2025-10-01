"""
KPI Measurement Executor

Measures actual time from navigation action to visual confirmation (node's KPI reference appearing).
Runs as background thread, processes queued measurement requests by scanning backward through
5 FPS FFmpeg captures.

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
        timeout_ms: int
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
        
        self.execution_result_id = execution_result_id
        self.team_id = team_id
        self.capture_dir = capture_dir
        self.action_timestamp = action_timestamp
        self.kpi_references = kpi_references
        self.timeout_ms = timeout_ms


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
        if KPIExecutor._instance is not None:
            raise RuntimeError("KPIExecutor is singleton. Use get_instance()")
        
        self.queue = queue.Queue(maxsize=1000)
        self.running = False
        self.worker_thread = None
        print(f"🔧 [KPIExecutor] Initialized (queue capacity: 1000)")
    
    def start(self):
        """Start background worker thread"""
        if self.running:
            print(f"⚠️ [KPIExecutor] Already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="KPI-Worker"
        )
        self.worker_thread.start()
        print(f"✅ [KPIExecutor] Worker thread started")
    
    def stop(self):
        """Stop background worker thread"""
        if not self.running:
            return
        
        print(f"🛑 [KPIExecutor] Stopping worker thread...")
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print(f"✅ [KPIExecutor] Worker thread stopped")
    
    def enqueue_measurement(self, request: KPIMeasurementRequest) -> bool:
        """
        Add measurement request to queue
        
        Returns:
            True if enqueued successfully, False if queue full
        """
        try:
            self.queue.put(request, block=False)
            print(f"📋 [KPIExecutor] Queued KPI measurement (queue size: {self.queue.qsize()})")
            return True
        except queue.Full:
            print(f"❌ [KPIExecutor] Queue full! Dropping KPI measurement request")
            return False
    
    def _worker_loop(self):
        """Background worker loop that processes measurement requests"""
        print(f"🔄 [KPIExecutor] Worker loop started")
        
        while self.running:
            try:
                # Wait for measurement request with timeout (allows clean shutdown)
                try:
                    request = self.queue.get(timeout=1.0)
                except queue.Empty:
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
                time.sleep(1)  # Prevent tight loop on errors
        
        print(f"🛑 [KPIExecutor] Worker loop exited")
    
    def _process_measurement(self, request: KPIMeasurementRequest):
        """
        Process single KPI measurement request
        
        Scans captures from action_timestamp until match or timeout.
        Stops immediately when match found.
        """
        print(f"🔍 [KPIExecutor] Processing KPI measurement")
        print(f"   • Execution result: {request.execution_result_id[:8]}")
        print(f"   • Action timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        print(f"   • Timeout: {request.timeout_ms}ms")
        print(f"   • KPI references: {len(request.kpi_references)}")
        
        start_time = time.time()
        
        # Scan captures - stops at first match or timeout
        match_result = self._scan_until_match(
            capture_dir=request.capture_dir,
            action_timestamp=request.action_timestamp,
            timeout_ms=request.timeout_ms,
            kpi_references=request.kpi_references
        )
        
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
    
    def _scan_until_match(
        self,
        capture_dir: str,
        action_timestamp: float,
        timeout_ms: int,
        kpi_references: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Scan captures from action_timestamp until match or timeout.
        Stops immediately when match found - minimal scanning.
        
        Returns:
            Dict with success, timestamp, captures_scanned, error
        """
        from backend_host.src.controllers.verification.image_verification_controller import ImageVerificationController
        from backend_host.src.controllers.verification.text_verification_controller import TextVerificationController
        
        # Create verification controllers (lightweight, no device needed)
        image_ctrl = ImageVerificationController(None)
        text_ctrl = TextVerificationController(None)
        
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
        
        # Scan captures sequentially - STOP at first match
        for i, capture in enumerate(all_captures):
            all_refs_match = True
            
            for kpi_ref in kpi_references:
                verification_type = kpi_ref.get('verification_type', 'image')
                
                try:
                    if verification_type == 'image':
                        result = image_ctrl.execute_verification(kpi_ref, image_source_url=capture['path'])
                    elif verification_type in ['text', 'ocr']:
                        result = text_ctrl.execute_verification(kpi_ref, image_source_url=capture['path'])
                    else:
                        print(f"⚠️ [KPIExecutor] Unsupported verification type: {verification_type}")
                        all_refs_match = False
                        break
                    
                    if not result.get('success'):
                        all_refs_match = False
                        break
                        
                except Exception as e:
                    print(f"⚠️ [KPIExecutor] Verification execution error: {e}")
                    all_refs_match = False
                    break
            
            # MATCH FOUND - stop immediately
            if all_refs_match:
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
        Update execution_results with KPI measurement result
        """
        try:
            from shared.src.lib.supabase.client import get_supabase
            supabase = get_supabase()
            
            update_data = {
                'kpi_measurement_success': success,
                'kpi_measurement_ms': kpi_ms,
                'kpi_measurement_error': error
            }
            
            result = supabase.table('execution_results').update(update_data).eq(
                'id', execution_result_id
            ).eq('team_id', team_id).execute()
            
            if result.data:
                print(f"💾 [KPIExecutor] Stored KPI result: {kpi_ms}ms (success: {success})")
            else:
                print(f"⚠️ [KPIExecutor] No record updated for execution_result_id: {execution_result_id[:8]}")
                
        except Exception as e:
            print(f"❌ [KPIExecutor] Error storing KPI result: {e}")
            import traceback
            traceback.print_exc()


# Module-level function to get service instance
def get_kpi_executor() -> KPIExecutor:
    """Get singleton KPI executor instance"""
    return KPIExecutor.get_instance()

