"""
Event Router

Routes events to appropriate agents based on event type and agent triggers.
Integrates with Agent Registry to find matching agents.
"""

from typing import List, Dict, Any
from datetime import datetime

from database import get_async_db
from agent.registry import AgentRegistry, get_agent_registry
from events.event_bus import EventBus, Event, EventPriority, get_event_bus


class EventRouter:
    """
    Event Router
    
    Routes incoming events to agents that should handle them.
    Logs routing decisions and unhandled events.
    """
    
    def __init__(
        self,
        event_bus: EventBus = None,
        registry: AgentRegistry = None
    ):
        """
        Initialize Event Router
        
        Args:
            event_bus: Event bus for publishing (optional)
            registry: Agent registry for lookup (optional)
        """
        self.event_bus = event_bus or get_event_bus()
        self.registry = registry or get_agent_registry()
        self.db = get_async_db()
    
    async def route_event(self, event: Event) -> bool:
        """
        Route event to appropriate agents
        
        Args:
            event: Event to route
            
        Returns:
            True if routed to at least one agent, False if unhandled
        """
        # Log event first
        await self._log_event(event)
        
        # Get agents that should handle this event
        agents = await self.registry.get_agents_for_event(
            event.type,
            event.team_id
        )
        
        if not agents:
            # No agents registered for this event
            await self._log_unhandled(event)
            
            # Publish unhandled event notification
            await self.event_bus.publish(Event(
                type="event.unhandled",
                payload={
                    "event_type": event.type,
                    "event_id": event.id
                },
                priority=EventPriority.LOW,
                team_id=event.team_id
            ))
            
            print(f"[@router] ⚠️ Unhandled: {event.type} (no agents registered)")
            return False
        
        # Publish event for registered agents
        await self.event_bus.publish(event)
        
        print(f"[@router] ✅ Routed: {event.type} → {len(agents)} agent(s)")
        
        return True
    
    async def get_routing_stats(self, team_id: str = 'default') -> Dict[str, Any]:
        """
        Get event routing statistics
        
        Args:
            team_id: Team namespace
            
        Returns:
            Statistics dictionary
        """
        query = """
            SELECT 
                COUNT(*) as total_events,
                COUNT(processed_by) as processed_events,
                COUNT(*) FILTER (WHERE processed_by IS NULL) as unprocessed_events,
                COUNT(DISTINCT event_type) as unique_event_types,
                AVG(EXTRACT(EPOCH FROM (processed_at - timestamp))) as avg_processing_time_seconds
            FROM event_log
            WHERE team_id = $1
            AND timestamp > NOW() - INTERVAL '24 hours'
        """
        
        result = await self.db.fetchrow(query, team_id)
        
        return {
            'total_events': result['total_events'],
            'processed_events': result['processed_events'],
            'unprocessed_events': result['unprocessed_events'],
            'unique_event_types': result['unique_event_types'],
            'avg_processing_time_seconds': float(result['avg_processing_time_seconds'] or 0)
        }
    
    async def get_event_types(self, team_id: str = 'default') -> List[str]:
        """
        Get list of all event types seen
        
        Args:
            team_id: Team namespace
            
        Returns:
            List of event type strings
        """
        query = """
            SELECT DISTINCT event_type
            FROM event_log
            WHERE team_id = $1
            ORDER BY event_type
        """
        
        results = await self.db.fetch(query, team_id)
        return [row['event_type'] for row in results]
    
    async def _log_event(self, event: Event):
        """Log event routing (already logged by event_bus, this is supplementary)"""
        # Event is already logged by event_bus.publish()
        # This method can be used for additional routing-specific logging if needed
        pass
    
    async def _log_unhandled(self, event: Event):
        """Log unhandled event"""
        # Update event_log to mark as unhandled (could add a flag)
        # For now, unhandled events just won't have a processed_by value
        print(f"[@router] 📝 Logged unhandled event: {event.type}")


# Global instance
_event_router = None

def get_event_router() -> EventRouter:
    """Get or create global event router instance"""
    global _event_router
    if _event_router is None:
        _event_router = EventRouter()
    return _event_router

