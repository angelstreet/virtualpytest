"""
QA Manager Agent - YAML-Driven

The orchestrator loads everything from YAML config:
- Tools from agent's skills
- Sub-agents from agent's subagents
- Claude decides when to delegate based on tool availability
"""

import re
import logging
import uuid
import time
from typing import Dict, Any, AsyncGenerator, Optional

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, MAX_TOKENS, LANGFUSE_ENABLED
from ..observability import track_generation, track_tool_call, flush
from .session import Session
from .tool_bridge import ToolBridge
from .message_types import EventType, AgentEvent, ApprovalRequest


class QAManagerAgent:
    """
    QA Manager - YAML-Driven Orchestrator
    
    Everything comes from YAML:
    - Identity (name, nickname, specialty)
    - Tools (skills)
    - Sub-agents (subagents with delegate_for)
    
    Claude decides when to delegate based on available tools.
    """
    
    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build system prompt dynamically from YAML config"""
        config = self.agent_config
        ctx = context or {}
        
        allow_auto_nav = ctx.get('allow_auto_navigation', False)
        current_page = ctx.get('current_page', '/')
        
        # Tools from YAML
        tools_list = '\n'.join(f"- `{skill}`" for skill in config['skills'])
        
        # Sub-agents from YAML
        subagents_section = ""
        if config.get('subagents_info'):
            lines = []
            for sa in config['subagents_info']:
                delegate_str = ', '.join(sa['delegate_for']) if sa['delegate_for'] else 'general tasks'
                extra_skills = [s for s in sa['skills'] if s not in config['skills']][:5]
                extra_str = f" (has: {', '.join(extra_skills)})" if extra_skills else ""
                lines.append(f"- **{sa['nickname']}** (`{sa['id']}`): {sa['description']} | For: {delegate_str}{extra_str}")
            subagents_section = "\n".join(lines)
        
        return f"""You are {config['name']}, {config['specialty']}.

## Identity
- **Name**: {config['nickname']}
- **Platform**: {config['platform']}

## CONCISENESS
- Be extremely concise. Max 2 sentences after data.
- Direct answers only.

## Context
- Auto-Navigation: {str(allow_auto_nav).lower()}
- Current Page: {current_page}

## Your Tools
{tools_list}

## Your Sub-Agents
{subagents_section if subagents_section else "None"}

## Rules

1. **Use your tools first** - If you have the tool, use it directly.
2. **Delegate if you lack the tool** - Say exactly: `DELEGATE TO [agent_id]`

Examples:
- "How many test cases?" → Use `list_testcases`, report count
- "Navigate to home on mobile device" → You lack `navigate_to_node` → `DELEGATE TO qa-mobile-manager`
- "Test login flow on web" → You lack device control → `DELEGATE TO qa-web-manager`
- "Check STB video playback" → You lack device control → `DELEGATE TO qa-stb-manager`

