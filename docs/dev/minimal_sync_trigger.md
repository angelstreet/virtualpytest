# Minimal Parent Node Sync Trigger

## Simple Requirements
1. **Sync name + screenshot**: When parent node label or screenshot changes → update in all subtrees
2. **Cascade delete**: When parent node deleted → delete entire subtree

## Implementation

### 1. Simple Sync Trigger (Name + Screenshot Only)
```sql
CREATE OR REPLACE FUNCTION sync_parent_label_screenshot()
RETURNS TRIGGER AS $$
BEGIN
    -- Only sync if this node is referenced as a parent by subtrees
    -- AND only if label or screenshot changed
    IF EXISTS(
        SELECT 1 FROM navigation_trees 
        WHERE parent_node_id = NEW.node_id 
        AND team_id = NEW.team_id
    ) THEN
        -- Update label and screenshot in all subtree duplicates
        UPDATE navigation_nodes 
        SET 
            label = NEW.label,
            data = jsonb_set(
                COALESCE(data, '{}'), 
                '{screenshot}', 
                to_jsonb(NEW.data->>'screenshot')
            ),
            updated_at = NOW()
        WHERE 
            node_id = NEW.node_id
            AND team_id = NEW.team_id
            AND tree_id IN (
                SELECT id FROM navigation_trees 
                WHERE parent_node_id = NEW.node_id 
                AND team_id = NEW.team_id
            );
            
        RAISE NOTICE 'Synced label/screenshot for parent node % to subtrees', NEW.node_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER sync_parent_label_screenshot_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot'
    )
    EXECUTE FUNCTION sync_parent_label_screenshot();
```

### 2. Cascade Delete Trigger (Delete Subtrees)
```sql
CREATE OR REPLACE FUNCTION cascade_delete_subtrees()
RETURNS TRIGGER AS $$
BEGIN
    -- When a parent node is deleted, delete all its subtrees
    DELETE FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    RAISE NOTICE 'Deleted subtrees for parent node %', OLD.node_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create the delete trigger
CREATE TRIGGER cascade_delete_subtrees_trigger
    AFTER DELETE ON navigation_nodes
    FOR EACH ROW
    EXECUTE FUNCTION cascade_delete_subtrees();
```

## Test Scenarios

### Test 1: Label Sync
```sql
-- Update parent node label
UPDATE navigation_nodes 
SET label = 'live_updated'
WHERE node_id = 'node-1749036265480' 
AND tree_id = 'bbf2d95d-72c2-4701-80a7-0b9d131a5c38';

-- Verify sync worked
SELECT tree_id, label FROM navigation_nodes 
WHERE node_id = 'node-1749036265480';
-- Should show 'live_updated' in both parent tree and subtree
```

### Test 2: Screenshot Sync  
```sql
-- Update parent node screenshot
UPDATE navigation_nodes 
SET data = jsonb_set(data, '{screenshot}', '"new_screenshot.jpg"')
WHERE node_id = 'node-1749036265480' 
AND tree_id = 'bbf2d95d-72c2-4701-80a7-0b9d131a5c38';

-- Verify sync worked
SELECT tree_id, data->>'screenshot' FROM navigation_nodes 
WHERE node_id = 'node-1749036265480';
-- Should show 'new_screenshot.jpg' in both parent tree and subtree
```

### Test 3: Cascade Delete
```sql
-- Delete parent node
DELETE FROM navigation_nodes 
WHERE node_id = 'node-1749036265480' 
AND tree_id = 'bbf2d95d-72c2-4701-80a7-0b9d131a5c38';

-- Verify subtree was deleted
SELECT count(*) FROM navigation_trees 
WHERE parent_node_id = 'node-1749036265480';
-- Should return 0
```

## Migration Script
```sql
-- Deploy the minimal sync triggers
BEGIN;

-- 1. Create sync function
CREATE OR REPLACE FUNCTION sync_parent_label_screenshot()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS(
        SELECT 1 FROM navigation_trees 
        WHERE parent_node_id = NEW.node_id 
        AND team_id = NEW.team_id
    ) THEN
        UPDATE navigation_nodes 
        SET 
            label = NEW.label,
            data = jsonb_set(
                COALESCE(data, '{}'), 
                '{screenshot}', 
                to_jsonb(NEW.data->>'screenshot')
            ),
            updated_at = NOW()
        WHERE 
            node_id = NEW.node_id
            AND team_id = NEW.team_id
            AND tree_id IN (
                SELECT id FROM navigation_trees 
                WHERE parent_node_id = NEW.node_id 
                AND team_id = NEW.team_id
            );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Create delete function
CREATE OR REPLACE FUNCTION cascade_delete_subtrees()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 3. Create triggers
DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
CREATE TRIGGER sync_parent_label_screenshot_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot'
    )
    EXECUTE FUNCTION sync_parent_label_screenshot();

DROP TRIGGER IF EXISTS cascade_delete_subtrees_trigger ON navigation_nodes;
CREATE TRIGGER cascade_delete_subtrees_trigger
    AFTER DELETE ON navigation_nodes
    FOR EACH ROW
    EXECUTE FUNCTION cascade_delete_subtrees();

COMMIT;
```

## Rollback Plan
```sql
-- To disable triggers if needed
DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
DROP TRIGGER IF EXISTS cascade_delete_subtrees_trigger ON navigation_nodes;
DROP FUNCTION IF EXISTS sync_parent_label_screenshot();
DROP FUNCTION IF EXISTS cascade_delete_subtrees();
```

## Benefits
✅ **Minimal scope**: Only syncs label + screenshot  
✅ **Automatic**: No application code changes needed
✅ **Safe cascade**: Subtrees deleted when parent removed
✅ **Performance**: Only fires on relevant changes
✅ **Simple**: Easy to understand and maintain
