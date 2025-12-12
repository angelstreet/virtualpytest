"""
Navigation Tools - UI navigation execution

Navigate through UI trees using pathfinding and action execution.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class NavigationTools:
    """UI navigation execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def list_navigation_nodes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List navigation nodes available in a tree
        
        Can accept EITHER tree_id OR userinterface_name (same approach as frontend)
        
        Args:
            params: {
                'tree_id': str (OPTIONAL) - Direct tree ID,
                'userinterface_name': str (OPTIONAL) - Convert to tree_id first,
                'team_id': str (OPTIONAL),
                'page': int (OPTIONAL) - Page number (default: 0),
                'limit': int (OPTIONAL) - Results per page (default: 100)
            }
            
        Returns:
            MCP-formatted response with list of navigation nodes and their properties
        """
        tree_id = params.get('tree_id')
        userinterface_name = params.get('userinterface_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        page = params.get('page', 0)
        limit = params.get('limit', 100)
        
        # OPTION 1: If userinterface_name provided, convert to tree_id (SAME AS FRONTEND)
        if userinterface_name and not tree_id:
            print(f"[@MCP:list_navigation_nodes] Converting userinterface_name '{userinterface_name}' to tree_id")
            
            # Step 1: Get userinterface by name to get UUID
            ui_result = self.api.get(f'/server/userinterface/getUserInterfaceByName/{userinterface_name}', params={'team_id': team_id})
            if not ui_result or not ui_result.get('id'):
                return {"content": [{"type": "text", "text": f"Error: User interface '{userinterface_name}' not found"}], "isError": True}
            
            userinterface_id = ui_result['id']
            print(f"[@MCP:list_navigation_nodes] Got userinterface_id: {userinterface_id}")
            
            # Step 2: Get tree by userinterface_id (SAME API AS FRONTEND)
            tree_result = self.api.get(f'/server/navigationTrees/getTreeByUserInterfaceId/{userinterface_id}', params={'include_nested': 'true', 'team_id': team_id})
            
            if not tree_result.get('success') or not tree_result.get('tree'):
                return {"content": [{"type": "text", "text": f"Error: No navigation tree found for '{userinterface_name}'"}], "isError": True}
            
            tree_id = tree_result['tree']['id']
            nodes = tree_result['tree'].get('metadata', {}).get('nodes', [])
            
            print(f"[@MCP:list_navigation_nodes] Got tree_id: {tree_id} with {len(nodes)} nodes")
            
            # Filter out ENTRY nodes (same as frontend)
            filtered_nodes = [node for node in nodes if node.get('id') != 'ENTRY' and node.get('type') != 'entry' and node.get('label', '').lower() != 'entry']
            
            if not filtered_nodes:
                return {"content": [{"type": "text", "text": f"No navigation nodes found for '{userinterface_name}'"}], "isError": False}
            
            response_text = f"📋 Navigation nodes for '{userinterface_name}' (tree: {tree_id}, {len(filtered_nodes)} nodes):\n\n"
            response_text += "  ⚠️  CRITICAL: Use the node_id STRING shown below (e.g., 'home'), NOT the database UUID!\n"
            response_text += "      For create_edge: source_node_id='home' ✅  NOT source_node_id='ce97c317-...' ❌\n\n"
            
            for node in filtered_nodes[:50]:  # Limit display to first 50
                # CRITICAL: Show node_id (the string identifier), not id (the UUID)
                node_id = node.get('node_id', 'unknown')  # This is the actual node_id string (e.g., 'home')
                db_uuid = node.get('id')  # This is the database UUID (primary key)
                label = node.get('label', 'unnamed')
                node_type = node.get('type', 'unknown')
                
                # Show the string identifier prominently
                response_text += f"  • {label}\n"
                response_text += f"      → node_id: '{node_id}' ← USE THIS in create_edge()\n"
                if db_uuid:
                    response_text += f"      (DB UUID: {db_uuid}... - internal only)\n"
                response_text += f"      type: {node_type}\n"
            
            if len(filtered_nodes) > 50:
                response_text += f"\n... and {len(filtered_nodes) - 50} more nodes\n"
            
            return {
                "content": [{"type": "text", "text": response_text}],
                "isError": False,
                "nodes": filtered_nodes,
                "total": len(filtered_nodes),
                "tree_id": tree_id  # Include tree_id for reference
            }
        
        # OPTION 2: Direct tree_id lookup (backward compatible)
        if not tree_id:
            return {"content": [{"type": "text", "text": "Error: Either tree_id or userinterface_name is required"}], "isError": True}
        
        query_params = {
            'team_id': team_id,
            'page': page,
            'limit': limit
        }
        
        # Call EXISTING endpoint
        print(f"[@MCP:list_navigation_nodes] Calling /server/navigationTrees/{tree_id}/nodes")
        result = self.api.get(f'/server/navigationTrees/{tree_id}/nodes', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list navigation nodes')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response
        nodes = result.get('nodes', [])
        total = result.get('total', len(nodes))
        
        if not nodes:
            return {"content": [{"type": "text", "text": f"No navigation nodes found in tree {tree_id}"}], "isError": False}
        
        response_text = f"📋 Navigation nodes in tree {tree_id} (showing {len(nodes)} of {total}):\n\n"
        response_text += "  ⚠️  CRITICAL: Use the node_id STRING shown below (e.g., 'home'), NOT the database UUID!\n"
        response_text += "      For create_edge: source_node_id='home' ✅  NOT source_node_id='ce97c317-...' ❌\n\n"
        
        for node in nodes[:50]:  # Limit display to first 50
            # CRITICAL: Show node_id (the string identifier), not id (the UUID)
            node_id = node.get('node_id', 'unknown')  # This is the actual node_id string (e.g., 'home')
            db_uuid = node.get('id')  # This is the database UUID (primary key)
            label = node.get('label', 'unnamed')
            node_type = node.get('type', 'unknown')
            
            response_text += f"  • {label}\n"
            response_text += f"      → node_id: '{node_id}' ← USE THIS in create_edge()\n"
            if db_uuid:
                response_text += f"      (DB UUID: {db_uuid}... - internal only)\n"
            response_text += f"      type: {node_type}\n"
            
            # Show position if available
            position = node.get('position')
            if position:
                x = position.get('x', 0)
                y = position.get('y', 0)
                response_text += f"      position: ({x}, {y})\n"
        
        if len(nodes) > 50:
            response_text += f"\n... and {len(nodes) - 50} more nodes\n"
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
            "nodes": nodes,  # Include full data for programmatic use
            "total": total
        }
    
    def navigate_to_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to target node using pathfinding. Requires take_control() first. tree_id auto-resolved from userinterface_name.
        
        Example: navigate_to_node(host_name='sunri-pi1', device_id='device1', userinterface_name='google_tv', target_node_label='shop')
        
        Args:
            params: {
                'host_name': str (REQUIRED - host where device is connected),
                'device_id': str (REQUIRED - device identifier),
                'userinterface_name': str (REQUIRED - UI name for auto-resolving tree_id),
                'target_node_label': str (REQUIRED - target screen like shop or home)
            }
            
        Returns:
            MCP-formatted response with navigation result
        """
        tree_id = params.get('tree_id')
        userinterface_name = params.get('userinterface_name')
        target_node_id = params.get('target_node_id')
        target_node_label = params.get('target_node_label')
        device_id = params.get('device_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        current_node_id = params.get('current_node_id')
        host_name = params.get('host_name')
        
        # Validate required parameters
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        if not target_node_id and not target_node_label:
            return {"content": [{"type": "text", "text": "Error: target_node_label is required"}], "isError": True}
        
        # Auto-resolve tree_id from userinterface_name if not provided
        if not tree_id:
            ui_result = self.api.get(f'/server/userinterface/getUserInterfaceByName/{userinterface_name}', params={'team_id': team_id})
            if not ui_result or not ui_result.get('id'):
                return {"content": [{"type": "text", "text": f"Error: User interface '{userinterface_name}' not found"}], "isError": True}
            
            userinterface_id = ui_result['id']
            tree_result = self.api.get(f'/server/navigationTrees/getTreeByUserInterfaceId/{userinterface_id}', params={'team_id': team_id})
            
            if not tree_result.get('success') or not tree_result.get('tree'):
                return {"content": [{"type": "text", "text": f"Error: No navigation tree found for '{userinterface_name}'"}], "isError": True}
            
            tree_id = tree_result['tree']['id']
            print(f"[@MCP:navigate_to_node] Auto-resolved tree_id: {tree_id} from userinterface_name: {userinterface_name}")
        
        # Build request - SAME format as frontend (navigationExecutionUtils.ts line 58-65)
        data = {
            'userinterface_name': userinterface_name,
            'device_id': device_id,
            'host_name': host_name
        }
        
        if target_node_id:
            data['target_node_id'] = target_node_id
        if target_node_label:
            data['target_node_label'] = target_node_label
        if current_node_id:
            data['current_node_id'] = current_node_id
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (navigationExecutionUtils.ts line 53)
        print(f"[@MCP:navigate_to_node] Calling /server/navigation/execute/{tree_id}")
        result = self.api.post(
            f'/server/navigation/execute/{tree_id}',
            data=data,
            params=query_params
        )
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Navigation failed')
            return {"content": [{"type": "text", "text": f"Navigation failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id) - SAME as frontend (navigationExecutionUtils.ts line 75)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:navigate_to_node] Async execution started: {execution_id}")
            
            # POLL for completion - SAME pattern as frontend (navigationExecutionUtils.ts line 84-142)
            return self._poll_navigation_completion(execution_id, device_id, host_name, team_id, target_node_label or target_node_id)
        
        # Sync result - return directly
        print(f"[@MCP:navigate_to_node] Sync execution completed")
        return self.formatter.format_api_response(result)
    
    def _poll_navigation_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, target_label: str, max_wait: int = 60) -> Dict[str, Any]:
        """
        Poll navigation execution until complete
        
        REUSES existing /server/navigation/execution/<id>/status API (same as frontend)
        Pattern from navigationExecutionUtils.ts lines 84-142
        """
        poll_interval = 1  # 1 second (same as frontend line 93)
        elapsed = 0
        
        print(f"[@MCP:poll_navigation] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (navigationExecutionUtils.ts line 85-86)
            status = self.api.get(
                f'/server/navigation/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_navigation] Navigation completed successfully after {elapsed}s")
                result = status.get('result', {})
                
                # Format detailed navigation summary
                formatted_result = self._format_navigation_result(result, target_label)
                return {"content": [{"type": "text", "text": formatted_result}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_navigation] Navigation failed after {elapsed}s")
                error = status.get('error', 'Navigation failed')
                return {"content": [{"type": "text", "text": f"❌ Navigation failed: {error}"}], "isError": True}
            
            elif current_status == 'running':
                progress = status.get('progress', 0)
                message = status.get('message', 'Running...')
                print(f"[@MCP:poll_navigation] Status: {message} ({progress}%) - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_navigation] Navigation timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Navigation timed out after {max_wait}s"}], "isError": True}
    
    def _format_navigation_result(self, result: Dict[str, Any], target_label: str) -> str:
        """
        Format navigation result with detailed step information
        
        Args:
            result: Navigation execution result from backend
            target_label: Target node label for reference
            
        Returns:
            Formatted string with navigation summary
        """
        message = result.get('message', f'Navigation to {target_label} completed')
        already_at_target = result.get('already_at_target', False)
        
        # Case 1: Already at target - simple message
        if already_at_target:
            return f"✅ {message}"
        
        # Case 2: Navigation with steps - detailed summary
        navigation_path = result.get('navigation_path', [])
        transitions_executed = result.get('transitions_executed', 0)
        actions_executed = result.get('actions_executed', 0)
        execution_time = result.get('execution_time', 0)
        
        # Build detailed output
        output = f"✅ {message}\n"
        output += f"📊 Summary: {transitions_executed} transitions, {actions_executed} actions, {execution_time:.1f}s\n"
        
        # Show navigation path if available
        if navigation_path and len(navigation_path) > 0:
            output += f"\n🗺️  Navigation Path ({len(navigation_path)} steps):\n"
            for i, step in enumerate(navigation_path):
                step_num = i + 1
                from_node = step.get('from_node_label', 'unknown')
                to_node = step.get('to_node_label', 'unknown')
                
                # Get action summary for this step
                actions = step.get('actions', [])
                action_summary = self._format_step_actions(actions)
                
                output += f"  {step_num}. {from_node} → {to_node}"
                if action_summary:
                    output += f" ({action_summary})"
                output += "\n"
        
        return output
    
    def _format_step_actions(self, actions: list) -> str:
        """Format actions for a single navigation step"""
        if not actions:
            return "no actions"
        
        if len(actions) == 1:
            action = actions[0]
            cmd = action.get('command', 'unknown')
            
            # Format based on command type
            if cmd == 'click_element_by_id':
                element_id = action.get('params', {}).get('element_id', '')
                return f"click {element_id}" if element_id else "click"
            elif cmd == 'press_key':
                key = action.get('params', {}).get('key', '')
                return f"press {key}" if key else "press key"
            elif cmd == 'launch_app':
                return "launch app"
            elif cmd == 'tap_coordinates':
                return "tap"
            else:
                return cmd
        else:
            # Multiple actions - just show count
            return f"{len(actions)} actions"
    
    def preview_userinterface(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compact text preview of userinterface navigation tree
        
        Shows all nodes, edges, actions, and verifications in compact format.
        Perfect for quick overview: "What do we test and how?"
        
        Args:
            params: {
                'userinterface_name': str (REQUIRED) - e.g., 'netflix_mobile'
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            Compact text showing all transitions (8-10 lines)
            
        Example output:
            netflix_mobile (7 nodes, 13 transitions)
            
            Entry→home: launch_app + tap(540,1645) [✓ Startseite]
            home⟷search: click(Suchen) ⟷ click(Nach oben navigieren) [✓ Suchen]
            home⟷content_detail: click(The Witcher) ⟷ BACK [✓ abspielen]
            ...
        """
        userinterface_name = params.get('userinterface_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        
        # Get complete userinterface data
        try:
            # Step 1: Get userinterface by name
            ui_result = self.api.get(f'/server/userinterface/getUserInterfaceByName/{userinterface_name}', params={'team_id': team_id})
            if not ui_result or not ui_result.get('id'):
                return {"content": [{"type": "text", "text": f"Error: User interface '{userinterface_name}' not found"}], "isError": True}
            
            userinterface_id = ui_result['id']
            
            # Step 2: Get complete tree data (same endpoint as get_userinterface_complete)
            tree_result = self.api.get(
                f'/server/navigationTrees/getTreeByUserInterfaceId/{userinterface_id}',
                params={
                    'team_id': team_id,
                    'include_nested': 'true',
                    'include_metrics': 'true'
                }
            )
            
            if not tree_result.get('success') or not tree_result.get('tree'):
                return {"content": [{"type": "text", "text": f"Error: No navigation data found for '{userinterface_name}'"}], "isError": True}
            
            complete_data = tree_result['tree'].get('metadata', {})
            
            # Format compact preview
            output = self._format_compact_preview(userinterface_name, complete_data)
            
            return {
                "content": [{"type": "text", "text": output}],
                "isError": False
            }
            
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}
    
    def _format_compact_preview(self, ui_name: str, data: Dict[str, Any]) -> str:
        """Format navigation tree as compact text with nodes and transitions"""
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        
        # Create node lookup (by node_id, not id)
        node_lookup = {node.get('node_id', node.get('id')): node for node in nodes}
        
        # Count transitions (edges * 2 for bidirectional)
        transition_count = sum(2 if len(edge.get('action_sets', [])) > 1 else 1 for edge in edges)
        
        output = f"{ui_name} ({len(nodes)} nodes, {transition_count} transitions)\n\n"
        
        # === NODES SECTION ===
        output += "=== NODES ===\n"
        for node in nodes:
            node_id = node.get('node_id', node.get('id', 'unknown'))
            label = node.get('label', node_id)
            
            # Skip entry-node (technical node, not a real screen)
            if node_id == 'entry-node' or label == 'Entry':
                continue
            
            # Show only label (for human readability)
            output += f"• {label}\n"
            
            # Get verifications from ROOT level (single source of truth)
            verifications = node.get('verifications', [])
            if verifications:
                for verif in verifications:
                    method = verif.get('method', '')
                    expected = verif.get('expected', True)
                    params = verif.get('params', {})
                    text = params.get('text', '')
                    timeout = params.get('timeout', 5000)
                    symbol = '✓' if expected else '✗'
                    if expected:
                        output += f"  Verifications: {symbol} {text} appears ({timeout}ms)\n"
                    else:
                        output += f"  Verifications: {symbol} {text} NOT present ({timeout}ms)\n"
            else:
                output += f"  Verifications: none\n"
            output += "\n"
        
        # === TRANSITIONS SECTION ===
        output += "=== TRANSITIONS ===\n"
        for edge in edges:
            # Get source and target labels
            source_node_id = edge.get('source_node_id', edge.get('source'))
            target_node_id = edge.get('target_node_id', edge.get('target'))
            
            source_label = edge.get('source_label')
            target_label = edge.get('target_label')
            
            if not source_label:
                source_node = node_lookup.get(source_node_id)
                source_label = source_node.get('label', source_node_id) if source_node else source_node_id
            
            if not target_label:
                target_node = node_lookup.get(target_node_id)
                target_label = target_node.get('label', target_node_id) if target_node else target_node_id
            
            action_sets = edge.get('action_sets', [])
            
            if not action_sets:
                continue
            
            # Check if bidirectional
            is_bidirectional = len(action_sets) > 1 and action_sets[1].get('actions')
            
            if is_bidirectional:
                output += f"{source_label} ⟷ {target_label}\n"
                # Forward actions
                forward_actions = action_sets[0].get('actions', [])
                output += f"  Forward: {self._format_actions_with_delay(forward_actions)}\n"
                # Backward actions
                backward_actions = action_sets[1].get('actions', [])
                output += f"  Backward: {self._format_actions_with_delay(backward_actions)}\n"
            else:
                output += f"{source_label} → {target_label}\n"
                forward_actions = action_sets[0].get('actions', [])
                output += f"  Actions: {self._format_actions_with_delay(forward_actions)}\n"
            
            output += "\n"
        
        return output
    
    def _format_actions(self, actions: list) -> str:
        """Format action list to compact string"""
        if not actions:
            return "none"
        
        formatted = []
        for action in actions[:3]:  # Limit to first 3 actions
            cmd = action.get('command', 'unknown')
            params = action.get('params', {})
            
            if cmd == 'launch_app':
                formatted.append('launch_app')
            elif cmd == 'tap_coordinates':
                x = params.get('x', 0)
                y = params.get('y', 0)
                formatted.append(f'tap({x},{y})')
            elif cmd == 'click_element':
                element_id = params.get('element_id', 'unknown')
                # Truncate long element names
                if len(element_id) > 20:
                    element_id = element_id[:17] + '...'
                formatted.append(f'click({element_id})')
            elif cmd == 'press_key':
                key = params.get('key', 'unknown')
                formatted.append(key)
            elif cmd == 'type_text':
                text = params.get('text', '')
                if len(text) > 15:
                    text = text[:12] + '...'
                formatted.append(f'type({text})')
            else:
                formatted.append(cmd)
        
        if len(actions) > 3:
            formatted.append(f'+{len(actions)-3}more')
        
        return ' + '.join(formatted)
    
    def _format_actions_with_delay(self, actions: list) -> str:
        """Format action list with delay information for detailed view"""
        if not actions:
            return "none [delay: 0ms]"
        
        formatted = []
        for action in actions:
            cmd = action.get('command', 'unknown')
            params = action.get('params', {})
            
            if cmd == 'launch_app':
                package = params.get('package', '')
                formatted.append(f'launch_app({package})')
            elif cmd == 'tap_coordinates':
                x = params.get('x', 0)
                y = params.get('y', 0)
                formatted.append(f'tap({x},{y})')
            elif cmd == 'click_element':
                element_id = params.get('element_id', 'unknown')
                if len(element_id) > 30:
                    element_id = element_id[:27] + '...'
                formatted.append(f'click({element_id})')
            elif cmd == 'press_key':
                key = params.get('key', 'unknown')
                formatted.append(key)
            elif cmd == 'type_text':
                text = params.get('text', '')
                if len(text) > 20:
                    text = text[:17] + '...'
                formatted.append(f'type({text})')
            else:
                formatted.append(cmd)
        
        # Get delay/wait_time from last action
        delay = 0
        if actions:
            last_action = actions[-1]
            delay = last_action.get('params', {}).get('wait_time', 0)
            if not delay:
                delay = last_action.get('params', {}).get('delay', 0)
        
        action_str = ' + '.join(formatted)
        return f"{action_str} [delay: {delay}ms]"
    
    def _get_verification_summary(self, node: Dict[str, Any]) -> str:
        """Extract verification summary from node"""
        if not node:
            return ""
        
        # Get verifications from ROOT level (single source of truth)
        verifications = node.get('verifications', [])
        if not verifications:
            return ""
        
        # Get first verification only for compact view
        verif = verifications[0]
        method = verif.get('method', '')
        expected = verif.get('expected', True)
        params = verif.get('params', {})
        
        # Format based on method
        if 'Element' in method:
            text = params.get('text', '')
            if len(text) > 15:
                text = text[:12] + '...'
            symbol = '✓' if expected else '✗'
            return f"[{symbol} {text}]"
        
        return ""

