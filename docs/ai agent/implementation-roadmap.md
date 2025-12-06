# Technical Implementation Roadmap
## Autonomous Multi-Agent Platform - Step-by-Step

---

## Phase 1: Core Infrastructure (CRITICAL - DO FIRST)
**Goal:** Enable event-driven architecture and multi-agent foundation

### Step 1.1: Event Bus Implementation
**Priority:** CRITICAL - Foundation for everything else
**Estimated Effort:** 3-5 days
**Dependencies:** None

**Technical Implementation:**

```python
# backend_server/src/events/event_bus.py
from typing import Callable, Dict, List, Any
from enum import Enum
import asyncio
from datetime import datetime
import redis.asyncio as redis

class EventPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class Event:
    def __init__(self, type: str, payload: Dict[str, Any], priority: EventPriority):
        self.type = type
        self.payload = payload
        self.priority = priority
        self.timestamp = datetime.utcnow()
        self.id = f"evt_{int(self.timestamp.timestamp() * 1000)}"

class EventBus:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
    
    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        await self.redis.publish(
            event.type,
            json.dumps({
                'id': event.id,
                'type': event.type,
                'payload': event.payload,
                'priority': event.priority.value,
                'timestamp': event.timestamp.isoformat()
            })
        )
    
    async def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def start(self):
        """Start listening for events"""
        self.running = True
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self.subscribers.keys())
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                event_type = event_data['type']
                
                # Call all subscribers for this event type
                for callback in self.subscribers.get(event_type, []):
                    await callback(event_data)
```

**Database Schema:**

```sql
-- migrations/add_event_log.sql
CREATE TABLE event_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    priority INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_by VARCHAR(255),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_event_log_type ON event_log(event_type);
CREATE INDEX idx_event_log_priority ON event_log(priority);
CREATE INDEX idx_event_log_timestamp ON event_log(timestamp);
```

**Tests:**

```python
# tests/test_event_bus.py
import pytest
from backend_server.src.events.event_bus import EventBus, Event, EventPriority

@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus("redis://localhost:6379")
    received = []
    
    async def handler(event_data):
        received.append(event_data)
    
    await bus.subscribe("test.event", handler)
    await bus.start()
    
    event = Event("test.event", {"data": "test"}, EventPriority.NORMAL)
    await bus.publish(event)
    
    await asyncio.sleep(0.1)
    assert len(received) == 1
    assert received[0]['type'] == "test.event"
```

**Deliverables:**
- ✅ Event Bus class with pub/sub
- ✅ Event priority system
- ✅ Database logging of all events
- ✅ Tests for basic pub/sub

---

### Step 1.2: Resource Lock Manager
**Priority:** CRITICAL - Required for parallel execution
**Estimated Effort:** 2-3 days
**Dependencies:** Event Bus (for lock notifications)

**Technical Implementation:**

