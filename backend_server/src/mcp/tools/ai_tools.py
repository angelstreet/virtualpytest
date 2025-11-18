"""
AI Tools - AI-powered test generation

Generate test graphs from natural language using AI.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class AITools:
    """AI-powered test generation tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def generate_test_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate test case graph from natural language prompt
        
        ⚠️ CRITICAL: Host/Device Selection
        - If user explicitly specifies host_name/device_id: Use those values directly
        - Otherwise: Call get_compatible_hosts(userinterface_name='...') FIRST to find compatible hosts
        - DO NOT use default values blindly without checking compatibility
        
        Uses AI to convert natural language descriptions into executable test graphs.
        Returns a graph object that can be saved or executed directly.
        
        REUSES existing /server/ai/generatePlan endpoint (same as frontend)
        Pattern from useTestCaseAI.ts line 45
        
        Workflow (when host NOT specified by user):
            1. Call get_compatible_hosts(userinterface_name='your_ui')
            2. Use recommended host_name and device_id from response
            3. Call generate_test_graph with those values
        
        Workflow (when user specifies host):
            1. User says "use host X with device Y"
            2. Call generate_test_graph directly with host_name='X', device_id='Y'
        
        Args:
            params: {
                'prompt': str (REQUIRED) - Natural language test description,
                'device_id': str (OPTIONAL),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL),
                'userinterface_name': str (REQUIRED),
                'current_node_id': str (OPTIONAL) - Starting node for context
            }
            
        Returns:
            MCP-formatted response with generated graph JSON, analysis, and stats.
            Graph can be passed to execute_testcase or save_testcase.
        """
        prompt = params.get('prompt')
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name = params.get('userinterface_name')
        current_node_id = params.get('current_node_id')
        
        # Validate required parameters
        if not prompt:
            return {"content": [{"type": "text", "text": "Error: prompt is required"}], "isError": True}
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
        # Build request - SAME format as frontend (useTestCaseAI.ts line 48-53)
        data = {
            'prompt': prompt,
            'userinterface_name': userinterface_name,
            'device_id': device_id,
            'host_name': host_name
        }
        
        if current_node_id:
            data['current_node_id'] = current_node_id
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useTestCaseAI.ts line 45)
        print(f"[@MCP:generate_test_graph] Calling /server/ai/generatePlan with prompt: {prompt[:50]}...")
        result = self.api.post('/server/ai/generatePlan', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'AI generation failed')
            
            # Check if disambiguation needed
            if result.get('needs_disambiguation'):
                ambiguities = result.get('ambiguities', [])
                return {
                    "content": [{
                        "type": "text", 
                        "text": f"⚠️ Disambiguation needed:\n" + "\n".join([f"- '{a.get('phrase')}' could mean: {', '.join(a.get('options', []))}" for a in ambiguities])
                    }], 
                    "isError": True
                }
            
            return {"content": [{"type": "text", "text": f"❌ AI generation failed: {error_msg}"}], "isError": True}
        
        # Check if not feasible
        if result.get('feasible') == False:
            return {"content": [{"type": "text", "text": f"❌ Task not feasible: {result.get('error', 'Cannot be automated with available nodes')}"}], "isError": True}
        
        # Success - format response with graph and metadata
        graph = result.get('graph', {})
        analysis = result.get('analysis', '')
        stats = result.get('generation_stats', {})
        
        response_text = f"✅ Test case generated successfully!\n\n"
        response_text += f"Analysis: {analysis}\n\n"
        
        if stats:
            block_counts = stats.get('block_counts', {})
            response_text += f"Blocks: {block_counts.get('total', 0)} total "
            response_text += f"({block_counts.get('navigation', 0)} nav, {block_counts.get('action', 0)} action, {block_counts.get('verification', 0)} verify)\n"
        
        response_text += f"\nUse execute_testcase() to run or save_testcase() to save."
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
            "graph": graph,  # Include graph for further operations
            "analysis": analysis,
            "stats": stats
        }

