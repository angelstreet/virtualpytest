"""
Analysis Tools

Tools for fetching, querying, and analyzing execution results.
Replaces backend_discard worker - agent does analysis autonomously.
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from shared.src.lib.utils.supabase_utils import get_supabase_client


class AnalysisTools:
    """Tools for analyzing execution results"""
    
    def __init__(self):
        self.supabase = None
    
    def _get_supabase(self):
        """Lazy load supabase client"""
        if self.supabase is None:
            self.supabase = get_supabase_client()
        return self.supabase
    
    def fetch_execution_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and parse execution report and logs from URLs.
        
        Args:
            report_url: URL to HTML report
            logs_url: URL to logs file (optional)
        
        Returns:
            Parsed report content and logs
        """
        report_url = params.get('report_url')
        logs_url = params.get('logs_url')
        
        if not report_url:
            return {
                "content": [{"type": "text", "text": "Error: report_url is required"}],
                "isError": True
            }
        
        try:
            result = {}
            
            # Fetch and parse report
            report_data = self._fetch_and_parse_report(report_url)
            result['report'] = report_data
            
            # Fetch logs if URL provided
            if logs_url:
                logs_data = self._fetch_logs(logs_url)
                result['logs'] = logs_data
            else:
                result['logs'] = None
            
            # Build summary
            summary = self._build_summary(result)
            
            return {
                "content": [{"type": "text", "text": summary}],
                "isError": False,
                "parsed_data": result
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True
            }
    
    def get_execution_results(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get execution results from database with filters.
        
        Args:
            userinterface_name: Filter by app/interface
            device_name: Filter by device
            host_name: Filter by host
            success: Filter by success status
            checked: Filter by checked status
            limit: Max results (default 1)
        
        Returns:
            List of execution results
        """
        try:
            supabase = self._get_supabase()
            
            userinterface_name = params.get('userinterface_name')
            device_name = params.get('device_name')
            host_name = params.get('host_name')
            success = params.get('success')
            checked = params.get('checked')
            limit = params.get('limit', 1)
            
            print(f"[@analysis] get_execution_results: ui={userinterface_name}, device={device_name}, host={host_name}, success={success}, limit={limit}")
            
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
            
            # Build summary text
            summary_lines = [f"Found {len(formatted_results)} execution result(s):\n"]
            for i, r in enumerate(formatted_results, 1):
                status = "✅ PASS" if r['success'] else "❌ FAIL"
                checked_status = f" [Analyzed: {r['check_type']}]" if r['checked'] else " [Not analyzed]"
                summary_lines.append(f"{i}. {r['script_name']} ({r['script_type']})")
                summary_lines.append(f"   Status: {status}{checked_status}")
                summary_lines.append(f"   Interface: {r['userinterface_name']} | Device: {r['device_name']}")
                summary_lines.append(f"   Duration: {r['execution_time_ms']}ms")
                if r['error_msg']:
                    summary_lines.append(f"   Error: {r['error_msg'][:100]}")
                if r['html_report_r2_url']:
                    summary_lines.append(f"   Report: {r['html_report_r2_url'][:80]}...")
                if r['discard_comment']:
                    summary_lines.append(f"   Analysis: {r['discard_comment'][:100]}")
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
                action = "discarded (false positive)" if discard else "validated (kept)"
                return {
                    "content": [{"type": "text", "text": f"✅ Analysis saved: {classification} - Result {action}"}],
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
    
    def _fetch_and_parse_report(self, report_url: str) -> Dict[str, Any]:
        """Fetch and parse HTML report"""
        try:
            print(f"[@analysis] Fetching report: {report_url[:60]}...")
            response = requests.get(report_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            parsed = {
                'steps': [],
                'errors': [],
                'raw_text': ''
            }
            
            # Extract steps
            for step in soup.select('.step, .test-step, [class*="step"]'):
                step_data = self._extract_step(step)
                if step_data:
                    parsed['steps'].append(step_data)
            
            # Fallback: table rows
            if not parsed['steps']:
                for row in soup.select('tr'):
                    step_data = self._extract_step_from_row(row)
                    if step_data:
                        parsed['steps'].append(step_data)
            
            # Extract errors
            for error in soup.select('.error, .failure, .exception, [class*="error"]'):
                error_text = error.get_text(strip=True)
                if error_text:
                    parsed['errors'].append(error_text[:500])
            
            # Get raw text
            body = soup.find('body')
            if body:
                parsed['raw_text'] = body.get_text(separator='\n', strip=True)[:8000]
            
            return parsed
            
        except Exception as e:
            print(f"[@analysis] Error parsing report: {e}")
            return {'error': str(e)}
    
    def _fetch_logs(self, logs_url: str) -> Dict[str, Any]:
        """Fetch logs content (truncated)"""
        try:
            print(f"[@analysis] Fetching logs: {logs_url[:60]}...")
            response = requests.get(logs_url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            max_size = 30000
            truncated = len(content) > max_size
            
            if truncated:
                content = content[:15000] + "\n\n... [TRUNCATED] ...\n\n" + content[-15000:]
            
            return {
                'content': content,
                'truncated': truncated,
                'original_size': len(response.text)
            }
            
        except Exception as e:
            print(f"[@analysis] Error fetching logs: {e}")
            return {'error': str(e)}
    
    def _extract_step(self, element) -> Optional[Dict[str, Any]]:
        """Extract step data from element"""
        classes = element.get('class', [])
        text = element.get_text(strip=True)
        
        if not text:
            return None
        
        status = 'unknown'
        class_str = ' '.join(classes).lower()
        if 'pass' in class_str or 'success' in class_str:
            status = 'passed'
        elif 'fail' in class_str or 'error' in class_str:
            status = 'failed'
        elif 'skip' in class_str:
            status = 'skipped'
        
        name_elem = element.select_one('.step-name, .name, h3, h4, strong')
        name = name_elem.get_text(strip=True) if name_elem else text[:100]
        
        error_elem = element.select_one('.error, .message, [class*="error"]')
        error = error_elem.get_text(strip=True)[:200] if error_elem else None
        
        return {'name': name, 'status': status, 'error': error}
    
    def _extract_step_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract step from table row"""
        cells = row.select('td')
        if len(cells) < 2:
            return None
        
        text = ' '.join(c.get_text(strip=True) for c in cells)
        if not text.strip():
            return None
        
        status = 'unknown'
        if 'pass' in text.lower() or '✓' in text or '✅' in text:
            status = 'passed'
        elif 'fail' in text.lower() or '✗' in text or '❌' in text:
            status = 'failed'
        
        return {
            'name': cells[0].get_text(strip=True)[:200],
            'status': status,
            'error': None
        }
    
    def _build_summary(self, result: Dict[str, Any]) -> str:
        """Build summary text for agent"""
        lines = []
        
        # Report
        report = result.get('report')
        if report and not report.get('error'):
            lines.append("═══ REPORT ANALYSIS ═══")
            
            steps = report.get('steps', [])
            if steps:
                passed = sum(1 for s in steps if s['status'] == 'passed')
                failed = sum(1 for s in steps if s['status'] == 'failed')
                lines.append(f"Steps: {len(steps)} total, {passed} passed, {failed} failed")
            
            errors = report.get('errors', [])
            if errors:
                lines.append(f"\nErrors ({len(errors)}):")
                for err in errors[:5]:
                    lines.append(f"  - {err[:200]}")
            
            raw_text = report.get('raw_text', '')
            if raw_text:
                lines.append("\n═══ REPORT CONTENT ═══")
                lines.append(raw_text[:5000])
        elif report and report.get('error'):
            lines.append(f"Report error: {report['error']}")
        
        # Logs
        logs = result.get('logs')
        if logs and not logs.get('error'):
            lines.append("\n═══ LOGS ═══")
            if logs.get('truncated'):
                lines.append(f"(Truncated from {logs['original_size']} bytes)")
            lines.append(logs.get('content', '')[:3000])
        elif logs and logs.get('error'):
            lines.append(f"\nLogs error: {logs['error']}")
        
        return '\n'.join(lines)
