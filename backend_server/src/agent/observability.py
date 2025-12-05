"""
Langfuse Observability Integration

Optional LLM observability for token tracking, cost monitoring, and tracing.
Auto-enabled when LANGFUSE_HOST is configured in .env
"""

import os
import logging
from typing import Optional, Any, Dict
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Auto-enable Langfuse if LANGFUSE_HOST is configured
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "")
LANGFUSE_ENABLED = bool(LANGFUSE_HOST)

# Log Langfuse status once at import
if LANGFUSE_ENABLED:
    logger.info(f"Langfuse observability enabled (host={LANGFUSE_HOST})")

# Langfuse client (lazy loaded)
_langfuse_client = None


def get_langfuse():
    """Get Langfuse client (lazy initialization)"""
    global _langfuse_client
    
    if not LANGFUSE_ENABLED:
        return None
    
    if _langfuse_client is None:
        try:
            from langfuse import Langfuse
            
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            
            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=LANGFUSE_HOST,
            )
            logger.info("Langfuse client initialized")
        except ImportError:
            logger.warning("Langfuse not installed. Run: pip install langfuse")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            return None
    
    return _langfuse_client


class ObservabilitySpan:
    """Wrapper for Langfuse span/generation tracking"""
    
    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self._trace = None
        self._span = None
    
    def __enter__(self):
        langfuse = get_langfuse()
        if langfuse:
            self._trace = langfuse.trace(
                id=self.trace_id,
                name=self.name,
                session_id=self.session_id,
                user_id=self.user_id,
                metadata=self.metadata,
            )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._trace and exc_type:
            self._trace.update(
                level="ERROR",
                status_message=str(exc_val),
            )
    
    def generation(
        self,
        name: str,
        model: str,
        input_data: Any,
        output_data: Any = None,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record an LLM generation (API call)"""
        if not self._trace:
            return
        
        try:
            self._trace.generation(
                name=name,
                model=model,
                input=input_data,
                output=output_data,
                usage=usage,
                metadata=metadata,
            )
        except Exception as e:
            logger.debug(f"Failed to record generation: {e}")
    
    def span(
        self,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a span (tool call, processing step)"""
        if not self._trace:
            return
        
        try:
            self._trace.span(
                name=name,
                input=input_data,
                output=output_data,
                metadata=metadata,
            )
        except Exception as e:
            logger.debug(f"Failed to record span: {e}")
    
    def event(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an event"""
        if not self._trace:
            return
        
        try:
            self._trace.event(name=name, metadata=metadata)
        except Exception as e:
            logger.debug(f"Failed to record event: {e}")


def track_generation(
    agent_name: str,
    model: str,
    messages: list,
    response: Any,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Track an LLM generation call using Langfuse v2 SDK.
    
    Args:
        agent_name: Name of the agent (Explorer, Builder, etc.)
        model: Model name (claude-sonnet-4-20250514)
        messages: Input messages
        response: Anthropic response object
        session_id: Chat session ID
        user_id: User ID
    """
    langfuse = get_langfuse()
    if not langfuse:
        return
    
    
    try:
        # Extract usage from response
        usage = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
        
        # Add cache metrics if available
        cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
        cache_create = getattr(response.usage, 'cache_creation_input_tokens', 0)
        
        metadata = {
            "agent": agent_name,
            "cache_read_tokens": cache_read,
            "cache_create_tokens": cache_create,
            "stop_reason": response.stop_reason,
        }
        
        # Extract output text
        output_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                output_text += block.text
        
        # Langfuse v2 SDK - create trace then add generation
        trace = langfuse.trace(
            name=f"{agent_name} Call",
            session_id=session_id,
            user_id=user_id,
            metadata={"agent": agent_name},
        )
        
        trace.generation(
            name=f"{agent_name} Generation",
            model=model,
            input=messages,
            output=output_text,
            usage=usage,
            metadata=metadata,
        )
        
    except Exception as e:
        logger.debug(f"Failed to track generation: {e}")


def track_tool_call(
    agent_name: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    success: bool,
    session_id: Optional[str] = None,
):
    """Track a tool call using Langfuse v2 SDK"""
    langfuse = get_langfuse()
    if not langfuse:
        return
    
    try:
        # Langfuse v2 SDK - create trace then add span
        trace = langfuse.trace(
            name=f"{agent_name} Tool: {tool_name}",
            session_id=session_id,
            metadata={
                "agent": agent_name,
                "tool": tool_name,
                "success": success,
            },
        )
        
        trace.span(
            name=tool_name,
            input=tool_input,
            output=tool_output,
            level="DEFAULT" if success else "ERROR",
        )
        
    except Exception as e:
        logger.debug(f"Failed to track tool call: {e}")


def flush():
    """Flush any pending Langfuse data"""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.debug(f"Failed to flush Langfuse: {e}")


# Convenience decorator for tracking agent runs
def observe_agent(agent_name: str):
    """Decorator to track agent execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session_id = kwargs.get('context', {}).get('session_id')
            user_id = kwargs.get('context', {}).get('user_id')
            
            with ObservabilitySpan(
                name=f"{agent_name} Run",
                session_id=session_id,
                user_id=user_id,
                metadata={"agent": agent_name},
            ):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

