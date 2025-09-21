"""
Server API Testing Routes

Comprehensive API endpoint testing with HTML report generation and R2 storage.
Minimalist approach for testing all server routes systematically.
"""

import json
import time
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
import requests
import subprocess

# Create blueprint
server_api_testing_bp = Blueprint('server_api_testing', __name__, url_prefix='/server/api-testing')

# Default values for API testing
DEFAULT_VALUES = {
    "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    "host_name": "sunri-pi1",
    "device_id": "device1", 
    "device_model": "android_mobile",
    "userinterface_name": "horizon_android_mobile"
}

# Test configuration - comprehensive server endpoints
TEST_CONFIG = {
    "endpoints": [
        # ========================================
        # CRITICAL ENDPOINTS (Must always work)
        # ========================================
        {
            "name": "System Health",
            "method": "GET",
            "url": "/server/system/health",
            "expected_status": [200],
            "category": "critical"
        },
        {
            "name": "System Status",
            "method": "GET", 
            "url": "/server/system/status",
            "expected_status": [200],
            "category": "critical"
        },
        {
            "name": "Get Locked Devices",
            "method": "GET",
            "url": "/server/control/lockedDevices",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "critical"
        },
        {
            "name": "Take Control",
            "method": "POST",
            "url": "/server/control/takeControl",
            "body": {
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "expected_status": [200, 400, 404],
            "category": "critical"
        },
        
        # ========================================
        # AI & EXECUTION ENDPOINTS
        # ========================================
        {
            "name": "AI Task Execution",
            "method": "POST",
            "url": "/server/ai-execution/executeTask",
            "body": {
                "task_description": "go to live",
                "userinterface_name": DEFAULT_VALUES["userinterface_name"],
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200, 202, 400],
            "category": "core"
        },
        {
            "name": "AI Plan Generation",
            "method": "POST",
            "url": "/server/ai-generation/generatePlan",
            "body": {
                "prompt": "go to live",
                "userinterface_name": DEFAULT_VALUES["userinterface_name"],
                "device_model": DEFAULT_VALUES["device_model"]
            },
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200, 400],
            "category": "core"
        },
        
        # ========================================
        # NAVIGATION ENDPOINTS
        # ========================================
        {
            "name": "Get Navigation Nodes",
            "method": "GET",
            "url": "/server/navigation/getNodes",
            "params": {
                "device_model": DEFAULT_VALUES["device_model"],
                "userinterface_name": DEFAULT_VALUES["userinterface_name"],
                "team_id": DEFAULT_VALUES["team_id"]
            },
            "expected_status": [200, 404],
            "category": "core"
        },
        {
            "name": "Execute Navigation",
            "method": "POST",
            "url": "/server/navigation/executeNavigation",
            "body": {
                "tree_id": "test-tree-id",
                "target_node_id": "live",
                "current_node_id": "home",
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200, 400, 404],
            "category": "core"
        },
        {
            "name": "Get Navigation Trees",
            "method": "GET",
            "url": "/server/navigationTrees/getNavigationTrees",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "core"
        },
        
        # ========================================
        # ACTION & VERIFICATION ENDPOINTS
        # ========================================
        {
            "name": "Get Actions",
            "method": "GET",
            "url": "/server/action/getActions",
            "params": {"device_model": DEFAULT_VALUES["device_model"]},
            "expected_status": [200],
            "category": "core"
        },
        {
            "name": "Execute Actions",
            "method": "POST",
            "url": "/server/action/executeBatch",
            "body": {
                "actions": [{
                    "command": "press_key",
                    "params": {"key": "HOME"},
                    "action_type": "remote"
                }],
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "expected_status": [200, 400, 404],
            "category": "core"
        },
        {
            "name": "Get Verifications",
            "method": "GET",
            "url": "/server/verification/getVerifications",
            "params": {"device_model": DEFAULT_VALUES["device_model"]},
            "expected_status": [200],
            "category": "core"
        },
        
        # ========================================
        # CAMPAIGN & SCRIPT ENDPOINTS
        # ========================================
        {
            "name": "Get Campaigns",
            "method": "GET",
            "url": "/server/campaign/getCampaigns",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "core"
        },
        {
            "name": "Get Scripts",
            "method": "GET",
            "url": "/server/script/getScripts",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "core"
        },
        {
            "name": "Execute Script",
            "method": "POST",
            "url": "/server/script/executeScript",
            "body": {
                "script_name": "test_script",
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"],
                "userinterface_name": DEFAULT_VALUES["userinterface_name"]
            },
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200, 202, 400, 404],
            "category": "core"
        },
        
        # ========================================
        # CONFIGURATION ENDPOINTS
        # ========================================
        {
            "name": "Get User Interfaces",
            "method": "GET",
            "url": "/server/userinterface/getUserInterfaces",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "config"
        },
        {
            "name": "Get Device Models",
            "method": "GET",
            "url": "/server/devicemodel/getDeviceModels",
            "expected_status": [200],
            "category": "config"
        },
        {
            "name": "Get Devices",
            "method": "GET",
            "url": "/server/device/getDevices",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "config"
        },
        
        # ========================================
        # MONITORING & METRICS ENDPOINTS
        # ========================================
        {
            "name": "Get System Metrics",
            "method": "GET",
            "url": "/server/metrics/getSystemMetrics",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200, 404],
            "category": "monitoring"
        },
        {
            "name": "Get Alerts",
            "method": "GET",
            "url": "/server/alerts/getAlerts",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "monitoring"
        },
        
        # ========================================
        # RESULTS & ANALYTICS ENDPOINTS
        # ========================================
        {
            "name": "Get Execution Results",
            "method": "GET",
            "url": "/server/execution-results/getResults",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "analytics"
        },
        {
            "name": "Get Script Results",
            "method": "GET",
            "url": "/server/script-results/getResults",
            "params": {"team_id": DEFAULT_VALUES["team_id"]},
            "expected_status": [200],
            "category": "analytics"
        },
        
        # ========================================
        # REMOTE & STREAM ENDPOINTS
        # ========================================
        {
            "name": "Take Screenshot",
            "method": "POST",
            "url": "/server/remote/takeScreenshot",
            "body": {
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "expected_status": [200, 400, 404],
            "category": "remote"
        },
        {
            "name": "Execute Remote Command",
            "method": "POST",
            "url": "/server/remote/executeCommand",
            "body": {
                "command": "press_key",
                "params": {"key": "HOME"},
                "host_name": DEFAULT_VALUES["host_name"],
                "device_id": DEFAULT_VALUES["device_id"]
            },
            "expected_status": [200, 400, 404],
            "category": "remote"
        }
    ]
}

