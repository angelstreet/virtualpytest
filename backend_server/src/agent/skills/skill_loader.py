"""
Skill Loader

Loads skill definitions from YAML files and provides access to them.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .skill_schema import SkillDefinition

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Loads and manages skill definitions from YAML files
    
    Skills are loaded once at startup and cached in memory.
    """
    
    # Class-level cache for loaded skills
    _skills: Dict[str, SkillDefinition] = {}
    _loaded: bool = False
    
    @classmethod
    def load_all_skills(cls) -> None:
        """
        Load all skill definitions from YAML files.
        Called once on server startup.
        """
        if cls._loaded:
            return
        
        definitions_dir = Path(__file__).parent / 'definitions'
        
        if not definitions_dir.exists():
            logger.warning(f"[skills] Definitions directory not found: {definitions_dir}")
            cls._loaded = True
            return
        
        yaml_files = list(definitions_dir.glob('*.yaml'))
        logger.info(f"[skills] ═══════════════════════════════════════════════")
        logger.info(f"[skills] Loading {len(yaml_files)} skill definitions...")
        logger.info(f"[skills] ═══════════════════════════════════════════════")
        
        loaded = 0
        errors = []
        
        for yaml_file in sorted(yaml_files):
            try:
                with open(yaml_file, 'r') as f:
                    yaml_content = yaml.safe_load(f)
                
                skill = SkillDefinition(**yaml_content)
                cls._skills[skill.name] = skill
                
                platform_str = skill.platform or 'all'
                device_str = '🔌' if skill.requires_device else '📝'
                logger.info(f"[skills]   {device_str} {skill.name:25} ({platform_str:6}) - {len(skill.tools)} tools")
                
                loaded += 1
                
            except Exception as e:
                errors.append(f"  ❌ {yaml_file.name}: {e}")
        
        cls._loaded = True
        
        if errors:
            logger.error(f"[skills] ")
            logger.error(f"[skills] ⚠️ Failed to Load ({len(errors)}):")
            for line in errors:
                logger.error(f"[skills] {line}")
        
        logger.info(f"[skills] ")
        logger.info(f"[skills] ═══════════════════════════════════════════════")
        logger.info(f"[skills] Total: {loaded}/{len(yaml_files)} skills loaded")
        logger.info(f"[skills] ═══════════════════════════════════════════════")
    
    @classmethod
    def reload(cls) -> None:
        """Reload all skills from YAML (for development)"""
        cls._skills.clear()
        cls._loaded = False
        cls.load_all_skills()
    
    @classmethod
    def get_skill(cls, skill_name: str) -> Optional[SkillDefinition]:
        """Get a skill by name"""
        if not cls._loaded:
            cls.load_all_skills()
        return cls._skills.get(skill_name)
    
    @classmethod
    def get_all_skills(cls) -> Dict[str, SkillDefinition]:
        """Get all loaded skills"""
        if not cls._loaded:
            cls.load_all_skills()
        return cls._skills.copy()
    
    @classmethod
    def get_skills_for_agent(cls, skill_names: List[str]) -> List[SkillDefinition]:
        """Get skill definitions for a list of skill names"""
        if not cls._loaded:
            cls.load_all_skills()
        return [cls._skills[name] for name in skill_names if name in cls._skills]
    
    @classmethod
    def get_skill_descriptions(cls, skill_names: List[str]) -> str:
        """
        Get formatted descriptions of skills for system prompt
        
        Returns:
            Formatted string with skill names and descriptions (no triggers for token efficiency)
        """
        if not cls._loaded:
            cls.load_all_skills()
        
        lines = []
        for name in skill_names:
            skill = cls._skills.get(name)
            if skill:
                platform_str = f" [{skill.platform}]" if skill.platform else ""
                lines.append(f"- **{skill.name}**{platform_str}: {skill.description.split('.')[0]}.")
        
        return '\n'.join(lines) if lines else "No skills available."
    
    @classmethod
    def match_skill(cls, message: str, available_skills: List[str]) -> Optional[SkillDefinition]:
        """
        Find the best matching skill for a user message
        
        Args:
            message: User message
            available_skills: List of skill names this agent can use
            
        Returns:
            Best matching SkillDefinition or None
        """
        if not cls._loaded:
            cls.load_all_skills()
        
        message_lower = message.lower()
        
        # Score each available skill
        best_skill = None
        best_score = 0
        
        for skill_name in available_skills:
            skill = cls._skills.get(skill_name)
            if not skill:
                continue
            
            score = 0
            for trigger in skill.triggers:
                if trigger.lower() in message_lower:
                    # Longer triggers are more specific = higher score
                    score += len(trigger)
            
            if score > best_score:
                best_score = score
                best_skill = skill
        
        return best_skill
    
    @classmethod
    def is_valid_skill(cls, skill_name: str) -> bool:
        """Check if a skill name exists"""
        if not cls._loaded:
            cls.load_all_skills()
        return skill_name in cls._skills
    
    @classmethod
    def validate_skills(cls, skill_names: List[str]) -> tuple[List[str], List[str]]:
        """
        Validate a list of skill names
        
        Returns:
            (valid_skills, invalid_skills)
        """
        if not cls._loaded:
            cls.load_all_skills()
        
        valid = []
        invalid = []
        for name in skill_names:
            if name in cls._skills:
                valid.append(name)
            else:
                invalid.append(name)
        return valid, invalid

