# Action Command Validation - Implementation Plan

## Problem

Same issue as verifications, but for edge actions:
- **Verifications:** `check_element_exists` (invalid) saved to nodes → fails at execution
- **Actions:** `click_element_by_index` (invalid) saved to edges → fails at execution

## Current State

### What's Validated
- ✅ `action_sets` structure
- ✅ Max 2 action sets
- ✅ `default_action_set_id` exists

### What's NOT Validated
- ❌ Action command names (e.g., `click_element`, `press_key`)
- ❌ Device model compatibility
- ❌ Required parameters

## Solution Design

### 1. Create Action Validator (`backend_server/src/mcp/utils/action_validator.py`)

Similar to `VerificationValidator`, but for actions:

```python
class ActionValidator:
    """
    Validates action commands against available controllers.
    
    Prevents invalid action commands from being saved to edges,
    catching errors at creation time rather than execution time.
    """
    
    def validate_actions(
        self,
        action_sets: List[Dict[str, Any]],
        device_model: str,
        host_name: str = None,
        device_id: str = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate action commands in action_sets against available controllers.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
```

### 2. Add to `tree_tools.py` - `create_edge()` and `update_edge()`

```python
def create_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...
    
    # ✅ NEW: VALIDATE ACTIONS
    action_sets = params.get('action_sets', [])
    if action_sets:
        device_model = get_device_model_from_tree(tree_id)
        is_valid, errors, warnings = self.action_validator.validate_actions(
            action_sets,
            device_model
        )
        
        if not is_valid:
            return error_with_available_commands(errors, device_model)
    
    # ... continue with edge creation ...
```

### 3. Add to Backend API Route

In `server_navigation_trees_routes.py`:

```python
@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges', methods=['POST'])
def create_edge_api(tree_id):
    # ... existing code ...
    
    # ✅ VALIDATION: Check actions if provided
    action_sets = edge_data.get('action_sets', [])
    if action_sets:
        # Validate actions against device model
        validator = ActionValidator(api_client)
        is_valid, errors, warnings = validator.validate_actions(...)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_msg,
                'errors': errors
            }), 400
```

### 4. Populate `action_commands` Database Table

Add migration: `20251117_add_action_commands_table.sql`

```sql
CREATE TABLE action_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model VARCHAR(50) NOT NULL,
    command_name VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- 'remote', 'adb', 'web'
    params_schema JSONB,
    description TEXT,
    category VARCHAR(50),
    UNIQUE (device_model, command_name)
);

-- Web/host_vnc commands
INSERT INTO action_commands VALUES
('host_vnc', 'click_element', 'web', ...),
('host_vnc', 'type_text', 'web', ...),
('host_vnc', 'press_key', 'web', ...);

-- Android mobile commands
INSERT INTO action_commands VALUES
('android_mobile', 'click_element', 'adb', ...),
('android_mobile', 'swipe_up', 'adb', ...),
('android_mobile', 'launch_app', 'adb', ...);
```

## Implementation Steps

1. ✅ **Create ActionValidator** utility
2. ✅ **Update tree_tools.py** - Add validation to create_edge/update_edge
3. ✅ **Update backend API** - Add validation to edge routes
4. ✅ **Create database schema** - action_commands table
5. ✅ **Apply migration** - Populate with valid commands
6. ✅ **Test validation** - Try invalid command, verify rejection

## Benefits

| Before | After |
|--------|-------|
| Invalid commands saved | ❌ Rejected at creation |
| Error at execution | ✅ Error at save time |
| No guidance | ✅ Shows available commands |
| Debugging difficult | ✅ Clear error messages |

## Example Error Message

```
❌ Invalid action command(s):

Action 1 in forward action_set: Invalid command 'click_element_by_index' for device model 'android_mobile'
   Available commands: click_element, swipe_up, swipe_down, launch_app, press_key...
   Did you mean 'click_element'?

📋 Available action commands for 'android_mobile':
  **ADB**:
    - click_element
    - swipe_up
    - swipe_down
    - launch_app
    - press_key
    - type_text

💡 To see full details, call: list_actions(device_id='device1', host_name='sunri-pi1')
```

## Correct Action Commands

### Web (host_vnc)
- `click_element` - Click web element
- `type_text` - Type into input field
- `press_key` - Press keyboard key
- `navigate_to_url` - Navigate to URL

### Android Mobile
- `click_element` - Click by text/id
- `swipe_up`, `swipe_down`, `swipe_left`, `swipe_right` - Swipe gestures
- `launch_app` - Launch app by package
- `press_key` - Press key (BACK, HOME, etc.)
- `type_text` - Type into input

### Android TV
- Same as android_mobile
- Additional remote commands via IR

## Priority

**HIGH** - Same severity as verification validation:
- Prevents invalid commands from being saved
- Catches errors early (creation vs execution)
- Improves developer experience
- Reduces debugging time

## Estimated Effort

- ActionValidator class: 1-2 hours
- tree_tools.py updates: 30 min
- Backend route updates: 30 min
- Migration creation: 30 min
- Testing: 1 hour

**Total: ~4 hours**

## Dependencies

- ✅ VerificationValidator pattern (already implemented)
- ✅ Database migration system (already working)
- ✅ list_actions MCP tool (already exists)

## Next Steps

Would you like me to implement this action validation system now?

