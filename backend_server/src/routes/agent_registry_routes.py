"""
Agent Registry REST API Routes

System agents are loaded from YAML on startup.
No team_id - agents are global system resources.
"""

from flask import Blueprint, request, jsonify, Response
from typing import Optional

from agent.registry import (
    get_agent_registry,
    AgentDefinition,
    validate_agent_yaml,
    export_agent_yaml,
    AgentValidationError,
    reload_agents
)

# Create blueprint
server_agent_registry_bp = Blueprint('server_agent_registry', __name__, url_prefix='/server/agents')


@server_agent_registry_bp.route('/', methods=['GET'])
def list_agents():
    """
    List all system agents (loaded from YAML templates).
    
    Query params:
        - selectable: Filter by selectable (true/false)
        - platform: Filter by platform (web/mobile/stb)
    
    NOTE: No team_id - agents are global system resources.
    """
    try:
        registry = get_agent_registry()
        
        # Check for filters
        selectable_filter = request.args.get('selectable')
        platform_filter = request.args.get('platform')
        
        if selectable_filter == 'true':
            agents = registry.get_selectable_agents()
        elif selectable_filter == 'false':
            agents = registry.get_internal_agents()
        elif platform_filter:
            agents = registry.get_agents_by_platform(platform_filter)
        else:
            agents = registry.list_agents()
        
        return jsonify({
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>', methods=['GET'])
def get_agent(agent_id: str):
    """
    Get specific agent by ID.
    
    NOTE: No team_id or version - returns system agent from YAML.
    """
    try:
        registry = get_agent_registry()
        agent = registry.get(agent_id)
        
        if not agent:
            return jsonify({'error': f'Agent not found: {agent_id}'}), 404
        
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/<agent_id>/export', methods=['GET'])
def export_agent(agent_id: str):
    """
    Export agent as YAML file.
    """
    try:
        registry = get_agent_registry()
        agent = registry.get(agent_id)
        
        if not agent:
            return jsonify({'error': f'Agent not found: {agent_id}'}), 404
        
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


@server_agent_registry_bp.route('/events/<event_type>', methods=['GET'])
def get_agents_for_event(event_type: str):
    """
    Get all agents that handle a specific event type.
    """
    try:
        registry = get_agent_registry()
        agents = registry.get_agents_for_event(event_type)
        
        return jsonify({
            'event_type': event_type,
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/reload', methods=['POST'])
def reload_agents_endpoint():
    """
    Reload all agents from YAML templates.
    Useful for development when YAML files are modified.
    """
    try:
        reload_agents()
        
        registry = get_agent_registry()
        agents = registry.list_agents()
        
        return jsonify({
            'message': 'Agents reloaded from YAML',
            'count': len(agents),
            'agents': [a.metadata.id for a in agents]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_registry_bp.route('/selectable', methods=['GET'])
def list_selectable_agents():
    """
    List only agents that can be selected by users in the UI dropdown.
    Convenience endpoint - same as ?selectable=true
    """
    try:
        registry = get_agent_registry()
        agents = registry.get_selectable_agents()
        
        return jsonify({
            'agents': [agent.to_dict() for agent in agents],
            'count': len(agents)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Keep import endpoint for custom agents (future feature)
@server_agent_registry_bp.route('/import', methods=['POST'])
def import_agent_yaml():
    """
    Import custom agent from YAML.
    
    NOTE: This is for user-created custom agents, not system agents.
    System agents should be modified by editing YAML templates and calling /reload.
    
    Body: YAML string or file upload
    """
    try:
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
        
        # For now, just validate and return success
        # In future, this could save to database for custom agents
        return jsonify({
            'agent_id': agent.metadata.id,
            'version': agent.metadata.version,
            'nickname': agent.metadata.nickname,
            'message': 'Agent YAML validated successfully. To add system agents, place YAML in templates/ and call /reload.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
