# Bidirectional Edges - Quick Reference Guide

## 🎯 How It Works Now (Simplified)

### Core Concept
**Every edge has exactly 2 action sets with predictable IDs:**
- `source_to_target` - Forward direction actions
- `target_to_source` - Reverse direction actions

### Example Structure
```typescript
// Edge from home → home_saved
edge = {
  id: "edge-node-1-node-2-123456789",
  source: "node-1",        // home node
  target: "node-2",        // home_saved node
  data: {
    action_sets: [
      {
        id: "home_to_home_saved",           // Index 0 = Forward
        label: "home → home_saved",
        actions: [/* click Saved Tab */]
      },
      {
        id: "home_saved_to_home",           // Index 1 = Reverse  
        label: "home_saved → home",
        actions: [/* click Home Tab */]
      }
    ],
    default_action_set_id: "home_to_home_saved"  // Always forward direction
  }
}
```

## 🔄 Panel Display Logic

### Two Panels Per Edge
1. **Panel 1** (Index 0): Shows `home → home_saved` with forward actions
2. **Panel 2** (Index 1): Shows `home_saved → home` with reverse actions

### Direction Parsing
```typescript
// Simple parsing in EdgeSelectionPanel
if (actionSet.id.includes('_to_')) {
  const toIndex = actionSet.id.indexOf('_to_');
  const fromLabel = actionSet.id.substring(0, toIndex);          // "home"
  const toLabel = actionSet.id.substring(toIndex + 4);           // "home_saved"
  // Display: "home → home_saved"
}
```

## ✏️ Edit Dialog Logic

### Direction Selection
```typescript
// In EdgeSelectionPanel.handleEdit()
const forwardActionSetId = edgeForm.action_sets[0].id;           // "home_to_home_saved"
edgeForm.direction = actionSet.id === forwardActionSetId ? 'forward' : 'reverse';

// In useEdgeEdit hook
const direction = edgeForm.direction || 'forward';
const actionSet = direction === 'forward' 
  ? edgeForm.action_sets[0]  // Index 0 = Forward
  : edgeForm.action_sets[1]; // Index 1 = Reverse
```

## 🚀 Edge Creation

### Always Creates Both Directions
```typescript
// In useNavigationEditor.createEdgeData()
return {
  action_sets: [
    {
      id: `${cleanSourceLabel}_to_${cleanTargetLabel}`,    // Forward
      label: `${sourceLabel} → ${targetLabel}`,
      actions: [], retry_actions: [], failure_actions: []
    },
    {
      id: `${cleanTargetLabel}_to_${cleanSourceLabel}`,    // Reverse
      label: `${targetLabel} → ${sourceLabel}`, 
      actions: [], retry_actions: [], failure_actions: []
    }
  ],
  default_action_set_id: `${cleanSourceLabel}_to_${cleanTargetLabel}`
};
```

## 🗃️ Database Structure

### Migration Applied
- ✅ All edges now have exactly 2 action sets
- ✅ Clean, predictable IDs: `source_to_target` and `target_to_source`
- ✅ No more priority numbers or complex parsing

### Query Example
```sql
SELECT 
  ne.edge_id,
  jsonb_array_elements(ne.action_sets)->>'id' as action_set_id,
  jsonb_array_elements(ne.action_sets)->>'label' as action_set_label
FROM navigation_edges ne
WHERE ne.edge_id = 'your-edge-id';

-- Result:
-- home_to_home_saved    | "home → home_saved"
-- home_saved_to_home    | "home_saved → home"
```

## 🎯 Key Benefits

- ✅ **Predictable**: Always exactly 2 action sets per edge
- ✅ **Simple**: No more priority handling or complex parsing
- ✅ **Clear**: Direction is obvious from action set ID
- ✅ **Reliable**: No more infinite loops or missing directions
- ✅ **Maintainable**: Less code, fewer edge cases

## 🔧 Troubleshooting

### Common Issues
1. **Wrong direction loading in edit dialog**: Check that `direction` is set correctly in `EdgeSelectionPanel.handleEdit()`
2. **Missing panels**: Verify edge has exactly 2 action sets in database
3. **Direction parsing errors**: Ensure action set IDs follow `source_to_target` format

### Debug Commands
```javascript
// In browser console - check edge structure
console.log(selectedEdge.data.action_sets);

// Check direction assignment
console.log(edgeForm.direction);

// Verify action set order
console.log(edgeForm.action_sets.map(as => as.id));
```

---
*Last updated: Implementation completed with database migration*
