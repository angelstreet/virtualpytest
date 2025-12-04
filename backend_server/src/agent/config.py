"""
Agent System Configuration

Environment variables required:
- ANTHROPIC_API_KEY: Your Anthropic API key
"""

import os
from typing import Dict, Any

# Model configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

# Get API key from environment
def get_anthropic_api_key() -> str:
    """Get Anthropic API key from environment"""
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
    return key

# Manager Safe Tools (Read-only metadata)
MANAGER_TOOLS = [
    # Requirements & Coverage
    "list_requirements",
    "get_requirement",
    "get_testcase_requirements",
    "get_requirement_coverage",
    "get_coverage_summary",
    "get_uncovered_requirements",
    
    # Test Cases
    "list_testcases",
    "load_testcase",
    
    # User Interfaces & Navigation
    "list_userinterfaces",
    "get_userinterface_complete",
    "list_nodes",
    "list_edges",
    "list_navigation_nodes",
    "preview_userinterface",
    
    # Device & Host
    "get_device_info",
    "get_compatible_hosts",
    "get_execution_status",
    
    # Scripts
    "list_scripts",
    
    # System
    "list_services",
    "view_logs",
    
    # Verifications
    "list_verifications"
]

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

