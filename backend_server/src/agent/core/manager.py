"""
QA Manager Agent

The orchestrator that understands user intent, detects mode,
delegates to specialist agents, and reports results.
"""

import re
import logging
import uuid
import time
from typing import Dict, Any, AsyncGenerator, Optional

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, MAX_TOKENS, Mode, MODE_AGENTS, MANAGER_TOOLS, LANGFUSE_ENABLED
from ..observability import track_generation, track_tool_call, flush
from .session import Session
from .tool_bridge import ToolBridge
from .message_types import EventType, AgentEvent, ApprovalRequest
from ..agents.explorer import ExplorerAgent
from ..agents.builder import BuilderAgent
from ..agents.executor import ExecutorAgent
from ..agents.analyst import AnalystAgent
from ..agents.maintainer import MaintainerAgent


class QAManagerAgent:
    """
    QA Manager - The Orchestrator
    
    - Understands user requests
    - Detects operating mode (CREATE/VALIDATE/MAINTAIN)
    - Delegates to specialist agents
    - Handles approvals
    - Reports results
    """
    
    BASE_SYSTEM_PROMPT = """You are {agent_name}, {agent_specialty}.

## Your Identity
- **Name**: {agent_nickname}
- **Specialty**: {specialty}
- **Platform Focus**: {platform}
- **Key Areas**: {focus_areas}

## Current Context
- **Auto-Navigation Enabled**: {allow_auto_navigation}
- **User's Current Page**: {current_page}

## CRITICAL: CONCISENESS
- **Be extremely concise.** Users are busy engineers.
- Direct answers only. No fluff.
- **MAXIMUM 2 SENTENCES** for simple queries after presenting data.

## 2-STEP WORKFLOW

### STEP 1: NAVIGATION (ONLY if auto-navigation is enabled)

**⚠️ IMPORTANT: allow_auto_navigation = {allow_auto_navigation}**

**IF allow_auto_navigation is FALSE → DO NOT call navigate_to_page. Skip directly to Step 2.**

Only call `navigate_to_page()` if ALL of these are true:
1. `allow_auto_navigation` is `true`
2. User is NOT already on the target page
3. Request relates to a specific page

### STEP 2: DATA FETCHING (MANDATORY for data queries)

**Skip Step 2 ONLY if:**
- Request is purely navigation ("go to X", "open X page", "take me to X")

**ALWAYS Execute Step 2 for data queries:**
- "how many alerts?" → call `get_alerts()` and report the numbers
- "list test cases" → call `list_testcases()` and report the data
- "show devices" → call `get_device_info()` and report

**NEVER say "you can see it on the page" - USE TOOLS to fetch actual data!**

### REQUEST CLASSIFICATION

| Request Type | Step 1 | Step 2 |
|--------------|--------|--------|
| "go to incidents" | ✅ Navigate | ❌ Skip |
| "how many alerts?" | ✅ Navigate (if enabled) | ✅ `get_alerts()` |
| "show active alerts" | ✅ Navigate (if enabled) | ✅ `get_alerts(status="active")` |
| "list test cases" | ✅ Navigate (if enabled) | ✅ `list_testcases()` |

## Your Tools

**⚠️ CRITICAL: You can ONLY use tools from this exact list. Do NOT invent or guess tool names!**
**If a tool doesn't exist, you will get an error. There is NO `list_navigation_trees` tool - use `list_userinterfaces` instead.**

### Navigation (STEP 1)
- `navigate_to_page`: Navigate browser to: dashboard, device control, incidents, heatmap, reports, test cases, settings

### Data Tools (STEP 2 - fetch actual data)
- `get_alerts`: Fetch alert counts and details. **USE THIS for alert/incident questions!**
- `list_testcases`: Count or list tests
- `list_userinterfaces`: See available apps (returns `root_tree_id` for each - use this to get tree IDs!)
- `list_requirements`: Check requirements
- `get_coverage_summary`: Check coverage status
- `get_device_info`: Get device information
- `list_navigation_nodes`: List nodes in a tree (needs `tree_id` from `list_userinterfaces`)

## Examples

**Example 1**: "How many alerts?" (auto-navigation OFF)
- Step 1: SKIP (auto-navigation is disabled)
- Step 2: `get_alerts()` → "12 active alerts, 100 resolved (112 total)"

**Example 2**: "How many alerts?" (auto-navigation ON)
- Step 1: `navigate_to_page("incidents")`
- Step 2: `get_alerts()` → "12 active alerts, 100 resolved (112 total)"

**Example 3**: "Show active alerts"
- Step 1: Skip if auto-navigation OFF, otherwise navigate
- Step 2: `get_alerts(status="active")` → List the active alerts

**Example 4**: "List all test cases"
- Step 1: Skip if auto-navigation OFF
- Step 2: `list_testcases()` → Report the test case data

## Your Specialists (for complex tasks)
- **Explorer**: UI discovery, navigation tree building
- **Builder**: Test cases, requirements, coverage setup
- **Executor**: Test execution (devices, parallelization, retries)
- **Analyst**: Result analysis, metrics, coverage reports
- **Maintainer**: Fix broken selectors, self-healing

Be efficient. Provide DATA, not explanations."""

    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Get the system prompt customized for the selected agent and context"""
        config = self.agent_config
        ctx = context or {}
        
        # Get navigation context with defaults
        allow_auto_nav = ctx.get('allow_auto_navigation', False)
        current_page = ctx.get('current_page', '/')
        
        return self.BASE_SYSTEM_PROMPT.format(
            agent_name=config['name'],
            agent_nickname=config['nickname'],
            agent_specialty=config['specialty'],
            specialty=config['specialty'],
            platform=config['platform'],
            focus_areas=', '.join(config['focus_areas']),
            allow_auto_navigation=str(allow_auto_nav).lower(),
            current_page=current_page,
        )

    def __init__(self, api_key: Optional[str] = None, user_identifier: Optional[str] = None, agent_id: Optional[str] = None):
        """
        Initialize QA Manager
        
        Args:
            api_key: Optional API key to use (overrides environment)
            user_identifier: Optional user/session identifier for retrieving stored API key
            agent_id: Selected agent ID for specialized behavior
        """
        self.logger = logging.getLogger(__name__)
        self.user_identifier = user_identifier
        self._api_key = api_key
        self._client = None
        self.tool_bridge = ToolBridge()
        
        # Load agent config from registry (YAML source of truth)
        self.agent_id = agent_id or 'ai-assistant'
        self.agent_config = self._load_agent_config(self.agent_id)
        
        # Initialize specialist agents (pass API key to each)
        self.agents = {
            "explorer": ExplorerAgent(self.tool_bridge, api_key=self._get_api_key_safe()),
            "builder": BuilderAgent(self.tool_bridge, api_key=self._get_api_key_safe()),
            "executor": ExecutorAgent(self.tool_bridge, api_key=self._get_api_key_safe()),
            "analyst": AnalystAgent(self.tool_bridge, api_key=self._get_api_key_safe()),
            "maintainer": MaintainerAgent(self.tool_bridge, api_key=self._get_api_key_safe()),
        }
        
        self.logger.info(f"QA Manager initialized as {self.agent_config['nickname']} ({self.agent_id}) with 5 specialist agents")
    
    def _load_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Load agent config from YAML registry"""
        from ..registry import get_agent_registry
        
        registry = get_agent_registry()
        agent_def = registry.get(agent_id)
        
        if not agent_def:
            raise ValueError(f"Agent '{agent_id}' not found in registry. Check YAML templates.")
        
        # Convert AgentDefinition to config dict for system prompt
        metadata = agent_def.metadata
        config = agent_def.config
        
        # Access Pydantic model attributes (not dict)
        platform = config.platform_filter if config else None
        
        return {
            'name': metadata.name,
            'nickname': metadata.nickname or metadata.name,
            'specialty': metadata.description,
            'platform': platform or 'all',
            'focus_areas': metadata.tags or [],
            'skills': agent_def.skills or [],
            'subagents': [s.id for s in (agent_def.subagents or [])],
        }
    
    @property
    def nickname(self) -> str:
        """Get the display name for events"""
        return self.agent_config['nickname']
    
    def _get_api_key_safe(self) -> Optional[str]:
        """Get API key safely without raising exceptions"""
        try:
            if self._api_key:
                return self._api_key
            return get_anthropic_api_key(identifier=self.user_identifier)
        except ValueError:
            return None
    
    @property
    def client(self):
        """Lazy-load Anthropic client"""
        if self._client is None:
            key = self._get_api_key_safe()
            if not key:
                raise ValueError("ANTHROPIC_API_KEY not configured. Please set your API key.")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client
    
    @property
    def api_key_configured(self) -> bool:
        """Check if API key is configured"""
        return self._get_api_key_safe() is not None
    
    def detect_mode(self, message: str) -> str:
        """
        Detect operating mode from user message
        
        Returns:
            Mode.CREATE, Mode.VALIDATE, Mode.MAINTAIN, or Mode.ANALYZE
        """
        message_lower = message.lower()
        
        # NAVIGATE indicators - handle UI navigation requests directly (no delegation)
        navigate_keywords = ["go to", "navigate to", "take me to", "show me the", "open the"]
        if any(kw in message_lower for kw in navigate_keywords):
            return Mode.ANALYZE  # Use ANALYZE so manager handles directly with navigate_to_page tool
        
        # CREATE indicators (must be explicit - don't default to this)
        create_keywords = ["automate", "create new", "build", "new site", "set up", 
                         "discover", "explore", "navigation tree", "start exploration"]
        if any(kw in message_lower for kw in create_keywords):
            return Mode.CREATE
        
        # MAINTAIN indicators  
        maintain_keywords = ["fix", "repair", "broken", "update selector", 
                           "selector changed", "not working", "failed edge"]
        if any(kw in message_lower for kw in maintain_keywords):
            return Mode.MAINTAIN
        
        # VALIDATE indicators (run + analyze)
        validate_keywords = ["run test", "execute test", "validate", "regression", 
                           "run all", "execute all"]
        if any(kw in message_lower for kw in validate_keywords):
            return Mode.VALIDATE
        
        # ANALYZE indicators (queries, analysis, info retrieval)
        # This is the default for information queries
        analyze_keywords = ["analyze", "analysis", "why did", "root cause", 
                          "is this a bug", "check jira", "review results",
                          "what failed", "investigate", 
                          # Simple query words
                          "how many", "count", "list", "show me", "what are",
                          "tell me", "get", "find", "search", "coverage",
                          "requirements", "testcase", "test case"]
        if any(kw in message_lower for kw in analyze_keywords):
            return Mode.ANALYZE
        
        # Default to ANALYZE for simple queries (safer than CREATE)
        return Mode.ANALYZE
    
    def extract_context(self, message: str) -> Dict[str, Any]:
        """Extract context information from user message"""
        context = {}
        
        # Extract userinterface name (common patterns)
        ui_patterns = [
            r"userinterface[:\s]+([a-zA-Z0-9_-]+)",
            r"for\s+([a-zA-Z0-9_-]+)\s+userinterface",
            r"using\s+([a-zA-Z0-9_-]+)",
        ]
        for pattern in ui_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                context["userinterface_name"] = match.group(1)
                break
        
        # Extract URL if present
        url_match = re.search(r"https?://[^\s]+", message)
        if url_match:
            context["url"] = url_match.group(0)
        
        return context
    
    @property
    def tool_names(self) -> list[str]:
        """Tools available to the QA Manager"""
        return MANAGER_TOOLS

    async def process_message(
        self, 
        message: str, 
        session: Session
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Process a user message
        
        Args:
            message: User's message
            session: Current session
            
        Yields:
            AgentEvent objects for frontend
        """
        self.logger.info(f"Processing message: {message[:100]}...")
        
        # Check if API key is configured
        if not self.api_key_configured:
            yield AgentEvent(
                type=EventType.ERROR,
                agent=self.nickname,
                content="⚠️ API key not configured. Please enter your Anthropic API key to continue.",
            )
            yield AgentEvent(
                type=EventType.SESSION_ENDED,
                agent=self.nickname,
                content="Session ended - API key required",
            )
            return
        
        # Check for context window compaction
        if session.needs_compaction(threshold=50):
            yield AgentEvent(
                type=EventType.THINKING,
                agent="System",
                content="Compacting conversation history to save memory...",
            )
            
            msgs_to_summary = session.get_messages_for_summary()
            if msgs_to_summary:
                # Filter keys for API
                api_messages = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in msgs_to_summary
                ]
                
                summary_prompt = "Summarize the key actions, test results, errors, and context from this conversation history. Be concise but preserve critical details like IDs, selectors, and failure reasons."
                
                try:
                    summary_response = self.client.messages.create(
                        model=DEFAULT_MODEL,
                        max_tokens=1024,
                        messages=[
                            *api_messages,
                            {"role": "user", "content": summary_prompt}
                        ]
                    )
                    summary_text = summary_response.content[0].text
                    session.apply_summary(summary_text)
                    
                    yield AgentEvent(
                        type=EventType.MESSAGE,
                        agent="System",
                        content="🧹 Conversation history compacted.",
                    )
                except Exception as e:
                    self.logger.error(f"Compaction failed: {e}")

        # Add user message to session
        session.add_message("user", message)
        
        # Check for pending approval response
        if session.pending_approval:
            yield AgentEvent(
                type=EventType.ERROR,
                agent=self.nickname,
                content="Please respond to the pending approval first.",
            )
            return
        
        # Detect mode
        mode = self.detect_mode(message)
        session.mode = mode
        
        yield AgentEvent(
            type=EventType.MODE_DETECTED,
            agent=self.nickname,
            content=f"Mode detected: {mode}",
        )
        
        # Extract context
        extracted_context = self.extract_context(message)
        for key, value in extracted_context.items():
            session.set_context(key, value)
        
        # Use Claude to understand and plan
        yield AgentEvent(
            type=EventType.THINKING,
            agent=self.nickname,
            content="Analyzing your request...",
        )
        
        # Get manager's response with Hybrid Tool Loop
        planning_prompt = f"""User request: {message}
        
        Detected mode: {mode}
        Extracted context: {extracted_context}
        
        Based on this request:
        1. If it's a simple query (list/count), use your tools directly.
        2. If it's complex, delegate to a specialist.
        
        Respond with tool use OR a brief plan."""

        # Message history for this turn (to support tool use loop)
        turn_messages = [{"role": "user", "content": planning_prompt}]
        tools = self.tool_bridge.get_tool_definitions(self.tool_names)
        
        plan = ""
        tools_used = False
        
        # Ensure session_id is in context for Langfuse tracking
        if "session_id" not in session.context:
            session.set_context("session_id", session.id)
        
        # Tool Use Loop
        while True:
            start_time = time.time()
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1024,
                system=self.get_system_prompt(session.context),  # Agent-specific prompt with navigation context
                messages=turn_messages,
                tools=tools
            )
            duration_ms = int((time.time() - start_time) * 1000)
            metrics = {
                "duration_ms": duration_ms,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
            
            # Track with Langfuse if enabled
            if LANGFUSE_ENABLED:
                track_generation(
                    agent_name=self.nickname,
                    model=DEFAULT_MODEL,
                    messages=turn_messages,
                    response=response,
                    session_id=session.id,
                    user_id=session.context.get("user_id"),
                )
            
            # Add assistant response to history
            turn_messages.append({"role": "assistant", "content": response.content})
            
            # Process response
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            text_content = next((b.text for b in response.content if b.type == "text"), "")
            
            if tool_use:
                tools_used = True
                # Yield tool call event
                yield AgentEvent(
                    type=EventType.TOOL_CALL,
                    agent=self.nickname,
                    content=f"Calling tool: {tool_use.name}",
                    tool_name=tool_use.name,
                    tool_params=tool_use.input,
                    metrics=metrics
                )
                
                # Execute tool with validation
                try:
                    result = self.tool_bridge.execute(tool_use.name, tool_use.input, allowed_tools=self.tool_names)
                    
                    # Track tool call with Langfuse
                    if LANGFUSE_ENABLED:
                        track_tool_call(
                            agent_name=self.nickname,
                            tool_name=tool_use.name,
                            tool_input=tool_use.input,
                            tool_output=result,
                            success=True,
                            session_id=session.id,
                        )
                    
                    yield AgentEvent(
                        type=EventType.TOOL_RESULT,
                        agent=self.nickname,
                        content="Tool execution successful",
                        tool_name=tool_use.name,
                        tool_result=result,
                        success=True
                    )
                    
                    # Add result to history
                    turn_messages.append({
                        "role": "user", 
                        "content": [
                            {"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}
                        ]
                    })
                    
                except Exception as e:
                    # Track failed tool call with Langfuse
                    if LANGFUSE_ENABLED:
                        track_tool_call(
                            agent_name=self.nickname,
                            tool_name=tool_use.name,
                            tool_input=tool_use.input,
                            tool_output=str(e),
                            success=False,
                            session_id=session.id,
                        )
                    
                    yield AgentEvent(
                        type=EventType.ERROR,
                        agent=self.nickname,
                        content=f"Tool error: {str(e)}",
                        error=str(e)
                    )
                    turn_messages.append({
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Error: {str(e)}", "is_error": True}
                        ]
                    })
            else:
                # No tool use - final answer or plan
                plan = text_content
                yield AgentEvent(
                    type=EventType.MESSAGE,
                    agent=self.nickname,
                    content=plan,
                    metrics=metrics
                )
                break
        
        # Decision: Delegate or Finish?
        # If we used tools AND we are in ANALYZE mode, we likely answered directly.
        # Unless the plan explicitly says "Delegating..."
        should_delegate = True
        if tools_used and mode == Mode.ANALYZE and "delegating" not in plan.lower():
            should_delegate = False
            
        if not should_delegate:
             # Flush Langfuse before returning
             if LANGFUSE_ENABLED:
                 flush()
             yield AgentEvent(type=EventType.SESSION_ENDED, agent=self.nickname, content="Task completed")
             return
        
        # Delegate to appropriate agents
        agents_to_use = MODE_AGENTS.get(mode, ["explorer"])
        
        for agent_name in agents_to_use:
            agent = self.agents.get(agent_name)
            if not agent:
                continue
            
            session.active_agent = agent_name
            
            # 1. QA Manager says it's delegating (completes QA Manager's message)
            yield AgentEvent(
                type=EventType.AGENT_DELEGATED,
                agent=self.nickname,
                content=f"Delegating to {agent.name}...",
            )
            
            # 2. New agent starts (frontend creates new message bubble)
            yield AgentEvent(
                type=EventType.AGENT_STARTED,
                agent=agent.name,
                content=f"{agent.name} starting...",
            )
            
            # Build task for agent (pass agent_name for context-aware task building)
            task = self._build_agent_task(message, mode, session.context, agent_name)
            
            # Run agent and stream events
            agent_result = None
            async for event in agent.run(task, session.context):
                # Check for cancellation
                if session.cancelled:
                    yield AgentEvent(
                        type=EventType.ERROR,
                        agent=self.nickname,
                        content="🛑 Operation stopped by user."
                    )
                    session.reset_cancellation()
                    return

                # Convert dict to AgentEvent
                yield AgentEvent(
                    type=EventType(event.get("type", "thinking")),
                    agent=event.get("agent", agent_name),
                    content=event.get("content", ""),
                    tool_name=event.get("tool"),
                    tool_params=event.get("params"),
                    tool_result=event.get("result"),
                    success=event.get("success"),
                    error=event.get("error"),
                    metrics=event.get("metrics"),
                )
                
                # Check if approval needed
                if event.get("type") == "approval_required":
                    approval = ApprovalRequest(
                        id=str(uuid.uuid4()),
                        agent=agent_name,
                        action=event.get("action", "Unknown action"),
                        options=event.get("options", ["approve", "reject"]),
                        context=event.get("context", {}),
                    )
                    session.request_approval(approval)
                    
                    yield AgentEvent(
                        type=EventType.APPROVAL_REQUIRED,
                        agent=self.nickname,
                        content="Approval needed to continue",
                        approval_id=approval.id,
                        approval_options=approval.options,
                    )
                    return  # Wait for approval
                
                # Update context with results
                if event.get("type") == "result":
                    result = event.get("content", {})
                    agent_result = result
                    session.add_result(agent_name, result)
                    
                    # Extract useful context from result
                    if isinstance(result, dict):
                        for key in ["tree_id", "exploration_id", "testcase_ids"]:
                            if key in result:
                                session.set_context(key, result[key])
            
            # Pass Executor results to Analyst (for VALIDATE mode)
            if agent_name == "executor" and mode == Mode.VALIDATE:
                session.set_context("execution_results", agent_result)
                yield AgentEvent(
                    type=EventType.MESSAGE,
                    agent=self.nickname,
                    content="Execution complete. Passing results to Analyst for analysis...",
                )
            
            # 3. Sub-agent completes (frontend closes sub-agent's message bubble)
            yield AgentEvent(
                type=EventType.AGENT_COMPLETED,
                agent=agent.name,
                content=f"Completed",
            )
        
        # Final summary
        session.active_agent = None
        
        yield AgentEvent(
            type=EventType.MESSAGE,
            agent=self.nickname,
            content=self._generate_summary(session),
        )
        
        yield AgentEvent(
            type=EventType.SESSION_ENDED,
            agent=self.nickname,
            content="Task completed",
        )
        
        # Flush Langfuse data to ensure it's sent
        if LANGFUSE_ENABLED:
            flush()
    
    def _build_agent_task(
        self, 
        original_message: str, 
        mode: str, 
        context: Dict[str, Any],
        agent_name: str = None
    ) -> str:
        """Build task description for specialist agent"""
        
        if mode == Mode.CREATE:
            return f"""Build a navigation tree and tests for this request:

{original_message}

Steps:
1. Use get_compatible_hosts to find a device
2. Use start_ai_exploration to discover UI
3. Approve the exploration plan
4. Validate all edges
5. Report what was created"""

        elif mode == Mode.VALIDATE:
            # Different tasks for Executor vs Analyst
            if agent_name == "executor":
                return f"""Execute tests with optimal strategy:

{original_message}

Steps:
1. Find best available devices (get_compatible_hosts)
2. Plan execution order for efficiency
3. Take control and execute tests
4. Apply retry strategy on failures
5. Return RAW results (pass/fail, duration, errors, screenshots)

Do NOT analyze results - just execute and report raw data."""

            elif agent_name == "analyst":
                # Get execution results from context
                execution_results = context.get("execution_results", {})
                return f"""Analyze these test execution results:

{original_message}

Execution Results:
{execution_results}

Steps:
1. Review each failure
2. Classify: REAL BUG vs UI CHANGE vs FLAKY vs ENVIRONMENT
3. Check if known issue (patterns, history)
4. Recommend action (create Jira, update test, retry, etc.)
5. Provide root cause analysis

Return structured analysis with classifications and recommendations."""

        elif mode == Mode.MAINTAIN:
            return f"""Fix the broken test/selector:

{original_message}

Steps:
1. Identify what's broken
2. Analyze current screen
3. Find new selector
4. Update and test
5. Report what was fixed"""

        elif mode == Mode.ANALYZE:
            # Simple queries (count, list, how many) - just answer directly
            simple_keywords = ["how many", "count", "list", "show", "what are", "total"]
            is_simple_query = any(kw in original_message.lower() for kw in simple_keywords)
            
            if is_simple_query:
                return f"""Answer this simple query directly:

{original_message}

IMPORTANT: This is a simple information request. 
- Just provide the answer concisely
- Do NOT analyze failures or provide recommendations
- Do NOT load individual test cases unless specifically asked
- If asked "how many", just call list_testcases and count them
- Keep your response SHORT (under 100 words)"""
            
            # Complex analysis queries
            return f"""Analyze test results or failures:

{original_message}

Steps:
1. Review the failures/results mentioned
2. Classify each: REAL BUG vs UI CHANGE vs FLAKY vs ENVIRONMENT
3. Check for patterns and known issues
4. Determine root cause
5. Recommend actions (create Jira, fix test, investigate further)

Provide clear classifications and actionable recommendations."""

        return original_message
    
    def _generate_summary(self, session: Session) -> str:
        """Generate session summary - brief, no duplication"""
        if not session.results:
            return ""
        
        # Just indicate completion, don't repeat results
        agents_used = [r.get("agent", "Agent") for r in session.results]
        return f"✓ Completed by {', '.join(agents_used)}"
    
    async def handle_approval(
        self, 
        session: Session, 
        approved: bool, 
        modifications: Dict[str, Any] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Handle approval response
        
        Args:
            session: Current session
            approved: Whether user approved
            modifications: Any user modifications
            
        Yields:
            AgentEvent objects
        """
        if not session.pending_approval:
            yield AgentEvent(
                type=EventType.ERROR,
                agent=self.nickname,
                content="No pending approval",
            )
            return
        
        approval = session.pending_approval
        session.clear_approval()
        
        yield AgentEvent(
            type=EventType.APPROVAL_RECEIVED,
            agent=self.nickname,
            content=f"Approval {'granted' if approved else 'rejected'}",
        )
        
        if approved:
            # Continue with the agent's task
            agent_name = approval.agent
            agent = self.agents.get(agent_name)
            
            if agent:
                # Apply modifications if any
                if modifications:
                    for key, value in modifications.items():
                        session.set_context(key, value)
                
                # Continue agent execution
                continue_task = f"Continue with approved action: {approval.action}"
                
                async for event in agent.run(continue_task, session.context):
                    yield AgentEvent(
                        type=EventType(event.get("type", "thinking")),
                        agent=event.get("agent", agent_name),
                        content=event.get("content", ""),
                    )
        else:
            yield AgentEvent(
                type=EventType.MESSAGE,
                agent=self.nickname,
                content="Action cancelled. What would you like to do instead?",
            )

