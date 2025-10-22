# Verification Sync Fix - Migration 007

**Date**: October 22, 2025  
**Issue**: Verifications not syncing from parent tree to subtree nodes  
**Status**: ✅ FIXED

## Problem Description

When editing a node's verifications in the parent tree, those changes were NOT automatically synced to the duplicate node in the subtree. This caused:

- **Symptom**: "No verifications for node" error during KPI measurement
- **Root cause**: Database trigger only synced `label` and `screenshot`, not `verifications`
- **Impact**: Subtree nodes had stale/empty verification arrays

## Example of the Bug

```
Node: node-1755856020800 (label: "live")

ROOT TREE (a1e05da1-ec92-4cd4-9162-dd1c60334857):
  verifications: [waitForImageToAppear with live_banner] ✅
  updated: Oct 22, 16:53

SUBTREE (8082ab9f-9719-40bb-98b5-1183906f8020):
  verifications: [] ❌ EMPTY
  updated: Oct 17, 18:06 (5 days old)
```

When navigation executed in the subtree, it queried the subtree node and found NO verifications.

## Root Cause Analysis

### Database Schema
The `navigation_nodes` table allows the SAME `node_id` to exist in multiple trees:

```sql
UNIQUE(tree_id, node_id)  -- Allows duplicates across trees
```

### Sync Trigger (OLD - Incomplete)
The trigger in `006_parent_node_sync_triggers.sql` only synced 2 fields:

```sql
UPDATE navigation_nodes 
SET 
    label = NEW.label,
    data = jsonb_set(..., '{screenshot}', ...),  -- Only screenshot from data
    updated_at = NOW()
WHERE ...
```

**Missing**: `verifications` field was NEVER synced!

## The Fix

### Migration 007: Add Verifications to Sync
Created `/setup/db/schema/007_add_verifications_to_parent_node_sync.sql`:

1. **Renamed function**: `sync_parent_label_screenshot()` → `sync_parent_node_to_subtrees()`
2. **Added verifications sync**:
   ```sql
   UPDATE navigation_nodes 
   SET 
       label = NEW.label,
       data = jsonb_set(..., '{screenshot}', ...),
       verifications = NEW.verifications,  -- ✅ ADDED
       updated_at = NOW()
   ```

3. **Updated trigger condition**:
   ```sql
   WHEN (
       OLD.label IS DISTINCT FROM NEW.label OR
       OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot' OR
       OLD.verifications IS DISTINCT FROM NEW.verifications  -- ✅ ADDED
   )
   ```

4. **Manual sync for existing nodes**:
   ```sql
   UPDATE navigation_nodes AS subtree
   SET verifications = parent.verifications
   FROM navigation_nodes AS parent
   WHERE subtree.node_id = parent.node_id
     AND parent.tree_id = 'root_tree_id'
     AND subtree.tree_id = 'subtree_id'
   ```

## Files Updated

1. **`007_add_verifications_to_parent_node_sync.sql`** (NEW)
   - Migration to extend the sync trigger

2. **`006_parent_node_sync_triggers.sql`** (UPDATED)
   - Updated for fresh installs to include verifications from the start
   - Function renamed to `sync_parent_node_to_subtrees()`
   - Trigger renamed to `sync_parent_node_to_subtrees_trigger`

3. **`CURRENT_DATABASE_BACKUP.sql`** (UPDATED)
   - Reflects current database state with new function/trigger names
   - Includes verifications in sync logic

4. **`auto_sync_nested_node.md`** (UPDATED)
   - Documentation updated with corrected function names

## Verification

After applying the fix:

```sql
SELECT node_id, label, tree_id, 
       jsonb_array_length(verifications) as verification_count
FROM navigation_nodes
WHERE node_id = 'node-1755856020800'
ORDER BY tree_id;
```

**Result**:
```
ROOT TREE:    1 verifications ✅
SUBTREE:      1 verifications ✅ (synced successfully)
```

## How It Works Now

1. **User edits verification** in parent tree node via UI
2. **Trigger fires** on `navigation_nodes` UPDATE
3. **Checks** if node is a parent (has subtrees)
4. **Syncs** `label`, `screenshot`, and `verifications` to ALL subtrees
5. **Subtree nodes** now have identical verifications

## Future Considerations

### Fields Currently Synced:
- ✅ `label`
- ✅ `screenshot` (from `data` field)
- ✅ `verifications`

### Fields NOT Synced (intentional):
- ❌ `position_x`, `position_y` (subtrees position nodes independently)
- ❌ `style` (subtrees may style differently)
- ❌ `data` (other than screenshot - tree-specific data)

### Potential Future Enhancements:
- Add `node_type` and `style` to sync if needed
- Add selective sync configuration (which fields to sync)
- Add bi-directional sync (subtree → parent) if needed

## Testing

Test the fix by:

1. Creating a subtree for a node
2. Editing the parent node's verifications
3. Verifying the subtree node updates automatically
4. Running navigation in the subtree context
5. Confirming verifications execute correctly

## Deployment Status

- ✅ Migration 007 applied to production database
- ✅ Existing stale nodes manually synced
- ✅ Schema files updated
- ✅ Documentation updated
- ✅ Trigger active and working

