-- 008_ai_plan_generation.sql
-- AI Plan Generation Cache System
-- Clean implementation with no backward compatibility

-- Drop existing table if it exists (for clean recreation)
DROP TABLE IF EXISTS ai_plan_generation CASCADE;

-- Create the ai_plan_generation table
CREATE TABLE ai_plan_generation (
    -- Primary identification
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fingerprint VARCHAR(32) UNIQUE NOT NULL,
    
    -- Prompt information
    original_prompt TEXT NOT NULL,
    normalized_prompt VARCHAR(255) NOT NULL,
    
    -- Context signature
    device_model VARCHAR(100) NOT NULL,
    userinterface_name VARCHAR(100) NOT NULL,
    available_nodes JSONB NOT NULL,
    
    -- Plan data
    plan JSONB NOT NULL,
    
    -- Performance metrics
    success_rate DECIMAL(5,4) NOT NULL DEFAULT 0.0000,
    execution_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    
    -- Usage tracking
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Team context (for multi-tenancy)
    team_id UUID NOT NULL REFERENCES teams(id)
);

-- Create indexes for performance
CREATE INDEX idx_ai_plan_generation_fingerprint ON ai_plan_generation(fingerprint);
CREATE INDEX idx_ai_plan_generation_normalized_prompt ON ai_plan_generation(normalized_prompt);
CREATE INDEX idx_ai_plan_generation_device_interface ON ai_plan_generation(device_model, userinterface_name);
CREATE INDEX idx_ai_plan_generation_team ON ai_plan_generation(team_id);
CREATE INDEX idx_ai_plan_generation_success_rate ON ai_plan_generation(success_rate DESC, execution_count DESC);
CREATE INDEX idx_ai_plan_generation_last_used ON ai_plan_generation(last_used DESC);
CREATE INDEX idx_ai_plan_generation_lookup ON ai_plan_generation(normalized_prompt, device_model, userinterface_name, success_rate DESC);
CREATE INDEX idx_ai_plan_generation_available_nodes ON ai_plan_generation USING GIN(available_nodes);
CREATE INDEX idx_ai_plan_generation_plan ON ai_plan_generation USING GIN(plan);

-- Enable Row Level Security
ALTER TABLE ai_plan_generation ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Match existing table pattern
CREATE POLICY "ai_plan_generation_access_policy" ON ai_plan_generation
    FOR ALL USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Function to update plan metrics after execution
CREATE OR REPLACE FUNCTION update_ai_plan_metrics(
    p_fingerprint VARCHAR(32),
    p_success BOOLEAN,
    p_execution_time_ms INTEGER,
    p_team_id UUID
) RETURNS VOID AS $$
BEGIN
    UPDATE ai_plan_generation 
    SET 
        execution_count = execution_count + 1,
        success_count = CASE WHEN p_success THEN success_count + 1 ELSE success_count END,
        success_rate = (CASE WHEN p_success THEN success_count + 1 ELSE success_count END)::DECIMAL / (execution_count + 1),
        last_used = NOW()
    WHERE fingerprint = p_fingerprint AND team_id = p_team_id;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old plans
CREATE OR REPLACE FUNCTION cleanup_ai_plan_generation(
    p_team_id UUID,
    p_days_old INTEGER DEFAULT 90,
    p_min_success_rate DECIMAL DEFAULT 0.3
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete old plans with low success rates
    DELETE FROM ai_plan_generation 
    WHERE team_id = p_team_id
    AND last_used < NOW() - INTERVAL '1 day' * p_days_old
    AND success_rate < p_min_success_rate;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_plan_generation TO authenticated;
GRANT EXECUTE ON FUNCTION update_ai_plan_metrics TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_ai_plan_generation TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE ai_plan_generation IS 'AI Plan Generation Cache - stores successful AI-generated plans for reuse';
COMMENT ON COLUMN ai_plan_generation.fingerprint IS 'MD5 hash of normalized prompt + context signature for fast lookups';
COMMENT ON COLUMN ai_plan_generation.normalized_prompt IS 'Standardized prompt format for semantic matching';
COMMENT ON COLUMN ai_plan_generation.available_nodes IS 'JSON array of navigation nodes available during plan generation';
COMMENT ON COLUMN ai_plan_generation.plan IS 'Complete AI-generated plan with steps and metadata';
COMMENT ON COLUMN ai_plan_generation.success_rate IS 'Calculated success rate (success_count / execution_count)';
COMMENT ON FUNCTION update_ai_plan_metrics IS 'Updates plan performance metrics after execution';
COMMENT ON FUNCTION cleanup_ai_plan_generation IS 'Removes old plans with poor performance';
