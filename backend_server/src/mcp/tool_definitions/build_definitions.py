"""
Build all tool definitions at startup - ZERO MANUAL CONFIGURATION.

Auto-discovers ALL tool classes in the tools/ folder and generates
definitions from their docstrings. Add a new tool file → it's automatically included!
"""

from typing import Dict, List, Any, Type
import os
import importlib
import inspect
from pathlib import Path
from .auto_generator import generate_from_class


def _discover_tool_classes() -> Dict[str, Type]:
    """
    Auto-discover all tool classes from the tools/ directory.
    
    Scans ../tools/*.py files, imports classes ending with "Tools",
    returns {category: ToolClass} mapping.
    
    Returns:
        {'control': ControlTools, 'navigation': NavigationTools, ...}
    """
    tools_dir = Path(__file__).parent.parent / 'tools'
    discovered = {}
    
    # Scan all *_tools.py files
    for file_path in tools_dir.glob('*_tools.py'):
        if file_path.name.startswith('_'):
            continue
        
        # Extract category name: "control_tools.py" → "control"
        category = file_path.stem.replace('_tools', '')
        
        try:
            # Import module
            module_name = f'backend_server.src.mcp.tools.{file_path.stem}'
            module = importlib.import_module(module_name)
            
            # Find class ending with "Tools"
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith('Tools') and obj.__module__ == module_name:
                    discovered[category] = obj
                    print(f"[AUTO-DISCOVER] ✅ Found {category}: {name}")
                    break
                    
        except Exception as e:
            print(f"[AUTO-DISCOVER] ⚠️  Failed to load {file_path.name}: {e}")
    
    return discovered


def _get_public_methods(tool_class: Type) -> List[str]:
    """
    Get all public methods from a tool class (methods that don't start with _).
    
    Args:
        tool_class: The tool class to inspect
        
    Returns:
        List of public method names
    """
    methods = []
    for name, method in inspect.getmembers(tool_class, inspect.isfunction):
        # Skip private methods and special methods
        if name.startswith('_'):
            continue
        # Skip inherited methods from object
        if name in ('format_api_response',):
            continue
        methods.append(name)
    return methods


# Auto-discover all tool classes at module load
print("[AUTO-DISCOVER] 🔍 Scanning tools directory...")
TOOL_REGISTRY = _discover_tool_classes()
print(f"[AUTO-DISCOVER] 🎉 Discovered {len(TOOL_REGISTRY)} tool categories")


class ToolDefinitionBuilder:
    """
    Auto-generates all tool definitions from implementation at startup.
    Zero manual configuration - discovers all tools automatically!
    
    Usage:
        builder = ToolDefinitionBuilder()
        builder.build_all()  # Generate all definitions
        
        # Get definitions for a specific category
        control_tools = builder.get_tools('control')
        
        # Or get by tool name
        take_control_def = builder.get_tool('take_control')
    """
    
    def __init__(self):
        self._definitions: Dict[str, List[Dict[str, Any]]] = {}
        self._tool_map: Dict[str, Dict[str, Any]] = {}
        self._built = False
    
    def build_all(self) -> None:
        """
        Build all tool definitions from auto-discovered classes.
        Call this during app initialization.
        """
        if self._built:
            return
        
        print("[TOOLS] 🔨 Auto-generating tool definitions from implementation...")
        
        for category, tool_class in TOOL_REGISTRY.items():
            try:
                # Auto-discover all public methods
                methods = _get_public_methods(tool_class)
                
                if not methods:
                    print(f"[TOOLS]   ⚠️  {category}: No public methods found")
                    continue
                
                # Generate definitions for all methods
                definitions = generate_from_class(tool_class, methods)
                self._definitions[category] = definitions
                
                # Build tool name -> definition map
                for tool_def in definitions:
                    self._tool_map[tool_def['name']] = tool_def
                
                print(f"[TOOLS]   ✅ {category}: {len(definitions)} tools")
                
            except Exception as e:
                print(f"[TOOLS]   ❌ {category}: {e}")
                import traceback
                traceback.print_exc()
        
        self._built = True
        print(f"[TOOLS] 🎉 Generated {len(self._tool_map)} total tool definitions")
    
    def get_tools(self, category: str) -> List[Dict[str, Any]]:
        """Get all tool definitions for a category."""
        if not self._built:
            self.build_all()
        return self._definitions.get(category, [])
    
    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        """Get a specific tool definition by name."""
        if not self._built:
            self.build_all()
        return self._tool_map.get(tool_name)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tool definitions (flat list)."""
        if not self._built:
            self.build_all()
        return list(self._tool_map.values())
    
    def get_tools_by_names(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Get multiple tool definitions by names."""
        if not self._built:
            self.build_all()
        return [self._tool_map[name] for name in tool_names if name in self._tool_map]


