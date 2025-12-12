"""
QA Manager Agent - Skill-Based Architecture with Prompt Caching

The orchestrator dynamically loads skills based on user requests:
- Router mode: Minimal tools, decides which skill to load
- Skill mode: Full tool access from loaded skill
- Prompt Caching: System prompt and tools are cached for 90% cost reduction
- Queue Worker: Background thread for processing Redis queue items

Skills are defined in YAML files and provide focused capabilities.
"""

import re
import logging
import time
import threading
import asyncio
import json
import os
from typing import Dict, Any, AsyncGenerator, Optional, List

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, LANGFUSE_ENABLED
from ..observability import track_generation, track_tool_call, flush
from .session import Session, SessionManager
from .tool_bridge import ToolBridge
from .message_types import EventType, AgentEvent
from .sherlock_handler import SherlockHandler
from .nightwatch_handler import NightwatchHandler
from .context_extractor import extract_context_from_result


class QAManagerAgent:
    """
    QA Manager - Skill-Based Orchestrator with Prompt Caching
    
    Operates in two modes:
    1. Router Mode: Uses minimal tools, decides which skill to load
    2. Skill Mode: Uses tools from the loaded skill
    
    Uses Anthropic's prompt caching for 90% cost reduction on repeated calls.
    
    Background Worker Configuration:
    - Alert processing filters are handled by agent-specific handlers (e.g., NightwatchHandler)
    - Each handler implements its own filtering logic (duration, rate limiting, etc.)
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
        
        # Queue worker state
        self._queue_worker_running = False
        self._queue_worker_thread: Optional[threading.Thread] = None
        self._session_manager = SessionManager()
        
        # Agent-specific handlers (lazy init based on agent_id)
        self._sherlock_handler: Optional[SherlockHandler] = None
        self._nightwatch_handler: Optional[NightwatchHandler] = None
        
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
        
        # Get background queues from config
        background_queues = []
        if config and hasattr(config, 'background_queues'):
            background_queues = config.background_queues or []
        
        # Get dry_run flag from config
        dry_run = False
        if config and hasattr(config, 'dry_run'):
            dry_run = config.dry_run or False
        
        return {
            'name': metadata.name,
            'nickname': metadata.nickname or metadata.name,
            'specialty': metadata.description,
            'platform': platform or 'all',
            'skills': agent_def.skills or [],
            'available_skills': getattr(agent_def, 'available_skills', []) or [],
            'subagents': [s.id for s in (agent_def.subagents or [])],
            'background_queues': background_queues,
            'dry_run': dry_run,
        }
    
    @property
    def nickname(self) -> str:
        return self.agent_config['nickname']
    
    @property
    def active_skill(self):
        """Currently loaded skill (None if in router mode)"""
        return self._active_skill
    
    def load_skill(self, skill_name: str) -> bool:
        """Load a skill by name"""
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
    
    def _build_context_section(self, ctx: Dict[str, Any]) -> str:
        """Build context section for system prompt - inject working context"""
        if not ctx:
            return ""
        
        # Extract key context values
        ui_name = ctx.get('userinterface_name')
        tree_id = ctx.get('tree_id')
        host = ctx.get('host_name')
        device = ctx.get('device_id')
        hosts_list = ctx.get('hosts', [])
        devices_list = ctx.get('devices', [])
        
        # Only show context if we have at least one value
        if not any([ui_name, tree_id, host, device, hosts_list, devices_list]):
            return ""
        
        lines = ["## Context"]
        
        # Show discovered resources
        if hosts_list:
            lines.append(f"Hosts: {', '.join(hosts_list)}")
        if devices_list:
            device_summary = ', '.join([f"{d.get('device_id')}" for d in devices_list[:3]])
            if len(devices_list) > 3:
                device_summary += f" +{len(devices_list) - 3}"
            lines.append(f"Devices: {device_summary}")
        
        # Show active working context
        if ui_name:
            lines.append(f"Interface: {ui_name}")
        if tree_id:
            lines.append(f"Tree: {tree_id}")
        if host:
            lines.append(f"Host: {host}")
        if device:
            lines.append(f"Device: {device}")
        
        # Add TWO newlines after context section (creates blank line separator)
        return '\n'.join(lines) + "\n\n"
    
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
        
        # Build context section
        context_section = self._build_context_section(ctx)
        
        return f"""You are {config['nickname']}, {config['specialty']}.