```python
# backend_server/src/resources/lock_manager.py
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from enum import Enum

class LockStatus(Enum):
    AVAILABLE = "available"
    LOCKED = "locked"
    QUEUED = "queued"

@dataclass
class ResourceLock:
    resource_id: str
    owner_id: str
    acquired_at: datetime
    expires_at: datetime
    priority: int

class ResourceLockManager:
    def __init__(self, event_bus):
        self.locks: Dict[str, ResourceLock] = {}
        self.queues: Dict[str, List[Dict]] = {}
        self.event_bus = event_bus
    
    async def acquire(self, resource_id: str, owner_id: str, 
                     timeout: int = 3600, priority: int = 3) -> bool:
        """
        Try to acquire lock on resource.
        Returns True if acquired, False if needs to queue.
        """
        if resource_id not in self.locks:
            # Resource available - acquire immediately
            self.locks[resource_id] = ResourceLock(
                resource_id=resource_id,
                owner_id=owner_id,
                acquired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=timeout),
                priority=priority
            )
            
            await self.event_bus.publish(Event(
                "resource.acquired",
                {"resource_id": resource_id, "owner_id": owner_id},
                EventPriority.NORMAL
            ))
            
            return True
        
        # Check if current lock expired
        if datetime.utcnow() > self.locks[resource_id].expires_at:
            await self.release(resource_id, self.locks[resource_id].owner_id)
            return await self.acquire(resource_id, owner_id, timeout, priority)
        
        # Resource locked - add to queue
        if resource_id not in self.queues:
            self.queues[resource_id] = []
        
        self.queues[resource_id].append({
            'owner_id': owner_id,
            'priority': priority,
            'queued_at': datetime.utcnow(),
            'timeout': timeout
        })
        
        # Sort queue by priority (lower number = higher priority)
        self.queues[resource_id].sort(key=lambda x: x['priority'])
        
        await self.event_bus.publish(Event(
            "resource.queued",
            {
                "resource_id": resource_id,
                "owner_id": owner_id,
                "position": len(self.queues[resource_id])
            },
            EventPriority.NORMAL
        ))
        
        return False
    
    async def release(self, resource_id: str, owner_id: str):
        """Release lock and process queue"""
        if resource_id not in self.locks:
            return
        
        if self.locks[resource_id].owner_id != owner_id:
            raise ValueError(f"Cannot release lock owned by {self.locks[resource_id].owner_id}")
        
        del self.locks[resource_id]
        
        await self.event_bus.publish(Event(
            "resource.released",
            {"resource_id": resource_id, "owner_id": owner_id},
            EventPriority.NORMAL
        ))
        
        # Process queue
        if resource_id in self.queues and self.queues[resource_id]:
            next_in_queue = self.queues[resource_id].pop(0)
            await self.acquire(
                resource_id,
                next_in_queue['owner_id'],
                next_in_queue['timeout'],
                next_in_queue['priority']
            )
    
    def is_available(self, resource_id: str) -> bool:
        """Check if resource is available"""
        if resource_id not in self.locks:
            return True
        
        return datetime.utcnow() > self.locks[resource_id].expires_at
    
    def get_status(self, resource_id: str) -> Dict:
        """Get current status of resource"""
        if resource_id not in self.locks:
            return {
                'status': LockStatus.AVAILABLE,
                'owner': None,
                'queue_length': len(self.queues.get(resource_id, []))
            }
        
        return {
            'status': LockStatus.LOCKED,
            'owner': self.locks[resource_id].owner_id,
            'acquired_at': self.locks[resource_id].acquired_at.isoformat(),
            'expires_at': self.locks[resource_id].expires_at.isoformat(),
            'queue_length': len(self.queues.get(resource_id, []))
        }
```

**Database Schema:**

```sql
-- migrations/add_resource_locks.sql
CREATE TABLE resource_locks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL, -- 'device', 'tree', 'userinterface'
    owner_id VARCHAR(255) NOT NULL,
    owner_type VARCHAR(50) NOT NULL, -- 'agent', 'user', 'system'
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    priority INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_resource_locks_resource ON resource_locks(resource_id);
CREATE INDEX idx_resource_locks_owner ON resource_locks(owner_id);
CREATE INDEX idx_resource_locks_expires ON resource_locks(expires_at);
```

**Deliverables:**
- ✅ Resource lock acquisition/release
- ✅ Priority-based queuing
- ✅ Lock expiration handling
- ✅ Status checking
- ✅ Integration with Event Bus

---

### Step 1.3: Agent Configuration Schema
**Priority:** CRITICAL - Defines agent structure
**Estimated Effort:** 2 days
**Dependencies:** None

**Technical Implementation:**

