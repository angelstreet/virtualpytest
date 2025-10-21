#!/usr/bin/env python3
"""
Browser Task Execution Script for VirtualPyTest

This script navigates to a URL using device.action, waits 10 seconds, 
then executes a browser-use AI task.

Usage:
    python test_scripts/browser_task.py --url <url> --task <task_description>
    
Examples:
    python test_scripts/browser_task.py --url "google.com" --task "Search for Python tutorials"
    python test_scripts/browser_task.py --url "https://youtube.com" --task "Find a video about cats"
    python test_scripts/browser_task.py --url "amazon.com" --task "Search for wireless headphones and show me the top 3 results"
"""

import sys
import os
import time
from typing import Dict, Any

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device

# Script arguments
# MUST be defined near top of file (within first 300 lines) for script analyzer
_script_args = [
    '--url:str:https://youtube.com',                    # URL to navigate to
    '--task:str:Launch funny cat video',  # Browser-use task description
    '--max_steps:int:10'                       # Maximum steps for browser-use (default: 20)
]


def capture_execution_summary(context, url: str, task: str, max_steps: int, nav_result: Dict[str, Any] = None, 
                             task_result: Dict[str, Any] = None) -> str:
    """Capture execution summary as text for report"""
    lines = []
    lines.append(f"🎯 [BROWSER_TASK] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"")
    
    # Navigation section
    lines.append(f"🌐 NAVIGATION")
    lines.append(f"   URL: {url}")
    if nav_result:
        nav_success = nav_result.get('success', False)
        nav_time = nav_result.get('execution_time', 0)
        lines.append(f"   Status: {'✅ SUCCESS' if nav_success else '❌ FAILED'}")
        lines.append(f"   Time: {nav_time}ms")
        if nav_success:
            final_url = nav_result.get('url', url)
            final_title = nav_result.get('title', 'Unknown')
            lines.append(f"   Final URL: {final_url}")
            lines.append(f"   Page Title: {final_title}")
        else:
            error = nav_result.get('error', 'Unknown error')
            lines.append(f"   Error: {error}")
    
    lines.append(f"")
    lines.append(f"⏳ WAIT: 10 seconds")
    lines.append(f"")
    
    # Browser-use task section
    lines.append(f"🤖 BROWSER-USE AI TASK")
    lines.append(f"   Task: {task}")
    lines.append(f"   Max Steps: {max_steps}")
    if task_result:
        task_success = task_result.get('success', False)
        task_time = task_result.get('execution_time', 0)
        lines.append(f"   Status: {'✅ SUCCESS' if task_success else '❌ FAILED'}")
        lines.append(f"   Time: {task_time}ms ({task_time/1000:.1f}s)")
        
        if task_success:
            result_summary = task_result.get('result_summary', 'Task completed')
            lines.append(f"   Result: {result_summary}")
            
            # Add execution logs if available (truncated)
            execution_logs = task_result.get('execution_logs', '')
            if execution_logs:
                log_lines = execution_logs.split('\n')
                lines.append(f"   Logs: {len(log_lines)} lines of execution logs")
                # Show first and last few lines
                if len(log_lines) > 10:
                    lines.append(f"")
                    lines.append(f"   📋 First 5 log lines:")
                    for log_line in log_lines[:5]:
                        if log_line.strip():
                            lines.append(f"      {log_line[:100]}")
                    lines.append(f"   ...")
                    lines.append(f"   📋 Last 5 log lines:")
                    for log_line in log_lines[-5:]:
                        if log_line.strip():
                            lines.append(f"      {log_line[:100]}")
        else:
            error = task_result.get('error', 'Unknown error')
            lines.append(f"   Error: {error}")
    
    lines.append(f"")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    return "\n".join(lines)


@script("browser_task", "Navigate to URL and execute browser-use task")
def main():
    """Main function: navigate to URL, wait, and execute browser-use task"""
    args = get_args()
    context = get_context()
    device = get_device()
    
    url = args.url
    task = args.task
    max_steps = args.max_steps
    
    print(f"🎯 [browser_task] URL: {url}")
    print(f"🎯 [browser_task] Task: {task}")
    print(f"🎯 [browser_task] Max Steps: {max_steps}")
    print(f"📱 [browser_task] Device: {device.device_name} ({device.device_model})")
    
    # Initialize results
    nav_result = None
    task_result = None
    
    # STEP 1: Get web controller to check browser status
    web_controller = device._get_controller('web')
    
    if not web_controller:
        context.error_message = "No web controller available on this device"
        context.overall_success = False
        summary_text = capture_execution_summary(context, url, task, max_steps, nav_result, task_result)
        context.execution_summary = summary_text
        return False
    
    # STEP 2: Ensure browser is open
    print(f"\n📋 [browser_task] ==========================================")
    print(f"📋 [browser_task] CHECKING BROWSER STATUS")
    print(f"📋 [browser_task] ==========================================\n")
    
    if not web_controller.is_connected:
        print(f"🌐 [browser_task] Browser not open, opening browser...")
        open_result = web_controller.open_browser()
        if not open_result.get('success'):
            context.error_message = f"Failed to open browser: {open_result.get('error', 'Unknown error')}"
            context.overall_success = False
            summary_text = capture_execution_summary(context, url, task, max_steps, nav_result, task_result)
            context.execution_summary = summary_text
            return False
        print(f"✅ [browser_task] Browser opened successfully")
    else:
        print(f"✅ [browser_task] Browser already open")
    
    # STEP 3: Navigate to URL using web controller directly
    print(f"\n📋 [browser_task] ==========================================")
    print(f"📋 [browser_task] NAVIGATING TO URL")
    print(f"📋 [browser_task] ==========================================\n")
    
    print(f"🌐 [browser_task] Navigating to: {url}")
    nav_result = web_controller.navigate_to_url(url)
    
    if not nav_result.get('success'):
        context.error_message = f"Navigation failed: {nav_result.get('error', 'Unknown error')}"
        context.overall_success = False
        summary_text = capture_execution_summary(context, url, task, max_steps, nav_result, task_result)
        context.execution_summary = summary_text
        return False
    
    final_url = nav_result.get('url', url)
    page_title = nav_result.get('title', 'Unknown')
    print(f"✅ [browser_task] Navigation successful!")
    print(f"   Final URL: {final_url}")
    print(f"   Page Title: {page_title}")
    
    # STEP 4: Wait 10 seconds
    print(f"\n⏳ [browser_task] Waiting 10 seconds before executing task...")
    time.sleep(10)
    print(f"✅ [browser_task] Wait complete")
    
    # STEP 5: Execute browser-use task
    print(f"\n📋 [browser_task] ==========================================")
    print(f"📋 [browser_task] EXECUTING BROWSER-USE TASK")
    print(f"📋 [browser_task] ==========================================\n")
    
    # Add context to task
    task_with_context = f"You are on website {final_url}\n\nExecute task: {task}"
    
    print(f"🤖 [browser_task] Task: {task}")
    print(f"🤖 [browser_task] Context: You are on website {final_url}")
    print(f"🤖 [browser_task] Max Steps: {max_steps}")
    task_result = web_controller.browser_use_task(task_with_context, max_steps=max_steps)
    
    if not task_result.get('success'):
        print(f"❌ [browser_task] Task execution failed: {task_result.get('error', 'Unknown error')}")
        context.error_message = f"Browser-use task failed: {task_result.get('error', 'Unknown error')}"
        context.overall_success = False
        summary_text = capture_execution_summary(context, url, task, max_steps, nav_result, task_result)
        context.execution_summary = summary_text
        return False
    
    print(f"✅ [browser_task] Task execution complete!")
    print(f"   Result: {task_result.get('result_summary', 'Task completed')}")
    print(f"   Time: {task_result.get('execution_time', 0)}ms")
    
    # STEP 6: Set overall success and capture summary
    context.overall_success = True
    
    # Store task result in metadata for later analysis
    context.metadata = {
        "url": url,
        "task": task,
        "navigation_result": nav_result,
        "task_result": task_result,
        "final_url": final_url,
        "page_title": page_title
    }
    
    # Capture summary
    summary_text = capture_execution_summary(context, url, task, max_steps, nav_result, task_result)
    context.execution_summary = summary_text
    
    return True


# Assign script arguments to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()

