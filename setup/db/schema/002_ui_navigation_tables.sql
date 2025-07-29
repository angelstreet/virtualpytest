-- VirtualPyTest UI & Navigation Tables Schema
-- This file contains tables for user interfaces, navigation trees, nodes, and edges

-- User interfaces (screens/apps being tested)
CREATE TABLE userinterfaces (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(name, team_id)
);

-- Navigation trees (renamed from original, now stores only metadata)
CREATE TABLE navigation_trees (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    userinterface_id uuid NOT NULL REFERENCES userinterfaces(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    root_node_id text, -- References first node's node_id
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(name, userinterface_id, team_id)
);

-- Navigation nodes (individual nodes with embedded verifications)
CREATE TABLE navigation_nodes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    node_id text NOT NULL, -- User-defined node identifier
    label text NOT NULL,
    position_x float NOT NULL DEFAULT 0,
    position_y float NOT NULL DEFAULT 0,
    node_type text NOT NULL DEFAULT 'default',
    style jsonb DEFAULT '{}',
    data jsonb DEFAULT '{}',
    verifications jsonb DEFAULT '[]', -- ✅ Embedded verification objects
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, node_id)
);

-- Navigation edges (individual edges with embedded actions and retry actions)
CREATE TABLE navigation_edges (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    edge_id text NOT NULL, -- User-defined edge identifier
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    label text,
    edge_type text NOT NULL DEFAULT 'default',
    style jsonb DEFAULT '{}',
    data jsonb DEFAULT '{}',
    actions jsonb DEFAULT '[]', -- ✅ Embedded action objects
    retry_actions jsonb DEFAULT '[]', -- ✅ Embedded retry action objects
    final_wait_time integer DEFAULT 0, -- ✅ Standard naming
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, edge_id)
);

-- Navigation trees history (for change tracking)
CREATE TABLE navigation_trees_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    version integer NOT NULL DEFAULT 1,
    change_description text,
    changed_by_user_id uuid,
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone DEFAULT now(),
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE
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

CREATE INDEX idx_navigation_nodes_tree ON navigation_nodes(tree_id);
CREATE INDEX idx_navigation_nodes_node_id ON navigation_nodes(node_id);
CREATE INDEX idx_navigation_nodes_team ON navigation_nodes(team_id);
CREATE INDEX idx_navigation_nodes_position ON navigation_nodes(position_x, position_y);

CREATE INDEX idx_navigation_edges_tree ON navigation_edges(tree_id);
CREATE INDEX idx_navigation_edges_edge_id ON navigation_edges(edge_id);
CREATE INDEX idx_navigation_edges_source ON navigation_edges(source_node_id);
CREATE INDEX idx_navigation_edges_target ON navigation_edges(target_node_id);
CREATE INDEX idx_navigation_edges_team ON navigation_edges(team_id);

CREATE INDEX idx_navigation_trees_history_tree ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team ON navigation_trees_history(team_id);

-- Enable Row Level Security (RLS)
ALTER TABLE userinterfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "userinterfaces_access_policy" ON userinterfaces
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

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