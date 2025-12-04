"""
VirtualPyTest AI Agent System

Multi-agent architecture for QA automation:
- QA Manager: Orchestrator (delegates, no direct tools)
- Explorer: UI discovery, navigation tree building
- Builder: Test case and requirements creation
- Executor: Test execution, evidence capture
- Maintainer: Self-healing, selector fixes
"""

from .core.manager import QAManagerAgent
from .core.session import Session, SessionManager
from .core.tool_bridge import ToolBridge

__all__ = [
    'QAManagerAgent',
    'Session',
    'SessionManager', 
    'ToolBridge',
]

