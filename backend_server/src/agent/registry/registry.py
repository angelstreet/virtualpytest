"""
Agent Registry Service

Manages storage, retrieval, and versioning of agent definitions.
Uses sync Supabase client for database operations.
"""

from typing import List, Optional, Dict, Any

from agent.registry.config_schema import AgentDefinition
from agent.registry.validator import validate_agent_dict, AgentValidationError
from shared.src.lib.database import agent_registry_db


class AgentRegistry:
    """
    Agent Registry Service
    
    Provides CRUD operations for agent definitions with versioning support.
    Uses sync database operations via shared DB layer.
    """
    
    def __init__(self):
        pass  # No async DB connection needed
    
    def register(
        self, 
        agent: AgentDefinition,
        team_id: str = 'default',
        created_by: Optional[str] = None
    ) -> str:
        """
        Register new agent or new version
        
        Args:
            agent: AgentDefinition to register
            team_id: Team namespace
            created_by: User ID who created this agent
            
        Returns:
            UUID of registered agent
            
        Raises:
            AgentValidationError: If agent configuration is invalid
        """
        # Register agent
        agent_id = agent_registry_db.register_agent(
            agent_id=agent.metadata.id,
            name=agent.metadata.name,
            version=agent.metadata.version,
            author=agent.metadata.author,
            description=agent.metadata.description,
            goal_type=agent.goal.type.value,
            goal_description=agent.goal.description,
            definition=agent.to_dict(),
            team_id=team_id,
            created_by=created_by,
            tags=agent.metadata.tags
        )
        
        if not agent_id:
            raise Exception(f"Failed to register agent {agent.metadata.id}")
        
        # Register event triggers
        if agent.triggers:
            triggers = [
                {
                    'type': t.type,
                    'priority': t.priority,
                    'filters': t.filters
                }
                for t in agent.triggers
            ]
            agent_registry_db.register_triggers(agent.metadata.id, triggers, team_id)
        
        print(f"[@registry] ✅ Registered: {agent.metadata.id} v{agent.metadata.version}")
        return str(agent_id)
    
    def get(
        self, 
        agent_id: str, 
        version: Optional[str] = None,
        team_id: str = 'default'
    ) -> Optional[AgentDefinition]:
        """
        Get agent by ID and version
        
        Args:
            agent_id: Agent identifier
            version: Version (if None, returns latest published version)
            team_id: Team namespace
            
        Returns:
            AgentDefinition or None if not found
        """
        definition = agent_registry_db.get_agent(agent_id, version, team_id)
        
        if definition:
            return AgentDefinition.from_dict(definition)
        return None
    
    def list_agents(
        self, 
        team_id: str = 'default',
        status: Optional[str] = None
    ) -> List[AgentDefinition]:
        """
        List all agents (latest versions)
        
        Args:
            team_id: Team namespace
            status: Filter by status (draft, published, deprecated)
            
        Returns:
            List of AgentDefinition objects
        """
        definitions = agent_registry_db.list_agents(team_id, status)
        return [AgentDefinition.from_dict(d) for d in definitions]
    
    def list_versions(
        self, 
        agent_id: str,
        team_id: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        List all versions of an agent
        
        Args:
            agent_id: Agent identifier
            team_id: Team namespace
            
        Returns:
            List of version info dictionaries
        """
        return agent_registry_db.list_agent_versions(agent_id, team_id)
    
    def get_agents_for_event(
        self, 
        event_type: str,
        team_id: str = 'default'
    ) -> List[AgentDefinition]:
        """
        Get all agents that should handle a specific event type
        
        Args:
            event_type: Event type (e.g., 'alert.blackscreen')
            team_id: Team namespace
            
        Returns:
            List of AgentDefinition objects
        """
        definitions = agent_registry_db.get_agents_for_event(event_type, team_id)
        return [AgentDefinition.from_dict(d) for d in definitions]
    
    def publish(
        self, 
        agent_id: str, 
        version: str,
        team_id: str = 'default'
    ) -> bool:
        """
        Publish an agent version (make it active)
        
        Args:
            agent_id: Agent identifier
            version: Version to publish
            team_id: Team namespace
            
        Returns:
            True if published, False if not found
        """
        return agent_registry_db.publish_agent(agent_id, version, team_id)
    
    def deprecate(
        self, 
        agent_id: str, 
        version: str,
        team_id: str = 'default'
    ) -> bool:
        """
        Deprecate an agent version
        
        Args:
            agent_id: Agent identifier
            version: Version to deprecate
            team_id: Team namespace
            
        Returns:
            True if deprecated, False if not found
        """
        return agent_registry_db.deprecate_agent(agent_id, version, team_id)
    
    def delete(
        self, 
        agent_id: str, 
        version: str,
        team_id: str = 'default'
    ) -> bool:
        """
        Delete an agent version
        
        Args:
            agent_id: Agent identifier
            version: Version to delete
            team_id: Team namespace
            
        Returns:
            True if deleted, False if not found
        """
        return agent_registry_db.delete_agent(agent_id, version, team_id)
    
    def search(
        self,
        query: str,
        team_id: str = 'default'
    ) -> List[AgentDefinition]:
        """
        Search agents by name, description, or tags
        
        Args:
            query: Search query string
            team_id: Team namespace
            
        Returns:
            List of matching AgentDefinition objects
        """
        definitions = agent_registry_db.search_agents(query, team_id)
        return [AgentDefinition.from_dict(d) for d in definitions]


# Global instance
_agent_registry: Optional[AgentRegistry] = None

def get_agent_registry() -> AgentRegistry:
    """Get or create global agent registry instance"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
