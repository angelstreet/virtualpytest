"""Deployment Scheduler - Manages periodic script execution"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.src.lib.supabase.client import get_supabase_client
from shared.src.lib.executors.script_executor import ScriptExecutor
import time

class DeploymentScheduler:
    def __init__(self, host_name):
        self.host_name = host_name
        self.scheduler = BackgroundScheduler()
        self.supabase = get_supabase_client()
        
    def start(self):
        """Start scheduler and sync from DB"""
        print(f"[@deployment_scheduler] Starting for {self.host_name}")
        self.scheduler.start()
        self._sync_from_db()
        
    def _sync_from_db(self):
        """Load active deployments from Supabase on startup"""
        try:
            result = self.supabase.table('deployments').select('*').eq('host_name', self.host_name).eq('status', 'active').execute()
            for dep in result.data:
                self._add_job(dep)
            print(f"[@deployment_scheduler] Synced {len(result.data)} deployments")
        except Exception as e:
            print(f"[@deployment_scheduler] Sync error: {e}")
    
    def _add_job(self, deployment):
        """Add deployment to scheduler"""
        config = deployment['schedule_config']
        
        if deployment['schedule_type'] == 'hourly':
            trigger = CronTrigger(hour='*', minute=config.get('minute', 0))
        elif deployment['schedule_type'] == 'daily':
            trigger = CronTrigger(hour=config.get('hour', 0), minute=config.get('minute', 0))
        elif deployment['schedule_type'] == 'weekly':
            trigger = CronTrigger(day_of_week=config.get('day', 0), hour=config.get('hour', 0), minute=config.get('minute', 0))
        
        self.scheduler.add_job(
            func=self._execute_deployment,
            args=[deployment['id']],
            trigger=trigger,
            id=deployment['id'],
            replace_existing=True
        )
        print(f"[@deployment_scheduler] Added job: {deployment['name']}")
    
    def _execute_deployment(self, deployment_id):
        """Execute deployment and record result"""
        print(f"[@deployment_scheduler] Executing deployment: {deployment_id}")
        exec_id = None
        try:
            # Get deployment config
            dep = self.supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
            
            # Create execution record
            exec_record = self.supabase.table('deployment_executions').insert({
                'deployment_id': deployment_id,
                'started_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }).execute().data[0]
            exec_id = exec_record['id']
            
            # Execute script
            executor = ScriptExecutor(self.host_name, dep['device_id'], 'unknown')
            result = executor.execute_script(dep['script_name'], dep['parameters'])
            
            # Update execution record
            self.supabase.table('deployment_executions').update({
                'completed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'success': result.get('script_success', False),
                'script_result_id': result.get('script_result_id')
            }).eq('id', exec_id).execute()
            
            print(f"[@deployment_scheduler] Deployment {deployment_id} completed: {result.get('script_success')}")
        except Exception as e:
            print(f"[@deployment_scheduler] Execution error: {e}")
            if exec_id:
                self.supabase.table('deployment_executions').update({
                    'completed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'success': False,
                    'error_message': str(e)
                }).eq('id', exec_id).execute()
    
    def add_deployment(self, deployment):
        """Add new deployment (called by API)"""
        self._add_job(deployment)
    
    def pause_deployment(self, deployment_id):
        """Pause deployment"""
        self.scheduler.pause_job(deployment_id)
        print(f"[@deployment_scheduler] Paused: {deployment_id}")
    
    def resume_deployment(self, deployment_id):
        """Resume deployment"""
        self.scheduler.resume_job(deployment_id)
        print(f"[@deployment_scheduler] Resumed: {deployment_id}")
    
    def remove_deployment(self, deployment_id):
        """Remove deployment"""
        self.scheduler.remove_job(deployment_id)
        print(f"[@deployment_scheduler] Removed: {deployment_id}")

# Global instance
_scheduler = None

def get_deployment_scheduler():
    global _scheduler
    if not _scheduler:
        from backend_host.src.lib.utils.host_utils import get_host_instance
        host = get_host_instance()
        _scheduler = DeploymentScheduler(host.host_name)
        _scheduler.start()
    return _scheduler

