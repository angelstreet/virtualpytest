"""
Analysis Tools

Tools for querying and analyzing execution results.
Reports are pre-fetched using backend_server.src.lib.report_fetcher (saves tokens).
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from shared.src.lib.utils.supabase_utils import get_supabase_client


class AnalysisTools:
    """Tools for analyzing execution results"""
    
    def __init__(self):
        self.supabase = None
        self.session_started = datetime.now(timezone.utc)
        
        # Session stats - tracked in memory as we process
        self.stats = {
            'processed': 0,
            'discarded': 0,
            'kept': 0,
            'by_classification': {},
            'last_processed': None,  # {id, script_name, classification, timestamp}
            'history': []  # Last N processed items
        }
    
    def _get_supabase(self):
        """Lazy load supabase client"""
        if self.supabase is None:
            self.supabase = get_supabase_client()
        return self.supabase
    
    def get_execution_results(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get execution results from database with filters.
        Automatically fetches and includes report content for analysis.
        
        Args:
            userinterface_name: Filter by app/interface
            device_name: Filter by device
            host_name: Filter by host
            success: Filter by success status
            checked: Filter by checked status
            limit: Max results (default 1)
            include_report: Auto-fetch report content (default True)
        
        Returns:
            List of execution results with pre-fetched report content
        """
        try:
            supabase = self._get_supabase()
            
            userinterface_name = params.get('userinterface_name')
            device_name = params.get('device_name')
            host_name = params.get('host_name')
            success = params.get('success')
            checked = params.get('checked')
            limit = params.get('limit', 1)
            include_report = params.get('include_report', True)  # Default True
            
            print(f"[@analysis] get_execution_results: ui={userinterface_name}, device={device_name}, host={host_name}, success={success}, limit={limit}, include_report={include_report}")
            
            # Build query
            query = supabase.table('script_results').select('*')
            
            # Apply filters
            if userinterface_name:
                query = query.eq('userinterface_name', userinterface_name)
            if device_name:
                query = query.eq('device_name', device_name)
            if host_name:
                query = query.eq('host_name', host_name)
            if success is not None:
                query = query.eq('success', success)
            if checked is not None:
                query = query.eq('checked', checked)
            
            # Order by most recent and limit
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            if not result.data:
                return {
                    "content": [{"type": "text", "text": "No execution results found matching criteria"}],
                    "isError": False,
                    "results": []
                }
            
            # Format results for agent
            formatted_results = []
            for r in result.data:
                formatted = {
                    'id': r.get('id'),
                    'script_name': r.get('script_name'),
                    'script_type': r.get('script_type'),
                    'userinterface_name': r.get('userinterface_name'),
                    'device_name': r.get('device_name'),
                    'host_name': r.get('host_name'),
                    'success': r.get('success'),
                    'error_msg': r.get('error_msg'),
                    'execution_time_ms': r.get('execution_time_ms'),
                    'html_report_r2_url': r.get('html_report_r2_url'),
                    'logs_url': r.get('logs_url'),
                    'created_at': r.get('created_at'),
                    # Analysis fields
                    'checked': r.get('checked', False),
                    'check_type': r.get('check_type'),
                    'discard': r.get('discard', False),
                    'discard_comment': r.get('discard_comment')
                }
                formatted_results.append(formatted)
            
            # Pre-fetch report content if requested (default True)
            if include_report and formatted_results:
                from backend_server.src.lib.report_fetcher import fetch_execution_report
                
                for r in formatted_results:
                    report_url = r.get('html_report_r2_url')
                    logs_url = r.get('logs_url')
                    
                    if report_url:
                        try:
                            report_data = fetch_execution_report(report_url, logs_url)
                            r['report_content'] = report_data.get('summary', '')
                        except Exception as e:
                            print(f"[@analysis] Warning: Failed to fetch report for {r['id']}: {e}")
                            r['report_content'] = None
            
            # Build summary text
            summary_lines = [f"Found {len(formatted_results)} execution result(s):\n"]
            for i, r in enumerate(formatted_results, 1):
                status = "✅ PASS" if r['success'] else "❌ FAIL"
                checked_status = f" [Analyzed: {r['check_type']}]" if r['checked'] else " [Not analyzed]"
                summary_lines.append(f"{i}. {r['script_name']} ({r['script_type']})")
                summary_lines.append(f"   SCRIPT_RESULT_ID: {r['id']}")
                summary_lines.append(f"   Status: {status}{checked_status}")
                summary_lines.append(f"   Interface: {r['userinterface_name']} | Device: {r['device_name']}")
                summary_lines.append(f"   Duration: {r['execution_time_ms']}ms")
                if r['error_msg']:
                    summary_lines.append(f"   Error: {r['error_msg'][:100]}")
                if r['discard_comment']:
                    summary_lines.append(f"   Analysis: {r['discard_comment'][:100]}")
                
                # Include pre-fetched report content
                if r.get('report_content'):
                    summary_lines.append(f"\n{r['report_content']}")
                
                summary_lines.append("")
            
            return {
                "content": [{"type": "text", "text": "\n".join(summary_lines)}],
                "isError": False,
                "results": formatted_results
            }
            
        except Exception as e:
            print(f"[@analysis] Error in get_execution_results: {e}")
            return {
                "content": [{"type": "text", "text": f"Error querying execution results: {e}"}],
                "isError": True
            }
    
    def update_execution_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save analysis results to database.
        
        Args:
            script_result_id: ID of script result to update
            discard: True if false positive, False if valid
            classification: BUG, SCRIPT_ISSUE, SYSTEM_ISSUE, VALID_PASS, VALID_FAIL
            explanation: Brief analysis explanation
        
        Returns:
            Success/failure status
        """
        try:
            supabase = self._get_supabase()
            
            script_result_id = params.get('script_result_id')
            discard = params.get('discard')
            classification = params.get('classification')
            explanation = params.get('explanation')
            
            if not script_result_id:
                return {
                    "content": [{"type": "text", "text": "Error: script_result_id is required"}],
                    "isError": True
                }
            
            if discard is None:
                return {
                    "content": [{"type": "text", "text": "Error: discard (true/false) is required"}],
                    "isError": True
                }
            
            if not classification:
                return {
                    "content": [{"type": "text", "text": "Error: classification is required"}],
                    "isError": True
                }
            
            if not explanation:
                return {
                    "content": [{"type": "text", "text": "Error: explanation is required"}],
                    "isError": True
                }
            
            # Build comment with classification
            discard_comment = f"[{classification}] {explanation[:200]}"
            
            print(f"[@analysis] update_execution_analysis: id={script_result_id}, discard={discard}, class={classification}")
            
            # Update database
            update_data = {
                'checked': True,
                'check_type': 'ai_agent',
                'discard': discard,
                'discard_comment': discard_comment,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase.table('script_results').update(update_data).eq('id', script_result_id).execute()
            
            if result.data:
                # Track session stats
                self.stats['processed'] += 1
                if discard:
                    self.stats['discarded'] += 1
                else:
                    self.stats['kept'] += 1
                
                # Track by classification
                if classification not in self.stats['by_classification']:
                    self.stats['by_classification'][classification] = 0
                self.stats['by_classification'][classification] += 1
                
                # Track last processed
                script_name = result.data[0].get('script_name', 'unknown') if result.data else 'unknown'
                script_type = result.data[0].get('script_type', '') if result.data else ''
                userinterface = result.data[0].get('userinterface_name', '') if result.data else ''
                
                self.stats['last_processed'] = {
                    'id': script_result_id,
                    'script_name': script_name,
                    'classification': classification,
                    'discard': discard,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Keep history (last 20)
                self.stats['history'].append(self.stats['last_processed'])
                if len(self.stats['history']) > 20:
                    self.stats['history'] = self.stats['history'][-20:]
                
                # Build rich markdown response
                action_text = "DISCARDED" if discard else "KEPT"
                action_icon = "❌" if discard else "✅"
                
                # Classification indicator
                class_icon = "✅" if classification == 'VALID_PASS' else "❌" if classification in ('BUG', 'VALID_FAIL') else ""
                class_display = f"{class_icon} **{classification}**" if class_icon else f"**{classification}**"
                
                markdown_response = f"""## {action_icon} Analysis Saved

