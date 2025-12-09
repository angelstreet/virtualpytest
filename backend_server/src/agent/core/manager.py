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
        
        return f"""You are {config['nickname']}, {config['specialty']}.

Platform: {config['platform']} | Auto-nav: {str(allow_auto_nav).lower()} | Page: {current_page}

## Tools
{tools_list}

## Sub-Agents
{subagents_section if subagents_section else "None"}

## Delegation Priority (CHECK IN ORDER)
1. **Execute/Run/Script/Deployment** → ALWAYS `DELEGATE TO qa-execution-manager` (ignore platform like "mobile/web/tv" in prompt)
2. **Create/Generate testcase/requirement** → DELEGATE TO qa-design-manager
3. **Navigation tree building/exploration** → Match platform (mobile/web/stb manager)
4. **Read-only queries** → Use your own tools

When delegating: Say ONLY `DELEGATE TO [agent_id]` (no explanation).
Max 2 sentences. Be direct."""

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
        
        # Build message history for Claude
        # - If delegated: Only use current user message (avoid token bloat from parent agent's chatter)
        # - If root: Include full session history for context
        turn_messages = []
        if _is_delegated:
            # Delegated agent: just the user's request (clean slate)
            turn_messages = [{"role": "user", "content": message}]
        else:
            # Root agent: include full conversation history for context
            for msg in session.messages:
                turn_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        tools = self.tool_bridge.get_tool_definitions(self.tool_names)
        
        # Estimate token count from tools (rough: 4 chars = 1 token)
        tools_chars = sum(len(str(t)) for t in tools)
        estimated_tool_tokens = tools_chars // 4
        
        # Warn about tool overload - models struggle with too many tools
        if len(tools) > 20 or estimated_tool_tokens > 6000:
            print(f"[AGENT WARNING] {self.nickname} has {len(tools)} tools (~{estimated_tool_tokens:,} tokens)")
            print(f"[AGENT WARNING] Models often produce empty responses when overwhelmed by tools.")
            print(f"[AGENT WARNING] Consider reducing tools or splitting into specialized sub-agents.")
        
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        response_text = ""
        
        # Tool loop
        while True:
            start = time.time()
            response = self.client.messages.create(
                model=DEFAULT_MODEL, max_tokens=4096,  # Increased from 1024 to allow longer responses
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
                    
                    # Tool results are part of turn_messages conversation - don't add to session
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}]})
                except Exception as e:
                    if LANGFUSE_ENABLED:
                        track_tool_call(self.nickname, tool_use.name, tool_use.input, str(e), False, session.id)
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Tool error: {e}", error=str(e))
                    
                    # Tool errors are part of turn_messages conversation - don't add to session
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Error: {e}", "is_error": True}]})
            else:
                response_text = text_content
                
                # Check for empty response - diagnose why
                if not response_text or not response_text.strip():
                    input_tokens = metrics.get('input_tokens', 0)
                    output_tokens = metrics.get('output_tokens', 0)
                    stop_reason = getattr(response, 'stop_reason', 'unknown')
                    
                    # Log detailed diagnostics
                    print(f"[AGENT DEBUG] {self.nickname} EMPTY RESPONSE:")
                    print(f"  - stop_reason: {stop_reason}")
                    print(f"  - input_tokens: {input_tokens}")
                    print(f"  - output_tokens: {output_tokens}")
                    print(f"  - content blocks: {[b.type for b in response.content]}")
                    
                    # Build diagnostic error message
                    error_msg = f"Agent returned empty response (stop_reason: {stop_reason}, input: {input_tokens:,}, output: {output_tokens})."
                    
                    if stop_reason == "max_tokens":
                        error_msg += " Model hit output token limit mid-response."
                    elif stop_reason == "end_turn" and output_tokens < 10:
                        # Model chose to end turn immediately - likely overwhelmed by context
                        error_msg += f" Model ended turn with minimal output. This usually means the request is too complex or has too many tools ({len(tools)} tools). Try reducing tools or simplifying."
                    elif input_tokens > 50000:
                        error_msg += " Very high input tokens - consider reducing context or tool count."
                    
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=error_msg, error="empty_response", metrics=metrics)
                    break
                
                # Check if this is a delegation response - if so, rewrite to show Nickname (Name)
                delegate_to_check = self._parse_delegation(response_text)
                if delegate_to_check:
                    info = self._get_subagent_info(delegate_to_check)
                    # Format: "→ Scout"
                    display_text = re.sub(
                        r'DELEGATE\s+TO\s+[\w-]+',
                        f'Delegate to {info["nickname"]}',
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
        yield AgentEvent(type=EventType.AGENT_DELEGATED, agent=self.nickname, content=f"→ {delegated_manager.nickname}")
        print(f"[AGENT DEBUG] {self.nickname} yielding AGENT_STARTED for {delegated_manager.nickname}")
        yield AgentEvent(type=EventType.AGENT_STARTED, agent=delegated_manager.nickname, content="")
        
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
            if isinstance(e, anthropic.InternalServerError):
                rid = getattr(e, "request_id", None) or getattr(getattr(e, "body", {}), "get", lambda *_: None)("request_id")
                msg = f"Anthropic 500 Internal Server Error (request_id={rid or 'unknown'}). This may be transient or quota-related."
                yield AgentEvent(type=EventType.ERROR, agent=delegated_manager.nickname, content=msg, error=str(e))
            else:
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
