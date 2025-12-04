"""
Agent Definitions

Each agent has:
- System prompt (personality, role)
- Tool list (from skills)
- Execution logic

Agent Responsibilities:
- Explorer: UI discovery, navigation tree building
- Builder: Test cases, requirements, coverage setup
- Executor: Execution STRATEGY (devices, parallelization, retries)
- Analyst: Result ANALYSIS (bug vs UI change, Jira lookup)
- Maintainer: Self-healing (fix selectors, update edges)
"""

from .explorer import ExplorerAgent
from .builder import BuilderAgent
from .executor import ExecutorAgent
from .analyst import AnalystAgent
from .maintainer import MaintainerAgent

__all__ = [
    'ExplorerAgent',
    'BuilderAgent',
    'ExecutorAgent',
    'AnalystAgent',
    'MaintainerAgent',
]

