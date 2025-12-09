"""Deployment tool definitions for scheduled script execution management"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get deployment-related tool definitions"""
    return [
        {
            "name": "create_deployment",
            "description": """Create a scheduled deployment for recurring script execution

Creates a cron-based scheduled deployment that runs a script on a device at specified intervals.

Example:
  create_deployment(
    name='daily_validation',
    host_name='sunri-pi1',
    device_id='device1',
    script_name='validation.py',
    userinterface_name='netflix_mobile',
    parameters='--edge login',
    cron_expression='0 9 * * *',  # Daily at 9 AM
    start_date='2024-12-10T00:00:00Z',  # Optional
    end_date='2024-12-31T23:59:59Z',  # Optional
    max_executions=100  # Optional
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Deployment name"},
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier"},
                    "script_name": {"type": "string", "description": "Script filename (e.g., 'validation.py')"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "parameters": {"type": "string", "description": "Script CLI parameters (optional)"},
                    "cron_expression": {"type": "string", "description": "Cron expression (e.g., '*/10 * * * *' for every 10 min)"},
                    "start_date": {"type": "string", "description": "ISO 8601 start date (optional)"},
                    "end_date": {"type": "string", "description": "ISO 8601 end date (optional)"},
                    "max_executions": {"type": "integer", "description": "Maximum number of executions (optional)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["name", "host_name", "device_id", "script_name", "cron_expression"]
            }
        },
        {
            "name": "list_deployments",
            "description": """List all deployments

Returns all scheduled deployments with their status, schedule, and execution count.

Example:
  list_deployments()""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": []
            }
        },
        {
            "name": "pause_deployment",
            "description": """Pause a deployment

Temporarily stops a deployment from executing. Can be resumed later.

Example:
  pause_deployment(deployment_id='abc-123-def-456')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["deployment_id"]
            }
        },
        {
            "name": "resume_deployment",
            "description": """Resume a paused deployment

Restarts a previously paused deployment.

Example:
  resume_deployment(deployment_id='abc-123-def-456')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["deployment_id"]
            }
        },
        {
            "name": "update_deployment",
            "description": """Update a deployment's schedule and constraints

Modify cron expression, start/end dates, or max executions of an existing deployment.

Example:
  update_deployment(
    deployment_id='abc-123-def-456',
    cron_expression='0 */2 * * *',  # Every 2 hours
    max_executions=50
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                    "cron_expression": {"type": "string", "description": "New cron expression (optional)"},
                    "start_date": {"type": "string", "description": "New start date (optional)"},
                    "end_date": {"type": "string", "description": "New end date (optional)"},
                    "max_executions": {"type": "integer", "description": "New max executions (optional)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["deployment_id"]
            }
        },
        {
            "name": "delete_deployment",
            "description": """Delete a deployment

Permanently removes a deployment and stops all future executions.

Example:
  delete_deployment(deployment_id='abc-123-def-456')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["deployment_id"]
            }
        },
        {
            "name": "get_deployment_history",
            "description": """Get execution history for a deployment

Returns past executions with status, duration, and report URLs.

Example:
  get_deployment_history(deployment_id='abc-123-def-456')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "deployment_id": {"type": "string", "description": "Deployment ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["deployment_id"]
            }
        }
    ]

