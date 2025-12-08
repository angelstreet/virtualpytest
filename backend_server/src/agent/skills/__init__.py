"""
Skill Registry - Maps YAML skills to MCP tools

NOTE: Individual skill files (explorer_skills.py, etc.) have been removed.
Skills are defined directly in YAML agent configs (registry/templates/*.yaml).

The SkillRegistry validates that skills listed in YAML exist as MCP tools.
"""

from .skill_registry import SkillRegistry, get_skill_registry, AVAILABLE_SKILLS

__all__ = ['SkillRegistry', 'get_skill_registry', 'AVAILABLE_SKILLS']
