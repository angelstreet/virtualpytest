# Service Executor Singleton Pattern

## ⚠️ CRITICAL ARCHITECTURE RULE

**Each device has singleton service executor instances that MUST be reused to preserve state and memory.**

## The Problem

Service executors maintain critical state that gets lost when new instances are created:

### NavigationExecutor State Loss
- `current_node_id` - Current navigation position
- `current_node_label` - Current node label  
- `current_tree_id` - Current tree being navigated

### ActionExecutor State Loss
- `action_screenshots` - Screenshot tracking for reporting
- `_action_type_cache` - Performance cache to avoid repeated controller lookups
- Navigation context (`tree_id`, `edge_id`, `action_set_id`)

### VerificationExecutor State Loss
- Navigation context (`tree_id`, `node_id`)
- Verification history and caching

## The Solution

### ✅ CORRECT Usage

```python
# Use device's existing executor instances
action_executor = device.action_executor
verification_executor = device.verification_executor  
navigation_executor = device.navigation_executor

# These preserve all state and caches
```

### ❌ INCORRECT Usage

```python
# DON'T create new instances - causes state loss!
action_executor = ActionExecutor(device)  # ❌ Loses state!
verification_executor = VerificationExecutor(device)  # ❌ Loses state!
```

## Protection Mechanisms

### 1. Factory Methods (Recommended Alternative)

```python
# If you must use a factory pattern
action_executor = ActionExecutor.get_for_device(device)
verification_executor = VerificationExecutor.get_for_device(device)
navigation_executor = NavigationExecutor.get_for_device(device)
```

### 2. Constructor Warnings

When creating new instances outside device initialization, you'll see:

```
⚠️ [ActionExecutor] WARNING: Creating new ActionExecutor instance for device device1
⚠️ [ActionExecutor] This may cause state loss! Use device.action_executor instead.
⚠️ [ActionExecutor] Call stack:
⚠️ [ActionExecutor]   File "your_script.py", line 42, in your_function
⚠️ [ActionExecutor]     action_executor = ActionExecutor(device)
```

### 3. Documentation in Class Headers

All service executors now have clear warnings:

```python
class ActionExecutor:
    """
    CRITICAL: Do not create new instances directly! Use device.action_executor instead.
    Each device has a singleton ActionExecutor that preserves state and caches.
    """
```

## Device Initialization

Service executors are created once during device initialization in `controller_manager.py`:

```python
# Only place where new instances should be created
device.action_executor = ActionExecutor(device, _from_device_init=True)
device.navigation_executor = NavigationExecutor(device, _from_device_init=True)  
device.verification_executor = VerificationExecutor(device, _from_device_init=True)
```

The `_from_device_init=True` flag suppresses warnings for legitimate creation.

## Benefits of Singleton Pattern

1. **State Preservation**: Navigation position, caches, and context maintained
2. **Memory Efficiency**: No duplicate executor instances
3. **Consistency**: All components use same executor instances
4. **Performance**: Cached data preserved across operations

## Migration Guide

### Before (State Loss)
```python
# ZapExecutor creating new instances
verification_executor = VerificationExecutor(self.device, context.tree_id, context.current_node_id)
action_executor = ActionExecutor(context.selected_device, context.tree_id, action_edge.get('edge_id'))
```

### After (State Preserved)
```python
# ZapExecutor using existing instances
verification_executor = self.device.verification_executor
action_executor = context.selected_device.action_executor
```

## Enforcement

This pattern is enforced through:

1. **Runtime Warnings**: Constructor warnings when creating outside device init
2. **Documentation**: Clear warnings in class docstrings
3. **Factory Methods**: Safe alternatives that return existing instances
4. **Code Reviews**: Architectural guidelines in this document

## Files Updated

- `backend_host/src/services/actions/action_executor.py`
- `backend_host/src/services/verifications/verification_executor.py`  
- `backend_host/src/services/navigation/navigation_executor.py`
- `backend_host/src/controllers/controller_manager.py`
- `shared/src/lib/executors/zap_executor.py`

## Testing

To verify the pattern works:

```python
# Test that device has executors
assert hasattr(device, 'action_executor')
assert hasattr(device, 'verification_executor') 
assert hasattr(device, 'navigation_executor')

# Test that they're the same instance
executor1 = device.action_executor
executor2 = device.action_executor
assert executor1 is executor2  # Same object reference
```

---

**Remember: Always use `device.{service}_executor` - never create new instances!**
