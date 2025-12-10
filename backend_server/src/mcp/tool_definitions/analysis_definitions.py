"""Analysis tool definitions for execution result analysis"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get analysis-related tool definitions"""
    return [
        {
            "name": "fetch_execution_report",
            "description": """Fetch and parse an HTML execution report from URL.

Returns parsed report with:
- Test steps and their status (passed/failed/skipped)
- Error messages and stack traces
- Screenshot references
- Timing information per step

Use this to analyze test failures and detect false positives.

Example:
  fetch_execution_report(report_url='http://host/reports/123/report.html')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "report_url": {
                        "type": "string", 
                        "description": "Full URL of the HTML report (from execute_script result)"
                    }
                },
                "required": ["report_url"]
            }
        },
        {
            "name": "fetch_execution_logs",
            "description": """Fetch raw execution logs from URL.

Returns log content (truncated to 50KB to avoid token explosion).
Use this for detailed debugging when report alone is insufficient.

Example:
  fetch_execution_logs(logs_url='http://host/reports/123/execution.log')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "logs_url": {
                        "type": "string",
                        "description": "Full URL of the logs file (from execute_script result)"
                    }
                },
                "required": ["logs_url"]
            }
        },
        {
            "name": "get_last_execution_event",
            "description": """Get the most recent execution event from the event bus.

Returns execution context including:
- script_name, execution_id
- success status, exit_code, duration
- report_url, logs_url
- host_name, device_id

Use this when you need to analyze the last execution but don't have the URLs.

Example:
  get_last_execution_event()""",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_execution_status",
            "description": """Get execution status by task ID.

Returns current status of an async execution task.

Example:
  get_execution_status(task_id='abc-123')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Execution task ID"
                    }
                },
                "required": ["task_id"]
            }
        },
        {
            "name": "get_analysis_queue_status",
            "description": """Get status of the background analysis queue.

Returns:
- queue_size: Number of pending analysis tasks
- processing: Whether currently processing a task
- current_task: Script name being analyzed (if any)
- completed_count: Number of completed analyses

Use this to check if the analyzer is busy with event-triggered tasks.
Chat requests bypass the queue and are processed immediately.

Example:
  get_analysis_queue_status()""",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]