def get_git_commit():
    """Get current git commit hash"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              capture_output=True, text=True, cwd='.')
        return result.stdout.strip() if result.returncode == 0 else 'unknown'
    except:
        return 'unknown'

def execute_single_test(test_config, base_url=None):
    """Execute a single API test"""
    start_time = time.time()
    
    # Get base URL from environment or default
    if base_url is None:
        import os
        base_url = os.getenv('SERVER_URL', 'http://localhost:5109')
    
    try:
        url = f"{base_url}{test_config['url']}"
        method = test_config['method']
        
        # Prepare request parameters
        kwargs = {
            'timeout': 10,
            'headers': {'Content-Type': 'application/json'}
        }
        
        if 'params' in test_config:
            kwargs['params'] = test_config['params']
            
        if 'body' in test_config and method in ['POST', 'PUT', 'PATCH']:
            kwargs['json'] = test_config['body']
        
        # Execute request
        response = requests.request(method, url, **kwargs)
        response_time = int((time.time() - start_time) * 1000)
        
        # Check if status code is expected
        expected_statuses = test_config.get('expected_status', [200])
        status = 'pass' if response.status_code in expected_statuses else 'fail'
        
        return {
            'endpoint': test_config['name'],
            'method': method,
            'url': test_config['url'],
            'status': status,
            'status_code': response.status_code,
            'response_time': response_time,
            'error': None if status == 'pass' else f"Expected {expected_statuses}, got {response.status_code}"
        }
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return {
            'endpoint': test_config['name'],
            'method': test_config.get('method', 'GET'),
            'url': test_config['url'],
            'status': 'fail',
            'status_code': None,
            'response_time': response_time,
            'error': str(e)
        }

def generate_html_report(report_data):
    """Generate HTML report"""
    passed = sum(1 for r in report_data['results'] if r['status'] == 'pass')
    failed = sum(1 for r in report_data['results'] if r['status'] == 'fail')
    percentage = int((passed / len(report_data['results'])) * 100) if report_data['results'] else 0
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>API Test Report - {report_data['timestamp']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .pass {{ color: #4caf50; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .status-pass {{ background-color: #e8f5e8; }}
        .status-fail {{ background-color: #ffeaea; }}
    </style>
</head>
<body>
    <div class="summary">
        <h1>API Test Report</h1>
        <p><strong>Git Commit:</strong> {report_data['git_commit']}</p>
        <p><strong>Timestamp:</strong> {report_data['timestamp']}</p>
        <p><strong>Results:</strong> <span class="pass">{passed} passed</span>, <span class="fail">{failed} failed</span> ({percentage}%)</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Endpoint</th>
                <th>Method</th>
                <th>Status</th>
                <th>Status Code</th>
                <th>Response Time</th>
                <th>Error</th>
            </tr>
        </thead>
        <tbody>"""
    
    for result in report_data['results']:
        status_class = f"status-{result['status']}"
        status_text = "✅ PASS" if result['status'] == 'pass' else "❌ FAIL"
        error_text = result.get('error', '') or ''
        status_code = result.get('status_code', 'N/A')
        
        html += f"""
            <tr class="{status_class}">
                <td>{result['endpoint']}</td>
                <td>{result['method']}</td>
                <td class="{result['status']}">{status_text}</td>
                <td>{status_code}</td>
                <td>{result['response_time']}ms</td>
                <td>{error_text}</td>
            </tr>"""
    
    html += """
        </tbody>
    </table>
</body>
</html>"""
    
    return html