```python
# backend_server/src/agent/config_schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class AgentGoalType(Enum):
    CONTINUOUS = "continuous"
    ON_DEMAND = "on-demand"

class EventTrigger(BaseModel):
    type: str  # e.g., "alert.blackscreen", "build.deployed"
    priority: str  # "critical", "high", "normal", "low"
    filters: Optional[Dict[str, Any]] = None

class SubAgentReference(BaseModel):
    id: str
    version: str  # e.g., ">=1.0.0", "2.1.0"
    delegate_for: List[str]  # Tasks this subagent handles

class AgentPermissions(BaseModel):
    devices: List[str]  # ["read", "take_control"]
    database: List[str]  # ["read", "write.testcases"]
    external: List[str]  # ["jira", "slack"]

class AgentConfig(BaseModel):
    max_parallel_tasks: int = 3
    approval_required_for: List[str] = []
    auto_retry: bool = True
    feedback_collection: bool = True
    timeout_seconds: int = 3600

class AgentMetadata(BaseModel):
    id: str
    name: str
    version: str
    author: str
    description: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AgentGoal(BaseModel):
    type: AgentGoalType
    description: str

class AgentDefinition(BaseModel):
    metadata: AgentMetadata
    goal: AgentGoal
    triggers: List[EventTrigger]
    event_pools: List[str]
    subagents: List[SubAgentReference]
    skills: List[str]
    permissions: AgentPermissions
    config: AgentConfig
    
    class Config:
        use_enum_values = True
```

**Database Schema:**

```sql
-- migrations/add_agent_registry.sql
CREATE TABLE agent_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50) NOT NULL,
    goal_description TEXT NOT NULL,
    definition JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, version)
);

CREATE INDEX idx_agent_registry_agent_id ON agent_registry(agent_id);
CREATE INDEX idx_agent_registry_version ON agent_registry(version);
CREATE INDEX idx_agent_registry_status ON agent_registry(status);

CREATE TABLE agent_event_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    filters JSONB,
    FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
);

CREATE INDEX idx_agent_triggers_event ON agent_event_triggers(event_type);
```

**YAML Schema Validator:**

```python
# backend_server/src/agent/validator.py
import yaml
from typing import Dict, Any
from .config_schema import AgentDefinition

def validate_agent_yaml(yaml_content: str) -> AgentDefinition:
    """Validate agent YAML and return AgentDefinition"""
    try:
        data = yaml.safe_load(yaml_content)
        return AgentDefinition(**data)
    except Exception as e:
        raise ValueError(f"Invalid agent configuration: {str(e)}")

def export_agent(agent: AgentDefinition) -> str:
    """Export agent to YAML"""
    return yaml.dump(agent.dict(), default_flow_style=False)
```

**Deliverables:**
- ✅ Pydantic models for agent config
- ✅ Database schema for agent registry
- ✅ YAML import/export functions
- ✅ Validation logic

---

### Step 1.4: Agent Registry Service
**Priority:** CRITICAL - Store and retrieve agents
**Estimated Effort:** 2-3 days
**Dependencies:** Agent Config Schema

**Technical Implementation:**

```python
# backend_server/src/agent/registry.py
from typing import List, Optional
from .config_schema import AgentDefinition
from ..database import get_db_session

class AgentRegistry:
    def __init__(self, db_session):
        self.db = db_session
    
    async def register(self, agent: AgentDefinition) -> str:
        """Register new agent or new version"""
        query = """
        INSERT INTO agent_registry (
            agent_id, name, version, author, description,
            goal_type, goal_description, definition, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (agent_id, version) 
        DO UPDATE SET 
            definition = EXCLUDED.definition,
            updated_at = NOW()
        RETURNING id
        """
        
        result = await self.db.fetchval(
            query,
            agent.metadata.id,
            agent.metadata.name,
            agent.metadata.version,
            agent.metadata.author,
            agent.metadata.description,
            agent.goal.type.value,
            agent.goal.description,
            agent.dict(),
            'draft'
        )
        
        # Register event triggers
        for trigger in agent.triggers:
            await self.register_trigger(agent.metadata.id, trigger)
        
        return str(result)
    
    async def register_trigger(self, agent_id: str, trigger):
        """Register event trigger for agent"""
        query = """
        INSERT INTO agent_event_triggers (agent_id, event_type, priority, filters)
        VALUES ($1, $2, $3, $4)
        """
        await self.db.execute(
            query,
            agent_id,
            trigger.type,
            trigger.priority,
            trigger.filters or {}
        )
    
    async def get(self, agent_id: str, version: Optional[str] = None) -> Optional[AgentDefinition]:
        """Get agent by ID and version (latest if not specified)"""
        if version:
            query = """
            SELECT definition FROM agent_registry
            WHERE agent_id = $1 AND version = $2
            """
            result = await self.db.fetchval(query, agent_id, version)
        else:
            query = """
            SELECT definition FROM agent_registry
            WHERE agent_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """
            result = await self.db.fetchval(query, agent_id)
        
        if result:
            return AgentDefinition(**result)
        return None
    
    async def list_agents(self) -> List[AgentDefinition]:
        """List all agents (latest versions)"""
        query = """
        SELECT DISTINCT ON (agent_id) definition
        FROM agent_registry
        ORDER BY agent_id, created_at DESC
        """
        results = await self.db.fetch(query)
        return [AgentDefinition(**r['definition']) for r in results]
    
    async def get_agents_for_event(self, event_type: str) -> List[AgentDefinition]:
        """Get all agents that should handle this event type"""
        query = """
        SELECT DISTINCT ar.definition
        FROM agent_registry ar
        JOIN agent_event_triggers aet ON ar.agent_id = aet.agent_id
        WHERE aet.event_type = $1
        AND ar.status = 'published'
        """
        results = await self.db.fetch(query, event_type)
        return [AgentDefinition(**r['definition']) for r in results]
```

**API Endpoints:**

```python
# backend_server/src/routes/agent_routes.py
from fastapi import APIRouter, Depends, HTTPException
from ..agent.registry import AgentRegistry
from ..agent.config_schema import AgentDefinition

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.post("/register")
async def register_agent(agent: AgentDefinition, registry: AgentRegistry = Depends()):
    """Register new agent or version"""
    agent_id = await registry.register(agent)
    return {"agent_id": agent_id, "message": "Agent registered successfully"}

@router.get("/{agent_id}")
async def get_agent(agent_id: str, version: str = None, registry: AgentRegistry = Depends()):
    """Get agent by ID and optional version"""
    agent = await registry.get(agent_id, version)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/")
async def list_agents(registry: AgentRegistry = Depends()):
    """List all registered agents"""
    agents = await registry.list_agents()
    return {"agents": agents, "count": len(agents)}
```

**Deliverables:**
- ✅ Agent registration service
- ✅ Version management
- ✅ Event trigger registration
- ✅ REST API endpoints
- ✅ Query by event type

---

## Phase 2: Runtime & Execution (CRITICAL)
**Goal:** Enable multi-agent parallel execution

### Step 2.1: Agent Runtime Manager
**Priority:** CRITICAL
**Estimated Effort:** 4-5 days
**Dependencies:** Event Bus, Resource Lock Manager, Agent Registry

**Technical Implementation:**

```python
# backend_server/src/agent/runtime.py
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio

class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class AgentInstance:
    agent_id: str
    version: str
    state: AgentState
    current_task: Optional[str] = None
    started_at: Optional[datetime] = None
    task_id: Optional[str] = None

class AgentRuntime:
    def __init__(self, event_bus, lock_manager, registry):
        self.event_bus = event_bus
        self.lock_manager = lock_manager
        self.registry = registry
        self.instances: Dict[str, AgentInstance] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def start_agent(self, agent_id: str, version: Optional[str] = None) -> str:
        """Start an agent instance"""
        agent_def = await self.registry.get(agent_id, version)
        if not agent_def:
            raise ValueError(f"Agent {agent_id} not found")
        
        instance_id = f"{agent_id}_{int(datetime.utcnow().timestamp())}"
        
        self.instances[instance_id] = AgentInstance(
            agent_id=agent_id,
            version=agent_def.metadata.version,
            state=AgentState.IDLE,
            started_at=datetime.utcnow()
        )
        
        # Subscribe to events
        for trigger in agent_def.triggers:
            await self.event_bus.subscribe(
                trigger.type,
                lambda event: self.handle_event(instance_id, event)
            )
        
        await self.event_bus.publish(Event(
            "agent.started",
            {"instance_id": instance_id, "agent_id": agent_id},
            EventPriority.NORMAL
        ))
        
        return instance_id
    
    async def handle_event(self, instance_id: str, event_data: Dict):
        """Handle event for agent instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return
        
        # Check if agent is available or already running
        if instance.state == AgentState.RUNNING:
            # Queue the event for later processing
            return
        
        # Update state
        instance.state = AgentState.RUNNING
        instance.current_task = event_data['type']
        instance.task_id = event_data['id']
        
        # Create task
        task = asyncio.create_task(
            self.execute_agent_task(instance_id, event_data)
        )
        self.tasks[instance.task_id] = task
    
    async def execute_agent_task(self, instance_id: str, event_data: Dict):
        """Execute agent task (this will call the actual agent logic)"""
        try:
            instance = self.instances[instance_id]
            agent_def = await self.registry.get(instance.agent_id, instance.version)
            
            # Here we would integrate with actual agent execution
            # For now, placeholder for agent logic
            await self.event_bus.publish(Event(
                "agent.task.started",
                {
                    "instance_id": instance_id,
                    "task_id": instance.task_id,
                    "event_type": event_data['type']
                },
                EventPriority.NORMAL
            ))
            
            # TODO: Call actual agent execution logic
            
            instance.state = AgentState.IDLE
            instance.current_task = None
            
            await self.event_bus.publish(Event(
                "agent.task.completed",
                {"instance_id": instance_id, "task_id": instance.task_id},
                EventPriority.NORMAL
            ))
            
        except Exception as e:
            instance.state = AgentState.ERROR
            await self.event_bus.publish(Event(
                "agent.task.failed",
                {
                    "instance_id": instance_id,
                    "task_id": instance.task_id,
                    "error": str(e)
                },
                EventPriority.HIGH
            ))
    
    async def stop_agent(self, instance_id: str):
        """Stop agent instance"""
        if instance_id in self.instances:
            instance = self.instances[instance_id]
            
            # Cancel running task if any
            if instance.task_id and instance.task_id in self.tasks:
                self.tasks[instance.task_id].cancel()
            
            del self.instances[instance_id]
            
            await self.event_bus.publish(Event(
                "agent.stopped",
                {"instance_id": instance_id},
                EventPriority.NORMAL
            ))
    
    def get_status(self, instance_id: str) -> Dict:
        """Get status of agent instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return None
        
        return {
            'instance_id': instance_id,
            'agent_id': instance.agent_id,
            'version': instance.version,
            'state': instance.state.value,
            'current_task': instance.current_task,
            'started_at': instance.started_at.isoformat() if instance.started_at else None
        }
    
    def list_instances(self) -> List[Dict]:
        """List all running instances"""
        return [self.get_status(iid) for iid in self.instances.keys()]
```

**Deliverables:**
- ✅ Agent instance management
- ✅ Event subscription per agent
- ✅ Task execution framework
- ✅ State management
- ✅ Status reporting

---

### Step 2.2: Event Router
**Priority:** HIGH
**Estimated Effort:** 2 days
**Dependencies:** Event Bus, Agent Registry

**Technical Implementation:**

```python
# backend_server/src/events/router.py
from typing import Dict, List
from .event_bus import Event, EventPriority

class EventRouter:
    def __init__(self, event_bus, registry):
        self.event_bus = event_bus
        self.registry = registry
    
    async def route_event(self, event: Event):
        """Route event to appropriate agents"""
        # Log event
        await self.log_event(event)
        
        # Get agents that should handle this event
        agents = await self.registry.get_agents_for_event(event.type)
        
        if not agents:
            # No agents registered for this event
            await self.event_bus.publish(Event(
                "event.unhandled",
                {"event_type": event.type, "event_id": event.id},
                EventPriority.LOW
            ))
            return
        
        # Publish event for registered agents
        await self.event_bus.publish(event)
    
    async def log_event(self, event: Event):
        """Log event to database"""
        # Implementation to log to event_log table
        pass
```

**Deliverables:**
- ✅ Event routing logic
- ✅ Agent matching
- ✅ Event logging
- ✅ Unhandled event detection

---

## Phase 3: Minimal UI Integration (HIGH PRIORITY)
**Goal:** Make new system visible and controllable

### Step 3.1: Agent Status API
**Priority:** HIGH
**Estimated Effort:** 1-2 days
**Dependencies:** Agent Runtime

