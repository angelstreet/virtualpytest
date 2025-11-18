"""
Tool definitions for VirtualPyTest MCP Server

This package contains MCP tool schemas organized by domain.
Each module exports a get_tools() function returning tool definitions.
"""

from .control_definitions import get_tools as get_control_tools
from .action_definitions import get_tools as get_action_tools
from .navigation_definitions import get_tools as get_navigation_tools
from .verification_definitions import get_tools as get_verification_tools
from .testcase_definitions import get_tools as get_testcase_tools
from .script_definitions import get_tools as get_script_tools
from .ai_definitions import get_tools as get_ai_tools
from .screenshot_definitions import get_tools as get_screenshot_tools
from .transcript_definitions import get_tools as get_transcript_tools
from .device_definitions import get_tools as get_device_tools
from .logs_definitions import get_tools as get_logs_tools
from .tree_definitions import get_tools as get_tree_tools
from .userinterface_definitions import get_tools as get_userinterface_tools
from .requirements_definitions import get_tools as get_requirements_tools

__all__ = [
    'get_control_tools',
    'get_action_tools',
    'get_navigation_tools',
    'get_verification_tools',
    'get_testcase_tools',
    'get_script_tools',
    'get_ai_tools',
    'get_screenshot_tools',
    'get_transcript_tools',
    'get_device_tools',
    'get_logs_tools',
    'get_tree_tools',
    'get_userinterface_tools',
    'get_requirements_tools',
]

