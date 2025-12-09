"""Deployment tools for scheduled script execution management"""

from typing import Dict, Any
from backend_server.src.mcp.api.mcp_api_client import MCPAPIClient
from backend_server.src.mcp.utils.mcp_formatter import MCPFormatter


class DeploymentTools:
    """Tools for managing scheduled deployments"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def create_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scheduled deployment"""
        team_id = params.get('team_id', 'default')
        
        deployment_data = {
            'name': params['name'],
            'host_name': params['host_name'],
            'device_id': params['device_id'],
            'script_name': params['script_name'],
            'userinterface_name': params.get('userinterface_name', ''),
            'parameters': params.get('parameters', ''),
            'cron_expression': params['cron_expression']
        }
        
        # Optional constraints
        if 'start_date' in params:
            deployment_data['start_date'] = params['start_date']
        if 'end_date' in params:
            deployment_data['end_date'] = params['end_date']
        if 'max_executions' in params:
            deployment_data['max_executions'] = params['max_executions']
        
        result = self.api.post('/server/deployment/create', deployment_data, {'team_id': team_id})
        
        if result.get('success'):
            deployment = result['deployment']
            response_text = "✅ Deployment created successfully\n\n"
            response_text += f"Name: {deployment['name']}\n"
            response_text += f"Script: {deployment['script_name']}\n"
            response_text += f"Device: {deployment['host_name']}:{deployment['device_id']}\n"
            response_text += f"Schedule: {deployment['cron_expression']}\n"
            if deployment.get('start_date'):
                response_text += f"Start: {deployment['start_date']}\n"
            if deployment.get('end_date'):
                response_text += f"End: {deployment['end_date']}\n"
            if deployment.get('max_executions'):
                response_text += f"Max runs: {deployment['max_executions']}\n"
            response_text += f"\nID: {deployment['id']}"
            
            return self.formatter.success(response_text)
        else:
            return self.formatter.error(f"Failed to create deployment: {result.get('error', 'Unknown error')}")
    
    def list_deployments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all deployments"""
        team_id = params.get('team_id', 'default')
        
        result = self.api.get('/server/deployment/list', {'team_id': team_id})
        
        if result.get('success'):
            deployments = result['deployments']
            if not deployments:
                return self.formatter.success("No deployments found")
            
            response_text = f"📅 Found {len(deployments)} deployment(s)\n\n"
            for dep in deployments:
                status_emoji = "▶️" if dep['status'] == 'active' else "⏸️"
                response_text += f"{status_emoji} {dep['name']}\n"
                response_text += f"  Script: {dep['script_name']}\n"
                response_text += f"  Device: {dep['host_name']}:{dep['device_id']}\n"
                response_text += f"  Schedule: {dep['cron_expression']}\n"
                response_text += f"  Status: {dep['status']}\n"
                response_text += f"  Runs: {dep.get('execution_count', 0)}"
                if dep.get('max_executions'):
                    response_text += f"/{dep['max_executions']}"
                response_text += f"\n  ID: {dep['id']}\n\n"
            
            return self.formatter.success(response_text)
        else:
            return self.formatter.error(f"Failed to list deployments: {result.get('error', 'Unknown error')}")
    
    def pause_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pause a deployment"""
        deployment_id = params['deployment_id']
        
        result = self.api.post(f'/server/deployment/pause/{deployment_id}', {})
        
        if result.get('success'):
            return self.formatter.success(f"⏸️ Deployment paused: {deployment_id}")
        else:
            return self.formatter.error(f"Failed to pause deployment: {result.get('error', 'Unknown error')}")
    
    def resume_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resume a deployment"""
        deployment_id = params['deployment_id']
        
        result = self.api.post(f'/server/deployment/resume/{deployment_id}', {})
        
        if result.get('success'):
            return self.formatter.success(f"▶️ Deployment resumed: {deployment_id}")
        else:
            return self.formatter.error(f"Failed to resume deployment: {result.get('error', 'Unknown error')}")
    
    def update_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update a deployment"""
        deployment_id = params['deployment_id']
        
        update_data = {}
        if 'cron_expression' in params:
            update_data['cron_expression'] = params['cron_expression']
        if 'start_date' in params:
            update_data['start_date'] = params['start_date']
        if 'end_date' in params:
            update_data['end_date'] = params['end_date']
        if 'max_executions' in params:
            update_data['max_executions'] = params['max_executions']
        
        result = self.api.put(f'/server/deployment/update/{deployment_id}', update_data)
        
        if result.get('success'):
            deployment = result['deployment']
            response_text = "✅ Deployment updated successfully\n\n"
            response_text += f"Schedule: {deployment['cron_expression']}\n"
            if deployment.get('start_date'):
                response_text += f"Start: {deployment['start_date']}\n"
            if deployment.get('end_date'):
                response_text += f"End: {deployment['end_date']}\n"
            if deployment.get('max_executions'):
                response_text += f"Max runs: {deployment['max_executions']}\n"
            
            return self.formatter.success(response_text)
        else:
            return self.formatter.error(f"Failed to update deployment: {result.get('error', 'Unknown error')}")
    
    def delete_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a deployment"""
        deployment_id = params['deployment_id']
        
        result = self.api.delete(f'/server/deployment/delete/{deployment_id}', {})
        
        if result.get('success'):
            return self.formatter.success(f"🗑️ Deployment deleted: {deployment_id}")
        else:
            return self.formatter.error(f"Failed to delete deployment: {result.get('error', 'Unknown error')}")
    
    def get_deployment_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get execution history for a deployment"""
        deployment_id = params['deployment_id']
        
        result = self.api.get(f'/server/deployment/history/{deployment_id}', {})
        
        if result.get('success'):
            executions = result['executions']
            if not executions:
                return self.formatter.success(f"No execution history for deployment: {deployment_id}")
            
            response_text = f"📊 Execution history for deployment: {deployment_id}\n"
            response_text += f"Total executions: {len(executions)}\n\n"
            
            for exec in executions[:10]:  # Show last 10
                status = "✅" if exec.get('success') else "❌"
                response_text += f"{status} {exec['started_at']}\n"
                if exec.get('completed_at'):
                    response_text += f"  Duration: {exec.get('duration', 'N/A')}s\n"
                if exec.get('report_url'):
                    response_text += f"  Report: {exec['report_url']}\n"
                response_text += "\n"
            
            if len(executions) > 10:
                response_text += f"... and {len(executions) - 10} more executions\n"
            
            return self.formatter.success(response_text)
        else:
            return self.formatter.error(f"Failed to get deployment history: {result.get('error', 'Unknown error')}")

