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


class QAManagerAgent:
    """
    QA Manager - Skill-Based Orchestrator with Prompt Caching
    
    Operates in two modes:
    1. Router Mode: Uses minimal tools, decides which skill to load
    2. Skill Mode: Uses tools from the loaded skill
    
    Uses Anthropic's prompt caching for 90% cost reduction on repeated calls.
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
        
        return {
            'name': metadata.name,
            'nickname': metadata.nickname or metadata.name,
            'specialty': metadata.description,
            'platform': platform or 'all',
            'skills': agent_def.skills or [],
            'available_skills': getattr(agent_def, 'available_skills', []) or [],
            'subagents': [s.id for s in (agent_def.subagents or [])],
            'background_queues': background_queues,
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

## Mode: Router

Quick queries → use router tools. Complex tasks → load a skill.

## Skills
{skill_descriptions}

## Router Tools
{tools_list}

## Rules
- Quick query → use tool directly
- Complex task → respond ONLY: `LOAD SKILL [name]`

Be concise."""
    
    def _build_skill_prompt(self, ctx: Dict[str, Any] = None) -> str:
        """Build skill mode prompt"""
        config = self.agent_config
        skill = self._active_skill
        
        return f"""You are {config['nickname']} executing **{skill.name}** skill.

{skill.system_prompt}

Tools: {', '.join(skill.tools)}

CRITICAL: Never modify URLs from tools. Copy exactly."""
    
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
        
        # Build cached system prompt and tools
        cached_system = self._build_cached_system(session.context)
        cached_tools = self._build_cached_tools(self.tool_names)
        
        print(f"[AGENT] Tools: {len(cached_tools)} | System: {len(cached_system[0]['text'])} chars")
        
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        response_text = ""
        
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
        
        # Save assistant response to session history
        if response_text:
            session.add_message("assistant", response_text, agent=self.nickname)
        
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
    
    def _get_redis_client(self):
        """Get Redis client for queue operations"""
        try:
            import redis
            
            redis_url = os.getenv('UPSTASH_REDIS_REST_URL', '')
            redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
            
            if redis_url:
                host = redis_url.replace('https://', '').replace('http://', '').split('/')[0]
                return redis.Redis(
                    host=host,
                    port=6379,
                    password=redis_token,
                    ssl=True,
                    ssl_cert_reqs=None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', '6379'))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                
                return redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
        except Exception as e:
            self.logger.error(f"[{self.nickname}] Failed to create Redis client: {e}")
            return None
    
    def _background_loop(self):
        """Background loop - monitors queues and processes items"""
        queues = self.agent_config.get('background_queues', [])
        redis_client = self._get_redis_client()
        
        if not redis_client:
            self.logger.error(f"[{self.nickname}] Cannot start background loop - no Redis")
            self._queue_worker_running = False
            return
        
        self.logger.info(f"[{self.nickname}] 🔄 Background loop started, monitoring: {queues}")
        
        while self._queue_worker_running:
            try:
                # BLPOP blocks until item arrives or timeout (60s)
                result = redis_client.blpop(queues, timeout=60)
                
                if result and self._queue_worker_running:
                    queue_name, task_json = result
                    task = json.loads(task_json)
                    
                    self.logger.info(f"[{self.nickname}] 📥 Task from {queue_name}: {task.get('type', 'unknown')}")
                    self._process_background_task(task, queue_name)
                    
            except Exception as e:
                if self._queue_worker_running:
                    self.logger.error(f"[{self.nickname}] Background loop error: {e}")
                    time.sleep(5)
        
        self.logger.info(f"[{self.nickname}] 👋 Background loop ended")
    
    def _process_background_task(self, task: Dict[str, Any], queue_name: str):
        """Process a single background task"""
        try:
            task_type = task.get('type', 'unknown')
            task_id = task.get('id', 'unknown')
            task_data = task.get('data', {})
            
            # Build message for agent based on task type
            message = self._build_task_message(task_type, task_id, task_data)
            
            # Create session for this task
            session = self._session_manager.create_session()
            session.set_context('task_id', task_id)
            session.set_context('task_type', task_type)
            session.set_context('queue_name', queue_name)
            
            # Process with agent (run async in sync context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                responses = []
                
                async def process():
                    async for event in self.process_message(message, session):
                        if event.type == EventType.MESSAGE:
                            responses.append(event.content)
                
                loop.run_until_complete(process())
                
                result = '\n'.join(responses)
                self.logger.info(f"[{self.nickname}] ✅ Task {task_id} complete")
                
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"[{self.nickname}] ❌ Task processing error: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_task_message(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """Build agent message from queue task. All data comes from queue, no DB fetch."""
        if task_type == 'script':
            script_name = task_data.get('script_name', 'Unknown')
            success = task_data.get('success', False)
            error_msg = task_data.get('error_msg', 'None')
            execution_time_ms = task_data.get('execution_time_ms', 0)
            report_url = task_data.get('html_report_r2_url', '')
            logs_url = task_data.get('logs_url', '')
            
            msg = f"""Analyze this script execution for false positive detection:

SCRIPT: {script_name}
RESULT: {'PASSED' if success else 'FAILED'}
ERROR: {error_msg}
DURATION: {execution_time_ms}ms
"""
            if report_url:
                msg += f"""
Use get_execution_result(report_url='{report_url}'"""
                if logs_url:
                    msg += f", logs_url='{logs_url}'"
                msg += ") to get the detailed report."
            
            msg += """

Classify as:
- BUG: Real application issue
- SCRIPT_ISSUE: Test/automation problem  
- SYSTEM_ISSUE: Infrastructure problem"""
            
            return msg
        
        else:
            return f"Unknown task type: {task_type}"
