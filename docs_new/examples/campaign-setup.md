# Campaign Setup Examples

**How to create and manage test campaigns for batch execution.**

---

## 🎯 **What are Campaigns?**

Campaigns allow you to:
- **Group multiple tests** together
- **Run tests in sequence** or parallel
- **Schedule automated execution**
- **Generate comprehensive reports**
- **Handle failures gracefully**

---

## 🚀 **Quick Campaign Examples**

### Basic Campaign Execution
```bash
# Run the default campaign
python test_campaign/campaign_fullzap.py

# Run with specific devices
python test_campaign/campaign_fullzap.py --devices device1,device2

# Run with custom parameters
python test_campaign/campaign_fullzap.py --max_iteration 20 --goto_live true
```

---

## 📋 **Campaign Configuration**

### Simple Campaign Config
```python
# campaign_config.py
campaign_config = {
    "name": "Basic Navigation Campaign",
    "description": "Test basic navigation across devices",
    "tests": [
        {
            "script": "goto.py",
            "args": "--node home",
            "description": "Navigate to home screen"
        },
        {
            "script": "goto.py", 
            "args": "--node live",
            "description": "Navigate to live TV"
        },
        {
            "script": "goto.py",
            "args": "--node settings",
            "description": "Navigate to settings"
        }
    ],
    "devices": ["device1", "device2"],
    "execution_mode": "sequential",
    "stop_on_failure": False
}
```

### Advanced Campaign Config
```python
# advanced_campaign_config.py
advanced_campaign = {
    "name": "Comprehensive Test Suite",
    "description": "Full device validation and performance testing",
    "tests": [
        # Setup phase
        {
            "script": "goto.py",
            "args": "--node home",
            "description": "Reset to home screen",
            "phase": "setup",
            "timeout": 30
        },
        
        # Navigation tests
        {
            "script": "goto.py",
            "args": "--node live",
            "description": "Test live TV navigation",
            "phase": "navigation",
            "timeout": 45
        },
        {
            "script": "goto.py",
            "args": "--node live_fullscreen",
            "description": "Test fullscreen navigation", 
            "phase": "navigation",
            "timeout": 60
        },
        
        # Performance tests
        {
            "script": "fullzap.py",
            "args": "--max_iteration 10 --action live_chup",
            "description": "Channel zapping performance",
            "phase": "performance",
            "timeout": 300
        },
        
        # Validation tests
        {
            "script": "validation.py",
            "args": "--focus_video_validation",
            "description": "Video quality validation",
            "phase": "validation",
            "timeout": 180
        }
    ],
    "devices": ["device1", "device2", "device3"],
    "execution_mode": "parallel",
    "max_parallel": 2,
    "stop_on_failure": True,
    "retry_failed": True,
    "retry_count": 2,
    "cleanup_on_failure": True
}
```

---

## 🏗️ **Creating Custom Campaigns**

