-- VirtualPyTest UI & Navigation Tables Schema
-- This file contains tables for user interfaces, navigation trees, nodes, and edges

-- Drop existing tables if they exist (for clean recreation)
DROP TRIGGER IF EXISTS cascade_delete_subtrees_trigger ON navigation_nodes;
DROP TRIGGER IF EXISTS sync_parent_label_screenshot_trigger ON navigation_nodes;
DROP TRIGGER IF EXISTS trigger_update_subtree_counts ON navigation_trees;
DROP FUNCTION IF EXISTS cascade_delete_subtrees() CASCADE;
DROP FUNCTION IF EXISTS sync_parent_label_screenshot() CASCADE;
DROP FUNCTION IF EXISTS update_node_subtree_counts() CASCADE;
DROP FUNCTION IF EXISTS get_tree_path(uuid) CASCADE;
DROP FUNCTION IF EXISTS get_descendant_trees(uuid) CASCADE;
DROP TABLE IF EXISTS navigation_trees_history CASCADE;
DROP TABLE IF EXISTS navigation_edges CASCADE;
DROP TABLE IF EXISTS navigation_nodes CASCADE;
DROP TABLE IF EXISTS navigation_trees CASCADE;
DROP TABLE IF EXISTS userinterfaces CASCADE;

-- User interfaces (screens/apps being tested) - UPDATED SCHEMA
CREATE TABLE userinterfaces (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    models text[] DEFAULT '{}'::text[],  -- UPDATED: Array of compatible device models
    min_version character varying,       -- UPDATED: Minimum version support
    max_version character varying,       -- UPDATED: Maximum version support
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Navigation trees (renamed from original, now stores only metadata)
CREATE TABLE navigation_trees (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id) ON DELETE CASCADE,  -- UPDATED: Made nullable
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    root_node_id uuid,  -- UPDATED: Changed from text to uuid
    
    -- Nested tree relationship columns
    parent_tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    parent_node_id text, -- References the node_id that spawned this subtree
    tree_depth integer DEFAULT 0, -- Depth level (0 = root, 1 = first level nested, etc.)
    is_root_tree boolean DEFAULT true, -- True only for top-level trees
    
    -- React Flow viewport position fields
    viewport_x double precision DEFAULT 0, -- React Flow viewport X position for restoring view state
    viewport_y double precision DEFAULT 0, -- React Flow viewport Y position for restoring view state  
    viewport_zoom double precision DEFAULT 1, -- React Flow viewport zoom level for restoring view state
    
    -- Constraints for nested trees
    CONSTRAINT check_tree_depth CHECK (tree_depth >= 0 AND tree_depth <= 5),
    CONSTRAINT check_parent_consistency 
    CHECK (
        (parent_tree_id IS NULL AND parent_node_id IS NULL AND is_root_tree = true) OR
        (parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL AND is_root_tree = false)
    )
);

-- Navigation nodes (individual nodes with embedded verifications)
CREATE TABLE navigation_nodes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    node_id text NOT NULL, -- User-defined node identifier
    label text NOT NULL,
    position_x double precision NOT NULL DEFAULT 0,
    position_y double precision NOT NULL DEFAULT 0,
    node_type text NOT NULL DEFAULT 'default',
    style jsonb DEFAULT '{}',
    data jsonb DEFAULT '{}',
    verifications jsonb DEFAULT '[]', -- ✅ Embedded verification objects
    kpi_references jsonb DEFAULT '[]', -- ✅ KPI measurement references (same format as verifications)
    use_verifications_for_kpi boolean DEFAULT false NOT NULL, -- ✅ When TRUE, use verifications[] for KPI instead of kpi_references[]
    
    -- Nested tree metadata
    has_subtree boolean DEFAULT false, -- True if this node has associated subtrees
    subtree_count integer DEFAULT 0, -- Number of subtrees linked to this node
    
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, node_id)
);

-- Navigation edges (individual edges with action_sets structure - NO LEGACY SUPPORT)
-- Each edge can contain MULTIPLE action sets for bidirectional navigation
-- Each action set represents one navigation method (e.g., "Click Tab", "Press Key")
--
-- ACTION SET STRUCTURE:
-- {
--   "id": "home_to_movies_1",           -- Unique ID within edge
--   "label": "Click Movies Tab",        -- Descriptive label for UI
--   "actions": [...],                   -- Array of actions to execute
--   "retry_actions": [...],             -- Array of retry actions if main fails
--   "failure_actions": [...],           -- Array of failure actions if retry fails
--   "priority": 1,                      -- Priority (1 = default/primary)
--   "conditions": {},                   -- Optional conditions for execution
--   "timer": 0                          -- Timer for auto-return (milliseconds)
-- }
--
-- EXAMPLES:
-- - Edge "home ↔ home_tvguide" has 2 action sets: forward + reverse
-- - Edge "home_tvguide ↔ tvguide_livetv" has 3 action sets: forward + 2 reverse methods
CREATE TABLE navigation_edges (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    edge_id text NOT NULL, -- User-defined edge identifier
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    label text, -- ✅ UPDATED: Now uses bidirectional format (e.g., "home ↔ home_tvguide")
    edge_type text NOT NULL DEFAULT 'default',
    style jsonb DEFAULT '{}',
    data jsonb DEFAULT '{}',
    action_sets jsonb NOT NULL DEFAULT '[]', -- ✅ REQUIRED: Array of action sets (2-3 per edge typical)
    default_action_set_id text NOT NULL, -- ✅ REQUIRED: ID of default action set (priority 1)
    final_wait_time integer DEFAULT 0,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, edge_id),
    
    -- Ensure action_sets is not empty and default_action_set_id exists
    CONSTRAINT check_action_sets_not_empty CHECK (jsonb_array_length(action_sets) > 0),
    CONSTRAINT check_default_action_set_exists CHECK (
        default_action_set_id IS NOT NULL AND 
        action_sets @> jsonb_build_array(jsonb_build_object('id', default_action_set_id))
    )
);

