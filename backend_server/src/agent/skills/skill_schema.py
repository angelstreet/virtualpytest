"""
Skill Definition Schema

Pydantic models defining the structure of skill configurations.
Skills are loaded from YAML files and provide focused capabilities to agents.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class SkillDefinition(BaseModel):
    """
    Complete skill definition
    
    Skills are focused capabilities that agents can dynamically load.
    They provide system prompts and tool access for specific tasks.
    """
    name: str = Field(
        ...,
        pattern="^[a-z0-9-]+$",
        description="Unique skill identifier (lowercase, hyphens)"
    )
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+(-[a-z0-9]+)?$",
        description="Semantic version"
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Description of what this skill does (used by agents for matching)"
    )
    triggers: List[str] = Field(
        default_factory=list,
        description="Keywords for auto-matching user requests"
    )
    system_prompt: str = Field(
        ...,
        min_length=50,
        description="Workflow instructions for the LLM"
    )
    tools: List[str] = Field(
        ...,
        min_length=1,
        description="MCP tools this skill exposes"
    )
    platform: Optional[str] = Field(
        default=None,
        description="Platform focus: mobile, web, stb, or null for all"
    )
    requires_device: bool = Field(
        default=False,
        description="Whether this skill needs device control"
    )
    timeout_seconds: int = Field(
        default=1800,
        ge=60,
        description="Default timeout for this skill"
    )
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ['mobile', 'web', 'stb']
            if v.lower() not in valid:
                raise ValueError(f"Platform must be one of: {valid}")
            return v.lower()
        return v
    
    def matches_triggers(self, message: str) -> bool:
        """Check if user message matches any of this skill's triggers"""
        message_lower = message.lower()
        return any(trigger.lower() in message_lower for trigger in self.triggers)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return self.model_dump(exclude_none=True)

