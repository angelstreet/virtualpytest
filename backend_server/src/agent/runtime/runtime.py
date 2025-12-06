"""
Agent Runtime Manager

Manages agent instance lifecycle, event subscriptions, and task execution.
Integrates with Event Bus, Resource Lock Manager, and Agent Registry.
"""

import asyncio
import json
from typing import Dict, Optional, List
from datetime import datetime

from database import get_async_db
from events import EventBus, Event, EventPriority, get_event_bus
from resources import ResourceLockManager, get_lock_manager
from agent.registry import AgentRegistry, get_agent_registry, AgentDefinition
from agent.runtime.state import AgentState, AgentInstanceState


class AgentRuntime:
    """
    Agent Runtime Manager
    
    Manages running agent instances, event subscriptions, and task execution.
    """
    
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        lock_manager: Optional[ResourceLockManager] = None,
        registry: Optional[AgentRegistry] = None
    ):
        """
        Initialize Agent Runtime
        
        Args:
            event_bus: Event bus for subscriptions (optional)
            lock_manager: Resource lock manager (optional)
            registry: Agent registry (optional)
        """
        self.event_bus = event_bus or get_event_bus()
        self.lock_manager = lock_manager or get_lock_manager()
        self.registry = registry or get_agent_registry()
        self.db = get_async_db()
        
        # In-memory instance tracking
        self.instances: Dict[str, AgentInstanceState] = {}
        
        # Task tracking
        self.tasks: Dict[str, asyncio.Task] = {}
        
        self._running = False
    
    async def start(self):
        """Start runtime (connect services)"""
        if self._running:
            return
        
        # Ensure event bus is connected
        await self.event_bus.connect()
        await self.event_bus.start()
        
        # Start lock manager cleanup
        await self.lock_manager.start()
        
        self._running = True
        print("[@runtime] ✅ Agent Runtime started")
    
    async def stop(self):
        """Stop runtime and all running instances"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop all running instances
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            await self.stop_agent(instance_id)
        
        # Stop services
        await self.lock_manager.stop()
        await self.event_bus.disconnect()
        
        print("[@runtime] Agent Runtime stopped")
    
    async def start_agent(
        self,
        agent_id: str,
        version: Optional[str] = None,
        team_id: str = 'default'
    ) -> str:
        """
        Start an agent instance
        
        Args:
            agent_id: Agent identifier
            version: Version (if None, uses latest published)
            team_id: Team namespace
            
        Returns:
            Instance ID
        """
        # Get agent definition
        agent_def = await self.registry.get(agent_id, version, team_id)
        
        if not agent_def:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Generate instance ID
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        instance_id = f"{agent_id}_{timestamp_ms}"
        
        # Create instance state
        instance_state = AgentInstanceState(
            instance_id=instance_id,
            agent_id=agent_id,
            version=agent_def.metadata.version,
            state=AgentState.IDLE,
            team_id=team_id
        )
        
        self.instances[instance_id] = instance_state
        
        # Record in database
        await self._record_instance_start(instance_state)
        
        # Subscribe to events
        await self._subscribe_to_events(instance_id, agent_def)
        
        # Publish event
        await self.event_bus.publish(Event(
            type="agent.started",
            payload={
                "instance_id": instance_id,
                "agent_id": agent_id,
                "version": agent_def.metadata.version
            },
            priority=EventPriority.NORMAL,
            team_id=team_id
        ))
        
        print(f"[@runtime] 🚀 Started: {instance_id}")
        
        return instance_id
    
    async def stop_agent(self, instance_id: str) -> bool:
        """
        Stop an agent instance
        
        Args:
            instance_id: Instance to stop
            
        Returns:
            True if stopped, False if not found
        """
        if instance_id not in self.instances:
            return False
        
        instance = self.instances[instance_id]
        
        # Cancel running task if any
        if instance.task_id and instance.task_id in self.tasks:
            self.tasks[instance.task_id].cancel()
            try:
                await self.tasks[instance.task_id]
            except asyncio.CancelledError:
                pass
        
        # Update state
        instance.update_state(AgentState.STOPPED)
        
        # Record in database
        await self._record_instance_stop(instance_id)
        
        # Remove from tracking
        del self.instances[instance_id]
        
        # Publish event
        await self.event_bus.publish(Event(
            type="agent.stopped",
            payload={"instance_id": instance_id},
            priority=EventPriority.NORMAL,
            team_id=instance.team_id
        ))
        
        print(f"[@runtime] 🛑 Stopped: {instance_id}")
        
        return True
    
    async def handle_event(self, instance_id: str, event: Event):
        """
        Handle event for agent instance
        
        Args:
            instance_id: Instance handling the event
            event: Event to handle
        """
        instance = self.instances.get(instance_id)
        
        if not instance:
            print(f"[@runtime] ⚠️ Instance {instance_id} not found")
            return
        
        # Check if agent is available
        if instance.state == AgentState.RUNNING:
            # Agent busy - could queue or skip
            print(f"[@runtime] ⏳ Instance {instance_id} busy, queuing event {event.id}")
            # TODO: Implement event queuing per instance
            return
        
        # Update state to running
        instance.update_state(
            AgentState.RUNNING,
            task=f"Handling {event.type}",
            task_id=event.id
        )
        
        # Create task
        task = asyncio.create_task(
            self._execute_agent_task(instance_id, event)
        )
        self.tasks[event.id] = task
        
        # Update database
        await self._update_instance_state(instance)
    
    async def _execute_agent_task(self, instance_id: str, event: Event):
        """
        Execute agent task (placeholder for actual agent logic)
        
        Args:
            instance_id: Instance executing the task
            event: Event that triggered the task
        """
        instance = self.instances[instance_id]
        started_at = datetime.utcnow()
        
        try:
            # Publish task started event
            await self.event_bus.publish(Event(
                type="agent.task.started",
                payload={
                    "instance_id": instance_id,
                    "task_id": event.id,
                    "event_type": event.type
                },
                priority=EventPriority.NORMAL,
                team_id=instance.team_id
            ))
            
            # TODO: This is where we would integrate with actual agent execution
            # For now, just simulate work
            await asyncio.sleep(1)
            
            print(f"[@runtime] ✅ Task completed: {instance_id} - {event.type}")
            
            # Update state to idle
            instance.update_state(AgentState.IDLE)
            
            # Record execution history
            await self._record_execution_history(
                instance,
                event,
                started_at,
                datetime.utcnow(),
                "success"
            )
            
            # Publish completion event
            await self.event_bus.publish(Event(
                type="agent.task.completed",
                payload={
                    "instance_id": instance_id,
                    "task_id": event.id,
                    "duration_seconds": (datetime.utcnow() - started_at).total_seconds()
                },
                priority=EventPriority.NORMAL,
                team_id=instance.team_id
            ))
            
        except asyncio.CancelledError:
            print(f"[@runtime] ⚠️ Task cancelled: {instance_id}")
            instance.update_state(AgentState.IDLE)
            raise
            
        except Exception as e:
            print(f"[@runtime] ❌ Task failed: {instance_id} - {str(e)}")
            instance.set_error(str(e))
            
            # Record failure
            await self._record_execution_history(
                instance,
                event,
                started_at,
                datetime.utcnow(),
                "failed",
                error_message=str(e)
            )
            
            # Publish failure event
            await self.event_bus.publish(Event(
                type="agent.task.failed",
                payload={
                    "instance_id": instance_id,
                    "task_id": event.id,
                    "error": str(e)
                },
                priority=EventPriority.HIGH,
                team_id=instance.team_id
            ))
        
        finally:
            # Clean up task
            if event.id in self.tasks:
                del self.tasks[event.id]
            
            # Update database
            await self._update_instance_state(instance)
    
    async def _subscribe_to_events(self, instance_id: str, agent_def: AgentDefinition):
        """Subscribe instance to its configured events"""
        for trigger in agent_def.triggers:
            # Create handler for this instance
            async def handler(event: Event):
                await self.handle_event(instance_id, event)
            
            await self.event_bus.subscribe(trigger.type, handler)
            
            print(f"[@runtime] 📥 {instance_id} subscribed to {trigger.type}")
    
    def get_status(self, instance_id: str) -> Optional[Dict]:
        """
        Get status of agent instance
        
        Args:
            instance_id: Instance to query
            
        Returns:
            Status dictionary or None if not found
        """
        instance = self.instances.get(instance_id)
        
        if not instance:
            return None
        
        return instance.to_dict()
    
    def list_instances(self, team_id: Optional[str] = None) -> List[Dict]:
        """
        List all running instances
        
        Args:
            team_id: Filter by team (optional)
            
        Returns:
            List of instance status dictionaries
        """
        instances = self.instances.values()
        
        if team_id:
            instances = [i for i in instances if i.team_id == team_id]
        
        return [i.to_dict() for i in instances]
    
    async def _record_instance_start(self, instance: AgentInstanceState):
        """Record instance start in database"""
        query = """
            INSERT INTO agent_instances (
                instance_id, agent_id, version, state,
                started_at, team_id
            )
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        await self.db.execute(
            query,
            instance.instance_id,
            instance.agent_id,
            instance.version,
            instance.state.value,
            instance.started_at,
            instance.team_id
        )
    
    async def _record_instance_stop(self, instance_id: str):
        """Record instance stop in database"""
        query = """
            UPDATE agent_instances
            SET stopped_at = NOW(), state = 'stopped'
            WHERE instance_id = $1
        """
        
        await self.db.execute(query, instance_id)
    
    async def _update_instance_state(self, instance: AgentInstanceState):
        """Update instance state in database"""
        query = """
            UPDATE agent_instances
            SET state = $1, current_task = $2, task_id = $3
            WHERE instance_id = $4
        """
        
        await self.db.execute(
            query,
            instance.state.value,
            instance.current_task,
            instance.task_id,
            instance.instance_id
        )
    
    async def _record_execution_history(
        self,
        instance: AgentInstanceState,
        event: Event,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        error_message: Optional[str] = None
    ):
        """Record task execution in history"""
        duration = (completed_at - started_at).total_seconds()
        
        query = """
            INSERT INTO agent_execution_history (
                instance_id, agent_id, version, task_id,
                event_type, event_id, started_at, completed_at,
                duration_seconds, status, error_message, team_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        
        await self.db.execute(
            query,
            instance.instance_id,
            instance.agent_id,
            instance.version,
            event.id,
            event.type,
            event.id,
            started_at,
            completed_at,
            duration,
            status,
            error_message,
            instance.team_id
        )


# Global instance
_agent_runtime: Optional[AgentRuntime] = None

def get_agent_runtime() -> AgentRuntime:
    """Get or create global agent runtime instance"""
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    return _agent_runtime

