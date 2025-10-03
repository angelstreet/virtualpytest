#!/usr/bin/env python3
"""
Backend Discard Service - Main Application

AI-powered false positive detection for alerts and test execution results.
Monitors Redis queues and updates database with AI analysis results.

Priority Processing: P1 (alerts) → P2 (scripts) → P3 (reserved)
AI Models: moonshotai/kimi-k2:free (text), qwen/qwen-2.5-vl-7b-instruct (vision)
"""

import sys
import os
import time
import signal
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_discard_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_discard_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import shared utilities
try:
    from shared.src.lib.utils.app_utils import load_environment_variables
    from shared.src.lib.utils.supabase_utils import get_supabase_client
except ImportError as e:
    print(f"❌ CRITICAL: Cannot import shared utilities: {e}")
    print("   Make sure project structure is correct")
    sys.exit(1)

# Import service components
from queue_processor import SimpleQueueProcessor
from ai_analyzer import SimpleAIAnalyzer, AnalysisResult


class BackendDiscardService:
    """Main service class for backend discard operations"""
    
    def __init__(self):
        self.running = False
        self.queue_processor = None
        self.ai_analyzer = None
        self.supabase = None
        self.stats = {
            'tasks_processed': 0,
            'alerts_processed': 0,
            'scripts_processed': 0,
            'ai_successes': 0,
            'ai_failures': 0,
            'db_updates': 0,
            'alerts_discarded': 0,
            'alerts_validated': 0,
            'scripts_discarded': 0,
            'scripts_validated': 0,
            'started_at': None
        }
    
    def initialize(self) -> bool:
        """Initialize service components"""
        try:
            print("🤖 Backend Discard Service - Initializing...")
            
            # Load environment variables (service-specific + project shared)
            load_environment_variables(mode='discard', calling_script_dir=current_dir)
            
            # Initialize components
            self.queue_processor = SimpleQueueProcessor()
            self.ai_analyzer = SimpleAIAnalyzer()
            self.supabase = get_supabase_client()
            
            if not self.supabase:
                print("❌ Failed to initialize Supabase client")
                return False
            
            # Test Redis connection
            if not self.queue_processor.health_check():
                print("❌ Redis health check failed")
                return False
            
            print("✅ Backend Discard Service initialized successfully")
            print(f"   • Redis: Connected")
            print(f"   • Supabase: Connected")
            print(f"   • AI: OpenRouter ready")
            
            self.stats['started_at'] = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize service: {e}")
            return False
    
    def is_already_checked_by_human(self, task_type: str, task_id: str) -> bool:
        """Check if task has already been checked by human"""
        try:
            table_name = 'alerts' if task_type == 'alert' else 'script_results'
            
            result = self.supabase.table(table_name).select('checked').eq('id', task_id).execute()
            
            if result.data and len(result.data) > 0:
                checked = result.data[0].get('checked', False)
                if checked:
                    print(f"📋 {task_type} {task_id} already checked by human")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking human status for {task_id}: {e}")
            return False
    
    def process_task(self, task: Dict[str, Any]) -> bool:
        """Process a single task from the queue"""
        try:
            task_type = task.get('type')
            task_id = task.get('id')
            task_data = task.get('data', {})
            created_at = task.get('created_at')
            
            print(f"🔄 Processing {task_type} task: {task_id}")
            self.stats['tasks_processed'] += 1
            
            # Check if already checked by human - skip AI processing
            if self.is_already_checked_by_human(task_type, task_id):
                print(f"⏭️ Skipping {task_type} {task_id} - already checked by human")
                return True
            
            # Analyze based on task type
            analysis = None
            if task_type == 'alert':
                analysis = self.ai_analyzer.analyze_alert(task_data)
                self.stats['alerts_processed'] += 1
                
            elif task_type == 'script':
                analysis = self.ai_analyzer.analyze_script_result(task_data)
                self.stats['scripts_processed'] += 1
            
            else:
                print(f"⚠️ Unknown task type: {task_type}")
                return False
            
            # Check AI analysis result
            if not analysis or not analysis.success:
                print(f"❌ AI analysis failed for {task_id}: {analysis.error if analysis else 'Unknown error'}")
                self.stats['ai_failures'] += 1
                return False
            
            print(f"🤖 AI Analysis: discard={analysis.discard}, confidence={analysis.confidence:.2f}, reason='{analysis.explanation}'")
            self.stats['ai_successes'] += 1
            
            # Track discard statistics
            if task_type == 'alert':
                if analysis.discard:
                    self.stats['alerts_discarded'] += 1
                else:
                    self.stats['alerts_validated'] += 1
            elif task_type == 'script':
                if analysis.discard:
                    self.stats['scripts_discarded'] += 1
                else:
                    self.stats['scripts_validated'] += 1
            
            # Update database
            if task_type == 'alert':
                success = self.update_alert(task_id, analysis)
            elif task_type == 'script':
                success = self.update_script_result(task_id, analysis)
            else:
                success = False
            
            if success:
                self.stats['db_updates'] += 1
                status = "✅ SUCCESS"
            else:
                status = "❌ DB UPDATE FAILED"
            
            print(f"{status} - Task {task_id} processed")
            return success
            
        except Exception as e:
            print(f"❌ Error processing task {task_id}: {e}")
            return False
    
    def update_alert(self, alert_id: str, analysis: AnalysisResult) -> bool:
        """Update alert with AI analysis results"""
        try:
            update_data = {
                'checked': True,
                'check_type': 'ai',
                'discard': analysis.discard,

                'discard_comment': analysis.explanation,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('alerts').update(update_data).eq('id', alert_id).execute()
            
            if result.data:
                print(f"📝 Updated alert {alert_id} in database")
                return True
            else:
                print(f"❌ Failed to update alert {alert_id} - not found")
                return False
                
        except Exception as e:
            print(f"❌ Error updating alert {alert_id}: {e}")
            return False
    
    def update_script_result(self, script_id: str, analysis: AnalysisResult) -> bool:
        """Update script result with AI analysis results"""
        try:
            update_data = {
                'checked': True,
                'check_type': 'ai',
                'discard': analysis.discard,

                'discard_comment': analysis.explanation,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('script_results').update(update_data).eq('id', script_id).execute()
            
            if result.data:
                print(f"📝 Updated script result {script_id} in database")
                return True
            else:
                print(f"❌ Failed to update script result {script_id} - not found")
                return False
                
        except Exception as e:
            print(f"❌ Error updating script result {script_id}: {e}")
            return False
    
    def print_stats(self):
        """Print service statistics"""
        uptime = datetime.now(timezone.utc) - self.stats['started_at'] if self.stats['started_at'] else None
        uptime_str = f"{uptime.total_seconds():.0f}s" if uptime else "Unknown"
        
        queue_lengths = self.queue_processor.get_all_queue_lengths()
        
        # Calculate discard rates
        total_alerts = self.stats['alerts_discarded'] + self.stats['alerts_validated']
        total_scripts = self.stats['scripts_discarded'] + self.stats['scripts_validated']
        alert_discard_rate = f"{(self.stats['alerts_discarded']/total_alerts*100):.1f}%" if total_alerts > 0 else "N/A"
        script_discard_rate = f"{(self.stats['scripts_discarded']/total_scripts*100):.1f}%" if total_scripts > 0 else "N/A"
        
        print(f"\n📊 Service Statistics (Uptime: {uptime_str}):")
        print(f"   • Tasks Processed: {self.stats['tasks_processed']}")
        print(f"   • Alerts: {self.stats['alerts_processed']} (🗑️  {self.stats['alerts_discarded']} discarded, ✅ {self.stats['alerts_validated']} valid - {alert_discard_rate} false positive rate)")
        print(f"   • Scripts: {self.stats['scripts_processed']} (🗑️  {self.stats['scripts_discarded']} discarded, ✅ {self.stats['scripts_validated']} valid - {script_discard_rate} false positive rate)")
        print(f"   • AI Analysis: {self.stats['ai_successes']} successful, {self.stats['ai_failures']} failed")
        print(f"   • DB Updates: {self.stats['db_updates']}")
        print(f"   • Queue Lengths: P1={queue_lengths.get('p1_alerts', 0)}, P2={queue_lengths.get('p2_scripts', 0)}, P3={queue_lengths.get('p3_reserved', 0)}")
    
    def _start_health_server(self, port):
        """Start HTTP health check server in background thread"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        class HealthHandler(BaseHTTPRequestHandler):
            def __init__(self, service_instance, *args, **kwargs):
                self.service = service_instance
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                if self.path == '/health':
                    is_healthy = self.service.queue_processor.health_check() if self.service.queue_processor else False
                    status_code = 200 if is_healthy else 500
                    # Make stats JSON serializable
                    stats = {}
                    if hasattr(self.service, 'stats') and self.service.stats:
                        stats = {k: (v.isoformat() if isinstance(v, datetime) else v) 
                                for k, v in self.service.stats.items()}
                    
                    # Get queue details
                    queue_lengths = self.service.queue_processor.get_all_queue_lengths() if self.service.queue_processor else {}
                    
                    response = {
                        'status': 'healthy' if is_healthy else 'unhealthy',
                        'service': 'backend_discard',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'stats': stats,
                        'queues': {
                            'incidents': {
                                'name': 'p1_alerts',
                                'length': queue_lengths.get('p1_alerts', 0),
                                'processed': stats.get('alerts_processed', 0),
                                'discarded': stats.get('alerts_discarded', 0),
                                'validated': stats.get('alerts_validated', 0)
                            },
                            'scripts': {
                                'name': 'p2_scripts', 
                                'length': queue_lengths.get('p2_scripts', 0),
                                'processed': stats.get('scripts_processed', 0),
                                'discarded': stats.get('scripts_discarded', 0),
                                'validated': stats.get('scripts_validated', 0)
                            }
                        }
                    }
                    
                    self.send_response(status_code)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress HTTP server logs
                pass
        
        def create_handler(*args, **kwargs):
            return HealthHandler(self, *args, **kwargs)
        
        def start_server():
            try:
                server = HTTPServer(('localhost', port), create_handler)
                print(f"✅ Health server started on port {port}")
                server.serve_forever()
            except Exception as e:
                print(f"❌ Could not start health server on port {port}: {e}")
        
        health_thread = threading.Thread(target=start_server, daemon=True)
        health_thread.start()
        return health_thread
    
    def run(self):
        """Main service loop with efficient BLPOP"""
        self.running = True
        # Get configuration and log startup details
        service_port = int(os.getenv('SERVER_PORT', '6209'))
        debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
        
        print(f"🚀 Backend Discard Service started (BLPOP mode - efficient!)")
        print(f"   Service Port: {service_port}")
        print(f"   Debug Mode: {debug_mode}")
        print(f"   Processing priority: P1 (alerts) → P2 (scripts) → P3 (reserved)")
        print(f"   Health endpoint: http://localhost:{service_port}/health")
        print(f"   ⚡ Using BLPOP for instant task retrieval (no polling overhead)")
        
        # Show initial queue lengths
        initial_queue_lengths = self.queue_processor.get_all_queue_lengths()
        print(f"📊 Initial queue lengths: P1={initial_queue_lengths.get('p1_alerts', 0)}, P2={initial_queue_lengths.get('p2_scripts', 0)}, P3={initial_queue_lengths.get('p3_reserved', 0)}")
        
        # Start health check server in background thread
        health_server = self._start_health_server(service_port)
        
        last_stats_time = time.time()
        stats_interval = 60 if debug_mode else 300  # Print stats every 1 minute in debug, 5 minutes in production
        blpop_timeout = 60  # BLPOP waits up to 60 seconds for tasks
        
        while self.running:
            try:
                # Use BLPOP to efficiently wait for tasks (blocks until task arrives or timeout)
                # No need to poll or sleep - Redis does the waiting for us!
                task = self.queue_processor.get_next_task_blocking(timeout=blpop_timeout)
                
                if task:
                    # Task arrived - process it immediately
                    queue_lengths_before = self.queue_processor.get_all_queue_lengths()
                    print(f"📊 Queue lengths before processing: P1={queue_lengths_before.get('p1_alerts', 0)}, P2={queue_lengths_before.get('p2_scripts', 0)}, P3={queue_lengths_before.get('p3_reserved', 0)}")
                    
                    self.process_task(task)
                    
                    # Show queue lengths after processing
                    queue_lengths_after = self.queue_processor.get_all_queue_lengths()
                    print(f"📊 Queue lengths after processing: P1={queue_lengths_after.get('p1_alerts', 0)}, P2={queue_lengths_after.get('p2_scripts', 0)}, P3={queue_lengths_after.get('p3_reserved', 0)}")
                else:
                    # BLPOP timeout (no tasks for 60 seconds) - this is normal
                    queue_lengths = self.queue_processor.get_all_queue_lengths()
                    print(f"📊 [IDLE] No tasks for {blpop_timeout}s: P1={queue_lengths.get('p1_alerts', 0)}, P2={queue_lengths.get('p2_scripts', 0)}, P3={queue_lengths.get('p3_reserved', 0)}")
                
                # Print full stats periodically
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    self.print_stats()
                    last_stats_time = current_time
                    
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(5)
        
        print("🛑 Backend Discard Service stopped")
        self.print_stats()
    
    def stop(self):
        """Stop the service gracefully"""
        print("🛑 Stopping Backend Discard Service...")
        self.running = False


# Global service instance
service = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global service
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    if service:
        service.stop()

def health_check() -> bool:
    """Simple health check"""
    try:
        # Check if service is initialized and running
        if service and service.queue_processor:
            return service.queue_processor.health_check()
        return False
    except Exception:
        return False

def main():
    """Main function"""
    global service
    
    print("🤖 VIRTUALPYTEST Backend Discard Service")
    print("AI-powered false positive detection")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and initialize service
    service = BackendDiscardService()
    
    if not service.initialize():
        print("❌ Service initialization failed")
        sys.exit(1)
    
    # Start service
    try:
        service.run()
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"❌ Service error: {e}")
        sys.exit(1)
    finally:
        if service:
            service.stop()

if __name__ == '__main__':
    main()
