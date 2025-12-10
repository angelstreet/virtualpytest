"""
QA Manager Agent - Skill-Based Architecture

The orchestrator dynamically loads skills based on user requests:
- Router mode: Minimal tools, decides which skill to load
- Skill mode: Full tool access from loaded skill

Skills are defined in YAML files and provide focused capabilities.
"""

import re
import logging
import time
from typing import Dict, Any, AsyncGenerator, Optional

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, LANGFUSE_ENABLED
from ..observability import track_generation, track_tool_call, flush
from .session import Session
from .tool_bridge import ToolBridge
from .message_types import EventType, AgentEvent


class QAManagerAgent:
    """
    QA Manager - Skill-Based Orchestrator
    
    Operates in two modes:
    1. Router Mode: Uses minimal tools, decides which skill to load
    2. Skill Mode: Uses tools from the loaded skill
    
    Skills are loaded dynamically based on user requests.
    """
    def __init__(self, api_key: Optional[str] = None, user_identifier: Optional[str] = None, agent_id: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.user_identifier = user_identifier
        self._api_key = api_key
        self._client = None
        self.tool_bridge = ToolBridge()
        
        # Load from YAML
        self.agent_id = agent_id or 'assistant'
        self.agent_config = self._load_agent_config(self.agent_id)
        
        # Active skill (None = router mode)
        self._active_skill = None
        
        # Load skills on startup
        from ..skills import SkillLoader
        SkillLoader.load_all_skills()
        
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
        
        return {
            'name': metadata.name,
            'nickname': metadata.nickname or metadata.name,
            'specialty': metadata.description,
            'platform': platform or 'all',
            'skills': agent_def.skills or [],
            'available_skills': getattr(agent_def, 'available_skills', []) or [],
            'subagents': [s.id for s in (agent_def.subagents or [])],
        }
    
    @property
    def nickname(self) -> str:
        return self.agent_config['nickname']
    
    @property
    def active_skill(self):
        """Currently loaded skill (None if in router mode)"""
        return self._active_skill
    
    def load_skill(self, skill_name: str) -> bool:
        """
        Load a skill by name
        
        Returns:
            True if skill was loaded, False if not available
        """
        from ..skills import SkillLoader
        
        available = self.agent_config.get('available_skills', [])
        if skill_name not in available:
            self.logger.warning(f"Skill '{skill_name}' not in available_skills: {available}")
            return False
        
        skill = SkillLoader.get_skill(skill_name)
        if not skill:
            self.logger.error(f"Skill '{skill_name}' not found in definitions")
            return False
        
        self._active_skill = skill
        self.logger.info(f"Loaded skill: {skill_name} ({len(skill.tools)} tools)")
        return True
    
    def unload_skill(self) -> None:
        """Unload current skill and return to router mode"""
        if self._active_skill:
            self.logger.info(f"Unloaded skill: {self._active_skill.name}")
        self._active_skill = None
    
    def _parse_skill_command(self, text: str) -> Optional[str]:
        """Parse 'LOAD SKILL [skill-name]' from Claude's response"""
        match = re.search(r'LOAD\s+SKILL\s+([\w-]+)', text, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build system prompt based on current mode"""
        if self._active_skill:
            return self._build_skill_prompt(context)
        return self._build_router_prompt(context)
    
    def _build_router_prompt(self, ctx: Dict[str, Any] = None) -> str:
        """Build router mode prompt - decides which skill to load"""
        from ..skills import SkillLoader
        
        config = self.agent_config
        ctx = ctx or {}
        
        # Get skill descriptions for available skills
        available = config.get('available_skills', [])
        skill_descriptions = SkillLoader.get_skill_descriptions(available)
        
        # Tools available in router mode
        tools_list = '\n'.join(f"- `{skill}`" for skill in config['skills'])
        
        return f"""You are {config['nickname']}, {config['specialty']}.

## Mode: Router (Skill Selection)

You have minimal tools for quick queries. For complex tasks, load a skill.

## Available Skills
{skill_descriptions}

## Router Tools (for quick queries)
{tools_list}

## Instructions
1. Read the user's request carefully
2. If it's a quick query (list, status, info), use your router tools
3. If it requires specialized work, respond with: `LOAD SKILL [skill-name]`

Examples:
- "List testcases" → Use list_testcases tool
- "Show device status" → Use get_device_info tool
- "Explore the sauce-demo app" → LOAD SKILL exploration-web
- "Run testcase TC_AUTH_01" → LOAD SKILL execution
- "Create a testcase for login" → LOAD SKILL design

Be direct. Max 2 sentences unless asked for details."""
    
    def _build_skill_prompt(self, ctx: Dict[str, Any] = None) -> str:
        """Build skill mode prompt - use loaded skill's system prompt"""
        config = self.agent_config
        skill = self._active_skill
        ctx = ctx or {}
        
        tools_list = '\n'.join(f"- `{tool}`" for tool in skill.tools)
        
        return f"""You are {config['nickname']}, executing the **{skill.name}** skill.

{skill.system_prompt}

## Available Tools
{tools_list}

## Session Commands
- Say "UNLOAD SKILL" when task is complete to return to router mode
- Stay in this skill until task is done or user asks for something else

Be thorough with this skill's workflow. Use the tools systematically.

**CRITICAL: NEVER modify URLs returned by tools. Copy URLs EXACTLY as returned - do not change any characters, especially dates.**"""
    
    @property
    def tool_names(self) -> list[str]:
        """Get current tool names based on mode"""
        if self._active_skill:
            return self._active_skill.tools
        return self.agent_config.get('skills', [])
    
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
    
    async def process_message(self, message: str, session: Session, _is_delegated: bool = False) -> AsyncGenerator[AgentEvent, None]:
        """Process user message with skill-based routing
        
        Args:
            message: User message to process
            session: Session object
            _is_delegated: Internal flag - True when called from parent agent
        """
        print(f"\n{'='*60}")
        print(f"[AGENT DEBUG] {self.nickname} process_message START")
        print(f"[AGENT DEBUG] _is_delegated={_is_delegated}, active_skill={self._active_skill.name if self._active_skill else 'None'}")
        print(f"[AGENT DEBUG] message={message[:50]}...")
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
        
        # Only add message if not delegated
        if not _is_delegated:
            session.add_message("user", message)
        
        if session.pending_approval:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="Respond to pending approval first.")
            return
        
        # Check for explicit unload command
        if "unload skill" in message.lower():
            if self._active_skill:
                skill_name = self._active_skill.name
                self.unload_skill()
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=f"✓ Unloaded skill: {skill_name}. Back in router mode.")
            else:
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content="Already in router mode.")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        mode_str = f"[{self._active_skill.name}]" if self._active_skill else "[router]"
        print(f"[AGENT DEBUG] {self.nickname} {mode_str} yielding THINKING event")
        yield AgentEvent(type=EventType.THINKING, agent=self.nickname, content=f"Analyzing... {mode_str}")
        
        # Build message history
        turn_messages = []
        if _is_delegated:
            turn_messages = [{"role": "user", "content": message}]
        else:
            for msg in session.messages:
                turn_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        tools = self.tool_bridge.get_tool_definitions(self.tool_names)
        
        # Estimate token count
        tools_chars = sum(len(str(t)) for t in tools)
        estimated_tool_tokens = tools_chars // 4
        
        if len(tools) > 20 or estimated_tool_tokens > 6000:
            print(f"[AGENT WARNING] {self.nickname} has {len(tools)} tools (~{estimated_tool_tokens:,} tokens)")
        
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        response_text = ""
        
        # Tool loop
        while True:
            start = time.time()
            response = self.client.messages.create(
                model=DEFAULT_MODEL, max_tokens=4096,
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
                    
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}]})
                except Exception as e:
                    if LANGFUSE_ENABLED:
                        track_tool_call(self.nickname, tool_use.name, tool_use.input, str(e), False, session.id)
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Tool error: {e}", error=str(e))
                    
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Error: {e}", "is_error": True}]})
            else:
                response_text = text_content
                
                # Check for empty response
                if not response_text or not response_text.strip():
                    input_tokens = metrics.get('input_tokens', 0)
                    output_tokens = metrics.get('output_tokens', 0)
                    stop_reason = getattr(response, 'stop_reason', 'unknown')
                    
                    print(f"[AGENT DEBUG] {self.nickname} EMPTY RESPONSE:")
                    print(f"  - stop_reason: {stop_reason}")
                    print(f"  - input_tokens: {input_tokens}")
                    print(f"  - output_tokens: {output_tokens}")
                    
                    error_msg = f"Agent returned empty response (stop_reason: {stop_reason}, input: {input_tokens:,}, output: {output_tokens})."
                    
                    if stop_reason == "max_tokens":
                        error_msg += " Model hit output token limit mid-response."
                    elif stop_reason == "end_turn" and output_tokens < 10:
                        error_msg += f" Model ended turn with minimal output ({len(tools)} tools). Try simplifying."
                    elif input_tokens > 50000:
                        error_msg += " Very high input tokens - consider reducing context."
                    
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=error_msg, error="empty_response", metrics=metrics)
                    break
                
                # Check for skill load command
                skill_to_load = self._parse_skill_command(response_text)
                if skill_to_load:
                    print(f"[AGENT DEBUG] {self.nickname} loading skill: {skill_to_load}")
                    
                    # Emit the response first (shows intent)
                    display_text = re.sub(
                        r'LOAD\s+SKILL\s+[\w-]+',
                        f'Loading skill: **{skill_to_load}**',
                        response_text,
                        flags=re.IGNORECASE
                    )
                    yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=display_text, metrics=metrics)
                    
                    # Load the skill
                    if self.load_skill(skill_to_load):
                        yield AgentEvent(type=EventType.SKILL_LOADED, agent=self.nickname, content=f"✓ Loaded skill: {skill_to_load}")
                        
                        # Re-process with loaded skill
                        print(f"[AGENT DEBUG] {self.nickname} re-processing with skill {skill_to_load}")
                        async for event in self.process_message(message, session, _is_delegated=True):
                            yield event
                    else:
                        yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Failed to load skill: {skill_to_load}")
                    break
                
                # Check for unload command in response
                if "unload skill" in response_text.lower():
                    if self._active_skill:
                        skill_name = self._active_skill.name
                        self.unload_skill()
                        display_text = response_text.replace("UNLOAD SKILL", f"✓ Unloaded skill: {skill_name}")
                        yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=display_text, metrics=metrics)
                    else:
                        yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                    break
                
                # Normal response
                print(f"[AGENT DEBUG] {self.nickname} yielding MESSAGE: {response_text[:100]}...")
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                break
        
        # Save assistant response to session history
        if response_text:
            session.add_message("assistant", response_text, agent=self.nickname)
        
        if LANGFUSE_ENABLED:
            flush()
        
        # Only root agent emits SESSION_ENDED
        if not _is_delegated:
            print(f"[AGENT DEBUG] {self.nickname} yielding SESSION_ENDED (root)")
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
            if modifications:
                for k, v in modifications.items():
                    session.set_context(k, v)
            
            async for event in self.process_message(f"Continue: {approval.action}", session, _is_delegated=True):
                yield event
        else:
            yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content="Cancelled. What next?")
        
        yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