-- Navigation trees history (UPDATED SCHEMA)
CREATE TABLE navigation_trees_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    version_number integer NOT NULL,  -- UPDATED: More specific naming
    modification_type text NOT NULL CHECK (modification_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'restore'::text])),  -- UPDATED: Added enum constraint
    modified_by uuid,  -- UPDATED: Renamed from changed_by_user_id
    tree_data jsonb NOT NULL,  -- UPDATED: Made NOT NULL
    changes_summary text,  -- UPDATED: Renamed from change_description
    created_at timestamp with time zone DEFAULT now(),
    restored_from_version integer  -- UPDATED: Added for restore tracking
);

-- Add Foreign Key Constraints
ALTER TABLE navigation_nodes 
    ADD CONSTRAINT fk_navigation_nodes_tree 
    FOREIGN KEY (tree_id) REFERENCES navigation_trees(id) ON DELETE CASCADE;

ALTER TABLE navigation_edges
    ADD CONSTRAINT fk_navigation_edges_tree
    FOREIGN KEY (tree_id) REFERENCES navigation_trees(id) ON DELETE CASCADE;

-- Add Indexes for Performance
CREATE INDEX idx_navigation_trees_userinterface ON navigation_trees(userinterface_id);
CREATE INDEX idx_navigation_trees_team ON navigation_trees(team_id);
CREATE INDEX idx_navigation_trees_name ON navigation_trees(name);

-- Nested tree indexes
CREATE INDEX idx_navigation_trees_parent_tree ON navigation_trees(parent_tree_id);
CREATE INDEX idx_navigation_trees_parent_node ON navigation_trees(parent_node_id);
CREATE INDEX idx_navigation_trees_depth ON navigation_trees(tree_depth);
CREATE INDEX idx_navigation_trees_is_root ON navigation_trees(is_root_tree);

CREATE INDEX idx_navigation_nodes_tree ON navigation_nodes(tree_id);
CREATE INDEX idx_navigation_nodes_node_id ON navigation_nodes(node_id);
CREATE INDEX idx_navigation_nodes_team ON navigation_nodes(team_id);
CREATE INDEX idx_navigation_nodes_position ON navigation_nodes(position_x, position_y);
CREATE INDEX idx_navigation_nodes_has_subtree ON navigation_nodes(has_subtree);
CREATE INDEX idx_navigation_nodes_kpi_references ON navigation_nodes USING GIN (kpi_references);
CREATE INDEX idx_navigation_nodes_use_verifications_for_kpi ON navigation_nodes(use_verifications_for_kpi) WHERE use_verifications_for_kpi = TRUE;

CREATE INDEX idx_navigation_edges_tree ON navigation_edges(tree_id);
CREATE INDEX idx_navigation_edges_edge_id ON navigation_edges(edge_id);
CREATE INDEX idx_navigation_edges_source ON navigation_edges(source_node_id);
CREATE INDEX idx_navigation_edges_target ON navigation_edges(target_node_id);

-- NEW: Indexes for action_sets structure
CREATE INDEX idx_navigation_edges_action_sets ON navigation_edges USING GIN (action_sets);
CREATE INDEX idx_navigation_edges_default_action_set ON navigation_edges(default_action_set_id);
CREATE INDEX idx_navigation_edges_team ON navigation_edges(team_id);

CREATE INDEX idx_navigation_trees_history_tree ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team ON navigation_trees_history(team_id);

-- Viewport position index
CREATE INDEX idx_navigation_trees_viewport ON navigation_trees(viewport_x, viewport_y, viewport_zoom);

-- Add column comments
COMMENT ON COLUMN navigation_nodes.kpi_references IS 'KPI measurement references - same format as verifications, used to measure navigation performance timing';
COMMENT ON COLUMN navigation_nodes.use_verifications_for_kpi IS 'When TRUE, uses verifications[] for KPI measurement instead of kpi_references[]. Allows reusing existing verifications for performance measurement without duplication.';

