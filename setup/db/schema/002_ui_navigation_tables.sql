-- VirtualPyTest UI and Navigation Tables Schema
-- This file contains tables for user interfaces and navigation trees
-- NEW ARCHITECTURE: Normalized nodes/edges with embedded actions/verifications

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

-- Navigation trees (metadata container only)
CREATE TABLE navigation_trees (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    root_node_id text, -- Reference to node_id in navigation_nodes
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
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
    verifications jsonb DEFAULT '[]', -- Array of verification objects
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, node_id)
);

-- Navigation edges (connections between nodes with embedded actions)
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
    actions jsonb DEFAULT '[]', -- Array of action objects
    retry_actions jsonb DEFAULT '[]', -- Array of retry action objects
    final_wait_time integer DEFAULT 0,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    UNIQUE(tree_id, edge_id)
);

-- Navigation tree version history (for rollback capability)
CREATE TABLE navigation_trees_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    version_number integer NOT NULL,
    modification_type text NOT NULL CHECK (modification_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'restore'::text])),
    modified_by uuid,
    changes_summary text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    restored_from_version integer
);

-- Add foreign key constraints for node references
ALTER TABLE navigation_edges 
ADD CONSTRAINT fk_navigation_edges_source_node 
FOREIGN KEY (tree_id, source_node_id) REFERENCES navigation_nodes(tree_id, node_id) ON DELETE CASCADE;

ALTER TABLE navigation_edges 
ADD CONSTRAINT fk_navigation_edges_target_node 
FOREIGN KEY (tree_id, target_node_id) REFERENCES navigation_nodes(tree_id, node_id) ON DELETE CASCADE;

-- Add indexes for performance
CREATE INDEX idx_userinterfaces_team_id ON userinterfaces(team_id);
CREATE INDEX idx_navigation_trees_team_id ON navigation_trees(team_id);
CREATE INDEX idx_navigation_trees_userinterface ON navigation_trees(userinterface_id);
CREATE INDEX idx_navigation_nodes_tree_id ON navigation_nodes(tree_id);
CREATE INDEX idx_navigation_nodes_team_id ON navigation_nodes(team_id);
CREATE INDEX idx_navigation_nodes_node_id ON navigation_nodes(tree_id, node_id);
CREATE INDEX idx_navigation_edges_tree_id ON navigation_edges(tree_id);
CREATE INDEX idx_navigation_edges_team_id ON navigation_edges(team_id);
CREATE INDEX idx_navigation_edges_source ON navigation_edges(tree_id, source_node_id);
CREATE INDEX idx_navigation_edges_target ON navigation_edges(tree_id, target_node_id);
CREATE INDEX idx_navigation_trees_history_tree_id ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team_id ON navigation_trees_history(team_id);

-- Add comments
COMMENT ON TABLE userinterfaces IS 'User interface definitions and configurations';
COMMENT ON TABLE navigation_trees IS 'Navigation tree metadata containers';
COMMENT ON TABLE navigation_nodes IS 'Individual navigation nodes with embedded verifications';
COMMENT ON TABLE navigation_edges IS 'Navigation edges connecting nodes with embedded actions';
COMMENT ON TABLE navigation_trees_history IS 'Version history and audit trail for navigation trees with rollback capability';

COMMENT ON COLUMN navigation_nodes.verifications IS 'JSONB array of verification objects: [{"name": "check_element", "device_model": "android_mobile", "command": "element_exists", "params": {"element_id": "button"}}]';
COMMENT ON COLUMN navigation_edges.actions IS 'JSONB array of action objects: [{"name": "tap_button", "device_model": "android_mobile", "command": "tap_coordinates", "params": {"x": 100, "y": 200, "wait_time": 500}}]';
COMMENT ON COLUMN navigation_edges.retry_actions IS 'JSONB array of retry action objects with same structure as actions';
COMMENT ON COLUMN navigation_edges.final_wait_time IS 'Wait time in milliseconds after all edge actions complete';

-- Enable Row Level Security (RLS)
ALTER TABLE userinterfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_edges ENABLE ROW LEVEL SECURITY;
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

-- RLS Policies for navigation_nodes table
CREATE POLICY "Team members can access navigation nodes" ON navigation_nodes
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for navigation_edges table
CREATE POLICY "Team members can access navigation edges" ON navigation_edges
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

-- Migration views for backward compatibility during transition (TEMPORARY)
CREATE VIEW navigation_trees_legacy AS
SELECT 
    t.id,
    t.name,
    t.userinterface_id,
    t.team_id,
    t.description,
    t.root_node_id,
    t.created_at,
    t.updated_at,
    json_build_object(
        'nodes', COALESCE(nodes_json.nodes, '[]'::json),
        'edges', COALESCE(edges_json.edges, '[]'::json)
    ) as metadata
FROM navigation_trees t
LEFT JOIN (
    SELECT 
        tree_id,
        json_agg(json_build_object(
            'id', node_id,
            'type', node_type,
            'position', json_build_object('x', position_x, 'y', position_y),
            'data', json_build_object(
                'label', label,
                'verifications', verifications
            )
        )) as nodes
    FROM navigation_nodes 
    GROUP BY tree_id
) nodes_json ON t.id = nodes_json.tree_id
LEFT JOIN (
    SELECT 
        tree_id,
        json_agg(json_build_object(
            'id', edge_id,
            'source', source_node_id,
            'target', target_node_id,
            'type', edge_type,
            'data', json_build_object(
                'label', label,
                'actions', actions,
                'retryActions', retry_actions,
                'final_wait_time', final_wait_time
            )
        )) as edges
    FROM navigation_edges 
    GROUP BY tree_id
) edges_json ON t.id = edges_json.tree_id;

COMMENT ON VIEW navigation_trees_legacy IS 'Temporary backward compatibility view - reconstructs old metadata JSONB structure from normalized tables. Remove after frontend migration is complete.'; 