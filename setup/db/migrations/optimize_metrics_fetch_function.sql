-- Migration: Optimize metrics fetching using existing aggregated tables
-- Description: Use pre-aggregated node_metrics and edge_metrics tables for fast reads
-- Performance: ~5ms reads (data already aggregated, just needs to be fetched)

-- ============================================================================
-- OPTIMIZED FUNCTION TO GET ALL TREE METRICS IN ONE QUERY
-- ============================================================================

CREATE OR REPLACE FUNCTION get_tree_metrics_optimized(
    p_tree_id UUID,
    p_team_id UUID
)
RETURNS JSON
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
    v_node_metrics JSON;
    v_edge_metrics JSON;
    v_global_confidence NUMERIC;
    v_confidence_distribution JSON;
    v_all_confidences NUMERIC[];
    v_confidence NUMERIC;
BEGIN
    -- Get all node metrics for the tree
    SELECT json_object_agg(
        node_id,
        json_build_object(
            'volume', total_executions,
            'success_rate', success_rate::float,
            'avg_execution_time', avg_execution_time_ms,
            'confidence', CASE 
                WHEN total_executions = 0 THEN 0.0
                WHEN total_executions < 10 THEN success_rate::float * (total_executions / 10.0)
                ELSE success_rate::float
            END
        )
    )
    INTO v_node_metrics
    FROM node_metrics
    WHERE team_id = p_team_id
    AND tree_id = p_tree_id;
    
    -- Get all edge metrics for the tree (keyed by edge_id#action_set_id)
    SELECT json_object_agg(
        edge_id || COALESCE('#' || action_set_id, ''),
        json_build_object(
            'volume', total_executions,
            'success_rate', success_rate::float,
            'avg_execution_time', avg_execution_time_ms,
            'confidence', CASE 
                WHEN total_executions = 0 THEN 0.0
                WHEN total_executions < 10 THEN success_rate::float * (total_executions / 10.0)
                ELSE success_rate::float
            END
        )
    )
    INTO v_edge_metrics
    FROM edge_metrics
    WHERE team_id = p_team_id
    AND tree_id = p_tree_id;
    
    -- Calculate all confidences for distribution
    SELECT array_agg(confidence)
    INTO v_all_confidences
    FROM (
        -- Node confidences
        SELECT 
            CASE 
                WHEN total_executions = 0 THEN 0.0
                WHEN total_executions < 10 THEN success_rate::float * (total_executions / 10.0)
                ELSE success_rate::float
            END as confidence
        FROM node_metrics
        WHERE team_id = p_team_id AND tree_id = p_tree_id
        
        UNION ALL
        
        -- Edge confidences
        SELECT 
            CASE 
                WHEN total_executions = 0 THEN 0.0
                WHEN total_executions < 10 THEN success_rate::float * (total_executions / 10.0)
                ELSE success_rate::float
            END as confidence
        FROM edge_metrics
        WHERE team_id = p_team_id AND tree_id = p_tree_id
    ) all_conf;
    
    -- Calculate global confidence (average of all)
    IF v_all_confidences IS NOT NULL AND array_length(v_all_confidences, 1) > 0 THEN
        SELECT AVG(c) INTO v_global_confidence FROM unnest(v_all_confidences) c;
    ELSE
        v_global_confidence := 0.0;
    END IF;
    
    -- Calculate confidence distribution
    SELECT json_build_object(
        'high', COUNT(*) FILTER (WHERE c >= 0.8),
        'medium', COUNT(*) FILTER (WHERE c >= 0.5 AND c < 0.8),
        'low', COUNT(*) FILTER (WHERE c >= 0.1 AND c < 0.5),
        'untested', COUNT(*) FILTER (WHERE c < 0.1)
    )
    INTO v_confidence_distribution
    FROM unnest(v_all_confidences) c;
    
    -- Return combined metrics
    RETURN json_build_object(
        'success', true,
        'nodes', COALESCE(v_node_metrics, '{}'::json),
        'edges', COALESCE(v_edge_metrics, '{}'::json),
        'global_confidence', COALESCE(v_global_confidence, 0.0),
        'confidence_distribution', COALESCE(v_confidence_distribution, json_build_object('high', 0, 'medium', 0, 'low', 0, 'untested', 0))
    );
END;
$$;

COMMENT ON FUNCTION get_tree_metrics_optimized(UUID, UUID) IS 
'Read pre-aggregated metrics from node_metrics and edge_metrics tables. 
Extremely fast (~5ms) because data is already aggregated.
Calculates confidence and distribution on-the-fly.';

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_tree_metrics_optimized(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_tree_metrics_optimized(UUID, UUID) TO service_role;

-- ============================================================================
-- CREATE INDEX IF NOT EXISTS (for faster lookups)
-- ============================================================================

-- Indexes for node_metrics
CREATE INDEX IF NOT EXISTS idx_node_metrics_tree_team 
ON node_metrics(tree_id, team_id);

CREATE INDEX IF NOT EXISTS idx_node_metrics_node 
ON node_metrics(node_id, team_id);

-- Indexes for edge_metrics
CREATE INDEX IF NOT EXISTS idx_edge_metrics_tree_team 
ON edge_metrics(tree_id, team_id);

CREATE INDEX IF NOT EXISTS idx_edge_metrics_edge_action 
ON edge_metrics(edge_id, action_set_id, team_id);

-- ============================================================================
-- BACKWARD COMPATIBILITY: Keep old function name as alias
-- ============================================================================

CREATE OR REPLACE FUNCTION get_tree_metrics_from_mv(
    p_tree_id UUID,
    p_team_id UUID
)
RETURNS JSON
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT get_tree_metrics_optimized(p_tree_id, p_team_id);
$$;

COMMENT ON FUNCTION get_tree_metrics_from_mv(UUID, UUID) IS 
'Backward compatibility alias for get_tree_metrics_optimized.';

GRANT EXECUTE ON FUNCTION get_tree_metrics_from_mv(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_tree_metrics_from_mv(UUID, UUID) TO service_role;

