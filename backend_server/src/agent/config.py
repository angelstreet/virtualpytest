"""
Agent System Configuration

Environment variables required:
- ANTHROPIC_API_KEY: Your Anthropic API key

Optional (LLM Observability - auto-enabled when LANGFUSE_HOST is set):
- LANGFUSE_HOST: Langfuse server URL (e.g., http://localhost:3001)
- LANGFUSE_PUBLIC_KEY: Your Langfuse public key
- LANGFUSE_SECRET_KEY: Your Langfuse secret key
"""

import os
from typing import Dict, Any

# Model configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

# Langfuse observability (auto-enabled if LANGFUSE_HOST is configured)
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "")
LANGFUSE_ENABLED = bool(LANGFUSE_HOST)  # Auto-enable if host is set

# In-memory API key storage (per-user/session)
# Format: { 'user_id' or 'session_id': 'api_key' }
_user_api_keys: Dict[str, str] = {}

def set_user_api_key(identifier: str, api_key: str) -> None:
    """Store API key for a user/session"""
    _user_api_keys[identifier] = api_key

def get_user_api_key(identifier: str) -> str | None:
    """Get API key for a user/session"""
    return _user_api_keys.get(identifier)

def get_anthropic_api_key(identifier: str | None = None) -> str:
    """
    Get Anthropic API key from user storage or environment
    
    Args:
        identifier: User ID or session ID to retrieve user-specific key
        
    Returns:
        API key string
        
    Raises:
        ValueError: If no API key is found
    """
    # First check user-specific key
    if identifier:
        user_key = get_user_api_key(identifier)
        if user_key:
            return user_key
    
    # Fall back to environment variable
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
    return key

# Agent configuration
AGENT_CONFIG: Dict[str, Dict[str, Any]] = {
    "qa_manager": {
        "name": "QA Manager",
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,  # Hybrid: Orchestrator + Simple Tools
    },
    "explorer": {
        "name": "Explorer",
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,
    },
    "builder": {
        "name": "Builder", 
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,
    },
    "executor": {
        "name": "Executor",
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,
    },
    "analyst": {
        "name": "Analyst",
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,
    },
    "maintainer": {
        "name": "Maintainer",
        "model": DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "has_tools": True,
    },
}

# Operating modes
class Mode:
    CREATE = "CREATE"      # Build new navigation tree + tests
    VALIDATE = "VALIDATE"  # Run existing tests + analyze results
    MAINTAIN = "MAINTAIN"  # Fix broken tests/selectors
    ANALYZE = "ANALYZE"    # Analyze results only (no execution)

# Mode to agent mapping
# Note: VALIDATE runs Executor THEN Analyst (sequential)
MODE_AGENTS = {
    Mode.CREATE: ["explorer", "builder"],
    Mode.VALIDATE: ["executor", "analyst"],  # Execute then analyze
    Mode.MAINTAIN: ["maintainer"],
    Mode.ANALYZE: ["analyst"],  # Analysis only (for reviewing past results)
}