-- Nested Tree Helper Functions
-- Function to get all descendant trees
CREATE OR REPLACE FUNCTION get_descendant_trees(root_tree_id uuid)
RETURNS TABLE(tree_id uuid, tree_name text, depth integer, parent_tree_id uuid, parent_node_id text)
LANGUAGE sql
AS $$
    WITH RECURSIVE tree_hierarchy AS (
        -- Base case: start with the root tree
        SELECT id, name, tree_depth, parent_tree_id, parent_node_id
        FROM navigation_trees 
        WHERE id = root_tree_id
        
        UNION ALL
        
        -- Recursive case: find children
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id
        FROM navigation_trees nt
        INNER JOIN tree_hierarchy th ON nt.parent_tree_id = th.id
    )
    SELECT id, name, tree_depth, parent_tree_id, parent_node_id 
    FROM tree_hierarchy;
$$;

-- Function to get tree path (breadcrumb)
CREATE OR REPLACE FUNCTION get_tree_path(target_tree_id uuid)
RETURNS TABLE(tree_id uuid, tree_name text, depth integer, node_id text)
LANGUAGE sql
AS $$
    WITH RECURSIVE tree_path AS (
        -- Base case: start with target tree
        SELECT id, name, tree_depth, parent_tree_id, parent_node_id
        FROM navigation_trees 
        WHERE id = target_tree_id
        
        UNION ALL
        
        -- Recursive case: go up to parents
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id
        FROM navigation_trees nt
        INNER JOIN tree_path tp ON nt.id = tp.parent_tree_id
    )
    SELECT id, name, tree_depth, parent_node_id 
    FROM tree_path 
    ORDER BY tree_depth ASC;
$$;

-- Function to update node subtree counts
CREATE OR REPLACE FUNCTION update_node_subtree_counts()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update parent node's subtree information
        UPDATE navigation_nodes 
        SET 
            has_subtree = true,
            subtree_count = (
                SELECT COUNT(*) 
                FROM navigation_trees 
                WHERE parent_tree_id = NEW.parent_tree_id 
                AND parent_node_id = NEW.parent_node_id
            )
        WHERE tree_id = NEW.parent_tree_id 
        AND node_id = NEW.parent_node_id;
        
        RETURN NEW;
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        -- Update parent node's subtree information
        UPDATE navigation_nodes 
        SET 
            subtree_count = (
                SELECT COUNT(*) 
                FROM navigation_trees 
                WHERE parent_tree_id = OLD.parent_tree_id 
                AND parent_node_id = OLD.parent_node_id
            )
        WHERE tree_id = OLD.parent_tree_id 
        AND node_id = OLD.parent_node_id;
        
        -- If no more subtrees, set has_subtree to false
        UPDATE navigation_nodes 
        SET has_subtree = false
        WHERE tree_id = OLD.parent_tree_id 
        AND node_id = OLD.parent_node_id
        AND subtree_count = 0;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$;

-- Create trigger to automatically update subtree counts
CREATE TRIGGER trigger_update_subtree_counts
    AFTER INSERT OR DELETE ON navigation_trees
    FOR EACH ROW
    EXECUTE FUNCTION update_node_subtree_counts();

-- Enable Row Level Security (RLS)
ALTER TABLE userinterfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies (updated to match actual working database)
CREATE POLICY "userinterfaces_open_access" ON userinterfaces
FOR ALL 
TO public
USING (true);

CREATE POLICY "navigation_trees_access_policy" ON navigation_trees
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

CREATE POLICY "navigation_nodes_access_policy" ON navigation_nodes
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

CREATE POLICY "navigation_edges_access_policy" ON navigation_edges
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

CREATE POLICY "navigation_trees_history_access_policy" ON navigation_trees_history
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- ==============================================================================
-- NESTED NAVIGATION SYNC TRIGGERS
-- ==============================================================================
-- Automatic synchronization for parent nodes in nested trees

-- Function to sync parent node label and screenshot to subtrees
CREATE OR REPLACE FUNCTION sync_parent_label_screenshot()
RETURNS TRIGGER AS $$
BEGIN
    -- Only sync if this node is referenced as a parent by subtrees
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
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to cascade delete subtrees when parent node is deleted
CREATE OR REPLACE FUNCTION cascade_delete_subtrees()
RETURNS TRIGGER AS $$
BEGIN
    -- When a parent node is deleted, delete all its subtrees
    DELETE FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Sync trigger (only fires on label or screenshot changes)
CREATE TRIGGER sync_parent_label_screenshot_trigger
    AFTER UPDATE ON navigation_nodes
    FOR EACH ROW
    WHEN (
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot'
    )
    EXECUTE FUNCTION sync_parent_label_screenshot();

-- Cascade delete trigger
CREATE TRIGGER cascade_delete_subtrees_trigger
    AFTER DELETE ON navigation_nodes
    FOR EACH ROW
    EXECUTE FUNCTION cascade_delete_subtrees(); 