```python
# backend_server/src/routes/runtime_routes.py
from fastapi import APIRouter, WebSocket
from ..agent.runtime import AgentRuntime

router = APIRouter(prefix="/api/runtime", tags=["runtime"])

@router.get("/instances")
async def list_instances(runtime: AgentRuntime = Depends()):
    """List all running agent instances"""
    return {"instances": runtime.list_instances()}

@router.get("/instances/{instance_id}")
async def get_instance_status(instance_id: str, runtime: AgentRuntime = Depends()):
    """Get status of specific instance"""
    status = runtime.get_status(instance_id)
    if not status:
        raise HTTPException(status_code=404, detail="Instance not found")
    return status

@router.post("/instances/start")
async def start_agent_instance(agent_id: str, version: str = None, 
                               runtime: AgentRuntime = Depends()):
    """Start new agent instance"""
    instance_id = await runtime.start_agent(agent_id, version)
    return {"instance_id": instance_id, "message": "Agent started"}

@router.post("/instances/{instance_id}/stop")
async def stop_agent_instance(instance_id: str, runtime: AgentRuntime = Depends()):
    """Stop agent instance"""
    await runtime.stop_agent(instance_id)
    return {"message": "Agent stopped"}

@router.websocket("/instances/status")
async def instance_status_stream(websocket: WebSocket, runtime: AgentRuntime = Depends()):
    """Real-time status updates via WebSocket"""
    await websocket.accept()
    
    try:
        while True:
            status = runtime.list_instances()
            await websocket.send_json({"instances": status})
            await asyncio.sleep(1)
    except Exception:
        await websocket.close()
```

**Deliverables:**
- ✅ REST API for instance management
- ✅ WebSocket for real-time updates
- ✅ Start/stop endpoints

---

### Step 3.2: Frontend Agent Selector
**Priority:** HIGH
**Estimated Effort:** 2-3 days
**Dependencies:** Agent Status API

```typescript
// frontend/src/components/agent/AgentSelector.tsx
import React, { useState, useEffect } from 'react';
import { Select, Badge, Button } from '@/components/ui';

interface AgentInstance {
  instance_id: string;
  agent_id: string;
  version: string;
  state: 'idle' | 'running' | 'paused' | 'error';
  current_task: string | null;
}

export const AgentSelector: React.FC = () => {
  const [instances, setInstances] = useState<AgentInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);

  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket('ws://localhost:8000/api/runtime/instances/status');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setInstances(data.instances);
    };

    return () => ws.close();
  }, []);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'running': return 'green';
      case 'idle': return 'gray';
      case 'error': return 'red';
      case 'paused': return 'yellow';
      default: return 'gray';
    }
  };

  return (
    <div className="agent-selector">
      <div className="flex items-center gap-4 mb-4">
        <Select
          value={selectedInstance || ''}
          onChange={(e) => setSelectedInstance(e.target.value)}
        >
          <option value="">Select Agent</option>
          {instances.map((instance) => (
            <option key={instance.instance_id} value={instance.instance_id}>
              {instance.agent_id} v{instance.version}
            </option>
          ))}
        </Select>
        <Button variant="outline" size="sm">
          + Add Agent
        </Button>
      </div>

      <div className="space-y-2">
        {instances.map((instance) => (
          <div 
            key={instance.instance_id}
            className={`p-3 border rounded ${selectedInstance === instance.instance_id ? 'border-blue-500' : 'border-gray-200'}`}
            onClick={() => setSelectedInstance(instance.instance_id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge color={getStateColor(instance.state)}>
                  {instance.state.toUpperCase()}
                </Badge>
                <span className="font-medium">{instance.agent_id}</span>
                <span className="text-sm text-gray-500">v{instance.version}</span>
              </div>
            </div>
            {instance.current_task && (
              <div className="text-sm text-gray-600 mt-1">
                {instance.current_task}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

**Deliverables:**
- ✅ Agent selector dropdown
- ✅ Real-time status display
- ✅ Visual state indicators
- ✅ Instance management UI

---

## Phase 4: Basic Event Sources (MEDIUM PRIORITY)
**Goal:** Enable non-chat triggers

### Step 4.1: Alert System Integration
**Priority:** MEDIUM
**Estimated Effort:** 2 days
**Dependencies:** Event Bus

```python
# backend_server/src/events/sources/alert_source.py
from ..event_bus import EventBus, Event, EventPriority