Be efficient. Data, not explanations."""

    def __init__(self, api_key: Optional[str] = None, user_identifier: Optional[str] = None, agent_id: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.user_identifier = user_identifier
        self._api_key = api_key
        self._client = None
        self.tool_bridge = ToolBridge()
        
        # Load from YAML
        self.agent_id = agent_id or 'ai-assistant'
        self.agent_config = self._load_agent_config(self.agent_id)
        
        # Delegated managers loaded dynamically (not internal sub-agents)
        self._delegated_managers = {}
        
        self.logger.info(f"Manager initialized as {self.agent_config['nickname']} ({self.agent_id})")
    
    def _load_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Load agent config from YAML registry"""
        from ..registry import get_agent_registry
        
        registry = get_agent_registry()
        agent_def = registry.get(agent_id)
        
        if not agent_def:
            raise ValueError(f"Agent '{agent_id}' not found in registry.")
        
        metadata = agent_def.metadata
        config = agent_def.config
        platform = config.platform_filter if config else None
        
        # Load sub-agent info from YAML
        subagents_info = []
        for subagent_ref in (agent_def.subagents or []):
            subagent_def = registry.get(subagent_ref.id)
            if subagent_def:
                subagents_info.append({
                    'id': subagent_ref.id,
                    'nickname': subagent_def.metadata.nickname or subagent_ref.id,
                    'description': subagent_def.metadata.description,
                    'delegate_for': subagent_ref.delegate_for or [],
                    'skills': subagent_def.skills or [],
                })
        
        return {
            'name': metadata.name,
            'nickname': metadata.nickname or metadata.name,
            'specialty': metadata.description,
            'platform': platform or 'all',
            'skills': agent_def.skills or [],
            'subagents': [s.id for s in (agent_def.subagents or [])],
            'subagents_info': subagents_info,
        }
    
    def _get_delegated_manager(self, agent_id: str) -> Optional['QAManagerAgent']:
        """Lazy-load delegated manager when needed"""
        if agent_id in self._delegated_managers:
            return self._delegated_managers[agent_id]
        
        try:
            # Create a new QAManagerAgent with the delegated agent_id
            manager = QAManagerAgent(
                api_key=self._get_api_key_safe(),
                user_identifier=self.user_identifier,
                agent_id=agent_id
            )
            # Share the tool_bridge so MCP connections are reused
            manager.tool_bridge = self.tool_bridge
            self._delegated_managers[agent_id] = manager
            self.logger.info(f"Loaded delegated manager: {manager.nickname} ({agent_id})")
            return manager
        except Exception as e:
            self.logger.error(f"Failed to load delegated manager {agent_id}: {e}", exc_info=True)
            return None
    
    @property
    def nickname(self) -> str:
        return self.agent_config['nickname']
    
    def _get_api_key_safe(self) -> Optional[str]:
        try:
            return self._api_key or get_anthropic_api_key(identifier=self.user_identifier)
        except ValueError:
            return None
    
    @property
    def client(self):
        if self._client is None:
            key = self._get_api_key_safe()
            if not key:
                raise ValueError("ANTHROPIC_API_KEY not configured.")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client
    
    @property
    def api_key_configured(self) -> bool:
        return self._get_api_key_safe() is not None
    
    @property
    def tool_names(self) -> list[str]:
        """Tools from YAML skills"""
        return self.agent_config.get('skills', [])

    def _parse_delegation(self, text: str) -> Optional[str]:
        """Parse 'DELEGATE TO [agent_id]' from Claude's response"""
        match = re.search(r'DELEGATE\s+TO\s+([\w-]+)', text, re.IGNORECASE)
        return match.group(1).lower() if match else None

    def _resolve_agent_id(self, identifier: str) -> Optional[str]:
        """Resolve agent identifier (ID or nickname) to agent ID
        
        Args:
            identifier: Agent ID or nickname (case-insensitive)
            
        Returns:
            Resolved agent ID or None if not found
        """
        identifier_lower = identifier.lower()
        
        # Check if it's already a valid agent ID
        for sa_id in self.agent_config.get('subagents', []):
            if sa_id.lower() == identifier_lower:
                return sa_id
        
        # Check if it's a nickname
        for sa in self.agent_config.get('subagents_info', []):
            if sa['nickname'].lower() == identifier_lower:
                return sa['id']
        
        return None
    
    def _get_subagent_info(self, agent_id: str) -> Dict[str, str]:
        """Get nickname and description for a subagent by ID"""
        for sa in self.agent_config.get('subagents_info', []):
            if sa['id'] == agent_id:
                return {
                    'nickname': sa['nickname'],
                    'description': sa.get('description', ''),
                }
        return {'nickname': agent_id, 'description': ''}
    
    async def process_message(self, message: str, session: Session, _is_delegated: bool = False) -> AsyncGenerator[AgentEvent, None]:
        """Process user message - YAML-driven
        
        Args:
            message: User message to process
            session: Session object
            _is_delegated: Internal flag - True when called from parent agent delegation
        """
        print(f"\n{'='*60}")
        print(f"[AGENT DEBUG] {self.nickname} process_message START")
        print(f"[AGENT DEBUG] _is_delegated={_is_delegated}, message={message[:50]}...")
        print(f"{'='*60}")
        self.logger.info(f"[{self.nickname}] Processing: {message[:100]}...")
        
        if not self.api_key_configured:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="⚠️ API key not configured.")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Session ended")
            return
        
        # Context window compaction (only for root agent)
        if not _is_delegated and session.needs_compaction(threshold=50):
            yield AgentEvent(type=EventType.THINKING, agent="System", content="Compacting history...")
            msgs = session.get_messages_for_summary()
            if msgs:
                try:
                    api_msgs = [{"role": m["role"], "content": m["content"]} for m in msgs]
                    resp = self.client.messages.create(
                        model=DEFAULT_MODEL, max_tokens=1024,
                        messages=[*api_msgs, {"role": "user", "content": "Summarize key actions/results concisely."}]
                    )
                    session.apply_summary(resp.content[0].text)
                    yield AgentEvent(type=EventType.MESSAGE, agent="System", content="🧹 History compacted.")
                except Exception as e:
                    self.logger.error(f"Compaction failed: {e}")
        
        # Only add message if not delegated (parent already added it)
        if not _is_delegated:
            session.add_message("user", message)
        
        if session.pending_approval:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="Respond to pending approval first.")
            return
        
        print(f"[AGENT DEBUG] {self.nickname} yielding THINKING event")
        yield AgentEvent(type=EventType.THINKING, agent=self.nickname, content="Analyzing...")
        
        # Include full conversation history for context (allows reviewing past executions)
        # Convert session messages to Claude API format (strip agent/timestamp metadata)
        turn_messages = []
        for msg in session.messages:
            turn_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        tools = self.tool_bridge.get_tool_definitions(self.tool_names)
        
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        response_text = ""
        
        # Tool loop
        while True:
            start = time.time()
            response = self.client.messages.create(
                model=DEFAULT_MODEL, max_tokens=1024,
                system=self.get_system_prompt(session.context),
                messages=turn_messages, tools=tools
            )
            metrics = {
                "duration_ms": int((time.time() - start) * 1000),
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
            
            if LANGFUSE_ENABLED:
                track_generation(self.nickname, DEFAULT_MODEL, turn_messages, response, session.id, session.context.get("user_id"))
            
            turn_messages.append({"role": "assistant", "content": response.content})
            
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            text_content = next((b.text for b in response.content if b.type == "text"), "")
            
            if tool_use:
                yield AgentEvent(type=EventType.TOOL_CALL, agent=self.nickname, content=f"Calling: {tool_use.name}", tool_name=tool_use.name, tool_params=tool_use.input, metrics=metrics)
                
                try:
                    result = self.tool_bridge.execute(tool_use.name, tool_use.input, allowed_tools=self.tool_names)
                    if LANGFUSE_ENABLED:
                        track_tool_call(self.nickname, tool_use.name, tool_use.input, result, True, session.id)
                    yield AgentEvent(type=EventType.TOOL_RESULT, agent=self.nickname, content="Success", tool_name=tool_use.name, tool_result=result, success=True)
                    
                    # Save tool result to session history (for future context)
                    tool_result_text = f"🔧 Tool: {tool_use.name}\nResult: {str(result)}"
                    session.add_message("assistant", tool_result_text, agent=self.nickname)
                    
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}]})
                except Exception as e:
                    if LANGFUSE_ENABLED:
                        track_tool_call(self.nickname, tool_use.name, tool_use.input, str(e), False, session.id)
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Tool error: {e}", error=str(e))
                    
                    # Save tool error to session history (for future context)
                    tool_error_text = f"🔧 Tool: {tool_use.name}\nError: {str(e)}"
                    session.add_message("assistant", tool_error_text, agent=self.nickname)
                    
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Error: {e}", "is_error": True}]})
            else:
                response_text = text_content
                
                # Check if this is a delegation response - if so, rewrite to show Nickname (Name)
                delegate_to_check = self._parse_delegation(response_text)
                if delegate_to_check:
                    info = self._get_subagent_info(delegate_to_check)
                    # Format: "Handing off to **Scout** (QA Mobile Manager)"
                    desc_part = f" ({info['description']})" if info['description'] else ""
                    display_text = re.sub(
                        r'DELEGATE\s+TO\s+[\w-]+',
                        f'Handing off to **{info["nickname"]}**{desc_part}',
                        response_text,
                        flags=re.IGNORECASE
                    )
                    print(f"[AGENT DEBUG] {self.nickname} yielding MESSAGE (delegation): {display_text[:100]}...")
                    yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=display_text, metrics=metrics)
                else:
                    print(f"[AGENT DEBUG] {self.nickname} yielding MESSAGE: {response_text[:100]}...")
                    yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                break
        
        # Save assistant response to session history (for future context)
        if response_text:
            session.add_message("assistant", response_text, agent=self.nickname)
        
        # Check for delegation request (use original response_text for parsing)
        delegate_identifier = self._parse_delegation(response_text)
        print(f"[AGENT DEBUG] {self.nickname} delegation parsed: {delegate_identifier}")
        
        if not delegate_identifier:
            # No delegation - we're done
            print(f"[AGENT DEBUG] {self.nickname} NO DELEGATION - finishing")
            if LANGFUSE_ENABLED:
                flush()
            if not _is_delegated:
                print(f"[AGENT DEBUG] {self.nickname} yielding SESSION_ENDED (root)")
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            else:
                print(f"[AGENT DEBUG] {self.nickname} NOT yielding SESSION_ENDED (delegated)")
            return
        
        # Resolve identifier (could be ID or nickname) to agent ID
        delegate_to = self._resolve_agent_id(delegate_identifier)
        
        if not delegate_to:
            # Agent not found (neither ID nor nickname matched)
            print(f"[AGENT DEBUG] ERROR: Could not resolve '{delegate_identifier}' to any subagent")
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Cannot delegate to '{delegate_identifier}' - agent not found")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        print(f"[AGENT DEBUG] {self.nickname} resolved '{delegate_identifier}' to agent ID '{delegate_to}'")
        
        # Get info for display
        delegate_info = self._get_subagent_info(delegate_to)
        print(f"[AGENT DEBUG] {self.nickname} DELEGATING to {delegate_info['nickname']} ({delegate_to})")
        
        # Validate delegate is in our YAML config (should always pass after resolution, but double-check)
        if delegate_to not in self.agent_config['subagents']:
            print(f"[AGENT DEBUG] ERROR: {delegate_to} not in subagents {self.agent_config['subagents']}")
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Cannot delegate to '{delegate_info['nickname']}' - not in my subagents")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        # Get delegated manager
        delegated_manager = self._get_delegated_manager(delegate_to)
        if not delegated_manager:
            print(f"[AGENT DEBUG] ERROR: Failed to load delegated manager {delegate_to}")
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Failed to load {delegate_info['nickname']}")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        session.active_agent = delegate_to
        
        print(f"[AGENT DEBUG] {self.nickname} yielding AGENT_DELEGATED")
        yield AgentEvent(type=EventType.AGENT_DELEGATED, agent=self.nickname, content=f"Delegating to {delegated_manager.nickname}...")
        print(f"[AGENT DEBUG] {self.nickname} yielding AGENT_STARTED for {delegated_manager.nickname}")
        yield AgentEvent(type=EventType.AGENT_STARTED, agent=delegated_manager.nickname, content=f"{delegated_manager.nickname} taking over...")
        
        # Run delegated manager with original message (pass _is_delegated=True)
        print(f"[AGENT DEBUG] {self.nickname} calling {delegated_manager.nickname}.process_message()")
        try:
            event_count = 0
            async for event in delegated_manager.process_message(message, session, _is_delegated=True):
                event_count += 1
                if session.cancelled:
                    print(f"[AGENT DEBUG] Session cancelled!")
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="🛑 Stopped by user.")
                    session.reset_cancellation()
                    return
                
                # Forward all events from delegated manager
                print(f"[AGENT DEBUG] {self.nickname} forwarding event #{event_count} from {delegated_manager.nickname}: type={event.type}")
                yield event
            print(f"[AGENT DEBUG] {self.nickname} finished receiving events from {delegated_manager.nickname}, total={event_count}")
        except Exception as e:
            print(f"[AGENT DEBUG] ERROR in delegated manager: {e}")
            self.logger.error(f"[{self.nickname}] Error in delegated manager {delegated_manager.nickname}: {e}", exc_info=True)
            yield AgentEvent(type=EventType.ERROR, agent=delegated_manager.nickname, content=f"Error: {str(e)}", error=str(e))
        
        print(f"[AGENT DEBUG] {self.nickname} yielding AGENT_COMPLETED for {delegated_manager.nickname}")
        yield AgentEvent(type=EventType.AGENT_COMPLETED, agent=delegated_manager.nickname, content=f"{delegated_manager.nickname} completed")
        
        session.active_agent = None
        
        if LANGFUSE_ENABLED:
            flush()
        
        # Only root agent emits SESSION_ENDED
        if not _is_delegated:
            print(f"[AGENT DEBUG] {self.nickname} yielding SESSION_ENDED (root after delegation)")
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
        
        print(f"[AGENT DEBUG] {self.nickname} process_message END")
    
    async def handle_approval(self, session: Session, approved: bool, modifications: Dict[str, Any] = None) -> AsyncGenerator[AgentEvent, None]:
        """Handle approval response"""
        if not session.pending_approval:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="No pending approval")
            return
        
        approval = session.pending_approval
        session.clear_approval()
        
        yield AgentEvent(type=EventType.APPROVAL_RECEIVED, agent=self.nickname, content=f"Approval {'granted' if approved else 'rejected'}")
        
        if approved:
            manager = self._get_delegated_manager(approval.agent)
            if manager:
                if modifications:
                    for k, v in modifications.items():
                        session.set_context(k, v)
                
                async for event in manager.process_message(f"Continue: {approval.action}", session, _is_delegated=True):
                    yield event
        else:
            yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content="Cancelled. What next?")
        
        yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
