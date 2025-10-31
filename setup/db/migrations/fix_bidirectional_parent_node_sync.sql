-- Migration: Fix Bidirectional Parent Node Sync
-- Date: 2025-10-31
-- Description: Add reverse sync from subtree entry nodes back to parent nodes
--              When a screenshot/label/verification is updated in a subtree entry node,
--              it should automatically sync back to the parent node in the parent tree

-- ==============================================================================
-- BIDIRECTIONAL SYNC FUNCTION - SUBTREE TO PARENT
-- ==============================================================================

CREATE OR REPLACE FUNCTION sync_subtree_to_parent_node()
RETURNS TRIGGER AS $$
DECLARE
    parent_tree_id UUID;
    parent_node_id TEXT;
BEGIN
    -- Check if this node is an entry node in a subtree (node exists in a tree that has a parent)
    SELECT parent_tree_id, parent_node_id 
    INTO parent_tree_id, parent_node_id
    FROM navigation_trees 
    WHERE id = NEW.tree_id 
    AND team_id = NEW.team_id
    AND parent_tree_id IS NOT NULL
    AND parent_node_id IS NOT NULL;
    
    -- If this is a subtree entry node, sync back to parent
    IF parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL THEN
        -- Update the parent node in the parent tree with same node_id
        UPDATE navigation_nodes 
        SET 
            label = NEW.label,
            data = jsonb_set(
                COALESCE(data, '{}'), 
                '{screenshot}', 
                to_jsonb(NEW.data->>'screenshot')
            ),
            verifications = NEW.verifications,
            updated_at = NOW()
        WHERE 
            node_id = NEW.node_id
            AND tree_id = parent_tree_id
            AND team_id = NEW.team_id;
            
        -- Log sync operation for debugging
        IF FOUND THEN
            RAISE NOTICE 'Synced screenshot/label/verifications from subtree entry node % back to parent node in tree %', 
                         NEW.node_id, 
                         parent_tree_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path TO public, pg_temp;

-- ==============================================================================
-- CREATE REVERSE SYNC TRIGGER
-- ==============================================================================

DROP TRIGGER IF EXISTS sync_subtree_to_parent_trigger ON navigation_nodes;
CREATE TRIGGER sync_subtree_to_parent_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        -- Fire when label, screenshot, or verifications changes
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot' OR
        OLD.verifications IS DISTINCT FROM NEW.verifications
    )
    EXECUTE FUNCTION sync_subtree_to_parent_node();

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS
-- ==============================================================================
-- To rollback this migration, run:
--
-- DROP TRIGGER IF EXISTS sync_subtree_to_parent_trigger ON navigation_nodes;
-- DROP FUNCTION IF EXISTS sync_subtree_to_parent_node();

-- Log migration completion
SELECT 'Migration: Bidirectional parent node sync applied successfully' as status;

