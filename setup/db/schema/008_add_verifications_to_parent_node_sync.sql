-- Migration 007: Add Verifications to Parent Node Sync
-- Date: 2025-10-22
-- Description: Extend parent node sync trigger to include verifications field
--              This ensures verifications are automatically synced from parent to subtree nodes

-- Drop existing trigger and function to recreate with extended functionality
DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
DROP FUNCTION IF EXISTS sync_parent_label_screenshot() CASCADE;

-- ==============================================================================
-- EXTENDED SYNC FUNCTION - NOW INCLUDES VERIFICATIONS
-- ==============================================================================

-- Renamed function to reflect expanded scope
CREATE OR REPLACE FUNCTION sync_parent_node_to_subtrees()
RETURNS TRIGGER AS $$
BEGIN
    -- Only sync if this node is referenced as a parent by subtrees
    IF EXISTS(
        SELECT 1 FROM navigation_trees 
        WHERE parent_node_id = NEW.node_id 
        AND team_id = NEW.team_id
    ) THEN
        -- Update label, screenshot, and verifications in all subtree duplicates
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
            AND team_id = NEW.team_id
            AND tree_id IN (
                SELECT id FROM navigation_trees 
                WHERE parent_node_id = NEW.node_id 
                AND team_id = NEW.team_id
            );
            
        -- Log sync operation for debugging
        RAISE NOTICE 'Synced label/screenshot/verifications for parent node % to % subtrees', 
                     NEW.node_id, 
                     (SELECT COUNT(*) FROM navigation_trees WHERE parent_node_id = NEW.node_id AND team_id = NEW.team_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- CREATE TRIGGER - FIRES ON LABEL, SCREENSHOT, OR VERIFICATIONS CHANGES
-- ==============================================================================

CREATE TRIGGER sync_parent_node_to_subtrees_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        -- Fire when label, screenshot, or verifications changes
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot' OR
        OLD.verifications IS DISTINCT FROM NEW.verifications
    )
    EXECUTE FUNCTION sync_parent_node_to_subtrees();

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS
-- ==============================================================================
-- To rollback this migration, run:
--
-- DROP TRIGGER IF EXISTS sync_parent_node_to_subtrees_trigger ON navigation_nodes;
-- DROP FUNCTION IF EXISTS sync_parent_node_to_subtrees();
-- 
-- Then restore the old trigger:
-- CREATE TRIGGER sync_parent_label_screenshot_trigger
--     AFTER UPDATE ON navigation_nodes
--     FOR EACH ROW
--     WHEN (OLD.label IS DISTINCT FROM NEW.label OR OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot')
--     EXECUTE FUNCTION sync_parent_label_screenshot();

-- Log migration completion
SELECT 'Migration 007: Parent node verifications sync applied successfully' as status;

