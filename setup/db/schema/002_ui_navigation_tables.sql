-- VirtualPyTest UI and Navigation Tables Schema
-- This file contains tables for user interfaces and navigation trees

-- User interface definitions
CREATE TABLE userinterfaces (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    models uuid[] DEFAULT '{}'::uuid[],
    min_version character varying,
    max_version character varying,
    description text,
    config jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Navigation tree structures
CREATE TABLE navigation_trees (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    creator_id uuid,
    parent_tree_id uuid,
    tree_level integer DEFAULT 0,
    is_root boolean DEFAULT true,
    root_tree_id uuid,
    tree_path text[] DEFAULT '{}'::text[],
    metadata jsonb DEFAULT '{}'::jsonb,
    root_node_id uuid,
    parent_node_id text COMMENT ON COLUMN navigation_trees.parent_node_id IS 'ID of the node that opens this sub-tree (for nested navigation)'
);

-- Navigation tree version history
CREATE TABLE navigation_trees_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    version_number integer NOT NULL,
    modification_type text NOT NULL CHECK (modification_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'restore'::text])),
    modified_by uuid,
    tree_data jsonb NOT NULL,
    changes_summary text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    restored_from_version integer
);

-- Add foreign key constraints after table creation
ALTER TABLE navigation_trees 
ADD CONSTRAINT fk_navigation_trees_root 
FOREIGN KEY (root_tree_id) REFERENCES navigation_trees(id) ON DELETE SET NULL;

ALTER TABLE navigation_trees 
ADD CONSTRAINT navigation_trees_parent_tree_id_fkey 
FOREIGN KEY (parent_tree_id) REFERENCES navigation_trees(id) ON DELETE CASCADE;

-- Add indexes for performance
CREATE INDEX idx_userinterfaces_team_id ON userinterfaces(team_id);
CREATE INDEX idx_navigation_trees_team_id ON navigation_trees(team_id);
CREATE INDEX idx_navigation_trees_userinterface ON navigation_trees(userinterface_id);
CREATE INDEX idx_navigation_trees_parent ON navigation_trees(parent_tree_id);
CREATE INDEX idx_navigation_trees_root ON navigation_trees(root_tree_id);
CREATE INDEX idx_navigation_trees_is_root ON navigation_trees(is_root);
CREATE INDEX idx_navigation_trees_history_tree_id ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team_id ON navigation_trees_history(team_id);

-- Add comments
COMMENT ON TABLE userinterfaces IS 'User interface definitions and configurations';
COMMENT ON TABLE navigation_trees IS 'Navigation tree structures for UI testing';
COMMENT ON TABLE navigation_trees_history IS 'Version history and audit trail for navigation trees with rollback capability'; 