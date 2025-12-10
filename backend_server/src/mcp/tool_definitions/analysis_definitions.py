"""Analysis tool definitions"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get analysis tool definitions"""
    return [
        {
            "name": "get_execution_result",
            "description": """Fetch and parse execution report and logs from URLs.

Returns parsed content for analysis:
- Report: steps, errors, raw text
- Logs: content (truncated)

Use this to get detailed execution data, then classify as:
- BUG: Real application issue
- SCRIPT_ISSUE: Test/automation problem
- SYSTEM_ISSUE: Infrastructure problem

Example:
  get_execution_result(report_url='https://...', logs_url='https://...')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "report_url": {
                        "type": "string",
                        "description": "URL to the HTML execution report"
                    },
                    "logs_url": {
                        "type": "string",
                        "description": "URL to the logs file (optional)"
                    }
                },
                "required": ["report_url"]
            }
        }
    ]
