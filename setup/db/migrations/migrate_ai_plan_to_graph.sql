-- Migration: Rename ai_plan_generation table to ai_graph_cache
-- Reason: We generate graphs, not plans (align naming with codebase)

-- Step 1: Rename table
ALTER TABLE ai_plan_generation RENAME TO ai_graph_cache;

-- Step 2: Rename indexes
ALTER INDEX idx_ai_plan_generation_fingerprint RENAME TO idx_ai_graph_cache_fingerprint;
ALTER INDEX idx_ai_plan_generation_normalized_prompt RENAME TO idx_ai_graph_cache_normalized_prompt;
ALTER INDEX idx_ai_plan_generation_device_interface RENAME TO idx_ai_graph_cache_device_interface;
ALTER INDEX idx_ai_plan_generation_team RENAME TO idx_ai_graph_cache_team;
ALTER INDEX idx_ai_plan_generation_success_rate RENAME TO idx_ai_graph_cache_success_rate;
ALTER INDEX idx_ai_plan_generation_last_used RENAME TO idx_ai_graph_cache_last_used;
ALTER INDEX idx_ai_plan_generation_lookup RENAME TO idx_ai_graph_cache_lookup;
ALTER INDEX idx_ai_plan_generation_available_nodes RENAME TO idx_ai_graph_cache_available_nodes;
ALTER INDEX idx_ai_plan_generation_plan RENAME TO idx_ai_graph_cache_graph;

-- Step 3: Rename column (plan -> graph)
ALTER TABLE ai_graph_cache RENAME COLUMN plan TO graph;

-- Step 4: Rename policy
DROP POLICY IF EXISTS ai_plan_generation_access_policy ON ai_graph_cache;
CREATE POLICY "ai_graph_cache_access_policy" ON ai_graph_cache
  USING (team_id::text = current_setting('request.jwt.claims', true)::json->>'team_id');

-- Step 5: Drop and recreate function with new name
DROP FUNCTION IF EXISTS cleanup_ai_plan_generation(uuid, int, numeric);

CREATE OR REPLACE FUNCTION cleanup_ai_graph_cache(
    p_team_id uuid,
    p_days_old int DEFAULT 90,
    p_min_success_rate numeric DEFAULT 0.3
) RETURNS int AS $$
DECLARE
    deleted_count int;
BEGIN
    DELETE FROM ai_graph_cache 
    WHERE team_id = p_team_id
      AND last_used < (NOW() - (p_days_old || ' days')::interval)
      AND success_rate < p_min_success_rate;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Step 6: Update grants
REVOKE ALL ON ai_graph_cache FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_graph_cache TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_ai_graph_cache TO authenticated;

-- Step 7: Update comments
COMMENT ON TABLE ai_graph_cache IS 'AI Graph Cache - stores successful AI-generated graphs for reuse';
COMMENT ON COLUMN ai_graph_cache.fingerprint IS 'MD5 hash of normalized prompt + context signature for fast lookups';
COMMENT ON COLUMN ai_graph_cache.normalized_prompt IS 'Standardized prompt format for semantic matching';
COMMENT ON COLUMN ai_graph_cache.available_nodes IS 'JSON array of navigation nodes available during graph generation';
COMMENT ON COLUMN ai_graph_cache.graph IS 'Complete AI-generated graph with nodes and edges';
COMMENT ON COLUMN ai_graph_cache.success_rate IS 'Calculated success rate (success_count / execution_count)';
COMMENT ON FUNCTION cleanup_ai_graph_cache IS 'Removes old graphs with poor performance';

-- Migration complete

