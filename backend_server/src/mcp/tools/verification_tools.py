"""
Verification Tools - Device state verification

Verify UI elements, video playback, text, and other device states.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class VerificationTools:
    """Device state verification tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def list_verifications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available verification types for a device
        
        REUSES existing /server/system/device-actions endpoint (returns both actions and verifications)
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with categorized list of available verifications
        """
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        if not device_id:
            return {"content": [{"type": "text", "text": "Error: device_id is required"}], "isError": True}
        
        query_params = {
            'host_name': host_name,
            'device_id': device_id,
            'team_id': team_id
        }
        
        # Call EXISTING endpoint (same as list_actions - returns both)
        print(f"[@MCP:list_verifications] Calling /server/system/getDeviceActions")
        result = self.api.get('/server/system/getDeviceActions', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list verifications')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response - group verifications by type
        device_verification_types = result.get('device_verification_types', {})
        device_model = result.get('device_model', 'unknown')
        
        if not device_verification_types:
            return {"content": [{"type": "text", "text": f"No verifications available for {device_model} device"}], "isError": False}
        
        response_text = f"📋 Available verifications for {device_model} ({device_id}):\n\n"
        
        if device_model in ['host_vnc', 'web']:
            response_text += "For waitForElementToAppear search_term, use selector priority:\n"
            response_text += "1. #id > 2. //xpath > 3. [attr] or .class > 4. plain text (fallback)\n"
            response_text += "1 unique selector is enough. Only use multiple verifications if single selector is not unique.\n"
            response_text += "Prefer stable structural elements (form fields, buttons) over dynamic content.\n\n"
        
        for category, verifications in device_verification_types.items():
            if not verifications:
                continue
            response_text += f"**{category.upper()}** ({len(verifications)} verifications):\n"
            
            # Handle both dict and list structures
            if isinstance(verifications, dict):
                items = list(verifications.items())[:10]
                for method_name, method_info in items:
                    description = method_info.get('description', '')
                    params_dict = method_info.get('params', {})
                    
                    response_text += f"  • {method_name}\n"
                    if description:
                        response_text += f"    {description}\n"
                    if params_dict:
                        response_text += f"    params: {params_dict}\n"
                
                if len(verifications) > 10:
                    response_text += f"  ... and {len(verifications) - 10} more\n"
            elif isinstance(verifications, list):
                for verification in verifications[:10]:
                    label = verification.get('label', verification.get('command', 'unknown'))
                    command = verification.get('command', 'unknown')
                    params_dict = verification.get('params', {})
                    description = verification.get('description', '')
                    
                    response_text += f"  • {label} (command: {command})\n"
                    if params_dict:
                        response_text += f"    params: {params_dict}\n"
                    if description:
                        response_text += f"    {description}\n"
                
                if len(verifications) > 10:
                    response_text += f"  ... and {len(verifications) - 10} more\n"
            
            response_text += "\n"
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
            "device_verification_types": device_verification_types  # Include full data for programmatic use
        }
    
    def dump_ui_elements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dump UI elements from current device screen
        
        REUSES existing verification endpoints
        
        Args:
            params: {
                'device_id': str (OPTIONAL - defaults to 'device1'),
                'host_name': str (OPTIONAL - defaults to 'sunri-pi1'),
                'team_id': str (OPTIONAL),
                'platform': str (OPTIONAL - 'mobile', 'web', 'tv')
            }
            
        Returns:
            MCP-formatted response with UI elements array
        """
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        platform = params.get('platform', 'mobile')
        
        query_params = {
            'device_id': device_id,
            'host_name': host_name,
            'team_id': team_id,
            'platform': platform
        }
        
        print(f"[@MCP:dump_ui_elements] Dumping UI for {device_id} on {host_name}")
        
        # Use /server/remote/dumpUi endpoint (proxies to backend_host)
        result = self.api.post('/server/remote/dumpUi', data=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to dump UI elements')
            return {"content": [{"type": "text", "text": f"❌ UI dump failed: {error_msg}"}], "isError": True}
        
        # ✅ Get elements from backend and format like the console output
        # Backend provides elements array, we format it to match console logs
        elements = result.get('elements', [])
        
        if not elements:
            return {"content": [{"type": "text", "text": "No UI elements found"}], "isError": False}
        
        # Format output matching backend_host console format (host_remote_routes.py prints this)
        formatted_lines = []
        for i, element in enumerate(elements):
            # ✅ Get element name with EXACT same priority as backend console logs (android_mobile.py line 255-271)
            # Priority 1: content_desc (contentDesc in JSON)
            # Priority 2: text
            # Priority 3: className
            name = ""
            
            content_desc = element.get('contentDesc', '').strip()
            text = element.get('text', '').strip()
            
            if content_desc and content_desc != '<no content-desc>':
                name = content_desc
            elif text and text != '<no text>':
                name = f'"{text}"'  # Wrap text in quotes like console logs
            else:
                class_name = element.get('className', '')
                name = class_name.split('.')[-1] if class_name else "Unknown"
            
            # Parse bounds to get x, y, width, height
            bounds = element.get('bounds', {})
            x = bounds.get('left', 0)
            y = bounds.get('top', 0)
            width = bounds.get('right', 0) - x
            height = bounds.get('bottom', 0) - y
            
            element_id = element.get('id', i)
            
            formatted_lines.append(
                f"[HOST] Remote[ANDROID_MOBILE]: Element: {name} | Index: {element_id} | Order: {i+1} | X: {x} | Y: {y} | Width: {width} | Height: {height}"
            )
        
        # Compact text: just count and clickable element names
        clickable = [e for e in elements if e.get('clickable')]
        text_summary = f"{len(elements)} elements ({len(clickable)} clickable)"
        
        return {
            "content": [{"type": "text", "text": text_summary}],
            "isError": False,
            "elements": elements  # Full elements, no raw_result duplicate
        }
    
    def _poll_verification_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, max_wait: int = 30) -> Dict[str, Any]:
        """
        Poll verification execution until complete
        
        REUSES existing /server/verification/execution/<id>/status API (same as frontend)
        Pattern from useVerification.ts lines 278-306
        """
        poll_interval = 1  # 1 second (same as frontend line 283)
        elapsed = 0
        
        print(f"[@MCP:poll_verification] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (useVerification.ts line 273)
            status = self.api.get(
                f'/server/verification/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_verification] Verification completed successfully after {elapsed}s")
                result = status.get('result', {})
                passed = result.get('passed_count', 0)
                total = result.get('total_count', 0)
                message = f"Verification completed: {passed}/{total} passed"
                return {"content": [{"type": "text", "text": f"✅ {message}"}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_verification] Verification failed after {elapsed}s")
                error = status.get('error', 'Verification failed')
                return {"content": [{"type": "text", "text": f"❌ Verification failed: {error}"}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                print(f"[@MCP:poll_verification] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_verification] Verification timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Verification timed out after {max_wait}s"}], "isError": True}
    
    def verify_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute verifications for a specific node (frontend: NodeEditDialog "Run" button)
        
        This runs the embedded verifications directly using /server/verification/executeBatch.
        Frontend pattern: useVerification.ts handleTest (line 247) - NOT navigation!
        
        Args:
            node_id: Node identifier (REQUIRED)
            tree_id: Navigation tree ID (REQUIRED)
            device_id: Device identifier (optional - defaults to 'device1')
            host_name: Host name (optional - defaults to 'sunri-pi1')
            userinterface_name: User interface name (REQUIRED)
            team_id: Team ID (optional - defaults to default)
        
        Returns:
            Verification results with pass/fail status
        
        Example:
            verify_node({
                "node_id": "home",
                "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
                "userinterface_name": "netflix_mobile"
            })
        """
        try:
            node_id = params['node_id']
            tree_id = params['tree_id']
            userinterface_name = params['userinterface_name']
            device_id = params.get('device_id')
            host_name = params.get('host_name')
            team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
            
            print(f"[@MCP:verify_node] Verifying node {node_id} in tree {tree_id}")
            
            # STEP 1: Get the node to retrieve embedded verifications
            node_result = self.api.get(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                params={'team_id': team_id}
            )
            
            if not node_result.get('success'):
                error_msg = node_result.get('error', 'Unknown error')
                return {"content": [{"type": "text", "text": f"❌ Failed to get node: {error_msg}"}], "isError": True}
            
            node = node_result.get('node', {})
            verifications = node.get('verifications', [])
            node_label = node.get('label', node_id)
            
            if not verifications:
                return {"content": [{"type": "text", "text": f"ℹ️ Node {node_label} has no verifications to run"}], "isError": False}
            
            print(f"[@MCP:verify_node] Node has {len(verifications)} verifications - executing directly")
            
            # STEP 2: Execute verifications directly using /server/verification/executeBatch
            # SAME as frontend useVerification.ts line 247
            # Add userinterface_name to each verification for proper reference resolution
            verifications_with_ui = [
                {**v, 'userinterface_name': userinterface_name}
                for v in verifications
            ]
            
            result = self.api.post(
                '/server/verification/executeBatch',
                data={
                    'host_name': host_name,
                    'device_id': device_id,
                    'verifications': verifications_with_ui,
                    'node_id': node_id,
                    'tree_id': tree_id
                },
                params={'team_id': team_id}
            )
            
            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                return {"content": [{"type": "text", "text": f"❌ Verification execution failed: {error_msg}"}], "isError": True}
            
            # STEP 3: Handle async execution - poll for completion
            execution_id = result.get('execution_id')
            if execution_id:
                print(f"[@MCP:verify_node] Async verification started, polling execution {execution_id}")
                return self._poll_verification_completion(execution_id, device_id, host_name, team_id, max_wait=30)
            
            # Synchronous result
            verification_results = result.get('results', [])
            passed_count = result.get('passed_count', 0)
            total_count = result.get('total_count', 0)
            
            if passed_count == total_count:
                return {"content": [{"type": "text", "text": f"✅ Node verification passed: {passed_count}/{total_count} verifications succeeded\n   Node: {node_label}"}], "isError": False}
            else:
                failed = [vr for vr in verification_results if not vr.get('success')]
                failure_details = "\n   - ".join([f"{vr.get('command', 'unknown')}: {vr.get('message', 'no details')}" for vr in failed])
                return {"content": [{"type": "text", "text": f"❌ Node verification failed: {passed_count}/{total_count} verifications succeeded\n   Node: {node_label}\n   Failed:\n   - {failure_details}"}], "isError": True}
        
        except Exception as e:
            print(f"[@MCP:verify_node] Error: {e}")
            return {"content": [{"type": "text", "text": f"❌ Error verifying node: {str(e)}"}], "isError": True}

