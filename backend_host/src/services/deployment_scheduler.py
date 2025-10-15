"""Deployment Scheduler - Manages periodic script execution with cron expressions"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.executors.script_executor import ScriptExecutor
from datetime import datetime, timezone

class DeploymentScheduler:
    def __init__(self, host_name):
        self.host_name = host_name
        self.scheduler = BackgroundScheduler(timezone='UTC')
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
        """Add deployment to scheduler using cron expression"""
        cron_expr = deployment.get('cron_expression')
        if not cron_expr:
            print(f"[@deployment_scheduler] No cron expression for deployment {deployment.get('id')}")
            return
        
        # Parse cron expression (format: minute hour day month day_of_week)
        parts = cron_expr.split()
        if len(parts) != 5:
            print(f"[@deployment_scheduler] Invalid cron expression: {cron_expr}")
            return
        
        minute, hour, day, month, day_of_week = parts
        
        # Create cron trigger (always use UTC)
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone='UTC'
        )
        
        self.scheduler.add_job(
            func=self._execute_deployment,
            args=[deployment['id']],
            trigger=trigger,
            id=deployment['id'],
            replace_existing=True
        )
        print(f"[@deployment_scheduler] Added job: {deployment['name']} with cron: {cron_expr}")
    
    def _should_execute(self, deployment):
        """Check if deployment should execute based on constraints"""
        now = datetime.now(timezone.utc)
        
        # Check start date
        if deployment.get('start_date'):
            start_date_str = deployment['start_date']
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                if now < start_date:
                    return False, "Not started yet"
        
        # Check end date
        if deployment.get('end_date'):
            end_date_str = deployment['end_date']
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if now > end_date:
                    self._mark_as_expired(deployment['id'])
                    return False, "Expired by end date"
        
        # Check max executions
        if deployment.get('max_executions'):
            execution_count = deployment.get('execution_count', 0)
            if execution_count >= deployment['max_executions']:
                self._mark_as_completed(deployment['id'])
                return False, "Max executions reached"
        
        return True, "OK"
    
    def _mark_as_expired(self, deployment_id):
        """Mark deployment as expired and remove from scheduler"""
        try:
            self.supabase.table('deployments')\
                .update({'status': 'expired'})\
                .eq('id', deployment_id)\
                .execute()
            self.scheduler.remove_job(deployment_id)
            print(f"[@deployment_scheduler] Marked as expired: {deployment_id}")
        except Exception as e:
            print(f"[@deployment_scheduler] Error marking expired: {e}")
    
    def _mark_as_completed(self, deployment_id):
        """Mark deployment as completed and remove from scheduler"""
        try:
            self.supabase.table('deployments')\
                .update({'status': 'completed'})\
                .eq('id', deployment_id)\
                .execute()
            self.scheduler.remove_job(deployment_id)
            print(f"[@deployment_scheduler] Marked as completed: {deployment_id}")
        except Exception as e:
            print(f"[@deployment_scheduler] Error marking completed: {e}")
    
    def _execute_deployment(self, deployment_id):
        """Execute deployment with constraint checks"""
        print(f"[@deployment_scheduler] Triggering deployment: {deployment_id}")
        exec_id = None
        
        try:
            # Get deployment config
            dep = self.supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
            
            # Check if should execute (constraints)
            should_run, reason = self._should_execute(dep)
            if not should_run:
                print(f"[@deployment_scheduler] Skipping execution: {reason}")
                # Create skipped execution record
                self.supabase.table('deployment_executions').insert({
                    'deployment_id': deployment_id,
                    'scheduled_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'skipped',
                    'skip_reason': reason
                }).execute()
                return
            
            # Create execution record with UTC timestamp
            scheduled_at = datetime.now(timezone.utc).isoformat()
            exec_record = self.supabase.table('deployment_executions').insert({
                'deployment_id': deployment_id,
                'scheduled_at': scheduled_at,
                'started_at': scheduled_at,
                'status': 'running'
            }).execute().data[0]
            exec_id = exec_record['id']
            
            # Execute script
            executor = ScriptExecutor(self.host_name, dep['device_id'], 'unknown')
            result = executor.execute_script(dep['script_name'], dep['parameters'])
            
            # Update execution record with UTC timestamp
            self.supabase.table('deployment_executions').update({
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed' if result.get('script_success') else 'failed',
                'success': result.get('script_success', False),
                'script_result_id': result.get('script_result_id')
            }).eq('id', exec_id).execute()
            
            # Update deployment counters
            new_count = dep.get('execution_count', 0) + 1
            self.supabase.table('deployments').update({
                'execution_count': new_count,
                'last_executed_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', deployment_id).execute()
            
            print(f"[@deployment_scheduler] Deployment {deployment_id} completed: {result.get('script_success')}")
            
            # Check if max executions reached after this run
            if dep.get('max_executions') and new_count >= dep['max_executions']:
                self._mark_as_completed(deployment_id)
                
        except Exception as e:
            print(f"[@deployment_scheduler] Execution error: {e}")
            if exec_id:
                self.supabase.table('deployment_executions').update({
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'failed',
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

