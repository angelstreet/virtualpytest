"""Deployment Scheduler - Manages periodic script execution with cron expressions"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.executors.script_executor import ScriptExecutor
from datetime import datetime, timezone
import logging

# Configure deployment logger
deployment_logger = logging.getLogger('deployment_scheduler')
deployment_logger.setLevel(logging.INFO)
deployment_handler = logging.FileHandler('/tmp/deployments.log')
deployment_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
deployment_logger.addHandler(deployment_handler)

class DeploymentScheduler:
    def __init__(self, host_name):
        self.host_name = host_name
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self.supabase = get_supabase_client()
        
    def start(self):
        """Start scheduler and sync from DB"""
        print(f"[@deployment_scheduler] Starting for {self.host_name}")
        deployment_logger.info(f"=== DEPLOYMENT SCHEDULER STARTING === Host: {self.host_name}")
        self.scheduler.start()
        self._sync_from_db()
        
    def _sync_from_db(self):
        """Load active deployments from Supabase on startup"""
        try:
            result = self.supabase.table('deployments').select('*').eq('host_name', self.host_name).eq('status', 'active').execute()
            
            # Add jobs first
            for dep in result.data:
                self._add_job(dep)
            
            # Format deployment summary for both console and log file
            separator = "=" * 80
            header = f"{'DEPLOYMENTS':^80}"
            active_count = f"Active: {len(result.data)}"
            
            # Build the summary
            summary_lines = [
                "",
                separator,
                header,
                separator,
                active_count,
                ""
            ]
            
            if len(result.data) > 0:
                for dep in result.data:
                    # Get job info for next run time
                    job = self.scheduler.get_job(dep['id'])
                    next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC') if job and job.next_run_time else 'N/A'
                    
                    # Format last execution
                    last_exec = dep.get('last_executed_at')
                    if last_exec:
                        from datetime import datetime
                        last_exec_dt = datetime.fromisoformat(last_exec.replace('Z', '+00:00'))
                        last_exec_str = last_exec_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    else:
                        last_exec_str = 'Never'
                    
                    # Format frequency
                    cron_expr = dep.get('cron_expression', 'N/A')
                    
                    summary_lines.append(f"• {dep['name']}")
                    summary_lines.append(f"  Last execution:  {last_exec_str}")
                    summary_lines.append(f"  Next execution:  {next_run}")
                    summary_lines.append(f"  Frequency:       {cron_expr}")
                    summary_lines.append(f"  Executions:      {dep.get('execution_count', 0)}/{dep.get('max_executions', '∞')}")
                    summary_lines.append("")
            else:
                summary_lines.append("(No active deployments)")
                summary_lines.append("")
            
            summary_lines.append(separator)
            
            # Print to console
            for line in summary_lines:
                print(f"[@deployment_scheduler] {line}")
            
            # Write to log file
            for line in summary_lines:
                deployment_logger.info(line)
                
        except Exception as e:
            error_msg = f"Failed to sync deployments: {e}"
            print(f"[@deployment_scheduler] {error_msg}")
            deployment_logger.error(error_msg)
    
    def _add_job(self, deployment, log_details=False):
        """Add deployment to scheduler using cron expression"""
        cron_expr = deployment.get('cron_expression')
        if not cron_expr:
            print(f"[@deployment_scheduler] No cron expression for deployment {deployment.get('id')}")
            deployment_logger.warning(f"No cron expression for deployment {deployment.get('name')}")
            return
        
        # Parse cron expression (format: minute hour day month day_of_week)
        parts = cron_expr.split()
        if len(parts) != 5:
            print(f"[@deployment_scheduler] Invalid cron expression: {cron_expr}")
            deployment_logger.error(f"Invalid cron expression for {deployment.get('name')}: {cron_expr}")
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
        
        # Only log detailed info when adding individual deployments (not during sync)
        if log_details:
            job = self.scheduler.get_job(deployment['id'])
            next_run = job.next_run_time if job else None
            print(f"[@deployment_scheduler] Added: {deployment['name']} with cron: {cron_expr}")
            deployment_logger.info(f"ADDED: {deployment['name']} | Cron: {cron_expr} | Next run: {next_run} UTC")
    
    def _should_execute(self, deployment):
        """Check if deployment should execute based on constraints"""
        now = datetime.now(timezone.utc)
        dep_name = deployment.get('name', deployment['id'])
        
        # Check start date
        if deployment.get('start_date'):
            start_date_str = deployment['start_date']
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                if now < start_date:
                    deployment_logger.info(f"CONSTRAINT: {dep_name} | Skipped - Not started yet (starts: {start_date} UTC)")
                    return False, "Not started yet"
        
        # Check end date
        if deployment.get('end_date'):
            end_date_str = deployment['end_date']
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if now > end_date:
                    deployment_logger.warning(f"CONSTRAINT: {dep_name} | Expired (end date: {end_date} UTC)")
                    self._mark_as_expired(deployment['id'])
                    return False, "Expired by end date"
        
        # Check max executions
        if deployment.get('max_executions'):
            execution_count = deployment.get('execution_count', 0)
            if execution_count >= deployment['max_executions']:
                deployment_logger.warning(f"CONSTRAINT: {dep_name} | Max executions reached ({execution_count}/{deployment['max_executions']})")
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
            deployment_logger.warning(f"STATUS: {deployment_id} | EXPIRED - Removed from scheduler")
        except Exception as e:
            print(f"[@deployment_scheduler] Error marking expired: {e}")
            deployment_logger.error(f"Failed to mark deployment as expired: {e}")
    
    def _mark_as_completed(self, deployment_id):
        """Mark deployment as completed and remove from scheduler"""
        try:
            self.supabase.table('deployments')\
                .update({'status': 'completed'})\
                .eq('id', deployment_id)\
                .execute()
            self.scheduler.remove_job(deployment_id)
            print(f"[@deployment_scheduler] Marked as completed: {deployment_id}")
            deployment_logger.info(f"STATUS: {deployment_id} | COMPLETED - Removed from scheduler")
        except Exception as e:
            print(f"[@deployment_scheduler] Error marking completed: {e}")
            deployment_logger.error(f"Failed to mark deployment as completed: {e}")
    
    def _execute_deployment(self, deployment_id):
        """Execute deployment with constraint checks"""
        print(f"[@deployment_scheduler] Triggering deployment: {deployment_id}")
        exec_id = None
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get deployment config
            result = self.supabase.table('deployments').select('*').eq('id', deployment_id).execute()
            if not result.data or len(result.data) == 0:
                print(f"[@deployment_scheduler] Deployment {deployment_id} no longer exists, removing from scheduler")
                deployment_logger.warning(f"DELETED: {deployment_id} | Deployment no longer exists in database")
                self.scheduler.remove_job(deployment_id)
                return
            
            dep = result.data[0]
            dep_name = dep.get('name', deployment_id)
            
            deployment_logger.info(f"⚡ TRIGGERED: {dep_name} | Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # Check if should execute (constraints)
            should_run, reason = self._should_execute(dep)
            if not should_run:
                print(f"[@deployment_scheduler] Skipping execution: {reason}")
                deployment_logger.info(f"⏭️  SKIPPED: {dep_name} | Reason: {reason}")
                # Create skipped execution record
                self.supabase.table('deployment_executions').insert({
                    'deployment_id': deployment_id,
                    'scheduled_at': start_time.isoformat(),
                    'status': 'skipped',
                    'skip_reason': reason
                }).execute()
                return
            
            # Create execution record with UTC timestamp
            scheduled_at = start_time.isoformat()
            exec_record = self.supabase.table('deployment_executions').insert({
                'deployment_id': deployment_id,
                'scheduled_at': scheduled_at,
                'started_at': scheduled_at,
                'status': 'running'
            }).execute().data[0]
            exec_id = exec_record['id']
            
            deployment_logger.info(f"▶️  EXECUTING: {dep_name} | Script: {dep['script_name']} | Device: {dep['device_id']}")
            
            # Execute script
            executor = ScriptExecutor(self.host_name, dep['device_id'], 'unknown')
            result = executor.execute_script(dep['script_name'], dep['parameters'])
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Extract script_result_id from stdout if available
            script_result_id = None
            if result.get('stdout'):
                import re
                match = re.search(r'SCRIPT_RESULT_ID:([a-f0-9-]+)', result['stdout'])
                if match:
                    script_result_id = match.group(1)
                    print(f"[@deployment_scheduler] Extracted script_result_id: {script_result_id}")
            
            # Update execution record with UTC timestamp
            self.supabase.table('deployment_executions').update({
                'completed_at': end_time.isoformat(),
                'status': 'completed' if result.get('script_success') else 'failed',
                'success': result.get('script_success', False),
                'script_result_id': script_result_id
            }).eq('id', exec_id).execute()
            
            # Update deployment counters
            new_count = dep.get('execution_count', 0) + 1
            self.supabase.table('deployments').update({
                'execution_count': new_count,
                'last_executed_at': end_time.isoformat()
            }).eq('id', deployment_id).execute()
            
            print(f"[@deployment_scheduler] Deployment {deployment_id} completed: {result.get('script_success')}")
            
            status_emoji = "✅" if result.get('script_success') else "❌"
            deployment_logger.info(f"{status_emoji} COMPLETED: {dep_name} | Duration: {duration:.1f}s | Success: {result.get('script_success')} | Executions: {new_count}/{dep.get('max_executions', '∞')}")
            
            # Check if max executions reached after this run
            if dep.get('max_executions') and new_count >= dep['max_executions']:
                self._mark_as_completed(deployment_id)
                
        except Exception as e:
            print(f"[@deployment_scheduler] Execution error: {e}")
            deployment_logger.error(f"💥 ERROR: {deployment_id} | {str(e)}")
            if exec_id:
                self.supabase.table('deployment_executions').update({
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'failed',
                    'success': False,
                    'error_message': str(e)
                }).eq('id', exec_id).execute()
    
    def add_deployment(self, deployment):
        """Add new deployment (called by API)"""
        deployment_logger.info(f"API: Adding new deployment: {deployment.get('name')}")
        self._add_job(deployment, log_details=True)
    
    def pause_deployment(self, deployment_id):
        """Pause deployment"""
        self.scheduler.pause_job(deployment_id)
        print(f"[@deployment_scheduler] Paused: {deployment_id}")
        deployment_logger.info(f"⏸️  PAUSED: {deployment_id}")
    
    def resume_deployment(self, deployment_id):
        """Resume deployment"""
        self.scheduler.resume_job(deployment_id)
        print(f"[@deployment_scheduler] Resumed: {deployment_id}")
        job = self.scheduler.get_job(deployment_id)
        next_run = job.next_run_time if job else None
        deployment_logger.info(f"▶️  RESUMED: {deployment_id} | Next run: {next_run} UTC")
    
    def remove_deployment(self, deployment_id):
        """Remove deployment"""
        self.scheduler.remove_job(deployment_id)
        print(f"[@deployment_scheduler] Removed: {deployment_id}")
        deployment_logger.info(f"🗑️  REMOVED: {deployment_id}")

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

