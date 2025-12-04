"""
QA Manager Agent

The orchestrator that understands user intent, detects mode,
delegates to specialist agents, and reports results.
"""

import re
import logging
import uuid
from typing import Dict, Any, AsyncGenerator, Optional

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, MAX_TOKENS, Mode, MODE_AGENTS, MANAGER_TOOLS
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
    
    SYSTEM_PROMPT = """You are the QA Manager, a Senior QA Lead who orchestrates testing automation.

## Your Role
1. Understand user requests
2. **DIRECTLY ANSWER** simple questions using your tools (e.g., "how many test cases?")
3. **DELEGATE** complex tasks to specialist agents (e.g., "run regression", "fix bug")

## Your Tools (Direct Access)
You can now use these tools yourself. Do NOT delegate if you can answer directly:
- `list_testcases`: Count or list tests
- `list_userinterfaces`: See available apps
- `list_requirements`: Check requirements
- `get_coverage_summary`: Check coverage status

## Your Specialists (for complex tasks)
- **Explorer**: UI discovery, navigation tree building
- **Builder**: Test cases, requirements, coverage setup
- **Executor**: Test execution STRATEGY (devices, parallelization, retries)
- **Analyst**: Result ANALYSIS, metrics, counts, coverage reports
- **Maintainer**: Fix broken selectors, self-healing

## Operating Modes
Detect the mode from user messages:

**CREATE** - Keywords: "automate", "create", "build", "new site", "set up"
→ Delegate to Explorer (build tree) then Builder (create tests)

**VALIDATE** - Keywords: "run", "test", "validate", "regression", "execute"
→ Delegate to Executor (run tests) THEN Analyst (analyze results)

**ANALYZE** - Keywords: "analyze", "why did", "is this a bug", "investigate"
→ Delegate to Analyst (for deep analysis of failures)

**MAINTAIN** - Keywords: "fix", "repair", "broken", "update", "selector"
→ Delegate to Maintainer

## Decision Logic
1. **Can I answer this with `list_testcases` or similar?**
   → YES: Call the tool, get the result, and answer the user. DONE.
   → NO: Identify the mode and delegate to a specialist.

2. **Is this a request to run/change something?**
   → ALWAYS delegate.

## Response Format
- If answering directly: Just give the answer.
- If delegating: "Delegating to [Agent]..."

Be efficient. The user wants results."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = anthropic.Anthropic(api_key=get_anthropic_api_key())
        self.tool_bridge = ToolBridge()
        
        # Initialize specialist agents
        self.agents = {
            "explorer": ExplorerAgent(self.tool_bridge),
            "builder": BuilderAgent(self.tool_bridge),
            "executor": ExecutorAgent(self.tool_bridge),
            "analyst": AnalystAgent(self.tool_bridge),
            "maintainer": MaintainerAgent(self.tool_bridge),
        }
        
        self.logger.info("QA Manager initialized with 5 specialist agents")
    
    def detect_mode(self, message: str) -> str:
        """
        Detect operating mode from user message
        
        Returns:
            Mode.CREATE, Mode.VALIDATE, Mode.MAINTAIN, or Mode.ANALYZE
        """
        message_lower = message.lower()
        
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
                agent="QA Manager",
                content="Please respond to the pending approval first.",
            )
            return
        
        # Detect mode
        mode = self.detect_mode(message)
        session.mode = mode
        
        yield AgentEvent(
            type=EventType.MODE_DETECTED,
            agent="QA Manager",
            content=f"Mode detected: {mode}",
        )
        
        # Extract context
        extracted_context = self.extract_context(message)
        for key, value in extracted_context.items():
            session.set_context(key, value)
        
        # Use Claude to understand and plan
        yield AgentEvent(
            type=EventType.THINKING,
            agent="QA Manager",
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
        
        # Tool Use Loop
        while True:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=turn_messages,
                tools=tools
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
                    agent="QA Manager",
                    tool_name=tool_use.name,
                    tool_params=tool_use.input
                )
                
                # Execute tool
                try:
                    result = self.tool_bridge.execute(tool_use.name, tool_use.input)
                    
                    yield AgentEvent(
                        type=EventType.TOOL_RESULT,
                        agent="QA Manager",
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
                    yield AgentEvent(
                        type=EventType.ERROR,
                        agent="QA Manager",
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
                    agent="QA Manager",
                    content=plan,
                )
                break
        
        # Decision: Delegate or Finish?
        # If we used tools AND we are in ANALYZE mode, we likely answered directly.
        # Unless the plan explicitly says "Delegating..."
        should_delegate = True
        if tools_used and mode == Mode.ANALYZE and "delegating" not in plan.lower():
            should_delegate = False
            
        if not should_delegate:
             yield AgentEvent(type=EventType.SESSION_ENDED, agent="QA Manager", content="Task completed")
             return
        
        # Delegate to appropriate agents
        agents_to_use = MODE_AGENTS.get(mode, ["explorer"])
        
        for agent_name in agents_to_use:
            agent = self.agents.get(agent_name)
            if not agent:
                continue
            
            session.active_agent = agent_name
            
            yield AgentEvent(
                type=EventType.AGENT_DELEGATED,
                agent="QA Manager",
                content=f"Delegating to {agent.name} agent...",
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
                        agent="QA Manager",
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
                        agent="QA Manager",
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
                    agent="QA Manager",
                    content="Execution complete. Passing results to Analyst for analysis...",
                )
            
            yield AgentEvent(
                type=EventType.AGENT_COMPLETED,
                agent="QA Manager",
                content=f"{agent.name} agent completed",
            )
        
        # Final summary
        session.active_agent = None
        
        yield AgentEvent(
            type=EventType.MESSAGE,
            agent="QA Manager",
            content=self._generate_summary(session),
        )
        
        yield AgentEvent(
            type=EventType.SESSION_ENDED,
            agent="QA Manager",
            content="Task completed",
        )
    
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
                agent="QA Manager",
                content="No pending approval",
            )
            return
        
        approval = session.pending_approval
        session.clear_approval()
        
        yield AgentEvent(
            type=EventType.APPROVAL_RECEIVED,
            agent="QA Manager",
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
                agent="QA Manager",
                content="Action cancelled. What would you like to do instead?",
            )

