"""
Server Agent Routes - AI Agent Chat System

REST endpoints for session management.
SocketIO handlers for real-time chat with QA Manager and specialist agents.
"""

import os
import logging
import asyncio
import json
from datetime import datetime

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# =============================================================================
# Agent Conversation Logger - Separate file for debugging
# =============================================================================
AGENT_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'agent_conversations.log')

def ensure_log_dir():
    """Ensure log directory exists"""
    log_dir = os.path.dirname(AGENT_LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

def log_agent_event(event_type: str, session_id: str, data: dict):
    """
    Log agent conversation events to dedicated file for debugging
    
    Args:
        event_type: Type of event (USER_MESSAGE, AGENT_EVENT, TOOL_CALL, ERROR, etc.)
        session_id: Session ID
        data: Event data
    """
    ensure_log_dir()
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "session_id": session_id,
        "data": data
    }
    
    try:
        with open(AGENT_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
    except Exception as e:
        logger.error(f"Failed to write agent log: {e}")

# Blueprint for REST endpoints
server_agent_bp = Blueprint('server_agent', __name__, url_prefix='/server/agent')

# Lazy imports to avoid circular dependencies
_manager = None
_session_manager = None


def get_manager(team_id: str = None):
    """
    Get or create QA Manager instance (lazy load)
    
    Args:
        team_id: Team/user identifier for API key retrieval
        
    Returns:
        QAManagerAgent instance
    """
    # Always create a new manager with the team_id to ensure correct API key
    # (In-memory storage means we can't cache the manager globally)
    from agent.core.manager import QAManagerAgent
    logger.info(f"Initializing QA Manager agent for team: {team_id or 'default'}...")
    return QAManagerAgent(user_identifier=team_id)


def get_session_manager():
    """Get or create Session Manager instance (lazy load)"""
    global _session_manager
    if _session_manager is None:
        from agent.core.session import SessionManager
        _session_manager = SessionManager()
    return _session_manager


# =============================================================================
# REST Endpoints
# =============================================================================

@server_agent_bp.route('/health', methods=['GET'])
def health_check():
    """Health check - returns API key configuration status"""
    team_id = request.args.get('team_id')
    
    # Check for API key in environment OR user storage
    env_api_key = os.getenv('ANTHROPIC_API_KEY')
    user_api_key = None
    if team_id:
        from agent.config import get_user_api_key
        user_api_key = get_user_api_key(team_id)
    
    api_key_configured = bool(env_api_key and len(env_api_key) > 10) or bool(user_api_key)
    
    return jsonify({
        "success": True,
        "status": "healthy",
        "api_key_configured": api_key_configured,
        "manager_initialized": _manager is not None,
    })


@server_agent_bp.route('/api-key', methods=['POST'])
def save_api_key():
    """
    Save and validate user's Anthropic API key
    
    Body: { "api_key": "sk-ant-...", "team_id": "..." }
    """
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    team_id = data.get('team_id') or request.args.get('team_id')
    
    if not api_key:
        return jsonify({
            "success": False,
            "error": "API key required"
        }), 400
    
    if not api_key.startswith('sk-ant-'):
        return jsonify({
            "success": False,
            "error": "Invalid API key format. Must start with 'sk-ant-'"
        }), 400
    
    if not team_id:
        return jsonify({
            "success": False,
            "error": "team_id required"
        }), 400
    
    # Validate the API key by making a test request
    try:
        import anthropic
        test_client = anthropic.Anthropic(api_key=api_key)
        # Simple test - list available models or make a minimal request
        # Using a very small token limit to minimize cost
        test_response = test_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        
        # If we got here, the key is valid
        from agent.config import set_user_api_key
        set_user_api_key(team_id, api_key)
        
        return jsonify({
            "success": True,
            "message": "API key validated and saved successfully"
        })
        
    except anthropic.AuthenticationError:
        return jsonify({
            "success": False,
            "error": "Invalid API key - authentication failed"
        }), 401
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return jsonify({
            "success": False,
            "error": f"Validation error: {str(e)}"
        }), 500


@server_agent_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new chat session"""
    session_mgr = get_session_manager()
    session = session_mgr.create_session()
    
    return jsonify({
        "success": True,
        "session": session.to_dict(),
    })


@server_agent_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """List all sessions"""
    session_mgr = get_session_manager()
    sessions = session_mgr.list_sessions()
    
    return jsonify({
        "success": True,
        "sessions": sessions,
    })


@server_agent_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Get a specific session"""
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    
    if not session:
        return jsonify({
            "success": False,
            "error": "Session not found",
        }), 404
    
    return jsonify({
        "success": True,
        "session": session.to_dict(),
        "messages": session.messages,
    })


@server_agent_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a session"""
    session_mgr = get_session_manager()
    deleted = session_mgr.delete_session(session_id)
    
    return jsonify({
        "success": deleted,
    })


@server_agent_bp.route('/sessions/<session_id>/approve', methods=['POST'])
def approve_action(session_id: str):
    """
    Approve or reject a pending action
    
    Body: { "approved": true/false, "modifications": {} }
    """
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    
    if not session:
        return jsonify({
            "success": False,
            "error": "Session not found",
        }), 404
    
    if not session.pending_approval:
        return jsonify({
            "success": False,
            "error": "No pending approval",
        }), 400
    
    data = request.get_json() or {}
    approved = data.get("approved", False)
    modifications = data.get("modifications", {})
    
    manager = get_manager()
    
    async def run_approval():
        events = []
        async for event in manager.handle_approval(session, approved, modifications):
            events.append(event.to_dict())
        return events
    
    events = asyncio.run(run_approval())
    
    return jsonify({
        "success": True,
        "events": events,
    })


# =============================================================================
# SocketIO Handlers
# =============================================================================

def register_agent_socketio_handlers(socketio):
    """
    Register SocketIO event handlers for /agent namespace
    
    Call this from app.py after creating the socketio instance.
    """
    
    @socketio.on('connect', namespace='/agent')
    def handle_connect():
        logger.info("Client connected to /agent namespace")
        socketio.emit('connected', {'status': 'ok'}, namespace='/agent')
    
    @socketio.on('disconnect', namespace='/agent')
    def handle_disconnect():
        logger.info("Client disconnected from /agent namespace")
    
    @socketio.on('join_session', namespace='/agent')
    def handle_join_session(data):
        """Join a session room"""
        session_id = data.get('session_id')
        if session_id:
            from flask_socketio import join_room
            join_room(session_id)
            logger.info(f"Client joined session: {session_id}")
            socketio.emit('joined', {'session_id': session_id}, namespace='/agent')
    
    @socketio.on('leave_session', namespace='/agent')
    def handle_leave_session(data):
        """Leave a session room"""
        session_id = data.get('session_id')
        if session_id:
            from flask_socketio import leave_room
            leave_room(session_id)
            logger.info(f"Client left session: {session_id}")
    
    @socketio.on('send_message', namespace='/agent')
    def handle_message(data):
        """
        Handle user message
        
        Data: { "session_id": "...", "message": "...", "team_id": "..." }
        """
        session_id = data.get('session_id')
        message = data.get('message')
        team_id = data.get('team_id')
        
        if not session_id or not message:
            socketio.emit('error', {
                'error': 'session_id and message required'
            }, namespace='/agent')
            return
        
        # Log user message
        log_agent_event('USER_MESSAGE', session_id, {'message': message, 'team_id': team_id})
        
        session_mgr = get_session_manager()
        session = session_mgr.get_session(session_id)
        
        if not session:
            socketio.emit('error', {
                'error': 'Session not found'
            }, namespace='/agent')
            return
        
        # Store team_id in session context for API key retrieval
        if team_id:
            session.set_context('team_id', team_id)
        
        manager = get_manager(team_id=team_id)
        
        async def process_and_stream():
            try:
                async for event in manager.process_message(message, session):
                    event_dict = event.to_dict()
                    
                    # Log every agent event for debugging
                    log_agent_event('AGENT_EVENT', session_id, event_dict)
                    
                    socketio.emit('agent_event', 
                        event_dict, 
                        room=session_id,
                        namespace='/agent'
                    )
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                log_agent_event('ERROR', session_id, {
                    'error': str(e),
                    'type': type(e).__name__
                })
                socketio.emit('error', {
                    'error': str(e),
                    'type': type(e).__name__
                }, room=session_id, namespace='/agent')
            finally:
                # Ensure Langfuse data is flushed even on errors
                try:
                    from agent.observability import flush
                    flush()
                except Exception:
                    pass  # Ignore flush errors
        
        socketio.start_background_task(
            lambda: asyncio.run(process_and_stream())
        )
    
    @socketio.on('approve', namespace='/agent')
    def handle_approve(data):
        """
        Handle approval response
        
        Data: { "session_id": "...", "approved": true/false, "modifications": {} }
        """
        session_id = data.get('session_id')
        approved = data.get('approved', False)
        modifications = data.get('modifications', {})
        
        session_mgr = get_session_manager()
        session = session_mgr.get_session(session_id)
        
        if not session:
            socketio.emit('error', {
                'error': 'Session not found'
            }, namespace='/agent')
            return
        
        manager = get_manager()
        
        async def process_approval():
            try:
                async for event in manager.handle_approval(session, approved, modifications):
                    socketio.emit('agent_event',
                        event.to_dict(),
                        room=session_id,
                        namespace='/agent'
                    )
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error processing approval: {e}", exc_info=True)
                socketio.emit('error', {
                    'error': str(e),
                    'type': type(e).__name__
                }, room=session_id, namespace='/agent')
        
        socketio.start_background_task(
            lambda: asyncio.run(process_approval())
        )
        
    @socketio.on('stop_generation', namespace='/agent')
    def handle_stop(data):
        """Handle stop request"""
        session_id = data.get('session_id')
        
        if session_id:
            session_mgr = get_session_manager()
            session = session_mgr.get_session(session_id)
            if session:
                session.cancel()
                logger.info(f"Session {session_id} cancelled by user")
                # Emit cancelled event immediately so UI updates
                socketio.emit('agent_event', {
                    'type': 'error',
                    'agent': 'QA Manager',
                    'content': '🛑 Stopping...'
                }, room=session_id, namespace='/agent')
    
    logger.info("SocketIO handlers registered for /agent namespace")

