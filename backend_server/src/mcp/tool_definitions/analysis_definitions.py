"""Analysis tool definitions for execution result analysis"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get analysis tool definitions"""
    return [
        {
            "name": "fetch_execution_report",
            "description": """Fetch and parse execution report and logs from URLs.

Returns parsed content for analysis:
- Report: steps, errors, raw text
- Logs: content (truncated)

Use this after get_execution_results to fetch detailed report content.

Example:
  fetch_execution_report(report_url='https://...', logs_url='https://...')""",
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
        },
        {
            "name": "get_execution_results",
            "description": """Get execution results from database with filters.

Query script_results table by userinterface, device, host, or success status.
Returns the most recent results matching your criteria.

Use this to find executions to analyze, then use fetch_execution_report to get details.

Example:
  get_execution_results(userinterface_name='google_tv', limit=1)
  get_execution_results(device_name='device1', success=false, limit=5)""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {
                        "type": "string",
                        "description": "Filter by userinterface/app name"
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Filter by device name"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Filter by host name"
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Filter by success status (true/false)"
                    },
                    "checked": {
                        "type": "boolean",
                        "description": "Filter by checked status (true=already analyzed)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 1)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "update_execution_analysis",
            "description": """Save analysis results to database.

After analyzing an execution result, use this to store your classification.

Classifications:
- BUG: Real application issue found
- SCRIPT_ISSUE: Test automation problem
- SYSTEM_ISSUE: Infrastructure/environment problem
- VALID_PASS: Legitimate successful execution
- VALID_FAIL: Legitimate failure (real bug detected)

Example:
  update_execution_analysis(
    script_result_id='abc-123',
    discard=false,
    classification='BUG',
    explanation='Login button not responding - real UI issue'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "script_result_id": {
                        "type": "string",
                        "description": "Script result ID to update"
                    },
                    "discard": {
                        "type": "boolean",
                        "description": "True if false positive (discard), False if valid result (keep)"
                    },
                    "classification": {
                        "type": "string",
                        "description": "Classification: BUG, SCRIPT_ISSUE, SYSTEM_ISSUE, VALID_PASS, VALID_FAIL"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the analysis (max 200 chars)"
                    }
                },
                "required": ["script_result_id", "discard", "classification", "explanation"]
            }
        }
    ]
