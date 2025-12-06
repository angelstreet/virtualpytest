"""
Agent Registry REST API Routes

Provides HTTP endpoints for agent CRUD operations, versioning, and import/export.
"""

from flask import Blueprint, request, jsonify, Response
from typing import Optional
import yaml

from agent.registry import (
    AgentRegistry,
    get_agent_registry,
    AgentDefinition,
    validate_agent_yaml,
    export_agent_yaml,
    AgentValidationError
)
from agent.async_utils import run_async

# Create blueprint
server_agent_registry_bp = Blueprint('server_agent_registry', __name__, url_prefix='/api/agents')


def get_team_id() -> str:
    """Get team ID from request (placeholder - implement with auth)"""
    # TODO: Implement proper team/user authentication
    return request.headers.get('X-Team-ID', 'default')


def get_user_id() -> Optional[str]:
    """Get user ID from request (placeholder - implement with auth)"""
    # TODO: Implement proper authentication
    return request.headers.get('X-User-ID')


@server_agent_registry_bp.route('/', methods=['GET'])
def list_agents():
    """
    List all agents (latest versions)
    
    Query params:
        - status: Filter by status (draft, published, deprecated)
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        status = request.args.get('status')
        
        registry = get_agent_registry()
        agents = run_async(registry.list_agents(team_id, status))
        
        return jsonify({
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>', methods=['GET'])
def get_agent(agent_id: str):
    """
    Get specific agent by ID
    
    Query params:
        - version: Specific version (default: latest published)
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        version = request.args.get('version')
        
        registry = get_agent_registry()
        agent = run_async(registry.get(agent_id, version, team_id))
        
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>/versions', methods=['GET'])
def list_agent_versions(agent_id: str):
    """List all versions of an agent"""
    import asyncio
    
    try:
        team_id = get_team_id()
        
        registry = get_agent_registry()
        versions = run_async(registry.list_versions(agent_id, team_id))
        
        return jsonify({
            'agent_id': agent_id,
            'versions': versions,
            'count': len(versions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/', methods=['POST'])
def register_agent():
    """
    Register new agent or version
    
    Body: AgentDefinition JSON
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        user_id = get_user_id()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate and create agent
        try:
            agent = AgentDefinition(**data)
        except Exception as e:
            return jsonify({'error': f'Invalid agent definition: {str(e)}'}), 400
        
        registry = get_agent_registry()
        agent_id = run_async(registry.register(agent, team_id, user_id))
        
        return jsonify({
            'id': agent_id,
            'agent_id': agent.metadata.id,
            'version': agent.metadata.version,
            'message': 'Agent registered successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/import', methods=['POST'])
def import_agent_yaml():
    """
    Import agent from YAML
    
    Body: YAML string or file upload
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        user_id = get_user_id()
        
        # Check if file upload or raw YAML
        if 'file' in request.files:
            file = request.files['file']
            yaml_content = file.read().decode('utf-8')
        elif request.data:
            yaml_content = request.data.decode('utf-8')
        else:
            return jsonify({'error': 'No YAML content provided'}), 400
        
        # Validate YAML
        try:
            agent = validate_agent_yaml(yaml_content)
        except AgentValidationError as e:
            return jsonify({'error': str(e)}), 400
        
        # Register agent
        registry = get_agent_registry()
        agent_id = run_async(registry.register(agent, team_id, user_id))
        
        return jsonify({
            'id': agent_id,
            'agent_id': agent.metadata.id,
            'version': agent.metadata.version,
            'message': 'Agent imported successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>/export', methods=['GET'])
def export_agent(agent_id: str):
    """
    Export agent as YAML
    
    Query params:
        - version: Specific version (default: latest published)
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        version = request.args.get('version')
        
        registry = get_agent_registry()
        agent = run_async(registry.get(agent_id, version, team_id))
        
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Export to YAML
        yaml_content = export_agent_yaml(agent)
        
        # Return as downloadable file
        return Response(
            yaml_content,
            mimetype='text/yaml',
            headers={
                'Content-Disposition': f'attachment; filename={agent_id}-{agent.metadata.version}.yaml'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>/publish', methods=['POST'])
def publish_agent(agent_id: str):
    """
    Publish an agent version
    
    Body: { "version": "1.0.0" }
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        data = request.get_json()
        version = data.get('version')
        
        if not version:
            return jsonify({'error': 'Version required'}), 400
        
        registry = get_agent_registry()
        success = run_async(registry.publish(agent_id, version, team_id))
        
        if success:
            return jsonify({'message': 'Agent published successfully'}), 200
        else:
            return jsonify({'error': 'Agent not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>/deprecate', methods=['POST'])
def deprecate_agent(agent_id: str):
    """
    Deprecate an agent version
    
    Body: { "version": "1.0.0" }
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        data = request.get_json()
        version = data.get('version')
        
        if not version:
            return jsonify({'error': 'Version required'}), 400
        
        registry = get_agent_registry()
        success = run_async(registry.deprecate(agent_id, version, team_id))
        
        if success:
            return jsonify({'message': 'Agent deprecated successfully'}), 200
        else:
            return jsonify({'error': 'Agent not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id: str):
    """
    Delete an agent version
    
    Query params:
        - version: Version to delete (required)
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        version = request.args.get('version')
        
        if not version:
            return jsonify({'error': 'Version required'}), 400
        
        registry = get_agent_registry()
        success = run_async(registry.delete(agent_id, version, team_id))
        
        if success:
            return jsonify({'message': 'Agent deleted successfully'}), 200
        else:
            return jsonify({'error': 'Agent not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/search', methods=['GET'])
def search_agents():
    """
    Search agents by name, description, or tags
    
    Query params:
        - q: Search query
    """
    import asyncio
    
    try:
        team_id = get_team_id()
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        registry = get_agent_registry()
        agents = run_async(registry.search(query, team_id))
        
        return jsonify({
            'query': query,
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/events/<event_type>', methods=['GET'])
def get_agents_for_event(event_type: str):
    """Get all agents that handle a specific event type"""
    import asyncio
    
    try:
        team_id = get_team_id()
        
        registry = get_agent_registry()
        agents = run_async(registry.get_agents_for_event(event_type, team_id))
        
        return jsonify({
            'event_type': event_type,
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

