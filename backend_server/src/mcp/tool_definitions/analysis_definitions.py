"""Analysis tool definitions for execution result analysis"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get analysis tool definitions"""
    return [
        {
            "name": "fetch_execution_report",
            "description": """Fetch and display execution report content from URL.

Returns parsed content for viewing:
- Report: steps, errors, raw text
- Logs: content (truncated)

NOTE: This is a READ-ONLY operation - it does NOT update/analyze the result.
Use after get_execution_results when user wants to SEE report details.

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
Returns the most recent results INCLUDING any existing analysis (checked, classification, discard_comment).

NOTE: This is a READ-ONLY operation - it does NOT trigger analysis.
If result was already analyzed, the analysis fields will be populated.

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
            "description": """Save analysis classification to database.

ONLY use this when user EXPLICITLY asks to analyze/classify a result.
DO NOT call this when user just wants to fetch/view results.

When to use:
✅ User says: "analyze this", "classify this failure", "what's wrong with this"
❌ User says: "fetch last result", "show me results", "get execution"

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
        },
        {
            "name": "get_analysis_queue_status",
            "description": """Get analysis queue status and session processing stats.

Returns:
- Queue lengths: Items pending in Redis queues (p1_alerts, p2_scripts)
- Session stats: How many analyzed THIS SESSION (in-memory)
- Last processed: The last item analyzed in this session
- Classification breakdown: Count by type for this session

NOTE: For last EXECUTION result (from DB), use get_execution_results instead.
This tool shows QUEUE/SESSION state, not DB content.

Example:
  get_analysis_queue_status()""",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]
