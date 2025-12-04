"""
Base Agent Class

Common functionality for all specialist agents.
"""

import logging
from typing import Dict, Any, List, AsyncGenerator
from abc import ABC, abstractmethod

import anthropic

from ..config import get_anthropic_api_key, DEFAULT_MODEL, MAX_TOKENS


class BaseAgent(ABC):
    """Base class for all specialist agents"""
    
    def __init__(self, tool_bridge: 'ToolBridge'):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tool_bridge = tool_bridge
        self.client = anthropic.Anthropic(api_key=get_anthropic_api_key())
        
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
            "content": f"Processing task with {len(tools)} available tools..."
        }
        
        # Run agent loop
        while True:
            # Call Claude
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                system=self.system_prompt,
                messages=messages,
                tools=tools if tools else None,
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
                    "content": final_text
                }
                break
            
            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                # Yield tool call event
                yield {
                    "type": "tool_call",
                    "agent": self.name,
                    "tool": tool_call.name,
                    "params": tool_call.input,
                }
                
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
                    
                except Exception as e:
                    self.logger.error(f"Tool {tool_call.name} failed: {e}")
                    
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
        
        self.logger.info(f"[{self.name}] Task completed")