| Field | Value |
|-------|-------|
| **Script** | `{script_name}` |
| **Type** | {script_type or 'N/A'} |
| **Interface** | {userinterface or 'N/A'} |
| **Classification** | {class_display} |
| **Action** | {action_text} |

### Reasoning
> {explanation}

---
*Result ID: `{script_result_id[:8]}...`*"""

                return {
                    "content": [{"type": "text", "text": markdown_response}],
                    "isError": False
                }
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: Script result {script_result_id} not found"}],
                    "isError": True
                }
            
        except Exception as e:
            print(f"[@analysis] Error in update_execution_analysis: {e}")
            return {
                "content": [{"type": "text", "text": f"Error updating analysis: {e}"}],
                "isError": True
            }
    
    def get_analysis_queue_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get analysis queue status - pending items and session processing stats.
        
        Returns:
            Queue lengths and session statistics (no DB queries)
        """
        try:
            # Get Redis queue lengths
            queue_status = self._get_redis_queue_status()
            
            # Calculate session uptime
            uptime = datetime.now(timezone.utc) - self.session_started
            uptime_str = f"{int(uptime.total_seconds())}s"
            if uptime.total_seconds() > 60:
                uptime_str = f"{int(uptime.total_seconds() / 60)}m {int(uptime.total_seconds() % 60)}s"
            if uptime.total_seconds() > 3600:
                uptime_str = f"{int(uptime.total_seconds() / 3600)}h {int((uptime.total_seconds() % 3600) / 60)}m"
            
            # Build summary from session stats (no DB queries!)
            lines = [
                "═══ ANALYSIS QUEUE STATUS ═══\n",
                f"⏱️  Session Uptime: {uptime_str}",
                "",
                "📊 Redis Queues (Pending):",
                f"   • P1 Alerts:  {queue_status.get('p1_alerts', 0)}",
                f"   • P2 Scripts: {queue_status.get('p2_scripts', 0)}",
                f"   • P3 Reserved: {queue_status.get('p3_reserved', 0)}",
                "",
                "📈 Session Stats (This Session):",
                f"   • Processed:  {self.stats['processed']}",
                f"   • Kept:       {self.stats['kept']}",
                f"   • Discarded:  {self.stats['discarded']}",
            ]
            
            if self.stats['processed'] > 0:
                discard_rate = (self.stats['discarded'] / self.stats['processed']) * 100
                lines.append(f"   • Discard Rate: {discard_rate:.1f}%")
            
            # Classification breakdown
            if self.stats['by_classification']:
                lines.append("")
                lines.append("🏷️  Classification Breakdown:")
                for cls, count in self.stats['by_classification'].items():
                    lines.append(f"   • {cls}: {count}")
            
            # Last processed
            if self.stats['last_processed']:
                last = self.stats['last_processed']
                lines.append("")
                lines.append("📝 Last Processed:")
                lines.append(f"   • Script: {last['script_name']}")
                lines.append(f"   • Classification: {last['classification']}")
                lines.append(f"   • Action: {'Discarded' if last['discard'] else 'Kept'}")
            
            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "isError": False,
                "queue_status": queue_status,
                "session_stats": self.stats
            }
            
        except Exception as e:
            print(f"[@analysis] Error in get_analysis_queue_status: {e}")
            return {
                "content": [{"type": "text", "text": f"Error getting queue status: {e}"}],
                "isError": True
            }
    
    def _get_redis_queue_status(self) -> Dict[str, int]:
        """Get Redis queue lengths"""
        try:
            import redis
            import os
            
            redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
            redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
            
            if redis_url:
                host = redis_url.replace('https://', '').replace('http://', '').split('/')[0]
                client = redis.Redis(
                    host=host,
                    port=6379,
                    password=redis_token,
                    ssl=True,
                    ssl_cert_reqs=None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', '6379'))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                
                client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            return {
                'p1_alerts': client.llen('p1_alerts'),
                'p2_scripts': client.llen('p2_scripts'),
                'p3_reserved': client.llen('p3_reserved')
            }
            
        except Exception as e:
            print(f"[@analysis] Error getting Redis queue status: {e}")
            return {'p1_alerts': 0, 'p2_scripts': 0, 'p3_reserved': 0, 'error': str(e)}
