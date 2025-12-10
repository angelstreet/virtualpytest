"""
Agent Core Components

- Manager: QA Manager orchestrator
- Session: Chat session management
- ToolBridge: MCP tool integration
- MessageTypes: Event types for streaming
- EventBus: Pub/sub for agent triggers
"""

# Lightweight imports only - no MCP dependencies
from .session import Session, SessionManager
from .message_types import EventType, AgentEvent
from .event_bus import (
    AgentEventBus,
    ExecutionEvent,
    TriggerType,
    get_event_bus,
    AnalysisQueue,
    get_analysis_queue,
)

__all__ = [
    'Session',
    'SessionManager',
    'EventType',
    'AgentEvent',
    'AgentEventBus',
    'ExecutionEvent',
    'TriggerType',
    'get_event_bus',
    'AnalysisQueue',
    'get_analysis_queue',
]


