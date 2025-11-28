#!/usr/bin/env python3

"""
Parse security reports (Bandit JSON + Safety text + npm audit) into compact HTML
Outputs directly to docs/security/ for static serving
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Define paths
DOCS_SECURITY = Path("docs/security")
TEMP_DIR = DOCS_SECURITY / "temp"

HOST_BANDIT_JSON = TEMP_DIR / "host_bandit.json"
SERVER_BANDIT_JSON = TEMP_DIR / "server_bandit.json"
HOST_SAFETY_TXT = TEMP_DIR / "host_safety.txt"
SERVER_SAFETY_TXT = TEMP_DIR / "server_safety.txt"
FRONTEND_AUDIT_JSON = TEMP_DIR / "frontend_audit.json"

OUTPUT_HTML = DOCS_SECURITY / "index.html"
OUTPUT_HOST_JSON = DOCS_SECURITY / "host-report.json"
OUTPUT_SERVER_JSON = DOCS_SECURITY / "server-report.json"
OUTPUT_FRONTEND_JSON = DOCS_SECURITY / "frontend-report.json"


def parse_bandit_report(json_path):
    """Parse Bandit JSON report"""
    if not json_path.exists():
        return None
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    metrics = data.get('metrics', {}).get('_totals', {})
    results = data.get('results', [])
    
    # Group by severity
    by_severity = {
        'HIGH': [r for r in results if r.get('issue_severity') == 'HIGH'],
        'MEDIUM': [r for r in results if r.get('issue_severity') == 'MEDIUM'],
        'LOW': [r for r in results if r.get('issue_severity') == 'LOW']
    }
    
    return {
        'metrics': metrics,
        'by_severity': by_severity,
        'total_issues': len(results),
        'raw_data': data
    }


def parse_safety_report(txt_path):
    """Parse Safety text report"""
    if not txt_path.exists():
        return None
    
    with open(txt_path, 'r') as f:
        content = f.read()
    
    if 'command not found' in content or 'not installed' in content:
        return {'status': 'not_installed', 'count': 0}
    
    if 'No known security vulnerabilities' in content:
        return {'status': 'clean', 'count': 0}
    
    # Extract count
    import re
    match = re.search(r'(\d+)\s+vulnerabilities?\s+IGNORED', content)
    if match:
        return {'status': 'ignored', 'count': int(match.group(1))}
    
    return {'status': 'unknown', 'count': 0}


def parse_npm_audit(json_path):
    """Parse npm audit JSON report"""
    if not json_path.exists():
        return None
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'error' in data:
            return {'status': 'error', 'vulnerabilities': {}, 'total': 0}
        
        metadata = data.get('metadata', {})
        vulnerabilities = metadata.get('vulnerabilities', {})
        total = sum(vulnerabilities.values()) if vulnerabilities else 0
        
        return {
            'status': 'clean' if total == 0 else 'found',
            'vulnerabilities': vulnerabilities,
            'total': total,
            'raw_data': data
        }
    except:
        return {'status': 'error', 'vulnerabilities': {}, 'total': 0}


def generate_html_report():
    """Generate compact HTML security report"""
    
    # Parse all reports
    host_bandit = parse_bandit_report(HOST_BANDIT_JSON)
    server_bandit = parse_bandit_report(SERVER_BANDIT_JSON)
    host_safety = parse_safety_report(HOST_SAFETY_TXT)
    server_safety = parse_safety_report(SERVER_SAFETY_TXT)
    frontend_audit = parse_npm_audit(FRONTEND_AUDIT_JSON)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    
    # Calculate totals
    total_high = 0
    total_medium = 0
    total_low = 0
    
    if host_bandit:
        total_high += len(host_bandit['by_severity']['HIGH'])
        total_medium += len(host_bandit['by_severity']['MEDIUM'])
        total_low += len(host_bandit['by_severity']['LOW'])
    
    if server_bandit:
        total_high += len(server_bandit['by_severity']['HIGH'])
        total_medium += len(server_bandit['by_severity']['MEDIUM'])
        total_low += len(server_bandit['by_severity']['LOW'])
    
    # Save JSON reports
    if host_bandit:
        with open(OUTPUT_HOST_JSON, 'w') as f:
            json.dump(host_bandit['raw_data'], f, indent=2)
    
    if server_bandit:
        with open(OUTPUT_SERVER_JSON, 'w') as f:
            json.dump(server_bandit['raw_data'], f, indent=2)
    
    if frontend_audit and frontend_audit.get('raw_data'):
        with open(OUTPUT_FRONTEND_JSON, 'w') as f:
            json.dump(frontend_audit['raw_data'], f, indent=2)
    
    # Build compact HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 16px;
            color: #333;
            font-size: 14px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: #2c3e50;
            color: white;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header h1 {{ font-size: 18px; font-weight: 600; }}
        .timestamp {{ font-size: 12px; opacity: 0.9; }}
        
        .content {{ padding: 20px; }}
        
        .summary {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 16px;
        }}
        
        .summary-title {{ font-weight: 600; margin-bottom: 10px; font-size: 13px; }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}
        
        .summary-item {{
            text-align: center;
            background: white;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }}
        
        .summary-value {{
            font-size: 28px;
            font-weight: bold;
            line-height: 1;
        }}
        
        .summary-label {{
            font-size: 11px;
            color: #666;
            margin-top: 4px;
            text-transform: uppercase;
        }}
        
        .components-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 16px;
        }}
        
        .component-card {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 12px;
        }}
        
        .component-title {{
            font-size: 13px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
        }}
        
        .metric {{
            background: #f8f9fa;
            padding: 8px 4px;
            border-radius: 3px;
            text-align: center;
            border: 1px solid #e9ecef;
        }}
        
        .metric-value {{
            font-size: 20px;
            font-weight: bold;
            line-height: 1;
        }}
        
        .metric-label {{
            font-size: 10px;
            color: #666;
            margin-top: 2px;
        }}
        
        .status-note {{
            font-size: 11px;
            margin-top: 8px;
            padding: 6px 8px;
            background: #fff3cd;
            border-left: 3px solid #ffc107;
            border-radius: 2px;
            color: #856404;
        }}
        
        .downloads {{
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 4px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}
        
        .downloads-title {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }}
        
        .downloads a {{
            display: inline-block;
            margin: 0 6px;
            padding: 6px 12px;
            background: #2c3e50;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 12px;
        }}
        
        .downloads a:hover {{ background: #34495e; }}
        
        .severity-high {{ color: #dc3545; }}
        .severity-medium {{ color: #ff9800; }}
        .severity-low {{ color: #28a745; }}
        
        @media (max-width: 1200px) {{
            .components-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 768px) {{
            .components-grid {{ grid-template-columns: 1fr; }}
            .summary-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Security Report</h1>
            <div class="timestamp">{timestamp}</div>
        </div>
        
        <div class="content">
            <div class="summary">
                <div class="summary-title">Total Security Issues</div>
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="summary-value severity-high">{total_high}</div>
                        <div class="summary-label">High</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value severity-medium">{total_medium}</div>
                        <div class="summary-label">Medium</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value severity-low">{total_low}</div>
                        <div class="summary-label">Low</div>
                    </div>
                </div>
            </div>
            
            <div class="components-grid">
"""
    
    # Host Card
    if host_bandit:
        html += f"""
                <div class="component-card">
                    <div class="component-title">Backend Host</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value severity-high">{len(host_bandit['by_severity']['HIGH'])}</div>
                            <div class="metric-label">High</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-medium">{len(host_bandit['by_severity']['MEDIUM'])}</div>
                            <div class="metric-label">Medium</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-low">{len(host_bandit['by_severity']['LOW'])}</div>
                            <div class="metric-label">Low</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{host_bandit['metrics'].get('loc', 0)}</div>
                            <div class="metric-label">Lines</div>
                        </div>
                    </div>
"""
        if host_safety and host_safety.get('count', 0) > 0:
            html += f'<div class="status-note">⚠️ {host_safety["count"]} dependency issues (unpinned)</div>'
        html += "</div>"
    
    # Server Card
    if server_bandit:
        html += f"""
                <div class="component-card">
                    <div class="component-title">Backend Server</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value severity-high">{len(server_bandit['by_severity']['HIGH'])}</div>
                            <div class="metric-label">High</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-medium">{len(server_bandit['by_severity']['MEDIUM'])}</div>
                            <div class="metric-label">Medium</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-low">{len(server_bandit['by_severity']['LOW'])}</div>
                            <div class="metric-label">Low</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{server_bandit['metrics'].get('loc', 0)}</div>
                            <div class="metric-label">Lines</div>
                        </div>
                    </div>
"""
        if server_safety and server_safety.get('count', 0) > 0:
            html += f'<div class="status-note">⚠️ {server_safety["count"]} dependency issues (unpinned)</div>'
        html += "</div>"
    
    # Frontend Card
    if frontend_audit and frontend_audit['status'] != 'error':
        vulns = frontend_audit.get('vulnerabilities', {})
        html += f"""
                <div class="component-card">
                    <div class="component-title">Frontend</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value severity-high">{vulns.get('critical', 0) + vulns.get('high', 0)}</div>
                            <div class="metric-label">High</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-medium">{vulns.get('moderate', 0)}</div>
                            <div class="metric-label">Medium</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value severity-low">{vulns.get('low', 0)}</div>
                            <div class="metric-label">Low</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{frontend_audit.get('total', 0)}</div>
                            <div class="metric-label">Total</div>
                        </div>
                    </div>
                </div>
"""
    
    html += """
            </div>
            
            <div class="downloads">
                <div class="downloads-title">Raw Data Downloads</div>
                <a href="host-report.json" download>📄 Host JSON</a>
                <a href="server-report.json" download>📄 Server JSON</a>
                <a href="frontend-report.json" download>📄 Frontend JSON</a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    # Write HTML
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    
    print(f"✅ Generated: {OUTPUT_HTML}")
    if host_bandit:
        print(f"✅ Generated: {OUTPUT_HOST_JSON}")
    if server_bandit:
        print(f"✅ Generated: {OUTPUT_SERVER_JSON}")
    if frontend_audit and frontend_audit.get('raw_data'):
        print(f"✅ Generated: {OUTPUT_FRONTEND_JSON}")


if __name__ == '__main__':
    generate_html_report()