## Mode: Router

Quick queries → use router tools. Complex tasks → load a skill.

{context_section}## Skills
{skill_descriptions}

## Router Tools
{tools_list}

## Rules
- Quick query → use tool directly
- Complex task → respond ONLY: `LOAD SKILL [name]`
"""
    
    def _build_skill_prompt(self, ctx: Dict[str, Any] = None) -> str:
        """Build skill mode prompt"""
        config = self.agent_config
        skill = self._active_skill
        ctx = ctx or {}
        
        # Build context section
        context_section = self._build_context_section(ctx)
        
        return f"""You are {config['nickname']} executing **{skill.name}** skill.

{context_section}{skill.system_prompt}

Tools: {', '.join(skill.tools)}

Be direct and concise. Never modify URLs from tools. Tool errors in 1 sentence."""
    
    def _build_cached_system(self, context: Dict[str, Any] = None) -> List[Dict]:
        """Build system prompt with cache control for Anthropic prompt caching"""
        prompt_text = self.get_system_prompt(context)
        return [{
            "type": "text",
            "text": prompt_text,
            "cache_control": {"type": "ephemeral"}
        }]
    
    def _build_cached_tools(self, tool_names: List[str]) -> List[Dict]:
        """Build tool definitions with cache control on the last tool"""
        tools = self.tool_bridge.get_tool_definitions(tool_names)
        
        # Add cache_control to last tool (caches everything up to and including it)
        if tools:
            tools[-1]["cache_control"] = {"type": "ephemeral"}
        
        return tools

    def _log_turn_state(self, session: Session, system_prompt: List[Dict], turn_messages: List[Dict], summary: str, keep_last_n: int, incoming_message: str, is_delegated: bool) -> None:
        """Log injected context, summary, and the raw prompt (system + messages) being sent to the model"""
        ctx_keys = ['userinterface_name', 'tree_id', 'host_name', 'device_id', 'session_id']
        ctx_parts = [f"{k}={session.context[k]}" for k in ctx_keys if session.context.get(k)]
        context_line = ", ".join(ctx_parts) if ctx_parts else "None"
        
        print(f"[TURN] Incoming message: {incoming_message[:120]}{'...' if len(incoming_message) > 120 else ''}")
        print(f"[TURN] Injected context: {context_line}")
        
        print("[TURN] Rolling summary:")
        print(summary if summary else "(none)")
        
        # Show raw prompt exactly as sent to the model (system + messages)
        print("---------------- RAW prompt ----------------")
        try:
            print(json.dumps({
                "system": system_prompt,
                "messages": turn_messages,
            }, ensure_ascii=False, indent=2))
        except Exception:
            try:
                print(str({"system": system_prompt, "messages": turn_messages}))
            except Exception:
                print("<<unable to render prompt>>")
        print("--------------------------------------------")
    
    def _update_conversation_summary(self, session: Session, user_msg: str, ai_response: str, tool_calls: List[Dict]):
        """
        Update rolling 3-line conversation summary after each turn.
        Summary captures key actions/context from the conversation.
        """
        # Get existing summary
        existing_summary = session.get_context('conversation_summary', '')
        
        # Build this turn's summary line
        # Extract key action from tools or response
        action_summary = ""
        if tool_calls:
            # Summarize main tool action
            main_tool = tool_calls[0]['tool_name']
            params = tool_calls[0].get('params', {})
            
            # Extract key info based on tool type
            if 'navigate' in main_tool.lower():
                target = params.get('target_node_label', params.get('node_id', ''))
                ui = params.get('userinterface_name', '')
                action_summary = f"Navigated to '{target}'" + (f" on {ui}" if ui else "")
            elif 'take_control' in main_tool.lower():
                host = params.get('host_name', '')
                device = params.get('device_id', '')
                action_summary = f"Took control of {device} on {host}"
            elif 'click' in main_tool.lower() or 'execute' in main_tool.lower():
                action = params.get('action_type', params.get('command', 'action'))
                action_summary = f"Executed {action}"
            else:
                action_summary = f"Used {main_tool}"
        else:
            # No tools - use truncated response
            action_summary = ai_response[:50] + "..." if len(ai_response) > 50 else ai_response
        
        # Build new summary line: "User asked X → AI did Y"
        user_brief = user_msg[:30] + "..." if len(user_msg) > 30 else user_msg
        new_line = f"• {user_brief} → {action_summary}"
        
        # Combine with existing, keep only last 3 lines
        if existing_summary:
            lines = existing_summary.strip().split('\n')
            lines.append(new_line)
            # Keep only last 3
            lines = lines[-3:]
            new_summary = '\n'.join(lines)
        else:
            new_summary = new_line
        
        session.set_context('conversation_summary', new_summary)
        print(f"[SUMMARY] Updated: {new_summary}")
    
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
        """Process user message with skill-based routing and prompt caching"""
        print(f"\n{'='*60}")
        print(f"[AGENT] {self.nickname} | skill={self._active_skill.name if self._active_skill else 'router'}")
        print(f"[AGENT] message={message[:50]}...")
        print(f"{'='*60}")
        self.logger.info(f"[{self.nickname}] Processing: {message[:100]}...")
        
        if not self.api_key_configured:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="API key not configured.")
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
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=f"Unloaded {skill_name}. Back in router mode.")
            else:
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content="Already in router mode.")
            if not _is_delegated:
                yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        mode_str = f"[{self._active_skill.name}]" if self._active_skill else "[router]"
        yield AgentEvent(type=EventType.THINKING, agent=self.nickname, content=f"Analyzing... {mode_str}")
        
        # Build message history: summary + last 2 messages only (efficient)
        turn_messages = []
        KEEP_LAST_N = 2  # Keep last 1 turn (2 messages: 1 user + 1 assistant)
        summary = ""
        
        if _is_delegated:
            turn_messages = [{"role": "user", "content": message}]
        else:
            all_messages = session.messages
            
            # Always prepend summary if available (gives context from older turns)
            summary = session.get_context('conversation_summary', '')
            if summary and len(all_messages) > KEEP_LAST_N:
                turn_messages.append({
                    "role": "user",
                    "content": f"Summary:\n{summary}"
                })
            
            # Add last N messages (or all if fewer)
            messages_to_add = all_messages[-KEEP_LAST_N:] if len(all_messages) > KEEP_LAST_N else all_messages
            for msg in messages_to_add:
                turn_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Build cached system prompt and tools
        cached_system = self._build_cached_system(session.context)
        cached_tools = self._build_cached_tools(self.tool_names)
        
        # Debug log: show what context is being injected
        if session.context:
            ctx_keys = [k for k in ['hosts', 'devices', 'userinterface_name', 'tree_id', 'host_name', 'device_id'] if session.context.get(k)]
            if ctx_keys:
                print(f"[CONTEXT] Injecting: {', '.join(ctx_keys)}")
        
        # Log raw prompt only for root calls (avoid duplicate logs on delegated runs)
        if not _is_delegated:
            self._log_turn_state(session, cached_system, turn_messages, summary, KEEP_LAST_N, message, _is_delegated)
        
        print(f"[AGENT] Tools: {len(cached_tools)} | System: {len(cached_system[0]['text'])} chars")
        
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        response_text = ""
        
        # Track tool calls for context extraction and summary
        tool_calls_this_turn = []
        
        # Tools that set working context (interface, tree, host, device)
        CONTEXT_TOOLS = {
            'navigate_to_node', 'take_control', 'click_element', 'execute_device_action',
            'auto_discover_screen', 'get_node_tree', 'explore_navigation'
        }
        
        # Tool loop
        while True:
            start = time.time()
            
            # Use prompt caching via extra_headers
            # disable_parallel_tool_use ensures sequential tool execution (one at a time)
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                system=cached_system,
                messages=turn_messages,
                tools=cached_tools,
                tool_choice={"type": "auto", "disable_parallel_tool_use": True},
                extra_headers={
                    "anthropic-beta": "prompt-caching-2024-07-31"
                }
            )
            
            # Extract cache metrics if available
            cache_creation = getattr(response.usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
            
            metrics = {
                "duration_ms": int((time.time() - start) * 1000),
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_creation_tokens": cache_creation,
                "cache_read_tokens": cache_read,
            }
            
            # Log cache performance
            if cache_read > 0:
                print(f"[CACHE] Read {cache_read} tokens from cache (90% cheaper)")
            if cache_creation > 0:
                print(f"[CACHE] Created cache with {cache_creation} tokens")
            
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
                    
                    # Track tool call for summary
                    tool_calls_this_turn.append({
                        'tool_name': tool_use.name,
                        'params': tool_use.input,
                        'success': True
                    })
                    
                    # Extract context from tool inputs (for action tools)
                    if tool_use.name in CONTEXT_TOOLS:
                        for key in ['userinterface_name', 'tree_id', 'host_name', 'device_id']:
                            value = tool_use.input.get(key)
                            if value:
                                session.set_context(key, value)
                                print(f"[CONTEXT] Set {key}={value}")

                    # Extract context from tool outputs (discovery tools)
                    output_updates = extract_context_from_result(tool_use.name, result)
                    for key, value in output_updates.items():
                        session.set_context(key, value)
                        print(f"[CONTEXT] Set {key}={value} (from output)")
                    
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": json.dumps(result)}]})
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
                    
                    error_msg = f"Empty response (stop: {stop_reason}, in: {input_tokens}, out: {output_tokens})"
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=error_msg, error="empty_response", metrics=metrics)
                    break
                
                # Check for skill load command
                skill_to_load = self._parse_skill_command(response_text)
                if skill_to_load:
                    print(f"[AGENT] Loading skill: {skill_to_load}")
                    yield AgentEvent(type=EventType.SKILL_LOADED, agent=self.nickname, content=skill_to_load)
                    
                    if self.load_skill(skill_to_load):
                        # Re-process with loaded skill
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
                        display_text = response_text.replace("UNLOAD SKILL", f"Unloaded {skill_name}")
                        yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=display_text, metrics=metrics)
                    else:
                        yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                    break
                
                # Normal response
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                break
        
        # Save assistant response to session history (clean, no tool details)
        if response_text:
            session.add_message("assistant", response_text, agent=self.nickname)
            
            # Update rolling conversation summary (3-line max)
            if not _is_delegated:
                self._update_conversation_summary(session, message, response_text, tool_calls_this_turn)
        
        if LANGFUSE_ENABLED:
            flush()
        
        # Only root agent emits SESSION_ENDED
        if not _is_delegated:
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
    
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
    
    # =========================================================================
    # BACKGROUND WORKER - Processes items from configured Redis queues
    # =========================================================================
    
    def start_background(self) -> bool:
        """
        Start background thread to process items from configured queues.
        
        Returns:
            True if started, False if no queues configured or already running
        """
        queues = self.agent_config.get('background_queues', [])
        if not queues:
            self.logger.info(f"[{self.nickname}] No background_queues configured")
            return False
        
        if self._queue_worker_running:
            self.logger.warning(f"[{self.nickname}] Background worker already running")
            return False
        
        self._queue_worker_running = True
        self._queue_worker_thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name=f"agent-{self.agent_id}-background"
        )
        self._queue_worker_thread.start()
        self.logger.info(f"[{self.nickname}] 🚀 Background worker started, queues: {queues}")
        return True
    
    def stop_background(self):
        """Stop background worker thread"""
        if not self._queue_worker_running:
            return
        
        self._queue_worker_running = False
        if self._queue_worker_thread:
            self._queue_worker_thread.join(timeout=5)
        self.logger.info(f"[{self.nickname}] 🛑 Background worker stopped")
    
    @property
    def background_running(self) -> bool:
        """Check if background worker is running"""
        return self._queue_worker_running
    
    def _setup_redis_rest_api(self):
        """Setup Redis REST API client (uses Upstash REST API)"""
        try:
            import requests
            
            redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
            redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
            
            if not redis_url or not redis_token:
                self.logger.error(f"[{self.nickname}] Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN")
                return None
            
            # Store REST API config
            return {
                'url': redis_url,
                'headers': {
                    'Authorization': f'Bearer {redis_token}',
                    'Content-Type': 'application/json'
                }
            }
        except Exception as e:
            self.logger.error(f"[{self.nickname}] Failed to setup Redis REST API: {e}")
            return None
    
    def _redis_command(self, redis_config: dict, command: list):
        """Execute Redis command via REST API"""
        try:
            import requests
            response = requests.post(
                redis_config['url'],
                headers=redis_config['headers'],
                json=command,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"[{self.nickname}] Redis API error: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"[{self.nickname}] Redis command failed: {e}")
            return None
    
    def _background_loop(self):
        """Background loop - monitors queues and processes items"""
        try:
            print(f"[{self.nickname}] DEBUG: _background_loop thread started")
            self.logger.info(f"[{self.nickname}] DEBUG: _background_loop thread started")
            
            queues = self.agent_config.get('background_queues', [])
            print(f"[{self.nickname}] DEBUG: Queues to monitor: {queues}")
            
            redis_config = self._setup_redis_rest_api()
            print(f"[{self.nickname}] DEBUG: Redis config setup: {redis_config is not None}")
            
            if not redis_config:
                self.logger.error(f"[{self.nickname}] Cannot start background loop - no Redis")
                self._queue_worker_running = False
                return
            
            self.logger.info(f"[{self.nickname}] 🔄 Background loop started, monitoring: {queues}")
            print(f"[{self.nickname}] 🔄 Background loop started, monitoring: {queues}")
        except Exception as e:
            print(f"[{self.nickname}] FATAL ERROR in background loop startup: {e}")
            import traceback
            traceback.print_exc()
            self._queue_worker_running = False
            return
        
        # Check queue status on startup
        try:
            print(f"[{self.nickname}] DEBUG: Checking queue status...")
            for queue in queues:
                print(f"[{self.nickname}] DEBUG: Checking queue '{queue}'...")
                result = self._redis_command(redis_config, ['LLEN', queue])
                print(f"[{self.nickname}] DEBUG: LLEN result for '{queue}': {result}")
                if result and 'result' in result:
                    length = result['result']
                    print(f"[{self.nickname}] 📊 Queue '{queue}' has {length} pending items")
                    self.logger.info(f"[{self.nickname}] 📊 Queue '{queue}' has {length} pending items")
                else:
                    print(f"[{self.nickname}] WARNING: No result from LLEN for '{queue}'")
        except Exception as e:
            print(f"[{self.nickname}] ERROR checking queue status: {e}")
            import traceback
            traceback.print_exc()
            self.logger.warning(f"[{self.nickname}] Could not check queue status: {e}")
        
        try:
            while self._queue_worker_running:
                try:
                    # Poll queues in priority order (LPOP doesn't block, so we poll)
                    task_found = False
                    
                    for queue in queues:
                        result = self._redis_command(redis_config, ['LPOP', queue])
                        
                        # Always log when we get something from queue
                        if result and result.get('result'):
                            task_json = result['result']
                            print(f"[{self.nickname}] 🎯 GOT TASK from {queue}: {task_json[:100]}...")
                            
                            task = json.loads(task_json)
                            task_found = True
                            
                            task_type = task.get('type', 'unknown')
                            task_id = task.get('id', 'unknown')
                            print(f"[{self.nickname}] 📥 Processing task: type={task_type}, id={task_id}")
                            self.logger.info(f"[{self.nickname}] 📥 Task from {queue}: {task_type}")
                            self._process_background_task(task, queue)
                            print(f"[{self.nickname}] ✅ Task {task_id} processed")
                            break  # Process one task then restart loop
                    
                    # If no task found, sleep before next poll
                    if not task_found:
                        time.sleep(5)  # Poll every 5 seconds
                        
                except Exception as e:
                    if self._queue_worker_running:
                        print(f"[{self.nickname}] Background loop error: {e}")
                        self.logger.error(f"[{self.nickname}] Background loop error: {e}")
                        import traceback
                        traceback.print_exc()
                        time.sleep(5)
        except Exception as fatal_error:
            print(f"[{self.nickname}] FATAL ERROR in background loop: {fatal_error}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"[{self.nickname}] 👋 Background loop ended")
            self.logger.info(f"[{self.nickname}] 👋 Background loop ended")
    
    def _get_handler(self):
        """Get the appropriate handler based on agent type"""
        if self.agent_id == 'analyzer':
            if not self._sherlock_handler:
                self._sherlock_handler = SherlockHandler(self.nickname)
            return self._sherlock_handler
        elif self.agent_id == 'monitor':
            if not self._nightwatch_handler:
                self._nightwatch_handler = NightwatchHandler(self.nickname)
            return self._nightwatch_handler
        return None
    
    def _process_background_task(self, task: Dict[str, Any], queue_name: str):
        """Process a single background task with Socket.IO and Slack notifications"""
        task_id = 'unknown'
        is_dry_run = self.agent_config.get('dry_run', False)
        handler = self._get_handler()
        
        try:
            print(f"[{self.nickname}] 🔧 _process_background_task START (dry_run={is_dry_run})")
            print(f"[{self.nickname}] 🔧 Task keys: {list(task.keys())}")
            
            task_type = task.get('type', 'unknown')
            task_id = task.get('id', 'unknown')
            task_data = task.get('data', {})
            
            print(f"[{self.nickname}] 🔧 task_type={task_type}, task_id={task_id}")
            print(f"[{self.nickname}] 🔧 task_data keys: {list(task_data.keys())}")
            
            # DRY RUN MODE: Use Nightwatch handler
            if is_dry_run:
                if not self._nightwatch_handler:
                    self._nightwatch_handler = NightwatchHandler(self.nickname)
                self._nightwatch_handler.handle_dry_run_task(task_type, task_id, task_data, queue_name)
                return
            
            # Build message using appropriate handler
            if not handler:
                print(f"[{self.nickname}] ⚠️  No handler for agent_id={self.agent_id}")
                return
            
            # Check if handler wants to process with AI (filters: duration, rate limit, etc.)
            if hasattr(handler, 'should_process_with_ai'):
                if not handler.should_process_with_ai(task_id, task_data):
                    # Handler decided to skip AI processing (already marked in DB)
                    return
            
            print(f"[{self.nickname}] 🔧 Building task message...")
            message = handler.build_task_message(task_type, task_id, task_data)
            print(f"[{self.nickname}] 🔧 Message built: {message[:100]}...")
            
            # Create session for this task
            print(f"[{self.nickname}] 🔧 Creating session...")
            session = self._session_manager.create_session()
            session.set_context('task_id', task_id)
            session.set_context('task_type', task_type)
            session.set_context('queue_name', queue_name)
            session.set_context('is_background', True)
            print(f"[{self.nickname}] 🔧 Session created: {session.id}")
            
            # Get Socket.IO manager
            from ..socket_manager import socket_manager
            
            # Process with agent
            print(f"[{self.nickname}] 🔧 Starting async processing...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                responses = []
                
                async def process():
                    async for event in self.process_message(message, session):
                        if event.type == EventType.MESSAGE:
                            responses.append(event.content)
                        
                        # Emit event to Socket.IO
                        try:
                            event_dict = event.to_dict()
                            socket_manager.emit_to_room(
                                room='background_tasks',
                                event='agent_event',
                                data=event_dict,
                                namespace='/agent'
                            )
                            print(f"[{self.nickname}] 📡 Emitted event: {event.type} to background_tasks room")
                        except Exception as emit_error:
                            print(f"[{self.nickname}] ⚠️  Failed to emit event: {emit_error}")
                
                loop.run_until_complete(process())
                
                result = '\n'.join(responses)
                print(f"[{self.nickname}] ✅ Task {task_id} completed successfully")
                self.logger.info(f"[{self.nickname}] ✅ Task {task_id} complete")
                
                # Update handler state after successful AI processing (e.g., rate limits)
                if hasattr(handler, 'update_rate_limit'):
                    handler.update_rate_limit(task_data)
                
                # Send result to Slack via handler
                handler.send_to_slack(task_type, task_id, task_data, result)
                
            finally:
                loop.close()
                print(f"[{self.nickname}] 🔧 Event loop closed")
                
        except Exception as e:
            print(f"[{self.nickname}] ❌❌❌ TASK PROCESSING FAILED for task {task_id}")
            print(f"[{self.nickname}] ❌ Error: {e}")
            self.logger.error(f"[{self.nickname}] ❌ Task processing error: {e}")
            import traceback
            traceback.print_exc()
            print(f"[{self.nickname}] ❌❌❌ END OF ERROR")
    
