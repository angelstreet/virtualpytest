"""
AI Exploration Tools - Automated tree building via exploration executor

Provides LLMs with access to AI-powered navigation tree creation.
Replaces manual node/edge creation with intelligent automation.
"""

import time
from typing import Dict, Any
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory
from ..utils.api_client import MCPAPIClient


class ExplorationTools:
    """AI exploration tools for automated tree building"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
    
    def start_ai_exploration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start AI-powered exploration
        
        Calls: POST /api/host/ai-exploration/start
        """
        userinterface_name = params.get('userinterface_name')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id', 'team_1')
        original_prompt = params.get('original_prompt', '')
        start_node = params.get('start_node', 'home')
        
        if not userinterface_name:
            return self.formatter.error("userinterface_name is required")
        
        # Get compatible host/device
        try:
            hosts_response = self.api_client.get(
                f'/api/host/ai-exploration/compatible-hosts',
                params={'userinterface_name': userinterface_name}
            )
            
            if not hosts_response.get('success'):
                return self.formatter.error(
                    f"Failed to get compatible hosts: {hosts_response.get('error')}",
                    ErrorCategory.NOT_FOUND
                )
            
            host_name = hosts_response.get('recommended_host')
            device_id = hosts_response.get('recommended_device')
            
            if not tree_id:
                # Get tree_id from userinterface
                ui_response = self.api_client.get(
                    f'/api/navigation/userinterfaces',
                    params={'team_id': team_id}
                )
                
                if ui_response.get('success'):
                    userinterfaces = ui_response.get('userinterfaces', [])
                    ui = next((u for u in userinterfaces if u['name'] == userinterface_name), None)
                    if ui:
                        tree_id = ui.get('root_tree_id')
            
            if not tree_id:
                return self.formatter.error(
                    f"Could not find tree_id for userinterface '{userinterface_name}'. "
                    f"Create userinterface first with create_userinterface()",
                    ErrorCategory.NOT_FOUND
                )
            
        except Exception as e:
            return self.formatter.error(
                f"Failed to setup exploration: {str(e)}",
                ErrorCategory.BACKEND
            )
        
        # Start exploration
        try:
            response = self.api_client.post(
                f'/api/host/ai-exploration/start',
                json_data={
                    'tree_id': tree_id,
                    'userinterface_name': userinterface_name,
                    'team_id': team_id,
                    'original_prompt': original_prompt,
                    'start_node': start_node,
                    'host_name': host_name,
                    'device_id': device_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
                    f"Exploration failed to start: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            exploration_id = response.get('exploration_id')
            exploration_host = response.get('host_name')
            
            # Poll until plan is ready
            max_attempts = 60  # 60 seconds timeout
            for attempt in range(max_attempts):
                time.sleep(1)
                
                status_response = self.api_client.get(
                    f'/api/host/ai-exploration/status',
                    params={
                        'exploration_id': exploration_id,
                        'host_name': exploration_host,
                        'team_id': team_id
                    }
                )
                
                if not status_response.get('success'):
                    continue
                
                status = status_response.get('status')
                
                if status == 'awaiting_approval':
                    # Plan ready!
                    plan = status_response.get('exploration_plan', {})
                    screenshot = status_response.get('current_analysis', {}).get('screenshot')
                    
                    result_text = f"✅ AI Exploration Complete!\n\n"
                    result_text += f"**Exploration ID:** {exploration_id}\n"
                    result_text += f"**Host:** {exploration_host}\n"
                    result_text += f"**Strategy:** {plan.get('strategy', 'unknown')}\n"
                    result_text += f"**Menu Type:** {plan.get('menu_type', 'unknown')}\n"
                    result_text += f"**Items Found:** {len(plan.get('items', []))}\n\n"
                    
                    result_text += f"**Proposed Items:**\n"
                    for item in plan.get('items', [])[:10]:  # Show first 10
                        result_text += f"  • {item}\n"
                    
                    if len(plan.get('items', [])) > 10:
                        result_text += f"  ... and {len(plan.get('items', [])) - 10} more\n"
                    
                    result_text += f"\n**AI Reasoning:**\n{plan.get('reasoning', 'N/A')}\n\n"
                    
                    if screenshot:
                        result_text += f"**Screenshot:** {screenshot}\n\n"
                    
                    result_text += f"**Next Step:**\n"
                    result_text += f"Call `approve_exploration_plan()` to create nodes and edges.\n\n"
                    result_text += f"```python\n"
                    result_text += f"approve_exploration_plan(\n"
                    result_text += f"  exploration_id='{exploration_id}',\n"
                    result_text += f"  host_name='{exploration_host}',\n"
                    result_text += f"  userinterface_name='{userinterface_name}'\n"
                    result_text += f")\n"
                    result_text += f"```"
                    
                    return {"content": [{"type": "text", "text": result_text}], "isError": False}
                
                elif status == 'failed':
                    error = status_response.get('error', 'Unknown error')
                    return self.formatter.error(
                        f"Exploration failed: {error}",
                        ErrorCategory.BACKEND
                    )
            
            # Timeout
            return self.formatter.error(
                "Exploration timed out waiting for analysis to complete",
                ErrorCategory.TIMEOUT
            )
            
        except Exception as e:
            return self.formatter.error(
                f"Exploration error: {str(e)}",
                ErrorCategory.BACKEND
            )
    
    def get_exploration_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get exploration status"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', 'team_1')
        
        if not exploration_id or not host_name:
            return self.formatter.error("exploration_id and host_name are required")
        
        try:
            response = self.api_client.get(
                f'/api/host/ai-exploration/status',
                params={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
                    f"Failed to get status: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            # Format status
            status = response.get('status')
            current_step = response.get('current_step', '')
            plan = response.get('exploration_plan', {})
            error = response.get('error')
            
            result_text = f"**Status:** {status}\n"
            result_text += f"**Current Step:** {current_step}\n\n"
            
            if plan:
                result_text += f"**Plan:**\n"
                result_text += f"  Strategy: {plan.get('strategy')}\n"
                result_text += f"  Items: {len(plan.get('items', []))}\n"
            
            if error:
                result_text += f"\n**Error:** {error}\n"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Status check failed: {str(e)}", ErrorCategory.BACKEND)
    
    def approve_exploration_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Approve plan and create structure"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        team_id = params.get('team_id', 'team_1')
        selected_items = params.get('selected_items')
        selected_screen_items = params.get('selected_screen_items')
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            response = self.api_client.post(
                f'/api/host/ai-exploration/continue',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'userinterface_name': userinterface_name,
                    'team_id': team_id,
                    'selected_items': selected_items,
                    'selected_screen_items': selected_screen_items
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
                    f"Failed to create structure: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_created = response.get('nodes_created', 0)
            edges_created = response.get('edges_created', 0)
            node_ids = response.get('node_ids', [])
            edge_ids = response.get('edge_ids', [])
            
            result_text = f"✅ Navigation Structure Created!\n\n"
            result_text += f"**Nodes Created:** {nodes_created}\n"
            result_text += f"**Edges Created:** {edges_created}\n\n"
            
            if node_ids:
                result_text += f"**Nodes:**\n"
                for node_id in node_ids[:5]:
                    result_text += f"  • {node_id}\n"
                if len(node_ids) > 5:
                    result_text += f"  ... and {len(node_ids) - 5} more\n"
                result_text += "\n"
            
            result_text += f"**Next Step:**\n"
            result_text += f"Start validation with `validate_exploration_edges()`\n\n"
            result_text += f"```python\n"
            result_text += f"validate_exploration_edges(\n"
            result_text += f"  exploration_id='{exploration_id}',\n"
            result_text += f"  host_name='{host_name}',\n"
            result_text += f"  userinterface_name='{userinterface_name}'\n"
            result_text += f")\n"
            result_text += f"```"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Approval failed: {str(e)}", ErrorCategory.BACKEND)
    
    def validate_exploration_edges(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate edges sequentially"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        team_id = params.get('team_id', 'team_1')
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            # Start validation if needed
            start_response = self.api_client.post(
                f'/api/host/ai-exploration/start-validation',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'team_id': team_id
                }
            )
            
            # Validate next item
            response = self.api_client.post(
                f'/api/host/ai-exploration/validate-next',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'userinterface_name': userinterface_name,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                error = response.get('error', 'Unknown error')
                
                # Check if validation is complete
                if 'All items validated' in error or response.get('has_more_items') == False:
                    result_text = "✅ Validation Complete!\n\n"
                    result_text += "All edges have been tested.\n\n"
                    result_text += "**Next Step:**\n"
                    result_text += "Get verification suggestions with `get_node_verification_suggestions()`"
                    return {"content": [{"type": "text", "text": result_text}], "isError": False}
                
                return self.formatter.error(f"Validation failed: {error}", ErrorCategory.BACKEND)
            
            # Format validation result
            item = response.get('item', 'unknown')
            node_name = response.get('node_name', item)
            has_more = response.get('has_more_items', False)
            screenshot = response.get('screenshot_url')
            
            # Check result format (TV vs Mobile)
            if 'edge_results' in response:
                # TV format
                edge_results = response['edge_results']
                result_text = f"📊 Validated: {item}\n\n"
                result_text += f"**Node:** {node_name}\n"
                result_text += f"**Horizontal:** {edge_results.get('horizontal', 'N/A')}\n"
                result_text += f"**Enter (OK):** {edge_results.get('enter', 'N/A')}\n"
                result_text += f"**Exit (BACK):** {edge_results.get('exit', 'N/A')}\n"
            else:
                # Mobile format
                click_result = response.get('click_result', 'unknown')
                back_result = response.get('back_result', 'unknown')
                result_text = f"📊 Validated: {item}\n\n"
                result_text += f"**Node:** {node_name}\n"
                result_text += f"**Forward:** {click_result}\n"
                result_text += f"**Reverse:** {back_result}\n"
            
            if screenshot:
                result_text += f"\n**Screenshot:** {screenshot}\n"
            
            progress = response.get('progress', {})
            if progress:
                current = progress.get('current_item', progress.get('current', 0))
                total = progress.get('total_items', progress.get('total', 0))
                result_text += f"\n**Progress:** {current}/{total}\n"
            
            if has_more:
                result_text += f"\n**Next:** Call again to validate next edge"
            else:
                result_text += f"\n✅ **Validation Complete!**"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Validation failed: {str(e)}", ErrorCategory.BACKEND)
    
    def get_node_verification_suggestions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI verification suggestions"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', 'team_1')
        
        if not all([exploration_id, host_name]):
            return self.formatter.error("exploration_id and host_name are required")
        
        try:
            response = self.api_client.post(
                f'/api/host/ai-exploration/start-node-verification',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
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
                result_text += f"  Command: {verification.get('method', 'N/A')}\n"
                result_text += f"  Params: {verification.get('params', {})}\n\n"
            
            if len(suggestions) > 5:
                result_text += f"... and {len(suggestions) - 5} more suggestions\n\n"
            
            result_text += f"**Next Step:**\n"
            result_text += f"Apply verifications with `approve_node_verifications()`"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Failed to get suggestions: {str(e)}", ErrorCategory.BACKEND)
    
    def approve_node_verifications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply verifications to nodes"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        team_id = params.get('team_id', 'team_1')
        approved_verifications = params.get('approved_verifications', [])
        
        if not all([exploration_id, host_name, userinterface_name]):
            return self.formatter.error("exploration_id, host_name, and userinterface_name are required")
        
        try:
            response = self.api_client.post(
                f'/api/host/ai-exploration/approve-node-verifications',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'userinterface_name': userinterface_name,
                    'team_id': team_id,
                    'approved_verifications': approved_verifications
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
                    f"Failed to apply verifications: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_updated = response.get('nodes_updated', 0)
            
            result_text = f"✅ Verifications Applied!\n\n"
            result_text += f"**Nodes Updated:** {nodes_updated}\n\n"
            result_text += f"**Next Step:**\n"
            result_text += f"Finalize exploration with `finalize_exploration()`"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Failed to apply verifications: {str(e)}", ErrorCategory.BACKEND)
    
    def finalize_exploration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize exploration"""
        exploration_id = params.get('exploration_id')
        host_name = params.get('host_name')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id', 'team_1')
        
        if not all([exploration_id, host_name, tree_id]):
            return self.formatter.error("exploration_id, host_name, and tree_id are required")
        
        try:
            response = self.api_client.post(
                f'/api/host/ai-exploration/finalize',
                json_data={
                    'exploration_id': exploration_id,
                    'host_name': host_name,
                    'tree_id': tree_id,
                    'team_id': team_id
                }
            )
            
            if not response.get('success'):
                return self.formatter.error(
                    f"Failed to finalize: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_renamed = response.get('nodes_renamed', 0)
            edges_renamed = response.get('edges_renamed', 0)
            
            result_text = f"🎉 Exploration Complete!\n\n"
            result_text += f"**Nodes Finalized:** {nodes_renamed}\n"
            result_text += f"**Edges Finalized:** {edges_renamed}\n\n"
            result_text += f"All _temp suffixes removed. Navigation tree is ready to use!"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Finalization failed: {str(e)}", ErrorCategory.BACKEND)

