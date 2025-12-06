"""
Agent Configuration Validator

Validates agent YAML files and provides import/export functionality.
"""

import yaml
from typing import Dict, Any, List
from pydantic import ValidationError

from .config_schema import AgentDefinition


class AgentValidationError(Exception):
    """Raised when agent configuration is invalid"""
    pass


def validate_agent_yaml(yaml_content: str) -> AgentDefinition:
    """
    Validate agent YAML and return AgentDefinition
    
    Args:
        yaml_content: YAML string content
        
    Returns:
        Validated AgentDefinition object
        
    Raises:
        AgentValidationError: If YAML is invalid
    """
    try:
        # Parse YAML
        data = yaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            raise AgentValidationError("YAML must contain a dictionary")
        
        # Validate against schema
        agent = AgentDefinition(**data)
        
        return agent
        
    except yaml.YAMLError as e:
        raise AgentValidationError(f"Invalid YAML syntax: {str(e)}")
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            errors.append(f"{field}: {error['msg']}")
        raise AgentValidationError(f"Validation errors:\n" + "\n".join(errors))
    except Exception as e:
        raise AgentValidationError(f"Unexpected error: {str(e)}")


def export_agent_yaml(agent: AgentDefinition) -> str:
    """
    Export agent to YAML string
    
    Args:
        agent: AgentDefinition object
        
    Returns:
        YAML string
    """
    data = agent.to_dict()
    
    # Custom YAML formatting for readability
    yaml_str = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=80
    )
    
    # Add header comment
    header = f"""# Agent Configuration: {agent.metadata.name}
# Version: {agent.metadata.version}
# Author: {agent.metadata.author}
# 
# This configuration can be imported into any VirtualPyTest instance.
#
---
"""
    
    return header + yaml_str


def validate_agent_dict(data: Dict[str, Any]) -> AgentDefinition:
    """
    Validate agent dictionary (from JSON/API)
    
    Args:
        data: Dictionary containing agent configuration
        
    Returns:
        Validated AgentDefinition object
        
    Raises:
        AgentValidationError: If configuration is invalid
    """
    try:
        return AgentDefinition(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            errors.append(f"{field}: {error['msg']}")
        raise AgentValidationError(f"Validation errors:\n" + "\n".join(errors))


def get_validation_errors(yaml_content: str) -> List[str]:
    """
    Get list of validation errors without raising exception
    
    Args:
        yaml_content: YAML string content
        
    Returns:
        List of error messages (empty if valid)
    """
    try:
        validate_agent_yaml(yaml_content)
        return []
    except AgentValidationError as e:
        return [str(e)]
    except Exception as e:
        return [f"Unexpected error: {str(e)}"]

