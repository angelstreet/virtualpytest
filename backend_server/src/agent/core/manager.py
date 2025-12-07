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

1. **Use your tools first** - If you have the tool, use it.
2. **Delegate if you lack the tool** - Say exactly: `DELEGATE TO [agent_id]`

Examples:
- "How many test cases?" → Use `list_testcases`, report count
- "Navigate to home on device X" → You lack `navigate_to_node` → `DELEGATE TO explorer`
- "Run test TC_001" → You lack `execute_testcase` → `DELEGATE TO executor`

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
        
        # Sub-agents loaded dynamically from YAML (not hardcoded)
        self._sub_agents = {}
        
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
    
    def _get_sub_agent(self, agent_id: str):
        """Lazy-load sub-agent when needed"""
        if agent_id in self._sub_agents:
            return self._sub_agents[agent_id]
        
        # Import and create based on agent_id
        # These are the actual implementation classes
        agent_classes = {
            'explorer': ('..agents.explorer', 'ExplorerAgent'),
            'builder': ('..agents.builder', 'BuilderAgent'),
            'executor': ('..agents.executor', 'ExecutorAgent'),
            'analyst': ('..agents.analyst', 'AnalystAgent'),
            'maintainer': ('..agents.maintainer', 'MaintainerAgent'),
        }
        
        if agent_id not in agent_classes:
            self.logger.error(f"Unknown sub-agent: {agent_id}")
            return None
        
        module_path, class_name = agent_classes[agent_id]
        try:
            import importlib
            module = importlib.import_module(module_path, package=__name__.rsplit('.', 1)[0])
            agent_class = getattr(module, class_name)
            self._sub_agents[agent_id] = agent_class(self.tool_bridge, api_key=self._get_api_key_safe())
            return self._sub_agents[agent_id]
        except Exception as e:
            self.logger.error(f"Failed to load sub-agent {agent_id}: {e}")
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
        match = re.search(r'DELEGATE\s+TO\s+(\w+)', text, re.IGNORECASE)
        return match.group(1).lower() if match else None

    async def process_message(self, message: str, session: Session) -> AsyncGenerator[AgentEvent, None]:
        """Process user message - YAML-driven"""
        self.logger.info(f"Processing: {message[:100]}...")
        
        if not self.api_key_configured:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="⚠️ API key not configured.")
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Session ended")
            return
        
        # Context window compaction
        if session.needs_compaction(threshold=50):
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
        
        session.add_message("user", message)
        
        if session.pending_approval:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="Respond to pending approval first.")
            return
        
        yield AgentEvent(type=EventType.THINKING, agent=self.nickname, content="Analyzing...")
        
        # Simple prompt - Claude decides based on tools
        prompt = f"""User: {message}

Use your tools if you have them. Otherwise say: DELEGATE TO [agent_id]"""
        
        turn_messages = [{"role": "user", "content": prompt}]
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
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}]})
                except Exception as e:
                    if LANGFUSE_ENABLED:
                        track_tool_call(self.nickname, tool_use.name, tool_use.input, str(e), False, session.id)
                    yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Tool error: {e}", error=str(e))
                    turn_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Error: {e}", "is_error": True}]})
            else:
                response_text = text_content
                yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content=response_text, metrics=metrics)
                break
        
        # Check for delegation request
        delegate_to = self._parse_delegation(response_text)
        
        if not delegate_to:
            # No delegation - we're done
            if LANGFUSE_ENABLED:
                flush()
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        # Validate sub-agent is in our YAML config
        if delegate_to not in self.agent_config['subagents']:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Cannot delegate to '{delegate_to}' - not in my sub-agents: {self.agent_config['subagents']}")
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        # Get sub-agent
        sub_agent = self._get_sub_agent(delegate_to)
        if not sub_agent:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content=f"Failed to load sub-agent: {delegate_to}")
            yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
            return
        
        session.active_agent = delegate_to
        
        yield AgentEvent(type=EventType.AGENT_DELEGATED, agent=self.nickname, content=f"Delegating to {sub_agent.name}...")
        yield AgentEvent(type=EventType.AGENT_STARTED, agent=sub_agent.name, content=f"{sub_agent.name} starting...")
        
        # Run sub-agent with original message
        async for event in sub_agent.run(message, session.context):
            if session.cancelled:
                yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="🛑 Stopped by user.")
                session.reset_cancellation()
                return
            
            yield AgentEvent(
                type=EventType(event.get("type", "thinking")),
                agent=event.get("agent", delegate_to),
                content=event.get("content", ""),
                tool_name=event.get("tool"),
                tool_params=event.get("params"),
                tool_result=event.get("result"),
                success=event.get("success"),
                error=event.get("error"),
                metrics=event.get("metrics"),
            )
            
            if event.get("type") == "approval_required":
                approval = ApprovalRequest(
                    id=str(uuid.uuid4()),
                    agent=delegate_to,
                    action=event.get("action", "Unknown"),
                    options=event.get("options", ["approve", "reject"]),
                    context=event.get("context", {}),
                )
                session.request_approval(approval)
                yield AgentEvent(type=EventType.APPROVAL_REQUIRED, agent=self.nickname, content="Approval needed", approval_id=approval.id, approval_options=approval.options)
                return
            
            if event.get("type") == "result":
                result = event.get("content", {})
                session.add_result(delegate_to, result)
                if isinstance(result, dict):
                    for key in ["tree_id", "exploration_id", "testcase_ids"]:
                        if key in result:
                            session.set_context(key, result[key])
        
        yield AgentEvent(type=EventType.AGENT_COMPLETED, agent=sub_agent.name, content="Completed")
        
        session.active_agent = None
        yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Done")
        
        if LANGFUSE_ENABLED:
            flush()
    
    async def handle_approval(self, session: Session, approved: bool, modifications: Dict[str, Any] = None) -> AsyncGenerator[AgentEvent, None]:
        """Handle approval response"""
        if not session.pending_approval:
            yield AgentEvent(type=EventType.ERROR, agent=self.nickname, content="No pending approval")
            return
        
        approval = session.pending_approval
        session.clear_approval()
        
        yield AgentEvent(type=EventType.APPROVAL_RECEIVED, agent=self.nickname, content=f"Approval {'granted' if approved else 'rejected'}")
        
        if approved:
            agent = self._get_sub_agent(approval.agent)
            if agent:
                if modifications:
                    for k, v in modifications.items():
                        session.set_context(k, v)
                
                async for event in agent.run(f"Continue: {approval.action}", session.context):
                    yield AgentEvent(type=EventType(event.get("type", "thinking")), agent=event.get("agent", approval.agent), content=event.get("content", ""))
        else:
            yield AgentEvent(type=EventType.MESSAGE, agent=self.nickname, content="Cancelled. What next?")
