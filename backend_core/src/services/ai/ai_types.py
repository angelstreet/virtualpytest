"""
AI Types

Minimal data types for simplified AI system.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class ExecutionResult:
    plan_id: str
    success: bool
    step_results: List[Dict[str, Any]]
    total_time_ms: int
    error: Optional[str] = None