class AlertEventSource:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def emit_blackscreen_alert(self, device_id: str):
        """Emit blackscreen alert event"""
        event = Event(
            type="alert.blackscreen",
            payload={
                "device_id": device_id,
                "severity": "critical"
            },
            priority=EventPriority.CRITICAL
        )
        await self.event_bus.publish(event)
    
    async def emit_device_offline(self, device_id: str, duration_seconds: int):
        """Emit device offline alert"""
        event = Event(
            type="alert.device_offline",
            payload={
                "device_id": device_id,
                "duration_seconds": duration_seconds,
                "severity": "high"
            },
            priority=EventPriority.HIGH
        )
        await self.event_bus.publish(event)
```

**API Endpoints:**

```python
# backend_server/src/routes/event_routes.py
from fastapi import APIRouter
from ..events.sources.alert_source import AlertEventSource

router = APIRouter(prefix="/api/events", tags=["events"])

@router.post("/alerts/blackscreen")
async def emit_blackscreen(device_id: str, source: AlertEventSource = Depends()):
    """Emit blackscreen alert"""
    await source.emit_blackscreen_alert(device_id)
    return {"message": "Alert published"}

@router.post("/alerts/device-offline")
async def emit_device_offline(device_id: str, duration: int, 
                              source: AlertEventSource = Depends()):
    """Emit device offline alert"""
    await source.emit_device_offline(device_id, duration)
    return {"message": "Alert published"}
```

**Deliverables:**
- ✅ Alert event sources
- ✅ API endpoints for alerts
- ✅ Priority classification

---

### Step 4.2: Scheduler Integration
**Priority:** MEDIUM
**Estimated Effort:** 2-3 days
**Dependencies:** Event Bus

```python
# backend_server/src/events/sources/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..event_bus import EventBus, Event, EventPriority

class SchedulerEventSource:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.scheduler = AsyncIOScheduler()
    
    def schedule_event(self, event_type: str, cron_expr: str, payload: dict):
        """Schedule recurring event"""
        async def emit_scheduled_event():
            event = Event(
                type=event_type,
                payload=payload,
                priority=EventPriority.NORMAL
            )
            await self.event_bus.publish(event)
        
        self.scheduler.add_job(
            emit_scheduled_event,
            CronTrigger.from_crontab(cron_expr),
            id=f"{event_type}_{cron_expr}"
        )
    
    def start(self):
        """Start scheduler"""
        self.scheduler.start()
    
    def stop(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
```

**Database Schema:**

```sql
-- migrations/add_scheduled_events.sql
CREATE TABLE scheduled_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE
);
```

**Deliverables:**
- ✅ Cron-based scheduler
- ✅ Database-driven schedules
- ✅ Enable/disable schedules

---

## Summary: Critical Path (First 4 Weeks)

**Week 1: Core Infrastructure**
1. Event Bus (3 days)
2. Resource Lock Manager (2 days)

**Week 2: Agent Foundation**
3. Agent Config Schema (2 days)
4. Agent Registry (3 days)

**Week 3: Runtime**
5. Agent Runtime Manager (4 days)
6. Event Router (1 day)

**Week 4: UI & Integration**
7. Agent Status API (1 day)
8. Frontend Agent Selector (2 days)
9. Alert System Integration (2 days)

**After Week 4:** You have a working multi-agent platform that can:
- ✅ Register and version agents
- ✅ Handle events from multiple sources
- ✅ Run multiple agents in parallel
- ✅ Manage device resources
- ✅ Display agent status in UI
- ✅ Respond to alerts automatically

**Next Steps (Phase 5-6):**
- Feedback & Evaluation System
- Cost Controls via Langfuse
- Versioning & Marketplace
- Additional Event Sources (Webhooks, CI/CD)