### Campaign Script Template
```python
#!/usr/bin/env python3
"""
Custom Campaign Script Template
"""
import sys
import os
import time
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor

class CampaignExecutor:
    def __init__(self, campaign_name: str, campaign_config: dict):
        self.campaign_name = campaign_name
        self.config = campaign_config
        self.results = []
        
    def execute_campaign(self, devices: list = None):
        """Execute the campaign on specified devices"""
        target_devices = devices or self.config.get('devices', ['device1'])
        
        print(f"🚀 Starting campaign: {self.campaign_name}")
        print(f"📱 Target devices: {', '.join(target_devices)}")
        print(f"🧪 Tests to run: {len(self.config['tests'])}")
        
        campaign_start = datetime.now()
        
        for device in target_devices:
            print(f"\n📱 Running campaign on {device}")
            device_results = self.execute_device_campaign(device)
            self.results.append({
                'device': device,
                'results': device_results,
                'success_rate': self.calculate_success_rate(device_results)
            })
        
        campaign_duration = datetime.now() - campaign_start
        self.generate_campaign_report(campaign_duration)
        
    def execute_device_campaign(self, device: str) -> list:
        """Execute campaign tests on a specific device"""
        device_results = []
        
        for i, test in enumerate(self.config['tests'], 1):
            print(f"  🧪 Test {i}/{len(self.config['tests'])}: {test['description']}")
            
            # Build command
            script_path = f"test_scripts/{test['script']}"
            args = test.get('args', '')
            device_arg = f"--device {device}"
            command = f"python {script_path} {args} {device_arg}"
            
            # Execute test
            start_time = datetime.now()
            result = self.execute_test_command(command, test.get('timeout', 60))
            duration = datetime.now() - start_time
            
            test_result = {
                'test_name': test['description'],
                'script': test['script'],
                'success': result['success'],
                'duration': duration.total_seconds(),
                'output': result['output'],
                'error': result.get('error')
            }
            
            device_results.append(test_result)
            
            # Handle failure
            if not result['success'] and self.config.get('stop_on_failure', False):
                print(f"  ❌ Test failed, stopping campaign (stop_on_failure=True)")
                break
                
            # Wait between tests
            if i < len(self.config['tests']):
                time.sleep(2)
        
        return device_results
    
    def execute_test_command(self, command: str, timeout: int) -> dict:
        """Execute a test command with timeout"""
        import subprocess
        
        try:
            result = subprocess.run(
                command.split(),
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Test timed out after {timeout} seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def calculate_success_rate(self, results: list) -> float:
        """Calculate success rate for device results"""
        if not results:
            return 0.0
        
        successful = sum(1 for r in results if r['success'])
        return (successful / len(results)) * 100
    
    def generate_campaign_report(self, duration):
        """Generate and display campaign report"""
        print(f"\n📊 Campaign Report: {self.campaign_name}")
        print(f"⏱️  Total Duration: {duration}")
        print(f"📱 Devices Tested: {len(self.results)}")
        
        overall_success = 0
        total_tests = 0
        
        for device_result in self.results:
            device = device_result['device']
            success_rate = device_result['success_rate']
            test_count = len(device_result['results'])
            
            print(f"  📱 {device}: {success_rate:.1f}% success ({test_count} tests)")
            
            overall_success += sum(1 for r in device_result['results'] if r['success'])
            total_tests += test_count
        
        overall_rate = (overall_success / total_tests * 100) if total_tests > 0 else 0
        print(f"🎯 Overall Success Rate: {overall_rate:.1f}%")
        
        # Save detailed report
        self.save_detailed_report(duration, overall_rate)
    
    def save_detailed_report(self, duration, success_rate):
        """Save detailed report to file"""
        report_filename = f"campaign_report_{self.campaign_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'campaign_name': self.campaign_name,
            'execution_time': datetime.now().isoformat(),
            'duration_seconds': duration.total_seconds(),
            'overall_success_rate': success_rate,
            'device_results': self.results
        }
        
        import json
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved: {report_filename}")

# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Execute test campaign')
    parser.add_argument('--devices', type=str, help='Comma-separated device list')
    parser.add_argument('--config', type=str, default='basic', help='Campaign configuration')
    args = parser.parse_args()
    
    # Load campaign configuration
    if args.config == 'basic':
        from campaign_configs import basic_campaign_config as config
    elif args.config == 'advanced':
        from campaign_configs import advanced_campaign_config as config
    else:
        print(f"❌ Unknown config: {args.config}")
        sys.exit(1)
    
    # Parse devices
    devices = args.devices.split(',') if args.devices else None
    
    # Execute campaign
    executor = CampaignExecutor("Custom Campaign", config)
    executor.execute_campaign(devices)
```

---

## 📊 **Campaign Monitoring**

### Real-Time Monitoring
```python
def monitor_campaign_execution(campaign_id: str):
    """Monitor campaign execution in real-time"""
    import requests
    import time
    
    server_url = "http://localhost:5109"
    
    while True:
        try:
            response = requests.get(f"{server_url}/api/campaigns/{campaign_id}/status")
            if response.status_code == 200:
                status = response.json()
                
                print(f"📊 Campaign Status: {status['status']}")
                print(f"🧪 Tests Completed: {status['completed']}/{status['total']}")
                print(f"✅ Success Rate: {status['success_rate']:.1f}%")
                
                if status['status'] in ['completed', 'failed']:
                    break
                    
        except requests.RequestException:
            print("❌ Failed to get campaign status")
        
        time.sleep(10)  # Check every 10 seconds
```

### Campaign Metrics
```python
def analyze_campaign_metrics(campaign_results: dict):
    """Analyze campaign execution metrics"""
    
    # Duration analysis
    total_duration = sum(r['duration'] for device in campaign_results['device_results'] 
                        for r in device['results'])
    avg_test_duration = total_duration / len(campaign_results['device_results'])
    
    # Success analysis
    failed_tests = []
    for device in campaign_results['device_results']:
        for result in device['results']:
            if not result['success']:
                failed_tests.append({
                    'device': device['device'],
                    'test': result['test_name'],
                    'error': result.get('error', 'Unknown error')
                })
    
    # Performance analysis
    slowest_tests = sorted(
        [(device['device'], r['test_name'], r['duration']) 
         for device in campaign_results['device_results'] 
         for r in device['results']],
        key=lambda x: x[2], reverse=True
    )[:5]
    
    print("📈 Campaign Metrics Analysis")
    print(f"⏱️  Average test duration: {avg_test_duration:.1f}s")
    print(f"❌ Failed tests: {len(failed_tests)}")
    print(f"🐌 Slowest tests:")
    for device, test, duration in slowest_tests:
        print(f"   {device}: {test} ({duration:.1f}s)")
```

