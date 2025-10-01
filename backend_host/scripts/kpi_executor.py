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
import sys
import time
import glob
import queue
import signal
import logging
import threading
from typing import Dict, List, Optional, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/kpi_executor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
        
        self.execution_result_id = execution_result_id
        self.team_id = team_id
        self.capture_dir = capture_dir
        self.action_timestamp = action_timestamp
        self.kpi_references = kpi_references
        self.timeout_ms = timeout_ms
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
        if KPIExecutor._instance is not None:
            raise RuntimeError("KPIExecutor is singleton. Use get_instance()")
        
        self.queue = queue.Queue(maxsize=1000)
        self.running = False
        self.worker_thread = None
        logger.info("🔧 [KPIExecutor] Initialized (queue capacity: 1000)")
    
    def start(self):
        """Start background worker thread"""
        if self.running:
            logger.warning("⚠️ [KPIExecutor] Already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="KPI-Worker"
        )
        self.worker_thread.start()
        logger.info("✅ [KPIExecutor] Worker thread started")
    
    def stop(self):
        """Stop background worker thread"""
        if not self.running:
            return
        
        logger.info("🛑 [KPIExecutor] Stopping worker thread...")
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("✅ [KPIExecutor] Worker thread stopped")
    
    def enqueue_measurement(self, request: KPIMeasurementRequest) -> bool:
        """
        Add measurement request to queue
        
        Returns:
            True if enqueued successfully, False if queue full
        """
        try:
            self.queue.put(request, block=False)
            logger.info(f"📋 [KPIExecutor] Queued KPI measurement (queue size: {self.queue.qsize()})")
            return True
        except queue.Full:
            logger.error("❌ [KPIExecutor] Queue full! Dropping KPI measurement request")
            return False
    
    def _worker_loop(self):
        """Background worker loop that processes measurement requests"""
        logger.info("🔄 [KPIExecutor] Worker loop started")
        
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
                    logger.error(f"❌ [KPIExecutor] Error processing measurement: {e}", exc_info=True)
                finally:
                    self.queue.task_done()
                    
            except Exception as e:
                logger.error(f"❌ [KPIExecutor] Worker loop error: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight loop on errors
        
        logger.info("🛑 [KPIExecutor] Worker loop exited")
    
    def _process_measurement(self, request: KPIMeasurementRequest):
        """
        Process single KPI measurement request
        
        Scans captures from action_timestamp until match or timeout.
        Stops immediately when match found.
        """
        logger.info("🔍 [KPIExecutor] Processing KPI measurement")
        logger.info(f"   • Execution result: {request.execution_result_id[:8]}")
        logger.info(f"   • Action timestamp: {time.strftime('%H:%M:%S', time.localtime(request.action_timestamp))}")
        logger.info(f"   • Timeout: {request.timeout_ms}ms")
        logger.info(f"   • KPI references: {len(request.kpi_references)}")
        
        start_time = time.time()
        
        # Scan captures - stops at first match or timeout
        match_result = self._scan_until_match(request)
        
        # Store result
        if match_result['success']:
            kpi_ms = int((match_result['timestamp'] - request.action_timestamp) * 1000)
            logger.info(f"✅ [KPIExecutor] KPI match found!")
            logger.info(f"   • KPI duration: {kpi_ms}ms")
            logger.info(f"   • Captures scanned: {match_result['captures_scanned']}")
            self._update_result(request.execution_result_id, request.team_id, True, kpi_ms, None)
        else:
            logger.error(f"❌ [KPIExecutor] KPI measurement failed: {match_result['error']}")
            logger.info(f"   • Captures scanned: {match_result.get('captures_scanned', 0)}")
            self._update_result(request.execution_result_id, request.team_id, False, None, match_result['error'])
        
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ [KPIExecutor] Processing completed in {processing_time}ms")
    
    def _scan_until_match(self, request: KPIMeasurementRequest) -> Dict[str, Any]:
        """
        Scan captures from action_timestamp until match or timeout.
        Stops immediately when match found - minimal scanning.
        
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
        from backend_host.src.controllers.verification.image import ImageVerificationController
        from backend_host.src.controllers.verification.text import TextVerificationController
        
        # Create verification controllers in offline mode (no device needed)
        image_ctrl = ImageVerificationController(captures_path=capture_dir, device_model=request.device_model)
        text_ctrl = TextVerificationController(captures_path=capture_dir, device_model=request.device_model)
        
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
        
        logger.info(f"📸 [KPIExecutor] Found {len(all_captures)} captures in time window")
        
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
                        logger.warning(f"⚠️ [KPIExecutor] Unsupported verification type: {verification_type}")
                        all_refs_match = False
                        break
                    
                    if not result.get('success'):
                        all_refs_match = False
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ [KPIExecutor] Verification execution error: {e}")
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
                logger.info(f"💾 [KPIExecutor] Stored KPI result: {kpi_ms}ms (success: {success})")
            else:
                logger.warning(f"⚠️ [KPIExecutor] No record updated for execution_result_id: {execution_result_id[:8]}")
                
        except Exception as e:
            logger.error(f"❌ [KPIExecutor] Error storing KPI result: {e}", exc_info=True)


# Module-level function to get service instance
def get_kpi_executor() -> KPIExecutor:
    """Get singleton KPI executor instance"""
    return KPIExecutor.get_instance()


def main():
    """Main service loop"""
    logger.info("🚀 [KPIExecutor Service] Starting KPI Executor Service")
    
    # Get singleton instance and start worker
    executor = get_kpi_executor()
    executor.start()
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"🛑 [KPIExecutor Service] Received signal {signum}, shutting down...")
        executor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("✅ [KPIExecutor Service] Service running, waiting for KPI measurement requests...")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 [KPIExecutor Service] Keyboard interrupt received")
        executor.stop()


if __name__ == '__main__':
    main()