# Global singleton instance
_builder = None


def get_builder() -> ToolDefinitionBuilder:
    """Get the global tool definition builder (singleton)."""
    global _builder
    if _builder is None:
        _builder = ToolDefinitionBuilder()
        _builder.build_all()  # Auto-build on first access
    return _builder


# Convenience functions for backward compatibility
def get_control_tools() -> List[Dict[str, Any]]:
    """Get control tool definitions."""
    return get_builder().get_tools('control')


def get_navigation_tools() -> List[Dict[str, Any]]:
    """Get navigation tool definitions."""
    return get_builder().get_tools('navigation')


def get_device_tools() -> List[Dict[str, Any]]:
    """Get device tool definitions."""
    return get_builder().get_tools('device')


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """Get all tool definitions."""
    return get_builder().get_all_tools()


def get_tools_by_names(tool_names: List[str]) -> List[Dict[str, Any]]:
    """Get specific tool definitions by names."""
    return get_builder().get_tools_by_names(tool_names)


def export_definitions_to_files() -> None:
    """
    Export auto-generated definitions to *_definitions.py files for debugging.
    
    These files are DOCUMENTATION/DEBUG artifacts, not the source of truth.
    The source of truth is the docstrings in the tool implementations.
    """
    import json
    from pathlib import Path
    
    builder = get_builder()
    definitions_dir = Path(__file__).parent
    
    print("\n[EXPORT] 📝 Exporting auto-generated definitions to files for debugging...")
    
    for category in sorted(builder._definitions.keys()):
        tools = builder.get_tools(category)
        
        if not tools:
            continue
        
        # Create file content
        file_content = f'''"""
{category.title()} tool definitions - AUTO-GENERATED (DEBUG VIEW)

⚠️  DO NOT EDIT THIS FILE MANUALLY!
This file is auto-generated from docstrings in {category}_tools.py
To change definitions, update the docstrings in the implementation.

Generated: {len(tools)} tools
"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """
    Auto-generated tool definitions for {category}.
    
    🔍 DEBUG VIEW: This file shows what was generated from docstrings.
    ⚠️  Source of truth: ../tools/{category}_tools.py docstrings
    """
    return {json.dumps(tools, indent=4)}
'''
        
        # Write to file
        output_file = definitions_dir / f'{category}_definitions.py'
        output_file.write_text(file_content)
        print(f"[EXPORT]   ✅ {category}_definitions.py ({len(tools)} tools)")
    
    print(f"[EXPORT] 🎉 Exported {len(builder._definitions)} definition files")
    print(f"[EXPORT] 💡 Use these files for debugging - source is in tools/*.py")


# Auto-export on import (can be disabled if needed)
import os
if os.getenv('EXPORT_TOOL_DEFINITIONS', 'true').lower() == 'true':
    # Export after build completes
    _builder_instance = get_builder()
    if _builder_instance._built:
        try:
            export_definitions_to_files()
        except Exception as e:
            print(f"[EXPORT] ⚠️  Failed to export: {e}")

