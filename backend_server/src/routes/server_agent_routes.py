"""
Server Agent Routes - AI Agent Chat System

REST endpoints for session management.
SocketIO handlers for real-time chat with QA Manager and specialist agents.
"""

import os
import logging
import asyncio

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Blueprint for REST endpoints
server_agent_bp = Blueprint('server_agent', __name__, url_prefix='/server/agent')

# Lazy imports to avoid circular dependencies
_manager = None
_session_manager = None


def get_manager():
    """Get or create QA Manager instance (lazy load)"""
    global _manager
    if _manager is None:
        from agent.core.manager import QAManagerAgent
        logger.info("Initializing QA Manager agent...")
        _manager = QAManagerAgent()
    return _manager


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
    api_key = os.getenv('ANTHROPIC_API_KEY')
    api_key_configured = bool(api_key and len(api_key) > 10)
    
    return jsonify({
        "success": True,
        "status": "healthy",
        "api_key_configured": api_key_configured,
        "manager_initialized": _manager is not None,
    })


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
        
        Data: { "session_id": "...", "message": "..." }
        """
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            socketio.emit('error', {
                'error': 'session_id and message required'
            }, namespace='/agent')
            return
        
        session_mgr = get_session_manager()
        session = session_mgr.get_session(session_id)
        
        if not session:
            socketio.emit('error', {
                'error': 'Session not found'
            }, namespace='/agent')
            return
        
        manager = get_manager()
        
        async def process_and_stream():
            async for event in manager.process_message(message, session):
                socketio.emit('agent_event', 
                    event.to_dict(), 
                    room=session_id,
                    namespace='/agent'
                )
                await asyncio.sleep(0.05)
        
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
            async for event in manager.handle_approval(session, approved, modifications):
                socketio.emit('agent_event',
                    event.to_dict(),
                    room=session_id,
                    namespace='/agent'
                )
                await asyncio.sleep(0.05)
        
        socketio.start_background_task(
            lambda: asyncio.run(process_approval())
        )
    
    logger.info("SocketIO handlers registered for /agent namespace")

