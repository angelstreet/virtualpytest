"""
AI Exploration Tools - Automated tree building via server proxy

Uses /server/ai-generation/* routes which proxy to HOST.
Same endpoints as frontend AIGenerationModal uses.
"""

import time
from typing import Dict, Any
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory
from ..utils.api_client import MCPAPIClient


# Default team_id (same as frontend APP_CONFIG)
DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'


class ExplorationTools:
    """AI exploration tools for automated tree building"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
    
    def _get_compatible_host(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """
        Internal helper to get compatible host/device for a userinterface.
        Same logic as device_tools.get_compatible_hosts but returns raw data.
        """
        # Get userinterface by name
        ui_result = self.api_client.get(
            f'/server/userinterface/getUserInterfaceByName/{userinterface_name}',
            params={'team_id': team_id}
        )
        
        if not ui_result or 'error' in ui_result:
            return {'error': f"Userinterface '{userinterface_name}' not found"}
        
        models = ui_result.get('models', [])
        tree_id = ui_result.get('root_tree_id')
        
        if not models:
            return {'error': f"Userinterface '{userinterface_name}' has no device models"}
        
        # Get all hosts
        hosts_result = self.api_client.get('/server/system/getAllHosts')
        
        if not hosts_result.get('success'):
            return {'error': 'Failed to get hosts'}
        
        all_hosts = hosts_result.get('hosts', [])
        
        # Find first compatible host/device
        for host in all_hosts:
            for device in host.get('devices', []):
                device_model = device.get('device_model')
                device_capabilities = device.get('device_capabilities', {})
                
                if device_model in models or any(device_capabilities.get(m) for m in models):
                    return {
                        'success': True,
                        'host_name': host.get('host_name'),
                        'device_id': device.get('device_id'),
                        'tree_id': tree_id
                    }
        
        return {'error': f"No compatible hosts found for '{userinterface_name}'"}
    
    def start_ai_exploration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start AI-powered exploration
        
        Calls: POST /server/ai-generation/start-exploration (same as frontend)
        """
        userinterface_name = params.get('userinterface_name')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        original_prompt = params.get('original_prompt', '')
        start_node = params.get('start_node', 'home')
        
        if not userinterface_name:
            return self.formatter.format_error("userinterface_name is required")
        
        # Get compatible host/device
        host_info = self._get_compatible_host(userinterface_name, team_id)
        
        if 'error' in host_info:
            return self.formatter.format_error(host_info['error'], ErrorCategory.NOT_FOUND)
        
        host_name = host_info['host_name']
        device_id = host_info['device_id']
        
        if not tree_id:
            tree_id = host_info.get('tree_id')
        
        if not tree_id:
            return self.formatter.format_error(
                f"Could not find tree_id for userinterface '{userinterface_name}'",
                ErrorCategory.NOT_FOUND
            )
        
        # Start exploration via server proxy (same endpoint as frontend)
        try:
            response = self.api_client.post(
                '/server/ai-generation/start-exploration',
                data={
                    'tree_id': tree_id,
                    'root_tree_id': tree_id,
                    'host_name': host_name,
                    'device_id': device_id,
                    'userinterface_name': userinterface_name,
                    'original_prompt': original_prompt,
                    'start_node': start_node
                },
                params={'team_id': team_id}
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Exploration failed to start: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            exploration_id = response.get('exploration_id')
            exploration_host = response.get('host_name', host_name)
            
            # Poll until plan is ready (same as frontend)
            max_attempts = 60
            for attempt in range(max_attempts):
                time.sleep(2)
                
                status_response = self.api_client.get(
                    f'/server/ai-generation/exploration-status/{exploration_id}',
                    params={
                        'host_name': exploration_host,
                        'device_id': device_id,
                        'team_id': team_id
                    }
                )
                
                if not status_response.get('success'):
                    continue
                
                status = status_response.get('status')
                
                if status == 'awaiting_approval':
                    plan = status_response.get('exploration_plan', {})
                    screenshot = status_response.get('current_analysis', {}).get('screenshot')
                    
                    result_text = f"✅ AI Exploration Complete!\n\n"
                    result_text += f"**Exploration ID:** `{exploration_id}`\n"
                    result_text += f"**Host:** `{exploration_host}`\n"
                    result_text += f"**Strategy:** {plan.get('strategy', 'unknown')}\n"
                    result_text += f"**Menu Type:** {plan.get('menu_type', 'unknown')}\n"
                    result_text += f"**Items Found:** {len(plan.get('items', []))}\n\n"
                    
                    result_text += f"**Proposed Items:**\n"
                    for item in plan.get('items', [])[:10]:
                        result_text += f"  • {item}\n"
                    
                    if len(plan.get('items', [])) > 10:
                        result_text += f"  ... and {len(plan.get('items', [])) - 10} more\n"
                    
                    result_text += f"\n**AI Reasoning:**\n{plan.get('reasoning', 'N/A')}\n\n"
                    
                    result_text += f"**Next Step:** Call `approve_exploration_plan()` with:\n"
                    result_text += f"  exploration_id='{exploration_id}'\n"
                    result_text += f"  host_name='{exploration_host}'\n"
                    result_text += f"  userinterface_name='{userinterface_name}'\n"
                    
                    return {"content": [{"type": "text", "text": result_text}], "isError": False}
                
                elif status == 'failed':
                    error = status_response.get('error', 'Unknown error')
                    return self.formatter.format_error(f"Exploration failed: {error}", ErrorCategory.BACKEND)
            
            return self.formatter.format_error("Exploration timed out", ErrorCategory.TIMEOUT)
            
        except Exception as e:
            return self.formatter.format_error(f"Exploration error: {str(e)}", ErrorCategory.BACKEND)
    
    def get_exploration_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get exploration status"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        
        if not exploration_id or not host_name:
            return self.formatter.format_error("exploration_id and host_name are required")
        
        try:
            response = self.api_client.get(
                f'/server/ai-generation/exploration-status/{exploration_id}',
                params={
                    'host_name': host_name,
                    'device_id': device_id,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Failed to get status: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            status = response.get('status')
            current_step = response.get('current_step', '')
            plan = response.get('exploration_plan', {})
            
            result_text = f"**Status:** {status}\n"
            result_text += f"**Current Step:** {current_step}\n\n"
            
            if plan:
                result_text += f"**Plan:**\n"
                result_text += f"  Strategy: {plan.get('strategy')}\n"
                result_text += f"  Items: {len(plan.get('items', []))}\n"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Status check failed: {str(e)}", ErrorCategory.BACKEND)
    
    def approve_exploration_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Approve plan and create structure"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        selected_items = params.get('selected_items')
        selected_screen_items = params.get('selected_screen_items')
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.format_error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            response = self.api_client.post(
                f'/server/ai-generation/continue-exploration',
                data={
                    'exploration_id': exploration_id,
                    'device_id': device_id,
                    'selected_items': selected_items,
                    'selected_screen_items': selected_screen_items or selected_items
                },
                params={
                    'host_name': host_name,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Failed to create structure: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_created = response.get('nodes_created', 0)
            edges_created = response.get('edges_created', 0)
            
            result_text = f"✅ Navigation Structure Created!\n\n"
            result_text += f"**Nodes Created:** {nodes_created}\n"
            result_text += f"**Edges Created:** {edges_created}\n\n"
            result_text += f"**Next Step:** Call `validate_exploration_edges()` to test the edges\n"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Approval failed: {str(e)}", ErrorCategory.BACKEND)
    
    def validate_exploration_edges(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate edges sequentially"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.format_error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            # Start validation
            self.api_client.post(
                '/server/ai-generation/start-validation',
                data={
                    'exploration_id': exploration_id,
                    'device_id': device_id
                },
                params={'host_name': host_name, 'team_id': team_id}
            )
            
            # Validate next item
            response = self.api_client.post(
                '/server/ai-generation/validate-next-item',
                data={
                    'exploration_id': exploration_id,
                    'device_id': device_id
                },
                params={'host_name': host_name, 'team_id': team_id}
            )
            
            if not response.get('success'):
                error = response.get('error', 'Unknown error')
                
                if 'All items validated' in error or response.get('has_more_items') == False:
                    result_text = "✅ Validation Complete!\n\n"
                    result_text += "All edges have been tested.\n\n"
                    result_text += "**Next Step:** Call `get_node_verification_suggestions()` or `finalize_exploration()`"
                    return {"content": [{"type": "text", "text": result_text}], "isError": False}
                
                return self.formatter.format_error(f"Validation failed: {error}", ErrorCategory.BACKEND)
            
            item = response.get('item', 'unknown')
            node_name = response.get('node_name', item)
            has_more = response.get('has_more_items', False)
            click_result = response.get('click_result', 'unknown')
            back_result = response.get('back_result', 'unknown')
            
            result_text = f"📊 Validated: {item}\n\n"
            result_text += f"**Node:** {node_name}\n"
            result_text += f"**Forward:** {click_result}\n"
            result_text += f"**Reverse:** {back_result}\n"
            
            progress = response.get('progress', {})
            if progress:
                current = progress.get('current_item', 0)
                total = progress.get('total_items', 0)
                result_text += f"\n**Progress:** {current}/{total}\n"
            
            if has_more:
                result_text += f"\n**Next:** Call `validate_exploration_edges()` again to validate next edge"
            else:
                result_text += f"\n✅ **Validation Complete!**"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Validation failed: {str(e)}", ErrorCategory.BACKEND)
    
    def get_node_verification_suggestions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI verification suggestions"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        
        if not all([exploration_id, host_name]):
            return self.formatter.format_error("exploration_id and host_name are required")
        
        try:
            response = self.api_client.post(
                '/server/ai-generation/start-node-verification',
                data={
                    'device_id': device_id
                },
                params={'host_name': host_name, 'team_id': team_id}
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Failed to get suggestions: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            suggestions = response.get('suggestions', [])
            total_nodes = response.get('total_nodes', 0)
            
            result_text = f"✅ Verification Suggestions Generated!\n\n"
            result_text += f"**Nodes Analyzed:** {total_nodes}\n\n"
            
            for suggestion in suggestions[:5]:
                node_id = suggestion.get('node_id', 'unknown')
                verification = suggestion.get('verification', {})
                result_text += f"**{node_id}:**\n"
                result_text += f"  Method: {verification.get('method', 'N/A')}\n"
                result_text += f"  Params: {verification.get('params', {})}\n\n"
            
            if len(suggestions) > 5:
                result_text += f"... and {len(suggestions) - 5} more\n\n"
            
            result_text += f"**Next Step:** Call `approve_node_verifications()` or `finalize_exploration()`"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Failed: {str(e)}", ErrorCategory.BACKEND)
    
    def approve_node_verifications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply verifications to nodes"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        approved_verifications = params.get('approved_verifications', [])
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.format_error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            response = self.api_client.post(
                '/server/ai-generation/approve-node-verifications',
                data={
                    'device_id': device_id,
                    'approved_verifications': approved_verifications
                },
                params={'host_name': host_name, 'team_id': team_id}
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Failed: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_updated = response.get('nodes_updated', 0)
            
            result_text = f"✅ Verifications Applied!\n\n"
            result_text += f"**Nodes Updated:** {nodes_updated}\n\n"
            result_text += f"**Next Step:** Call `finalize_exploration()`"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Failed: {str(e)}", ErrorCategory.BACKEND)
    
    def finalize_exploration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize exploration - remove _temp suffixes"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        
        if not all([exploration_id, host_name, tree_id]):
            return self.formatter.format_error("exploration_id, host_name, and tree_id are required")
        
        try:
            response = self.api_client.post(
                '/server/ai-generation/finalize-structure',
                data={
                    'tree_id': tree_id,
                    'host_name': host_name
                },
                params={'team_id': team_id}
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Failed to finalize: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_renamed = response.get('nodes_renamed', 0)
            edges_renamed = response.get('edges_renamed', 0)
            
            result_text = f"🎉 Exploration Complete!\n\n"
            result_text += f"**Nodes Finalized:** {nodes_renamed}\n"
            result_text += f"**Edges Finalized:** {edges_renamed}\n\n"
            result_text += f"Navigation tree is ready to use!"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Finalization failed: {str(e)}", ErrorCategory.BACKEND)
