"""Deployment Scheduler - Manages periodic script execution with cron expressions"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.executors.script_executor import ScriptExecutor
from datetime import datetime, timezone
import logging
import threading

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
        self.db_lock = threading.Lock()  # Serialize concurrent DB operations
        
    def start(self):
        """Start scheduler and sync from DB"""
        print(f"[@deployment_scheduler] Starting for {self.host_name}")
        deployment_logger.info(f"=== DEPLOYMENT SCHEDULER STARTING === Host: {self.host_name}")
        self.scheduler.start()
        print(f"[@deployment_scheduler] APScheduler state: {self.scheduler.state}")
        print(f"[@deployment_scheduler] APScheduler running: {self.scheduler.running}")
        self._sync_from_db()
        print(f"[@deployment_scheduler] Active jobs count: {len(self.scheduler.get_jobs())}")
        
    def _sync_from_db(self):
        """Load active deployments from Supabase on startup"""
        try:
            # First, clean up any stale "running" executions from previous crashes/restarts
            print(f"[@deployment_scheduler] Checking for stale 'running' executions...")
            deployment_logger.info("Cleaning up stale 'running' executions from previous session...")
            
            try:
                # Get all deployments for this host to find their stale executions
                print(f"[@deployment_scheduler] Querying deployments for host: {self.host_name}")
                deployments_result = self.supabase.table('deployments').select('id').eq('host_name', self.host_name).execute()
                deployment_ids = [d['id'] for d in deployments_result.data]
                print(f"[@deployment_scheduler] Found {len(deployment_ids)} deployment(s) for this host")
                deployment_logger.info(f"Found {len(deployment_ids)} deployment(s) for host {self.host_name}")
                
                if not deployment_ids:
                    print(f"[@deployment_scheduler] No deployments for host {self.host_name}, skipping stale execution check")
                    deployment_logger.info(f"No deployments for host {self.host_name}")
                
                if deployment_ids:
                    # Find all running executions for this host's deployments
                    print(f"[@deployment_scheduler] Checking for running executions in {len(deployment_ids)} deployment(s)...")
                    stale_executions = self.supabase.table('deployment_executions')\
                        .select('id, deployment_id, started_at')\
                        .in_('deployment_id', deployment_ids)\
                        .eq('status', 'running')\
                        .execute()
                    
                    print(f"[@deployment_scheduler] Query returned {len(stale_executions.data) if stale_executions.data else 0} running execution(s)")
                    
                    if stale_executions.data:
                        stale_count = len(stale_executions.data)
                        print(f"[@deployment_scheduler] Found {stale_count} stale 'running' execution(s):")
                        for stale in stale_executions.data:
                            print(f"[@deployment_scheduler]   - Execution {stale['id']} started at {stale.get('started_at', 'unknown')}")
                        deployment_logger.warning(f"Found {stale_count} stale 'running' execution(s) - marking as failed")
                        
                        # Mark each stale execution as failed
                        for stale_exec in stale_executions.data:
                            try:
                                self.supabase.table('deployment_executions').update({
                                    'completed_at': datetime.now(timezone.utc).isoformat(),
                                    'status': 'failed',
                                    'success': False,
                                    'error_message': 'Execution aborted - scheduler restarted'
                                }).eq('id', stale_exec['id']).execute()
                                
                                print(f"[@deployment_scheduler] Marked stale execution {stale_exec['id']} as failed")
                                deployment_logger.info(f"Cleaned up stale execution: {stale_exec['id']} (started: {stale_exec.get('started_at', 'unknown')})")
                            except Exception as e:
                                print(f"[@deployment_scheduler] Failed to clean up execution {stale_exec['id']}: {e}")
                                deployment_logger.error(f"Failed to clean up stale execution {stale_exec['id']}: {e}")
                    else:
                        print(f"[@deployment_scheduler] No stale executions found")
                        deployment_logger.info("No stale executions found - clean state")
            except Exception as e:
                print(f"[@deployment_scheduler] Error cleaning up stale executions: {e}")
                deployment_logger.error(f"Error during stale execution cleanup: {e}")
            
            # Now load active deployments
            result = self.supabase.table('deployments').select('*').eq('host_name', self.host_name).eq('status', 'active').execute()
            
            # Add jobs
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
                    
                    # Format executions count
                    exec_count = dep.get('execution_count', 0)
                    max_exec = dep.get('max_executions')
                    if max_exec:
                        summary_lines.append(f"  Executions:      {exec_count}/{max_exec}")
                    else:
                        summary_lines.append(f"  Executions:      {exec_count}")
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
        
        # Add random delay to stagger concurrent executions (0-2 seconds)
        # This prevents multiple deployments from hitting DB at exact same moment
        stagger_delay = random.uniform(0, 2.0)
        time.sleep(stagger_delay)
        
        exec_id = None
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get deployment config
            try:
                result = self.supabase.table('deployments').select('*').eq('id', deployment_id).execute()
            except Exception as db_error:
                error_type = type(db_error).__name__
                print(f"[@deployment_scheduler] Failed to fetch deployment: {error_type}: {db_error}")
                print(f"[@deployment_scheduler] Raw error: {repr(db_error)}")
                deployment_logger.error(f"Failed to fetch deployment {deployment_id}: {error_type}: {db_error}")
                deployment_logger.error(f"Raw error: {repr(db_error)}")
                if hasattr(db_error, '__dict__'):
                    deployment_logger.error(f"Error attributes: {db_error.__dict__}")
                raise
            
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
            
            # Check if previous execution is still running
            running_check = self.supabase.table('deployment_executions')\
                .select('id, started_at')\
                .eq('deployment_id', deployment_id)\
                .eq('status', 'running')\
                .execute()
            
            if running_check.data and len(running_check.data) > 0:
                running_exec = running_check.data[0]
                started_at_str = running_exec.get('started_at', 'unknown')
                
                # Check if execution is stale (running for more than 1 hour)
                try:
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    age_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()
                    
                    if age_seconds > 3600:  # 1 hour = 3600 seconds
                        print(f"[@deployment_scheduler] Found stale execution (age: {age_seconds/3600:.1f} hours) - marking as failed")
                        deployment_logger.warning(f"Stale execution detected: {running_exec['id']} (age: {age_seconds/3600:.1f} hours) - marking as failed")
                        
                        # Mark stale execution as failed
                        self.supabase.table('deployment_executions').update({
                            'completed_at': datetime.now(timezone.utc).isoformat(),
                            'status': 'failed',
                            'success': False,
                            'error_message': f'Execution timed out - ran for {age_seconds/3600:.1f} hours'
                        }).eq('id', running_exec['id']).execute()
                        
                        # Continue with new execution (don't skip)
                        print(f"[@deployment_scheduler] Stale execution cleaned up, proceeding with new execution")
                    else:
                        # Execution is recent, skip this scheduled run
                        print(f"[@deployment_scheduler] Skipping - previous execution still running since {started_at_str} (age: {age_seconds:.0f}s)")
                        deployment_logger.warning(f"⏭️  SKIPPED: {dep_name} | Reason: Previous execution still running (started: {started_at_str}, age: {age_seconds:.0f}s)")
                        # Create skipped execution record
                        self.supabase.table('deployment_executions').insert({
                            'deployment_id': deployment_id,
                            'scheduled_at': start_time.isoformat(),
                            'status': 'skipped',
                            'skip_reason': 'Previous execution still running'
                        }).execute()
                        return
                except (ValueError, TypeError) as e:
                    # If we can't parse the date, assume it's stale and skip
                    print(f"[@deployment_scheduler] Could not parse started_at date: {e}, skipping execution")
                    deployment_logger.warning(f"⏭️  SKIPPED: {dep_name} | Reason: Previous execution still running (started: {started_at_str})")
                    self.supabase.table('deployment_executions').insert({
                        'deployment_id': deployment_id,
                        'scheduled_at': start_time.isoformat(),
                        'status': 'skipped',
                        'skip_reason': 'Previous execution still running'
                    }).execute()
                    return
            
            # Create execution record with UTC timestamp
            # Note: Supabase auto-generates unique UUID for 'id' field to avoid conflicts
            scheduled_at = start_time.isoformat()
            try:
                with self.db_lock:
                    exec_record = self.supabase.table('deployment_executions').insert({
                        'deployment_id': deployment_id,
                        'scheduled_at': scheduled_at,
                        'started_at': scheduled_at,
                        'status': 'running'
                    }).execute().data[0]
                    exec_id = exec_record['id']
                    print(f"[@deployment_scheduler] Created execution record: {exec_id}")
            except Exception as db_error:
                error_type = type(db_error).__name__
                print(f"[@deployment_scheduler] Failed to create execution record: {error_type}: {db_error}")
                print(f"[@deployment_scheduler] Raw error: {repr(db_error)}")
                deployment_logger.error(f"Failed to create execution record for {dep_name}: {error_type}: {db_error}")
                deployment_logger.error(f"Raw error: {repr(db_error)}")
                if hasattr(db_error, '__dict__'):
                    deployment_logger.error(f"Error attributes: {db_error.__dict__}")
                raise
            
            deployment_logger.info(f"▶️  EXECUTING: {dep_name} | Script: {dep['script_name']} | Device: {dep['device_id']}")
            
            # Build complete parameters including framework params
            # Framework params: --host and --device are flags, userinterface_name is positional
            framework_params = [
                f"--host {dep['host_name']}",
                f"--device {dep['device_id']}",
            ]
            
            # Combine framework flags with custom params first
            custom_params = dep.get('parameters', '').strip()
            all_params = ' '.join(framework_params)
            if custom_params:
                all_params = f"{all_params} {custom_params}"
            
            # Add userinterface_name as positional argument at the end (if available)
            if dep.get('userinterface_name'):
                all_params = f"{all_params} {dep['userinterface_name']}"
            
            # Execute script with complete parameters
            executor = ScriptExecutor(self.host_name, dep['device_id'], 'unknown')
            result = executor.execute_script(dep['script_name'], all_params)
            
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
            try:
                with self.db_lock:
                    self.supabase.table('deployment_executions').update({
                        'completed_at': end_time.isoformat(),
                        'status': 'completed' if result.get('script_success') else 'failed',
                        'success': result.get('script_success', False),
                        'script_result_id': script_result_id
                    }).eq('id', exec_id).execute()
            except Exception as db_error:
                error_type = type(db_error).__name__
                print(f"[@deployment_scheduler] Failed to update execution record: {error_type}: {db_error}")
                print(f"[@deployment_scheduler] Raw error: {repr(db_error)}")
                deployment_logger.error(f"Failed to update execution {exec_id}: {error_type}: {db_error}")
                deployment_logger.error(f"Raw error: {repr(db_error)}")
                if hasattr(db_error, '__dict__'):
                    deployment_logger.error(f"Error attributes: {db_error.__dict__}")
                raise
            
            # Update deployment counters
            new_count = dep.get('execution_count', 0) + 1
            try:
                with self.db_lock:
                    self.supabase.table('deployments').update({
                        'execution_count': new_count,
                        'last_executed_at': end_time.isoformat()
                    }).eq('id', deployment_id).execute()
            except Exception as db_error:
                error_type = type(db_error).__name__
                print(f"[@deployment_scheduler] Failed to update deployment counters: {error_type}: {db_error}")
                print(f"[@deployment_scheduler] Raw error: {repr(db_error)}")
                deployment_logger.error(f"Failed to update deployment {deployment_id} counters: {error_type}: {db_error}")
                deployment_logger.error(f"Raw error: {repr(db_error)}")
                if hasattr(db_error, '__dict__'):
                    deployment_logger.error(f"Error attributes: {db_error.__dict__}")
                raise
            
            print(f"[@deployment_scheduler] Deployment {deployment_id} completed: {result.get('script_success')}")
            
            # Format success status and execution count
            script_success = result.get('script_success')
            status_emoji = "✅" if script_success else "❌"
            success_str = "True" if script_success else "False"
            
            max_exec = dep.get('max_executions')
            if max_exec:
                exec_info = f"Executions: {new_count}/{max_exec}"
            else:
                exec_info = f"Executions: {new_count}"
            
            deployment_logger.info(f"{status_emoji} COMPLETED: {dep_name} | Duration: {duration:.1f}s | Success: {success_str} | {exec_info}")
            
            # Check if max executions reached after this run
            if dep.get('max_executions') and new_count >= dep['max_executions']:
                self._mark_as_completed(deployment_id)
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"[@deployment_scheduler] Execution error: {error_msg}")
            print(f"[@deployment_scheduler] Error type: {error_type}")
            print(f"[@deployment_scheduler] Raw error: {repr(e)}")
            
            # Log detailed error info
            deployment_logger.error(f"💥 ERROR: {deployment_id} | Type: {error_type}")
            deployment_logger.error(f"💥 ERROR: {deployment_id} | Message: {error_msg}")
            deployment_logger.error(f"💥 ERROR: {deployment_id} | Raw: {repr(e)}")
            
            # Try to extract more details if it's a Supabase error
            if hasattr(e, 'args') and len(e.args) > 0:
                deployment_logger.error(f"💥 ERROR: {deployment_id} | Args: {e.args}")
            if hasattr(e, '__dict__'):
                deployment_logger.error(f"💥 ERROR: {deployment_id} | Attributes: {e.__dict__}")
            
            if exec_id:
                try:
                    self.supabase.table('deployment_executions').update({
                        'completed_at': datetime.now(timezone.utc).isoformat(),
                        'status': 'failed',
                        'success': False,
                        'error_message': f"{error_type}: {error_msg}"
                    }).eq('id', exec_id).execute()
                except Exception as db_error:
                    db_error_type = type(db_error).__name__
                    print(f"[@deployment_scheduler] Failed to update execution record: {db_error_type}: {db_error}")
                    print(f"[@deployment_scheduler] Raw DB error: {repr(db_error)}")
                    deployment_logger.error(f"Failed to update execution record: {db_error_type}: {db_error}")
                    deployment_logger.error(f"Raw DB error: {repr(db_error)}")
    
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

