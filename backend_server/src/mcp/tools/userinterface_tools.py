"""
User Interface Management Tools for MCP

Provides CRUD operations for userinterface models (app structures).
These tools manage the top-level app models like Netflix, YouTube, etc.
"""

import logging
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory


class UserInterfaceTools:
    """User interface model management"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
        self.logger = logging.getLogger(__name__)
    
    def create_userinterface(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new userinterface (app model)
        
        Args:
            name: Interface name (e.g., 'netflix_android')
            device_model: Device model ('android_mobile', 'android_tv', 'web', etc.)
            description: Optional description
            team_id: Team ID (optional - uses default)
        
        Returns:
            Created userinterface with root tree info
        """
        try:
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            device_model = params['device_model']
            
            # STEP 1: Validate device_model by fetching valid models from database
            # Uses SAME endpoint as frontend (UserInterface.tsx line 86)
            self.logger.info(f"Fetching valid device models for validation")
            
            models_result = self.api_client.get(
                '/server/devicemodel/getAllModels',
                params={'team_id': team_id}
            )
            
            # Extract model names from response
            if isinstance(models_result, list):
                valid_model_names = [model.get('name') for model in models_result if model.get('name')]
            else:
                valid_model_names = []
            
            if not valid_model_names:
                self.logger.warning("No device models found in database - proceeding without validation")
            elif device_model not in valid_model_names:
                # Validation failed - return helpful error
                return self.formatter.format_error(
                    f"Invalid device_model: '{device_model}'\n\n"
                    f"Valid models for your team:\n"
                    f"  • {chr(10).join('  • '.join(valid_model_names[i:i+3]) for i in range(0, len(valid_model_names), 3))}\n\n"
                    f"💡 Use one of these model names, or create a custom model first.",
                    ErrorCategory.VALIDATION
                )
            else:
                self.logger.info(f"✅ Device model '{device_model}' validated successfully")
            
            # STEP 2: Build payload following backend API
            interface_data = {
                'name': params['name'],
                'models': [device_model],
                'description': params.get('description', f"UI model for {params['name']}"),
                'team_id': team_id
            }
            
            self.logger.info(f"Creating userinterface: {interface_data['name']}")
            
            # STEP 3: Call backend - EXISTING ENDPOINT
            result = self.api_client.post(
                '/server/userinterface/createUserInterface',
                data=interface_data,
                params={'team_id': team_id}
            )
            
            if result.get('success') or result.get('id'):
                interface = result if result.get('id') else result.get('interface', {})
                
                return self.formatter.format_success(
                    f"✅ Userinterface created: {interface.get('name')}\n"
                    f"   ID: {interface.get('id')}\n"
                    f"   Device Model: {device_model}\n"
                    f"   Root Tree: {interface.get('root_tree', {}).get('id', 'pending')}\n"
                    f"\n💡 Use get_userinterface_complete(userinterface_id='{interface.get('id')}') to get full tree data"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to create userinterface: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error creating userinterface: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def list_userinterfaces(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all userinterfaces for the team
        
        Args:
            team_id: Team ID (optional - uses default)
            force_refresh: Force cache refresh (optional - default false)
        
        Returns:
            List of all userinterfaces with root tree info
        """
        try:
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            force_refresh = params.get('force_refresh', False)
            
            self.logger.info(f"Listing userinterfaces for team {team_id}")
            
            # Call backend - EXISTING ENDPOINT
            result = self.api_client.get(
                '/server/userinterface/getAllUserInterfaces',
                params={
                    'team_id': team_id,
                    'force_refresh': 'true' if force_refresh else 'false'
                }
            )
            
            # Result is array directly (not wrapped in success)
            if isinstance(result, list):
                interfaces = result
            else:
                interfaces = result.get('interfaces', [])
            
            if not interfaces:
                return self.formatter.format_success(
                    "📋 No userinterfaces found for this team\n"
                    "\n💡 Create one with: create_userinterface(name='netflix_android', device_model='android_mobile')"
                )
            
            response_text = f"📋 User Interfaces ({len(interfaces)} total):\n\n"
            
            for interface in interfaces:
                name = interface.get('name', 'unnamed')
                interface_id = interface.get('id', 'unknown')
                models = interface.get('models', [])
                root_tree = interface.get('root_tree')
                
                response_text += f"• {name}\n"
                response_text += f"    ID: {interface_id}\n"
                response_text += f"    Models: {', '.join(models) if models else 'none'}\n"
                
                if root_tree:
                    tree_id = root_tree.get('id')
                    response_text += f"    ✅ Has navigation tree (ID: {tree_id})\n"
                    response_text += f"    💡 Get full tree: get_userinterface_complete(userinterface_id='{interface_id}')\n"
                else:
                    response_text += f"    ⚠️  No navigation tree yet\n"
                
                response_text += "\n"
            
            return {
                "content": [{"type": "text", "text": response_text}],
                "isError": False,
                "interfaces": interfaces,
                "total": len(interfaces)
            }
        
        except Exception as e:
            self.logger.error(f"Error listing userinterfaces: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def get_userinterface_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete userinterface with ALL nodes, edges, subtrees, and metrics
        
        Args:
            userinterface_id: User interface UUID
            team_id: Team ID (optional - uses default)
            include_metrics: Include metrics data (optional - default true)
        
        Returns:
            Complete tree structure with nodes, edges, subtrees, metrics
        """
        try:
            userinterface_id = params['userinterface_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            include_metrics = params.get('include_metrics', True)
            
            self.logger.info(f"Getting complete tree for userinterface {userinterface_id}")
            
            # Call backend - EXISTING ENDPOINT with include_nested=true
            result = self.api_client.get(
                f'/server/navigationTrees/getTreeByUserInterfaceId/{userinterface_id}',
                params={
                    'team_id': team_id,
                    'include_nested': 'true',  # Get ALL subtrees
                    'include_metrics': 'true' if include_metrics else 'false'
                }
            )
            
            if not result.get('success'):
                return self.formatter.format_error(
                    f"Failed to get userinterface: {result.get('error', 'Unknown error')}",
                    ErrorCategory.BACKEND
                )
            
            tree = result.get('tree', {})
            metadata = tree.get('metadata', {})
            nodes = metadata.get('nodes', [])
            edges = metadata.get('edges', [])
            metrics = result.get('metrics', {})
            
            response_text = f"✅ Complete tree for userinterface {userinterface_id}:\n\n"
            response_text += f"Tree ID: {tree.get('id')}\n"
            response_text += f"Tree Name: {tree.get('name')}\n"
            response_text += f"Nodes: {len(nodes)} (includes all subtrees)\n"
            response_text += f"Edges: {len(edges)} (includes all subtrees)\n"
            
            if include_metrics:
                node_metrics = metrics.get('nodes', {})
                edge_metrics = metrics.get('edges', {})
                response_text += f"Node Metrics: {len(node_metrics)}\n"
                response_text += f"Edge Metrics: {len(edge_metrics)}\n"
            
            response_text += f"\n💡 All nodes and edges are now available for inspection/modification"
            
            return {
                "content": [{"type": "text", "text": response_text}],
                "isError": False,
                "tree": tree,
                "nodes": nodes,
                "edges": edges,
                "metrics": metrics if include_metrics else None,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting complete userinterface: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def list_nodes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all nodes in a tree
        
        Args:
            tree_id: Navigation tree ID
            team_id: Team ID (optional - uses default)
            page: Page number (optional - default 0)
            limit: Results per page (optional - default 100)
        
        Returns:
            List of nodes with details
        """
        try:
            tree_id = params['tree_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            page = params.get('page', 0)
            limit = params.get('limit', 100)
            
            self.logger.info(f"Listing nodes for tree {tree_id}")
            
            # Call backend - EXISTING ENDPOINT
            result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/nodes',
                params={
                    'team_id': team_id,
                    'page': page,
                    'limit': limit
                }
            )
            
            if not result.get('success'):
                return self.formatter.format_error(
                    f"Failed to list nodes: {result.get('error', 'Unknown error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes = result.get('nodes', [])
            total = result.get('total', len(nodes))
            
            response_text = f"📋 Nodes in tree {tree_id} ({total} total, showing {len(nodes)}):\n\n"
            
            for node in nodes:
                node_id = node.get('node_id', 'unknown')
                label = node.get('label', 'unnamed')
                node_type = node.get('node_type', 'unknown')
                verifications_count = len(node.get('verifications', []))
                
                response_text += f"• {label} (node_id: '{node_id}')\n"
                response_text += f"    Type: {node_type}\n"
                response_text += f"    Verifications: {verifications_count}\n"
            
            return {
                "content": [{"type": "text", "text": response_text}],
                "isError": False,
                "nodes": nodes,
                "total": total,
                "page": page,
                "limit": limit
            }
        
        except Exception as e:
            self.logger.error(f"Error listing nodes: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def list_edges(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all edges in a tree
        
        Args:
            tree_id: Navigation tree ID
            team_id: Team ID (optional - uses default)
            node_ids: Optional list of node IDs to filter edges
        
        Returns:
            List of edges with action sets
        """
        try:
            tree_id = params['tree_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            node_ids = params.get('node_ids')
            
            self.logger.info(f"Listing edges for tree {tree_id}")
            
            # Call backend - EXISTING ENDPOINT
            query_params = {'team_id': team_id}
            if node_ids:
                query_params['node_ids'] = node_ids
            
            result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/edges',
                params=query_params
            )
            
            if not result.get('success'):
                return self.formatter.format_error(
                    f"Failed to list edges: {result.get('error', 'Unknown error')}",
                    ErrorCategory.BACKEND
                )
            
            edges = result.get('edges', [])
            
            response_text = f"📋 Edges in tree {tree_id} ({len(edges)} total):\n\n"
            
            for edge in edges:
                edge_id = edge.get('edge_id', 'unknown')
                source = edge.get('source_node_id', 'unknown')
                target = edge.get('target_node_id', 'unknown')
                action_sets = edge.get('action_sets', [])
                
                response_text += f"• {source} → {target} (edge_id: '{edge_id}')\n"
                response_text += f"    Action Sets: {len(action_sets)}\n"
                
                for action_set in action_sets:
                    set_id = action_set.get('id', 'unknown')
                    actions = action_set.get('actions', [])
                    response_text += f"      - {set_id}: {len(actions)} actions\n"
            
            return {
                "content": [{"type": "text", "text": response_text}],
                "isError": False,
                "edges": edges,
                "total": len(edges)
            }
        
        except Exception as e:
            self.logger.error(f"Error listing edges: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)

