"""
Base Agent Class

Common functionality for all specialist agents.
Uses Anthropic Prompt Caching to reduce token costs on repeated requests.
Integrates with Langfuse for optional observability (auto-enabled when LANGFUSE_HOST is set).
"""

import logging
import time
from typing import Dict, Any, List, AsyncGenerator
from abc import ABC, abstractmethod

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, MAX_TOKENS, LANGFUSE_ENABLED
from ..observability import track_generation, track_tool_call, flush


class BaseAgent(ABC):
    """Base class for all specialist agents"""
    
    def __init__(self, tool_bridge: 'ToolBridge', api_key: str = None):
        """
        Initialize the base agent.
        
        Args:
            tool_bridge: Tool bridge for executing tools
            api_key: Optional API key (if None, client will be initialized lazily)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tool_bridge = tool_bridge
        self._api_key = api_key
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Anthropic client - only created when needed"""
        if self._client is None:
            if self._api_key:
                self._client = anthropic.Anthropic(api_key=self._api_key)
            else:
                # Try to get from environment
                key = get_anthropic_api_key(identifier=None)
                self._client = anthropic.Anthropic(api_key=key)
        return self._client
    
    def set_api_key(self, api_key: str):
        """Set/update the API key and reset client"""
        self._api_key = api_key
        self._client = None  # Reset to force re-creation with new key
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name"""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent system prompt"""
        pass
    
    @property
    @abstractmethod
    def tool_names(self) -> List[str]:
        """List of tool names this agent can use"""
        pass
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for this agent"""
        return self.tool_bridge.get_tool_definitions(self.tool_names)
    
    async def run(
        self, 
        task: str, 
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent on a task
        
        Args:
            task: The task description
            context: Additional context (tree_id, exploration_id, etc.)
            
        Yields:
            Event dictionaries with type and content
        """
        self.logger.info(f"[{self.name}] Starting task: {task[:100]}...")
        
        # Build messages
        messages = [{"role": "user", "content": task}]
        
        # Add context to task if provided
        if context:
            context_str = "\n\nContext:\n" + "\n".join(
                f"- {k}: {v}" for k, v in context.items()
            )
            messages[0]["content"] += context_str
        
        # Get tools
        tools = self.get_tools()
        
        # Yield thinking event
        yield {
            "type": "thinking",
            "agent": self.name,
            "content": f"Analyzing your request..."
        }
        
        # Prepare system prompt with caching (reduces cost on subsequent requests)
        # Cache control tells Anthropic to cache this large static content
        system_with_cache = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        
        # Add cache control to the last tool (Anthropic caches tools up to and including marked tool)
        tools_with_cache = None
        if tools:
            tools_with_cache = tools.copy()
            if tools_with_cache:
                # Mark last tool for caching - this caches ALL tools
                tools_with_cache[-1] = {
                    **tools_with_cache[-1],
                    "cache_control": {"type": "ephemeral"}
                }
        
        # Run agent loop
        while True:
            start_time = time.time()
            # Call Claude with prompt caching enabled
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_with_cache,
                messages=messages,
                tools=tools_with_cache,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Track cache performance
            cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
            cache_create = getattr(response.usage, 'cache_creation_input_tokens', 0)
            
            metrics = {
                "duration_ms": duration_ms,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": cache_read,
                "cache_create_tokens": cache_create,
            }
            
            # Log cache performance
            if cache_read > 0:
                self.logger.info(f"[{self.name}] Cache HIT: {cache_read} tokens read from cache (90% cost reduction!)")
            elif cache_create > 0:
                self.logger.info(f"[{self.name}] Cache CREATED: {cache_create} tokens cached for future requests")
            
            # Track with Langfuse if enabled
            if LANGFUSE_ENABLED:
                session_id = context.get("session_id") if context else None
                user_id = context.get("user_id") if context else None
                track_generation(
                    agent_name=self.name,
                    model=DEFAULT_MODEL,
                    messages=messages,
                    response=response,
                    session_id=session_id,
                    user_id=user_id,
                )
            
            # Process response
            assistant_content = []
            tool_calls = []
            
            for block in response.content:
                if block.type == "text":
                    # Yield text as thinking
                    yield {
                        "type": "thinking",
                        "agent": self.name,
                        "content": block.text
                    }
                    assistant_content.append(block)
                    
                elif block.type == "tool_use":
                    tool_calls.append(block)
                    assistant_content.append(block)
            
            # Add assistant message
            messages.append({"role": "assistant", "content": assistant_content})
            
            # If no tool calls, we're done
            if not tool_calls:
                # Extract final result
                final_text = ""
                for block in assistant_content:
                    if hasattr(block, 'text'):
                        final_text += block.text
                
                yield {
                    "type": "result",
                    "agent": self.name,
                    "content": final_text,
                    "metrics": metrics
                }
                break
            
            # Execute tool calls
            tool_results = []
            for i, tool_call in enumerate(tool_calls):
                # Yield tool call event
                event = {
                    "type": "tool_call",
                    "agent": self.name,
                    "tool": tool_call.name,
                    "params": tool_call.input,
                }
                if i == 0:
                    event["metrics"] = metrics
                    
                yield event
                
                # Execute tool
                try:
                    result = self.tool_bridge.execute(tool_call.name, tool_call.input)
                    
                    # Yield tool result
                    yield {
                        "type": "tool_result",
                        "agent": self.name,
                        "tool": tool_call.name,
                        "result": result,
                        "success": True,
                    }
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result),
                    })
                    
                    # Track tool call with Langfuse
                    if LANGFUSE_ENABLED:
                        session_id = context.get("session_id") if context else None
                        track_tool_call(
                            agent_name=self.name,
                            tool_name=tool_call.name,
                            tool_input=tool_call.input,
                            tool_output=result,
                            success=True,
                            session_id=session_id,
                        )
                    
                except Exception as e:
                    self.logger.error(f"Tool {tool_call.name} failed: {e}")
                    
                    # Track failed tool call with Langfuse
                    if LANGFUSE_ENABLED:
                        session_id = context.get("session_id") if context else None
                        track_tool_call(
                            agent_name=self.name,
                            tool_name=tool_call.name,
                            tool_input=tool_call.input,
                            tool_output=str(e),
                            success=False,
                            session_id=session_id,
                        )
                    
                    yield {
                        "type": "tool_result",
                        "agent": self.name,
                        "tool": tool_call.name,
                        "error": str(e),
                        "success": False,
                    }
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                        "is_error": True,
                    })
            
            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})
            
            # Check stop reason
            if response.stop_reason == "end_turn":
                break
        
        # Flush Langfuse data to ensure it's sent
        if LANGFUSE_ENABLED:
            flush()
        
        self.logger.info(f"[{self.name}] Task completed")

