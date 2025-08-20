-- Migration 006: Parent Node Sync Triggers
-- Date: 2024-01-XX
-- Description: Add automatic sync triggers for parent node label/screenshot changes
--              and cascade delete for subtrees when parent node is deleted

-- ==============================================================================
-- SYNC TRIGGERS FOR NESTED NAVIGATION
-- ==============================================================================

-- 1. Function to sync parent node label and screenshot to subtrees
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
            
        -- Log sync operation for debugging
        RAISE NOTICE 'Synced label/screenshot for parent node % to % subtrees', 
                     NEW.node_id, 
                     (SELECT COUNT(*) FROM navigation_trees WHERE parent_node_id = NEW.node_id AND team_id = NEW.team_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Function to cascade delete subtrees when parent node is deleted
CREATE OR REPLACE FUNCTION cascade_delete_subtrees()
RETURNS TRIGGER AS $$
DECLARE
    subtree_count INTEGER;
BEGIN
    -- Count subtrees before deletion for logging
    SELECT COUNT(*) INTO subtree_count
    FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    -- When a parent node is deleted, delete all its subtrees
    -- This will cascade delete all nodes and edges in those subtrees
    DELETE FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    -- Log cascade delete for debugging
    IF subtree_count > 0 THEN
        RAISE NOTICE 'Cascade deleted % subtrees for parent node %', subtree_count, OLD.node_id;
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 3. Create sync trigger (only fires on label or screenshot changes)
DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
CREATE TRIGGER sync_parent_label_screenshot_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        -- Only fire when label or screenshot actually changes
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot'
    )
    EXECUTE FUNCTION sync_parent_label_screenshot();

-- 4. Create cascade delete trigger
DROP TRIGGER IF EXISTS cascade_delete_subtrees_trigger ON navigation_nodes;
CREATE TRIGGER cascade_delete_subtrees_trigger
    AFTER DELETE ON navigation_nodes
    FOR EACH ROW
    EXECUTE FUNCTION cascade_delete_subtrees();

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS
-- ==============================================================================
-- To rollback this migration, run:
--
-- DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
-- DROP TRIGGER IF EXISTS cascade_delete_subtrees_trigger ON navigation_nodes;
-- DROP FUNCTION IF EXISTS sync_parent_label_screenshot();
-- DROP FUNCTION IF EXISTS cascade_delete_subtrees();

-- Log migration completion
SELECT 'Migration 006: Parent node sync triggers applied successfully' as status;
