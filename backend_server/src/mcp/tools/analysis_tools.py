"""
Analysis Tools

Tool for fetching and parsing execution reports and logs.
Data comes from queue task, not database.
"""

import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup


class AnalysisTools:
    """Tools for analyzing execution results"""
    
    def get_execution_result(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
