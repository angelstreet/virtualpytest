# Auto-Generated Tool Definitions

## ✅ Best Practice: Single Source of Truth

Tool definitions are now **auto-generated from implementation code** at startup.  
**NO MANUAL EDITING REQUIRED** - just update docstrings!

## How It Works

1. **Write your tool method** with proper docstring
2. **Definitions generate automatically** at app startup
3. **No drift** - implementation IS the spec

## Example

```python
# backend_server/src/mcp/tools/control_tools.py

def take_control(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take exclusive control of a device. Locks device for exclusive use.
    
    Example: take_control(host_name='sunri-pi1', device_id='device1')
    
    Args:
        params: {
            'host_name': str (REQUIRED - host where device is connected),
            'device_id': str (REQUIRED - device identifier)
        }
        
    Returns:
        MCP-formatted response
    """
    # Implementation...
```

**That's it!** The tool definition is auto-generated from this docstring.

## Adding New Tools

1. **Update the docstring** in your tool implementation
2. **Add to registry** in `build_definitions.py`:

```python
TOOL_REGISTRY = {
    'control': {
        'class': ControlTools,
        'methods': ['take_control', 'release_control']
    },
    'navigation': {
        'class': NavigationTools,
        'methods': ['navigate_to_node']
    },
    # Add your new category:
    'mynew': {
        'class': MyNewTools,
        'methods': ['my_tool_method']
    }
}
```

3. **Done!** Definitions generate at startup.

## Docstring Format

```python
def my_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Short description of what the tool does.
    
    Example: my_tool(param1='value1', param2='value2')
    
    Args:
        params: {
            'param1': str (REQUIRED - description of param1),
            'param2': int (OPTIONAL - description of param2),
            'param3': bool (REQUIRED - description of param3)
        }
        
    Returns:
        Description of return value
    """
```

**Key points:**
- `REQUIRED` or `OPTIONAL` in caps
- Format: `'param_name': type (REQUIRED/OPTIONAL - description)`
- Include `Example:` line in description

## Testing

```bash
cd /Users/cpeengineering/virtualpytest
python3 -c "
from backend_server.src.mcp.tool_definitions.build_definitions import get_builder
builder = get_builder()
print(f'Generated {len(builder.get_all_tools())} tools')
"
```

## Benefits

✅ **No drift** - definitions always match implementation  
✅ **No manual sync** - change docstring, done  
✅ **Less code** - 80% less definition boilerplate  
✅ **Best practice** - industry standard (FastAPI, GraphQL, etc.)

## Migration

### Old Way (DEPRECATED):
```python
# Manual JSON definitions
def get_tools():
    return [{
        "name": "take_control",
        "description": "...",
        "inputSchema": {...}  # Manually maintained
    }]
```

### New Way (CURRENT):
```python
# Auto-generated from docstrings
def get_tools():
    return get_control_tools()  # Generated at startup
```

## Can I Delete Manual Definition Files?

**YES!** Once a tool is in the registry with proper docstring:

1. The old manual definition file becomes redundant
2. Keep it as reference during migration, then delete
3. Or replace content with just: `from .build_definitions import get_XXX_tools`

## Status

✅ **control_definitions.py** - Auto-generated  
✅ **navigation_definitions.py** - Auto-generated  
🔄 **Other tools** - Add to registry as needed

