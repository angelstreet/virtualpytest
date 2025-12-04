"""
Session Management

Tracks chat sessions, conversation history, and pending approvals.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .message_types import ApprovalRequest, ApprovalResponse
from ..config import Mode


@dataclass
class Session:
    """A chat session with the QA Manager"""
    
    id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Current state
    mode: Optional[str] = None  # CREATE, VALIDATE, MAINTAIN
    active_agent: Optional[str] = None  # Currently working agent
    
    # Conversation
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context (shared between agents)
    context: Dict[str, Any] = field(default_factory=dict)
    # Common context keys:
    # - userinterface_name: str
    # - tree_id: str
    # - exploration_id: str
    # - host_name: str
    # - device_id: str
    
    # Pending approval
    pending_approval: Optional[ApprovalRequest] = None
    
    # Results
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str, agent: str = None):
        """Add a message to the conversation"""
        self.messages.append({
            "role": role,
            "content": content,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.updated_at = datetime.utcnow()
    
    def set_context(self, key: str, value: Any):
        """Set a context value"""
        self.context[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value"""
        return self.context.get(key, default)
    
    def request_approval(self, request: ApprovalRequest):
        """Set pending approval request"""
        self.pending_approval = request
        self.updated_at = datetime.utcnow()
    
    def clear_approval(self):
        """Clear pending approval"""
        self.pending_approval = None
        self.updated_at = datetime.utcnow()
    
    def add_result(self, agent: str, result: Dict[str, Any]):
        """Add agent result"""
        self.results.append({
            "agent": agent,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "mode": self.mode,
            "active_agent": self.active_agent,
            "message_count": len(self.messages),
            "context": self.context,
            "pending_approval": self.pending_approval.to_dict() if self.pending_approval else None,
            "result_count": len(self.results),
        }


class SessionManager:
    """Manages chat sessions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._sessions: Dict[str, Session] = {}
    
    def create_session(self) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session = Session(id=session_id)
        self._sessions[session_id] = session
        self.logger.info(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self.logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        return [s.to_dict() for s in self._sessions.values()]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours"""
        now = datetime.utcnow()
        to_delete = []
        
        for session_id, session in self._sessions.items():
            age = (now - session.updated_at).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        if to_delete:
            self.logger.info(f"Cleaned up {len(to_delete)} old sessions")

