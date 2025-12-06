"""
Skill Registry

Central registry of all available skills/tools that agents can use.
Maps skill names (from YAML) to MCP tool implementations.
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass

# Import MCP tool definitions to get available tool names
from mcp.tool_definitions import (
    get_control_tools,
    get_action_tools,
    get_navigation_tools,
    get_verification_tools,
    get_testcase_tools,
    get_script_tools,
    get_ai_tools,
    get_screenshot_tools,
    get_device_tools,
    get_logs_tools,
    get_tree_tools,
    get_userinterface_tools,
    get_requirements_tools,
    get_screen_analysis_tools,
    get_exploration_tools,
)


@dataclass
class SkillInfo:
    """Information about a skill"""
    name: str
    category: str
    description: str
    requires_device: bool = False


def _extract_tool_names(tool_definitions: List[dict]) -> Dict[str, SkillInfo]:
    """Extract tool names and info from MCP tool definitions"""
    skills = {}
    for tool in tool_definitions:
        name = tool.get('name', '')
        desc = tool.get('description', '')[:100] if tool.get('description') else ''
        # Check if tool requires device control
        requires_device = 'device' in name.lower() or 'take_control' in name.lower()
        skills[name] = SkillInfo(
            name=name,
            category='mcp',
            description=desc,
            requires_device=requires_device
        )
    return skills


def _build_skill_registry() -> Dict[str, SkillInfo]:
    """Build registry of all available skills from MCP tools"""
    all_skills = {}
    
    # Categorize by tool definition file
    tool_categories = [
        ('control', get_control_tools()),
        ('action', get_action_tools()),
        ('navigation', get_navigation_tools()),
        ('verification', get_verification_tools()),
        ('testcase', get_testcase_tools()),
        ('script', get_script_tools()),
        ('ai', get_ai_tools()),
        ('screenshot', get_screenshot_tools()),
        ('device', get_device_tools()),
        ('logs', get_logs_tools()),
        ('tree', get_tree_tools()),
        ('userinterface', get_userinterface_tools()),
        ('requirements', get_requirements_tools()),
        ('screen_analysis', get_screen_analysis_tools()),
        ('exploration', get_exploration_tools()),
    ]
    
    for category, tools in tool_categories:
        for tool in tools:
            name = tool.get('name', '')
            if name:
                desc = tool.get('description', '')
                if desc and len(desc) > 100:
                    desc = desc[:100] + '...'
                all_skills[name] = SkillInfo(
                    name=name,
                    category=category,
                    description=desc,
                    requires_device='device' in category or name in ['take_control', 'navigate_to_node']
                )
    
    return all_skills


# Build the registry once at module load
_SKILL_REGISTRY = _build_skill_registry()

# Export list of available skill names
AVAILABLE_SKILLS: Set[str] = set(_SKILL_REGISTRY.keys())


class SkillRegistry:
    """
    Central registry for agent skills
    
    Validates skills from YAML configs against available MCP tools.
    """
    
    def __init__(self):
        self._skills = _SKILL_REGISTRY
    
    def is_valid_skill(self, skill_name: str) -> bool:
        """Check if a skill name is valid (exists in MCP tools)"""
        return skill_name in self._skills
    
    def validate_skills(self, skills: List[str]) -> tuple[List[str], List[str]]:
        """
        Validate a list of skills
        
        Returns:
            (valid_skills, invalid_skills)
        """
        valid = []
        invalid = []
        for skill in skills:
            if self.is_valid_skill(skill):
                valid.append(skill)
            else:
                invalid.append(skill)
        return valid, invalid
    
    def get_skill_info(self, skill_name: str) -> Optional[SkillInfo]:
        """Get detailed info about a skill"""
        return self._skills.get(skill_name)
    
    def get_all_skills(self) -> Dict[str, SkillInfo]:
        """Get all available skills"""
        return self._skills.copy()
    
    def get_skills_by_category(self, category: str) -> List[SkillInfo]:
        """Get skills filtered by category"""
        return [s for s in self._skills.values() if s.category == category]
    
    def list_categories(self) -> List[str]:
        """List all skill categories"""
        return list(set(s.category for s in self._skills.values()))
    
    def get_device_skills(self) -> List[str]:
        """Get skills that require device control"""
        return [name for name, info in self._skills.items() if info.requires_device]


# Global instance
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the skill registry instance"""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry

