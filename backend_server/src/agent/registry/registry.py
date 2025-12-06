"""
Agent Registry Service

Manages storage, retrieval, and versioning of agent definitions.
Integrates with PostgreSQL for persistence.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import get_async_db
from agent.registry.config_schema import AgentDefinition
from agent.registry.validator import validate_agent_dict, AgentValidationError


class AgentRegistry:
    """
    Agent Registry Service
    
    Provides CRUD operations for agent definitions with versioning support.
    """
    
    def __init__(self):
        self.db = get_async_db()
    
    async def register(
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
        try:
            # Insert or update agent registry
            query = """
                INSERT INTO agent_registry (
                    agent_id, name, version, author, description,
                    goal_type, goal_description, definition, status,
                    team_id, created_by, tags
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (agent_id, version) 
                DO UPDATE SET 
                    definition = EXCLUDED.definition,
                    updated_at = NOW()
                RETURNING id
            """
            
            agent_id = await self.db.fetchval(
                query,
                agent.metadata.id,
                agent.metadata.name,
                agent.metadata.version,
                agent.metadata.author,
                agent.metadata.description,
                agent.goal.type.value,
                agent.goal.description,
                json.dumps(agent.to_dict()),
                'draft',  # New agents start as draft
                team_id,
                created_by,
                agent.metadata.tags
            )
            
            # Register event triggers
            await self._register_triggers(agent.metadata.id, agent.triggers, team_id)
            
            print(f"[@registry] ✅ Registered: {agent.metadata.id} v{agent.metadata.version}")
            
            return str(agent_id)
            
        except Exception as e:
            print(f"[@registry] ❌ Failed to register agent: {e}")
            raise
    
    async def get(
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
        if version:
            query = """
                SELECT definition FROM agent_registry
                WHERE agent_id = $1 AND version = $2 AND team_id = $3
            """
            result = await self.db.fetchval(query, agent_id, version, team_id)
        else:
            # Get latest published version
            query = """
                SELECT definition FROM agent_registry
                WHERE agent_id = $1 AND team_id = $2 AND status = 'published'
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = await self.db.fetchval(query, agent_id, team_id)
        
        if result:
            return AgentDefinition.from_dict(result)
        return None
    
    async def list_agents(
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
        if status:
            query = """
                SELECT DISTINCT ON (agent_id) definition
                FROM agent_registry
                WHERE team_id = $1 AND status = $2
                ORDER BY agent_id, created_at DESC
            """
            results = await self.db.fetch(query, team_id, status)
        else:
            query = """
                SELECT DISTINCT ON (agent_id) definition
                FROM agent_registry
                WHERE team_id = $1
                ORDER BY agent_id, created_at DESC
            """
            results = await self.db.fetch(query, team_id)
        
        return [AgentDefinition.from_dict(row['definition']) for row in results]
    
    async def list_versions(
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
        query = """
            SELECT version, status, created_at, updated_at, author
            FROM agent_registry
            WHERE agent_id = $1 AND team_id = $2
            ORDER BY created_at DESC
        """
        
        results = await self.db.fetch(query, agent_id, team_id)
        
        return [
            {
                'version': row['version'],
                'status': row['status'],
                'created_at': row['created_at'].isoformat(),
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                'author': row['author']
            }
            for row in results
        ]
    
    async def get_agents_for_event(
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
        # Use database function for efficient lookup
        query = "SELECT * FROM get_agents_for_event($1, $2)"
        results = await self.db.fetch(query, event_type, team_id)
        
        return [AgentDefinition.from_dict(row['definition']) for row in results]
    
    async def publish(
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
        query = """
            UPDATE agent_registry
            SET status = 'published', updated_at = NOW()
            WHERE agent_id = $1 AND version = $2 AND team_id = $3
            RETURNING id
        """
        
        result = await self.db.fetchval(query, agent_id, version, team_id)
        
        if result:
            print(f"[@registry] 📢 Published: {agent_id} v{version}")
            return True
        
        return False
    
    async def deprecate(
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
        query = """
            UPDATE agent_registry
            SET status = 'deprecated', updated_at = NOW()
            WHERE agent_id = $1 AND version = $2 AND team_id = $3
            RETURNING id
        """
        
        result = await self.db.fetchval(query, agent_id, version, team_id)
        
        if result:
            print(f"[@registry] 🗑️ Deprecated: {agent_id} v{version}")
            return True
        
        return False
    
    async def delete(
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
        query = """
            DELETE FROM agent_registry
            WHERE agent_id = $1 AND version = $2 AND team_id = $3
            RETURNING id
        """
        
        result = await self.db.fetchval(query, agent_id, version, team_id)
        
        if result:
            print(f"[@registry] 🗑️ Deleted: {agent_id} v{version}")
            return True
        
        return False
    
    async def _register_triggers(
        self,
        agent_id: str,
        triggers: List,
        team_id: str
    ):
        """Register event triggers for agent"""
        # Delete existing triggers
        delete_query = """
            DELETE FROM agent_event_triggers
            WHERE agent_id = $1 AND team_id = $2
        """
        await self.db.execute(delete_query, agent_id, team_id)
        
        # Insert new triggers
        if triggers:
            insert_query = """
                INSERT INTO agent_event_triggers (
                    agent_id, event_type, priority, filters, team_id
                )
                VALUES ($1, $2, $3, $4, $5)
            """
            
            values = [
                (
                    agent_id,
                    trigger.type,
                    trigger.priority,
                    json.dumps(trigger.filters) if trigger.filters else '{}',
                    team_id
                )
                for trigger in triggers
            ]
            
            await self.db.executemany(insert_query, values)
    
    async def search(
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
        search_query = """
            SELECT DISTINCT ON (agent_id) definition
            FROM agent_registry
            WHERE team_id = $1
            AND (
                name ILIKE $2
                OR description ILIKE $2
                OR $3 = ANY(tags)
            )
            ORDER BY agent_id, created_at DESC
        """
        
        search_pattern = f"%{query}%"
        results = await self.db.fetch(search_query, team_id, search_pattern, query.lower())
        
        return [AgentDefinition.from_dict(row['definition']) for row in results]


# Global instance
_agent_registry: Optional[AgentRegistry] = None

def get_agent_registry() -> AgentRegistry:
    """Get or create global agent registry instance"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry

