-- Migration: Refresh materialized view after KPI column removal
-- Date: 2025-10-21
-- Description: Drop and recreate materialized view after navigation_nodes schema change

-- Drop the existing materialized view (it's now invalid due to column removal)
DROP MATERIALIZED VIEW IF EXISTS mv_full_navigation_trees CASCADE;

-- Recreate materialized view without KPI fields
CREATE MATERIALIZED VIEW mv_full_navigation_trees AS
SELECT 
    t.id as tree_id,
    t.team_id,
    json_build_object(
        'success', true,
        'tree', row_to_json(t.*),
        'nodes', COALESCE(
            (SELECT json_agg(n ORDER BY n.created_at)
             FROM (
                SELECT 
                    id,
                    tree_id,
                    node_id,
                    node_type,
                    label,
                    position_x,
                    position_y,
                    data,
                    style,
                    team_id,
                    has_subtree,
                    subtree_count,
                    verifications,
                    created_at,
                    updated_at
                FROM navigation_nodes
                WHERE tree_id = t.id
                AND team_id = t.team_id
             ) n),
            '[]'::json
        ),
        'edges', COALESCE(
            (SELECT json_agg(e ORDER BY e.created_at)
             FROM (
                SELECT 
                    id,
                    tree_id,
                    edge_id,
                    source_node_id,
                    target_node_id,
                    label,
                    data,
                    team_id,
                    action_sets,
                    default_action_set_id,
                    final_wait_time,
                    created_at,
                    updated_at
                FROM navigation_edges
                WHERE tree_id = t.id
                AND team_id = t.team_id
             ) e),
            '[]'::json
        )
    ) as full_tree_data,
    now() as last_refreshed
FROM navigation_trees t;

-- Create unique index for fast lookups by tree_id and team_id
CREATE UNIQUE INDEX idx_mv_full_trees_tree_team 
ON mv_full_navigation_trees(tree_id, team_id);

-- Grant permissions
GRANT SELECT ON mv_full_navigation_trees TO authenticated;
GRANT SELECT ON mv_full_navigation_trees TO service_role;

