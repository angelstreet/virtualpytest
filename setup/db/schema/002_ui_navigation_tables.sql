-- VirtualPyTest UI and Navigation Tables Schema
-- This file contains tables for user interfaces and navigation trees

-- User interface definitions
CREATE TABLE userinterfaces (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    models text[] NOT NULL DEFAULT '{}'::text[],
    min_version character varying,
    max_version character varying,
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

-- Enable Row Level Security (RLS)
ALTER TABLE userinterfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for userinterfaces table
CREATE POLICY "Allow userinterfaces access" ON userinterfaces
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for navigation_trees table
CREATE POLICY "Team members can access navigation trees" ON navigation_trees
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for navigation_trees_history table
CREATE POLICY "navigation_trees_history_policy" ON navigation_trees_history
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (EXISTS ( SELECT 1
   FROM team_members tm
  WHERE ((tm.team_id = navigation_trees_history.team_id) AND (tm.profile_id = auth.uid()))))); 