"""
Agent Core Components

- Manager: QA Manager orchestrator
- Session: Chat session management
- ToolBridge: MCP tool integration
- MessageTypes: Event types for streaming
- EventBus: Pub/sub for agent triggers
"""

from .manager import QAManagerAgent
from .session import Session, SessionManager
from .tool_bridge import ToolBridge
from .message_types import EventType, AgentEvent
from .event_bus import (
    AgentEventBus,
    ExecutionEvent,
    TriggerType,
    get_event_bus,
    AnalysisQueue,
    get_analysis_queue,
)
# Note: trigger_handler is NOT imported here to avoid circular imports
# Import it directly where needed: from agent.core.trigger_handler import initialize_triggers

__all__ = [
    'QAManagerAgent',
    'Session',
    'SessionManager',
    'ToolBridge',
    'EventType',
    'AgentEvent',
    'AgentEventBus',
    'ExecutionEvent',
    'TriggerType',
    'get_event_bus',
    'AnalysisQueue',
    'get_analysis_queue',
]


