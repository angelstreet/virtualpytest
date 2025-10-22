# Database Trigger-Based Parent Node Sync Plan

## Overview
Instead of application-level sync logic, use PostgreSQL triggers to automatically synchronize parent node changes to all subtree duplicates. This ensures data consistency without manual intervention.

## Architecture Design

### 1. Trigger Strategy
**Trigger Type**: `AFTER UPDATE` on `navigation_nodes` table
**Event**: When a parent node is updated, automatically update all subtree duplicates

### 2. Trigger Logic Flow
```sql
-- Pseudo-code for trigger function
WHEN navigation_nodes IS UPDATED:
  1. Check if updated node is a parent node (has subtrees referencing it)
  2. If yes, find all subtrees that reference this parent_node_id
  3. Update the duplicate nodes in those subtrees with synced fields
  4. Skip position fields (subtrees may position parent node differently)
```

## Implementation Plan

### Phase 1: Helper Function to Identify Parent Nodes
```sql
CREATE OR REPLACE FUNCTION is_parent_node(node_id_param TEXT, team_id_param UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if any subtrees reference this node as parent_node_id
    RETURN EXISTS(
        SELECT 1 FROM navigation_trees 
        WHERE parent_node_id = node_id_param 
        AND team_id = team_id_param
    );
END;
$$ LANGUAGE plpgsql;
```

### Phase 2: Function to Get Subtrees for Parent Node
```sql
CREATE OR REPLACE FUNCTION get_subtrees_for_parent_node(
    node_id_param TEXT, 
    team_id_param UUID
)
RETURNS TABLE(subtree_id UUID) AS $$
BEGIN
    RETURN QUERY
    SELECT id FROM navigation_trees 
    WHERE parent_node_id = node_id_param 
    AND team_id = team_id_param;
END;
$$ LANGUAGE plpgsql;
```

### Phase 3: Core Sync Function
```sql
CREATE OR REPLACE FUNCTION sync_parent_node_to_subtrees()
RETURNS TRIGGER AS $$
DECLARE
    subtree_record RECORD;
    sync_data JSONB;
BEGIN
    -- Only proceed if this is an UPDATE operation
    IF TG_OP != 'UPDATE' THEN
        RETURN NEW;
    END IF;
    
    -- Check if the updated node is a parent node
    IF NOT is_parent_node(NEW.node_id, NEW.team_id) THEN
        RETURN NEW;
    END IF;
    
    -- Log the sync operation
    RAISE NOTICE 'Syncing parent node % to subtrees', NEW.node_id;
    
    -- Define which fields to sync (exclude position and tree-specific data)
    sync_data := jsonb_build_object(
        'label', NEW.label,
        'data', NEW.data,
        'verifications', NEW.verifications,
        'node_type', NEW.node_type,
        'style', NEW.style
    );
    
    -- Update duplicate nodes in all subtrees
    FOR subtree_record IN 
        SELECT subtree_id FROM get_subtrees_for_parent_node(NEW.node_id, NEW.team_id)
    LOOP
        UPDATE navigation_nodes 
        SET 
            label = NEW.label,
            data = NEW.data,
            verifications = NEW.verifications,
            node_type = NEW.node_type,
            style = NEW.style,
            updated_at = NOW()
        WHERE 
            tree_id = subtree_record.subtree_id
            AND node_id = NEW.node_id
            AND team_id = NEW.team_id;
            
        -- Log each update
        RAISE NOTICE 'Updated parent node % in subtree %', NEW.node_id, subtree_record.subtree_id;
    END LOOP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Phase 4: Create the Trigger
```sql
-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS sync_parent_node_to_subtrees_trigger ON navigation_nodes;

-- Create the trigger
CREATE TRIGGER sync_parent_node_to_subtrees_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        -- Only fire when synced fields change
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data IS DISTINCT FROM NEW.data OR
        OLD.verifications IS DISTINCT FROM NEW.verifications OR
        OLD.node_type IS DISTINCT FROM NEW.node_type OR
        OLD.style IS DISTINCT FROM NEW.style
    )
    EXECUTE FUNCTION sync_parent_node_to_subtrees();
```

### Phase 5: Testing
## Advanced Features

### 1. Selective Field Sync
Allow configuration of which fields to sync:

```sql
-- Add configuration table
CREATE TABLE IF NOT EXISTS parent_node_sync_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    sync_fields JSONB DEFAULT '["label", "data", "verifications"]',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Modify sync function to use config
-- ... (query sync_config table for fields to sync)
```

### 2. Sync Prevention Flag
Add ability to temporarily disable sync for bulk operations:

```sql
-- Add session variable to disable sync
-- SET session.disable_parent_sync = true;

-- Modify trigger to check this flag
WHEN (
    current_setting('session.disable_parent_sync', true) != 'true'
    AND (OLD.label IS DISTINCT FROM NEW.label OR ...)
)
```

### 3. Conflict Resolution
Handle cases where subtree has intentionally different data:

```sql
-- Add metadata to track sync vs manual changes
-- In node.data: {"sync_override": {"label": "custom_label"}}
-- Skip syncing fields that have sync_override
```

## Benefits

### ✅ Automatic Synchronization
- **Zero application code** needed for sync
- **Immediate consistency** - changes propagate instantly
- **Transaction safety** - sync happens in same transaction

### ✅ Performance Optimized
- **Trigger only fires** when relevant fields change
- **Batched updates** for multiple subtrees
- **No polling** or background jobs needed

### ✅ Maintainable
- **Database-level consistency** enforcement
- **Clear separation** of concerns
- **Easy to disable/modify** without code changes

## Migration Strategy

### 1. Deploy Functions and Trigger
```sql
-- Apply all functions and trigger in migration
-- Test with small dataset first
```

### 2. Initial Data Sync
```sql
-- One-time sync of existing parent nodes to subtrees
UPDATE navigation_nodes SET updated_at = updated_at 
WHERE node_id IN (
    SELECT DISTINCT parent_node_id 
    FROM navigation_trees 
    WHERE parent_node_id IS NOT NULL
);
```

### 3. Validation
```sql
-- Query to verify sync is working
SELECT 
    'Parent vs Subtree Sync Check' as check_type,
    p.node_id,
    p.label as parent_label,
    s.label as subtree_label,
    CASE WHEN p.label = s.label THEN '✅ SYNCED' ELSE '❌ OUT_OF_SYNC' END as status
FROM navigation_nodes p
JOIN navigation_trees st ON st.parent_node_id = p.node_id
JOIN navigation_nodes s ON s.tree_id = st.id AND s.node_id = p.node_id
WHERE p.tree_id = st.parent_tree_id;
```

## Rollback Plan
```sql
-- If issues arise, easily disable
DROP TRIGGER IF EXISTS sync_parent_nodes_trigger ON navigation_nodes;

-- Or temporarily disable
ALTER TABLE navigation_nodes DISABLE TRIGGER sync_parent_nodes_trigger;
```

## Testing Strategy
1. **Unit Tests**: Update parent node, verify subtree sync
2. **Bulk Tests**: Update multiple parent nodes simultaneously  
3. **Performance Tests**: Measure trigger overhead
4. **Edge Cases**: Test with deeply nested subtrees

This trigger-based approach provides automatic, reliable synchronization while keeping the application code clean and simple.
