"""
Analysis Tools

Tools for fetching and parsing execution reports and logs.
Used by the analyzer agent to classify test failures.
"""

import re
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from backend_server.src.agent.core.event_bus import get_event_bus, get_analysis_queue


class AnalysisTools:
    """Tools for analyzing execution results"""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.analysis_queue = get_analysis_queue()
    
    def fetch_execution_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and parse an HTML execution report.
        
        Extracts:
        - Test steps with status
        - Error messages
        - Screenshot references
        - Timing info
        """
        report_url = params.get('report_url')
        
        if not report_url:
            return {
                "content": [{"type": "text", "text": "Error: report_url is required"}],
                "isError": True
            }
        
        try:
            print(f"[@analysis:fetch_report] Fetching: {report_url}")
            response = requests.get(report_url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            parsed = self._parse_report_html(soup)
            
            # Build summary
            total_steps = len(parsed['steps'])
            passed = sum(1 for s in parsed['steps'] if s['status'] == 'passed')
            failed = sum(1 for s in parsed['steps'] if s['status'] == 'failed')
            
            summary_text = f"📊 Report Analysis:\n"
            summary_text += f"- Total steps: {total_steps}\n"
            summary_text += f"- Passed: {passed}\n"
            summary_text += f"- Failed: {failed}\n"
            
            if parsed['errors']:
                summary_text += f"\n❌ Errors found:\n"
                for err in parsed['errors'][:5]:  # Limit to first 5
                    summary_text += f"  - {err[:200]}...\n" if len(err) > 200 else f"  - {err}\n"
            
            if parsed['screenshots']:
                summary_text += f"\n📸 {len(parsed['screenshots'])} screenshot(s) available"
            
            return {
                "content": [{"type": "text", "text": summary_text}],
                "isError": False,
                "parsed_report": parsed
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "content": [{"type": "text", "text": f"Failed to fetch report: {e}"}],
                "isError": True
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error parsing report: {e}"}],
                "isError": True
            }
    
    def _parse_report_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse HTML report into structured data"""
        parsed = {
            'steps': [],
            'errors': [],
            'screenshots': [],
            'summary': {},
            'raw_text': ''
        }
        
        # Try multiple common report formats
        
        # Format 1: Steps with class indicators
        for step in soup.select('.step, .test-step, [class*="step"]'):
            step_data = self._extract_step(step)
            if step_data:
                parsed['steps'].append(step_data)
        
        # Format 2: Table rows
        if not parsed['steps']:
            for row in soup.select('tr'):
                step_data = self._extract_step_from_row(row)
                if step_data:
                    parsed['steps'].append(step_data)
        
        # Extract errors
        for error in soup.select('.error, .failure, .exception, [class*="error"]'):
            error_text = error.get_text(strip=True)
            if error_text:
                parsed['errors'].append(error_text)
        
        # Extract screenshots
        for img in soup.select('img'):
            src = img.get('src', '')
            if src and ('screenshot' in src.lower() or 'capture' in src.lower() or '.png' in src or '.jpg' in src):
                parsed['screenshots'].append({
                    'src': src,
                    'alt': img.get('alt', ''),
                    'step': img.get('data-step', '')
                })
        
        # Get raw text (limited)
        body = soup.find('body')
        if body:
            parsed['raw_text'] = body.get_text(separator='\n', strip=True)[:10000]
        
        return parsed
    
    def _extract_step(self, element) -> Optional[Dict[str, Any]]:
        """Extract step data from a step element"""
        classes = element.get('class', [])
        text = element.get_text(strip=True)
        
        if not text:
            return None
        
        # Determine status from classes
        status = 'unknown'
        class_str = ' '.join(classes).lower()
        if 'pass' in class_str or 'success' in class_str:
            status = 'passed'
        elif 'fail' in class_str or 'error' in class_str:
            status = 'failed'
        elif 'skip' in class_str:
            status = 'skipped'
        
        # Try to extract step name and details
        name_elem = element.select_one('.step-name, .name, h3, h4, strong')
        name = name_elem.get_text(strip=True) if name_elem else text[:100]
        
        duration_elem = element.select_one('.duration, .time, [class*="duration"]')
        duration = duration_elem.get_text(strip=True) if duration_elem else None
        
        error_elem = element.select_one('.error, .message, [class*="error"]')
        error = error_elem.get_text(strip=True) if error_elem else None
        
        return {
            'name': name,
            'status': status,
            'duration': duration,
            'error': error
        }
    
    def _extract_step_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract step data from a table row"""
        cells = row.select('td')
        if len(cells) < 2:
            return None
        
        text = ' '.join(c.get_text(strip=True) for c in cells)
        if not text.strip():
            return None
        
        # Determine status
        status = 'unknown'
        row_text = text.lower()
        if 'pass' in row_text or '✓' in text or '✅' in text:
            status = 'passed'
        elif 'fail' in row_text or '✗' in text or '❌' in text:
            status = 'failed'
        elif 'skip' in row_text:
            status = 'skipped'
        
        return {
            'name': cells[0].get_text(strip=True)[:200],
            'status': status,
            'duration': cells[-1].get_text(strip=True) if len(cells) > 2 else None,
            'error': None
        }
    
    def fetch_execution_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch raw execution logs from URL.
        Truncates to 50KB to avoid token explosion.
        """
        logs_url = params.get('logs_url')
        
        if not logs_url:
            return {
                "content": [{"type": "text", "text": "Error: logs_url is required"}],
                "isError": True
            }
        
        try:
            print(f"[@analysis:fetch_logs] Fetching: {logs_url}")
            response = requests.get(logs_url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            max_size = 50000  # 50KB limit
            truncated = len(content) > max_size
            
            if truncated:
                # Keep first and last portions
                content = content[:25000] + "\n\n... [TRUNCATED] ...\n\n" + content[-25000:]
            
            return {
                "content": [{"type": "text", "text": content}],
                "isError": False,
                "truncated": truncated,
                "original_size": len(response.text)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "content": [{"type": "text", "text": f"Failed to fetch logs: {e}"}],
                "isError": True
            }
    
    def get_last_execution_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the most recent execution event from the event bus.
        Useful when analyzer needs context about what to analyze.
        """
        event = self.event_bus.get_last_event()
        
        if not event:
            return {
                "content": [{"type": "text", "text": "No recent execution events found"}],
                "isError": False
            }
        
        # Format event data
        status = "✅ PASSED" if event.success else "❌ FAILED"
        duration_s = event.execution_time_ms / 1000
        
        text = f"📋 Last Execution Event:\n"
        text += f"- Script: {event.script_name}\n"
        text += f"- Status: {status}\n"
        text += f"- Exit Code: {event.exit_code}\n"
        text += f"- Duration: {duration_s:.1f}s\n"
        text += f"- Device: {event.device_id} on {event.host_name}\n"
        text += f"- Report: {event.report_url}\n"
        text += f"- Logs: {event.logs_url}\n"
        text += f"- Timestamp: {event.timestamp.isoformat()}"
        
        return {
            "content": [{"type": "text", "text": text}],
            "isError": False,
            "event": event.to_dict()
        }
    
    def get_execution_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get execution status by task ID from the server"""
        task_id = params.get('task_id')
        
        if not task_id:
            return {
                "content": [{"type": "text", "text": "Error: task_id is required"}],
                "isError": True
            }
        
        # This would call the server endpoint
        # For now, check the event bus for matching execution
        events = self.event_bus.get_recent_events(100)
        for event in reversed(events):
            if event.execution_id == task_id:
                status = "✅ PASSED" if event.success else "❌ FAILED"
                return {
                    "content": [{"type": "text", "text": f"Execution {task_id}: {status}"}],
                    "isError": False,
                    "event": event.to_dict()
                }
        
        return {
            "content": [{"type": "text", "text": f"Execution {task_id} not found in recent events"}],
            "isError": False
        }
    
    def get_analysis_queue_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get status of the background analysis queue.
        
        Returns queue size, current task, and processing status.
        Chat requests bypass this queue and are processed immediately.
        """
        status = self.analysis_queue.get_status()
        
        text = "📊 Analysis Queue Status:\n"
        text += f"- Pending tasks: {status['queue_size']}\n"
        text += f"- Currently processing: {'Yes' if status['processing'] else 'No'}\n"
        
        if status['current_task']:
            text += f"- Current task: {status['current_task']}\n"
        
        text += f"- Worker running: {'Yes' if status['worker_alive'] else 'No'}\n"
        text += f"- Completed analyses: {status['completed_count']}\n"
        text += "\n💡 Note: Chat requests bypass the queue and are processed immediately."
        
        return {
            "content": [{"type": "text", "text": text}],
            "isError": False,
            "status": status
        }