---

## 🔄 **Scheduled Campaigns**

### Cron-based Scheduling
```bash
# Add to crontab for daily execution
0 2 * * * cd /path/to/virtualpytest && python test_campaign/nightly_regression.py

# Weekly comprehensive testing
0 1 * * 0 cd /path/to/virtualpytest && python test_campaign/weekly_comprehensive.py

# Hourly health checks
0 * * * * cd /path/to/virtualpytest && python test_campaign/health_check.py
```

### Automated Campaign Script
```python
#!/usr/bin/env python3
"""
Automated scheduled campaign
"""
def scheduled_campaign():
    """Execute scheduled campaign with email notifications"""
    
    # Execute campaign
    executor = CampaignExecutor("Nightly Regression", nightly_config)
    executor.execute_campaign()
    
    # Calculate overall success rate
    overall_success = sum(
        r['success_rate'] for r in executor.results
    ) / len(executor.results) if executor.results else 0
    
    # Send notification based on results
    if overall_success < 80:
        send_alert_email(
            subject="❌ Campaign Failed",
            message=f"Nightly regression failed with {overall_success:.1f}% success rate"
        )
    else:
        send_success_email(
            subject="✅ Campaign Completed",
            message=f"Nightly regression completed with {overall_success:.1f}% success rate"
        )

def send_alert_email(subject: str, message: str):
    """Send alert email (implement based on your email service)"""
    # Implementation depends on your email service
    pass

if __name__ == "__main__":
    scheduled_campaign()
```

---

## 🎯 **Campaign Best Practices**

### Design Principles
1. **Start Small**: Begin with simple campaigns, add complexity gradually
2. **Group Logically**: Group related tests together
3. **Handle Failures**: Plan for test failures and recovery
4. **Monitor Progress**: Use real-time monitoring for long campaigns

### Performance Optimization
```python
# Parallel execution for independent tests
campaign_config = {
    "execution_mode": "parallel",
    "max_parallel": 3,  # Don't overload devices
    "tests": [
        # Tests that can run in parallel
    ]
}

# Sequential execution for dependent tests
campaign_config = {
    "execution_mode": "sequential",
    "tests": [
        {"script": "setup.py"},      # Must run first
        {"script": "main_test.py"},  # Depends on setup
        {"script": "cleanup.py"}     # Must run last
    ]
}
```

### Error Handling
```python
# Robust error handling in campaigns
campaign_config = {
    "stop_on_failure": False,     # Continue even if tests fail
    "retry_failed": True,         # Retry failed tests
    "retry_count": 2,            # Maximum retry attempts
    "cleanup_on_failure": True,   # Clean up after failures
    "timeout_per_test": 120      # Prevent hanging tests
}
```

---

## 📊 **Campaign Reporting**

### HTML Report Generation
```python
def generate_html_report(campaign_results: dict) -> str:
    """Generate HTML report for campaign results"""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Campaign Report: {campaign_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .success {{ color: green; }}
            .failure {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Campaign Report: {campaign_name}</h1>
        <p>Execution Time: {execution_time}</p>
        <p>Overall Success Rate: <span class="{overall_class}">{success_rate:.1f}%</span></p>
        
        <h2>Device Results</h2>
        <table>
            <tr><th>Device</th><th>Success Rate</th><th>Tests</th><th>Duration</th></tr>
            {device_rows}
        </table>
        
        <h2>Test Details</h2>
        {test_details}
    </body>
    </html>
    """
    
    # Generate device rows
    device_rows = ""
    for device_result in campaign_results['device_results']:
        device = device_result['device']
        success_rate = device_result['success_rate']
        test_count = len(device_result['results'])
        total_duration = sum(r['duration'] for r in device_result['results'])
        
        status_class = "success" if success_rate >= 80 else "failure"
        
        device_rows += f"""
        <tr>
            <td>{device}</td>
            <td class="{status_class}">{success_rate:.1f}%</td>
            <td>{test_count}</td>
            <td>{total_duration:.1f}s</td>
        </tr>
        """
    
    # Format and return HTML
    return html_template.format(
        campaign_name=campaign_results['campaign_name'],
        execution_time=campaign_results['execution_time'],
        success_rate=campaign_results['overall_success_rate'],
        overall_class="success" if campaign_results['overall_success_rate'] >= 80 else "failure",
        device_rows=device_rows,
        test_details=""  # Add detailed test results if needed
    )
```

---

**Ready for advanced customization? Check [Custom Controllers Examples](custom-controllers.md)!** 🔧
