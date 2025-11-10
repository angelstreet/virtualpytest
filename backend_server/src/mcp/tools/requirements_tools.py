from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class RequirementsTools:
    """Requirements management and coverage tracking tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def create_requirement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new requirement
        
        Args:
            params: {
                'requirement_code': str (REQUIRED) - e.g., 'REQ_PLAYBACK_001'
                'requirement_name': str (REQUIRED) - e.g., 'User can play video'
                'description': str (OPTIONAL)
                'priority': str (OPTIONAL) - P1, P2, P3 (default: P2)
                'category': str (OPTIONAL) - e.g., 'playback', 'navigation'
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with requirement_id
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        body = {
            'team_id': team_id,
            'requirement_code': params.get('requirement_code'),
            'requirement_name': params.get('requirement_name'),
            'description': params.get('description'),
            'priority': params.get('priority', 'P2'),
            'category': params.get('category'),
            'app_type': params.get('app_type', 'all'),
            'device_model': params.get('device_model', 'all'),
            'status': params.get('status', 'active'),
            'source_document': params.get('source_document'),
            'acceptance_criteria': params.get('acceptance_criteria'),
            'created_by': params.get('created_by', 'mcp_user')
        }
        
        print(f"[@MCP:create_requirement] Creating requirement: {body['requirement_code']}")
        result = self.api.post('/server/requirements/create', json=body)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to create requirement')
            return {"content": [{"type": "text", "text": f"❌ Create failed: {error_msg}"}], "isError": True}
        
        requirement_id = result.get('requirement_id')
        response_text = f"✅ Requirement created: {body['requirement_code']}\n   ID: {requirement_id}\n   Priority: {body['priority']}\n   Category: {body['category']}"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def list_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all requirements with optional filters
        
        Args:
            params: {
                'team_id': str (OPTIONAL)
                'category': str (OPTIONAL)
                'priority': str (OPTIONAL)
                'status': str (OPTIONAL) - default: 'active'
            }
            
        Returns:
            MCP-formatted response with requirements list
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        query_params = {
            'team_id': team_id,
            'category': params.get('category'),
            'priority': params.get('priority'),
            'status': params.get('status', 'active')
        }
        
        # Remove None values
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        print(f"[@MCP:list_requirements] Fetching requirements with filters: {query_params}")
        result = self.api.get('/server/requirements/list', params=query_params)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list requirements')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        requirements = result.get('requirements', [])
        count = result.get('count', len(requirements))
        
        if not requirements:
            return {"content": [{"type": "text", "text": "No requirements found"}], "isError": False}
        
        response_text = f"📋 Requirements ({count} total):\n\n"
        
        for req in requirements[:50]:  # Limit to 50 for readability
            response_text += f"• {req['requirement_code']} - {req['requirement_name']}\n"
            response_text += f"  Priority: {req.get('priority', 'N/A')} | Category: {req.get('category', 'N/A')}\n"
            if req.get('description'):
                desc = req['description'][:100] + '...' if len(req['description']) > 100 else req['description']
                response_text += f"  Description: {desc}\n"
            response_text += "\n"
        
        if count > 50:
            response_text += f"\n... and {count - 50} more requirements"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_requirement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get requirement by ID
        
        Args:
            params: {
                'requirement_id': str (REQUIRED)
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with requirement details
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        requirement_id = params.get('requirement_id')
        
        query_params = {'team_id': team_id}
        
        print(f"[@MCP:get_requirement] Fetching requirement: {requirement_id}")
        result = self.api.get(f'/server/requirements/{requirement_id}', params=query_params)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Requirement not found')
            return {"content": [{"type": "text", "text": f"❌ Get failed: {error_msg}"}], "isError": True}
        
        req = result.get('requirement', {})
        
        response_text = f"📋 Requirement Details:\n\n"
        response_text += f"Code: {req['requirement_code']}\n"
        response_text += f"Name: {req['requirement_name']}\n"
        response_text += f"Priority: {req.get('priority', 'N/A')}\n"
        response_text += f"Category: {req.get('category', 'N/A')}\n"
        response_text += f"Status: {req.get('status', 'N/A')}\n"
        if req.get('description'):
            response_text += f"\nDescription:\n{req['description']}\n"
        if req.get('acceptance_criteria'):
            response_text += f"\nAcceptance Criteria:\n{req['acceptance_criteria']}\n"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def link_testcase_to_requirement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Link testcase to requirement for coverage tracking
        
        Args:
            params: {
                'testcase_id': str (REQUIRED)
                'requirement_id': str (REQUIRED)
                'coverage_type': str (OPTIONAL) - 'full', 'partial' (default: 'full')
                'coverage_notes': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response
        """
        body = {
            'testcase_id': params.get('testcase_id'),
            'requirement_id': params.get('requirement_id'),
            'coverage_type': params.get('coverage_type', 'full'),
            'coverage_notes': params.get('coverage_notes'),
            'created_by': params.get('created_by', 'mcp_user')
        }
        
        print(f"[@MCP:link_testcase_to_requirement] Linking testcase {body['testcase_id']} to requirement {body['requirement_id']}")
        result = self.api.post('/server/requirements/link-testcase', json=body)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to link testcase')
            return {"content": [{"type": "text", "text": f"❌ Link failed: {error_msg}"}], "isError": True}
        
        response_text = f"✅ Testcase linked successfully\n   Testcase: {body['testcase_id']}\n   Requirement: {body['requirement_id']}\n   Coverage: {body['coverage_type']}"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def unlink_testcase_from_requirement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unlink testcase from requirement
        
        Args:
            params: {
                'testcase_id': str (REQUIRED)
                'requirement_id': str (REQUIRED)
            }
            
        Returns:
            MCP-formatted response
        """
        body = {
            'testcase_id': params.get('testcase_id'),
            'requirement_id': params.get('requirement_id')
        }
        
        print(f"[@MCP:unlink_testcase_from_requirement] Unlinking testcase {body['testcase_id']} from requirement {body['requirement_id']}")
        result = self.api.post('/server/requirements/unlink-testcase', json=body)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to unlink testcase')
            return {"content": [{"type": "text", "text": f"❌ Unlink failed: {error_msg}"}], "isError": True}
        
        response_text = f"✅ Testcase unlinked successfully"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_testcase_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all requirements linked to a testcase
        
        Args:
            params: {
                'testcase_id': str (REQUIRED)
            }
            
        Returns:
            MCP-formatted response with requirements list
        """
        testcase_id = params.get('testcase_id')
        
        print(f"[@MCP:get_testcase_requirements] Fetching requirements for testcase: {testcase_id}")
        result = self.api.get(f'/server/requirements/testcase/{testcase_id}/requirements')
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to get requirements')
            return {"content": [{"type": "text", "text": f"❌ Get failed: {error_msg}"}], "isError": True}
        
        requirements = result.get('requirements', [])
        count = result.get('count', len(requirements))
        
        if not requirements:
            return {"content": [{"type": "text", "text": f"No requirements linked to testcase: {testcase_id}"}], "isError": False}
        
        response_text = f"📋 Requirements for testcase {testcase_id} ({count} total):\n\n"
        
        for req in requirements:
            response_text += f"• {req['requirement_code']} - {req['requirement_name']}\n"
            response_text += f"  Coverage: {req.get('coverage_type', 'full')}\n"
            if req.get('coverage_notes'):
                response_text += f"  Notes: {req['coverage_notes']}\n"
            response_text += "\n"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_requirement_coverage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed coverage for a requirement
        
        Args:
            params: {
                'requirement_id': str (REQUIRED)
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with coverage details
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        requirement_id = params.get('requirement_id')
        
        query_params = {'team_id': team_id}
        
        print(f"[@MCP:get_requirement_coverage] Fetching coverage for requirement: {requirement_id}")
        result = self.api.get(f'/server/requirements/{requirement_id}/coverage', params=query_params)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to get coverage')
            return {"content": [{"type": "text", "text": f"❌ Get failed: {error_msg}"}], "isError": True}
        
        coverage = result.get('coverage', {})
        
        response_text = f"📊 Coverage for {coverage.get('requirement_code', 'N/A')}:\n\n"
        response_text += f"Testcases: {coverage.get('testcase_count', 0)}\n"
        response_text += f"Scripts: {coverage.get('script_count', 0)}\n"
        response_text += f"Executions: {coverage.get('execution_count', 0)}\n"
        response_text += f"Last Execution: {coverage.get('last_execution_date', 'Never')}\n"
        
        if coverage.get('testcases'):
            response_text += f"\nLinked Testcases:\n"
            for tc in coverage['testcases'][:10]:
                response_text += f"  • {tc['testcase_name']} ({tc.get('coverage_type', 'full')})\n"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_coverage_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get coverage summary across all requirements
        
        Args:
            params: {
                'team_id': str (OPTIONAL)
                'category': str (OPTIONAL)
                'priority': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with coverage metrics
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        query_params = {
            'team_id': team_id,
            'category': params.get('category'),
            'priority': params.get('priority')
        }
        
        # Remove None values
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        print(f"[@MCP:get_coverage_summary] Fetching coverage summary")
        result = self.api.get('/server/requirements/coverage/summary', params=query_params)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to get coverage summary')
            return {"content": [{"type": "text", "text": f"❌ Get failed: {error_msg}"}], "isError": True}
        
        summary = result.get('summary', {})
        
        response_text = f"📊 Requirements Coverage Summary:\n\n"
        response_text += f"Total Requirements: {summary.get('total_requirements', 0)}\n"
        response_text += f"Covered: {summary.get('covered_requirements', 0)}\n"
        response_text += f"Uncovered: {summary.get('uncovered_requirements', 0)}\n"
        response_text += f"Coverage Rate: {summary.get('coverage_percentage', 0):.1f}%\n\n"
        
        if summary.get('by_priority'):
            response_text += "By Priority:\n"
            for priority, stats in summary['by_priority'].items():
                response_text += f"  {priority}: {stats.get('covered', 0)}/{stats.get('total', 0)} ({stats.get('percentage', 0):.1f}%)\n"
        
        if summary.get('by_category'):
            response_text += "\nBy Category:\n"
            for category, stats in summary['by_category'].items():
                response_text += f"  {category}: {stats.get('covered', 0)}/{stats.get('total', 0)} ({stats.get('percentage', 0):.1f}%)\n"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_uncovered_requirements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all requirements without test coverage
        
        Args:
            params: {
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with uncovered requirements
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        query_params = {'team_id': team_id}
        
        print(f"[@MCP:get_uncovered_requirements] Fetching uncovered requirements")
        result = self.api.get('/server/requirements/uncovered', params=query_params)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to get uncovered requirements')
            return {"content": [{"type": "text", "text": f"❌ Get failed: {error_msg}"}], "isError": True}
        
        requirements = result.get('requirements', [])
        count = result.get('count', len(requirements))
        
        if not requirements:
            return {"content": [{"type": "text", "text": "✅ All requirements have test coverage!"}], "isError": False}
        
        response_text = f"⚠️  Uncovered Requirements ({count} total):\n\n"
        
        for req in requirements[:50]:
            response_text += f"• {req['requirement_code']} - {req['requirement_name']}\n"
            response_text += f"  Priority: {req.get('priority', 'N/A')} | Category: {req.get('category', 'N/A')}\n\n"
        
        if count > 50:
            response_text += f"\n... and {count - 50} more uncovered requirements"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}