@server_api_testing_bp.route('/run', methods=['POST'])
def run_tests():
    """Execute selected API tests and return results"""
    try:
        data = request.get_json() or {}
        selected_endpoints = data.get('selected_endpoints', [])
        
        print("[@server_api_testing] Starting API test suite")
        
        # Generate report metadata
        report_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        git_commit = get_git_commit()
        
        # Filter endpoints based on selection
        endpoints_to_test = TEST_CONFIG['endpoints']
        if selected_endpoints:
            endpoints_to_test = [
                endpoint for endpoint in TEST_CONFIG['endpoints']
                if endpoint['name'] in selected_endpoints
            ]
        
        print(f"[@server_api_testing] Testing {len(endpoints_to_test)} selected endpoints")
        
        # Execute selected tests
        results = []
        for test_config in endpoints_to_test:
            print(f"[@server_api_testing] Testing: {test_config['name']}")
            result = execute_single_test(test_config)
            results.append(result)
            print(f"[@server_api_testing] Result: {result['status']} ({result.get('status_code', 'N/A')})")
        
        # Create report data
        report_data = {
            'id': report_id,
            'timestamp': timestamp,
            'git_commit': git_commit,
            'total_tests': len(results),
            'passed': sum(1 for r in results if r['status'] == 'pass'),
            'failed': sum(1 for r in results if r['status'] == 'fail'),
            'results': results
        }
        
        print(f"[@server_api_testing] Test suite completed: {report_data['passed']}/{report_data['total_tests']} passed")
        
        return jsonify({
            'success': True,
            'report': report_data
        })
        
    except Exception as e:
        print(f"[@server_api_testing] Error running tests: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_api_testing_bp.route('/report/<report_id>/html', methods=['GET'])
def get_html_report(report_id):
    """Generate HTML report for a specific test run"""
    try:
        # For now, we'll generate a sample report
        # In production, this would fetch from R2 storage
        sample_report = {
            'id': report_id,
            'timestamp': datetime.now().isoformat(),
            'git_commit': get_git_commit(),
            'results': []
        }
        
        html_content = generate_html_report(sample_report)
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_api_testing_bp.route('/config', methods=['GET'])
def get_test_config():
    """Get current test configuration"""
    return jsonify({
        'success': True,
        'config': TEST_CONFIG,
        'total_endpoints': len(TEST_CONFIG['endpoints'])
    })

@server_api_testing_bp.route('/quick', methods=['POST'])
def quick_test():
    """Run a quick test of critical endpoints only"""
    try:
        # Get only critical endpoints
        critical_endpoints = [
            endpoint for endpoint in TEST_CONFIG['endpoints']
            if endpoint.get('category') == 'critical'
        ]
        
        print(f"[@server_api_testing] Running quick test with {len(critical_endpoints)} critical endpoints")
        
        results = []
        for test_config in critical_endpoints:
            print(f"[@server_api_testing] Quick testing: {test_config['name']}")
            result = execute_single_test(test_config)
            results.append(result)
        
        passed = sum(1 for r in results if r['status'] == 'pass')
        failed = len(results) - passed
        
        # Create a proper report structure like the full test
        report = {
            'id': f"quick-{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'git_commit': get_git_commit(),
            'total_tests': len(results),
            'passed': passed,
            'failed': failed,
            'results': results,
            'quick_test': True
        }
        
        return jsonify({
            'success': True,
            'quick_test': True,
            'passed': passed,
            'total': len(results),
            'results': results,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_api_testing_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get available endpoint categories"""
    try:
        categories = {}
        for endpoint in TEST_CONFIG['endpoints']:
            category = endpoint.get('category', 'uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(endpoint['name'])
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_endpoints': len(TEST_CONFIG['endpoints'])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
