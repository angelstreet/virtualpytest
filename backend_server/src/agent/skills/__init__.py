"""
Agent Skills - Tool mappings per agent

Each agent has access to a specific subset of MCP tools.
"""

from .explorer_skills import EXPLORER_TOOLS
from .builder_skills import BUILDER_TOOLS
from .executor_skills import EXECUTOR_TOOLS
from .analyst_skills import ANALYST_TOOLS
from .maintainer_skills import MAINTAINER_TOOLS

__all__ = [
    'EXPLORER_TOOLS',
    'BUILDER_TOOLS', 
    'EXECUTOR_TOOLS',
    'ANALYST_TOOLS',
    'MAINTAINER_TOOLS',
]

