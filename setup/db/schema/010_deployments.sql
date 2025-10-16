-- 010_deployments.sql
-- Periodic Deployment System
-- Manages scheduled script executions on hosts with APScheduler integration

-- Drop existing tables if they exist (for clean recreation)
DROP TABLE IF EXISTS deployment_executions CASCADE;
DROP TABLE IF EXISTS deployments CASCADE;

-- Create deployments table
CREATE TABLE deployments (
    -- Primary identification
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Deployment configuration
    name TEXT NOT NULL,
    host_name TEXT NOT NULL,
    device_id TEXT NOT NULL,
    script_name TEXT NOT NULL,
    userinterface_name TEXT NOT NULL,
    parameters TEXT,
    
    -- Schedule configuration (cron-based)
    cron_expression TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    max_executions INTEGER,
    
    -- Execution tracking
    execution_count INTEGER DEFAULT 0 NOT NULL,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Status management
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'stopped', 'completed', 'expired')),
    
    -- Timestamps and audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Create deployment_executions table
CREATE TABLE deployment_executions (
    -- Primary identification
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    script_result_id UUID REFERENCES script_results(id),
    
    -- Execution tracking
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, -- When it was supposed to run
    started_at TIMESTAMP WITH TIME ZONE, -- When execution actually started (null if skipped)
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'skipped')),
    skip_reason TEXT, -- 'device_locked' if skipped
    success BOOLEAN,
    error_message TEXT
);

-- Create indexes for performance
CREATE INDEX idx_deployments_host_status ON deployments(host_name, status);
CREATE INDEX idx_deployments_team ON deployments(team_id);
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_cron ON deployments(cron_expression) WHERE status = 'active';
CREATE INDEX idx_deployments_next_run ON deployments(last_executed_at) WHERE status = 'active';
CREATE INDEX idx_deployment_executions_deployment ON deployment_executions(deployment_id);
CREATE INDEX idx_deployment_executions_started ON deployment_executions(started_at DESC);
CREATE INDEX idx_deployment_executions_status ON deployment_executions(status, scheduled_at);

-- Enable Row Level Security
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deployment_executions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Team-based access
CREATE POLICY "deployments_team_access" ON deployments
    FOR ALL USING (
        (auth.uid() IS NULL) OR 
        (auth.role() = 'service_role'::text) OR 
        (team_id = (SELECT team_id FROM users WHERE id = auth.uid()))
    );

CREATE POLICY "deployment_executions_team_access" ON deployment_executions
    FOR ALL USING (
        (auth.uid() IS NULL) OR 
        (auth.role() = 'service_role'::text) OR 
        (deployment_id IN (SELECT id FROM deployments WHERE team_id = (SELECT team_id FROM users WHERE id = auth.uid())))
    );

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON deployments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON deployment_executions TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE deployments IS 'Periodic Deployment System - scheduled script executions managed by APScheduler with cron expressions';
COMMENT ON COLUMN deployments.name IS 'User-friendly deployment name';
COMMENT ON COLUMN deployments.host_name IS 'Target host for deployment execution';
COMMENT ON COLUMN deployments.device_id IS 'Target device identifier';
COMMENT ON COLUMN deployments.script_name IS 'Script to execute';
COMMENT ON COLUMN deployments.cron_expression IS 'Cron expression for scheduling (e.g., */10 * * * * for every 10 minutes)';
COMMENT ON COLUMN deployments.start_date IS 'Optional: When to start scheduling (NULL = start immediately)';
COMMENT ON COLUMN deployments.end_date IS 'Optional: When to stop scheduling (NULL = run forever)';
COMMENT ON COLUMN deployments.max_executions IS 'Optional: Maximum number of executions (NULL = unlimited)';
COMMENT ON COLUMN deployments.execution_count IS 'Number of times this deployment has executed';
COMMENT ON COLUMN deployments.last_executed_at IS 'Timestamp of last execution';
COMMENT ON COLUMN deployments.status IS 'Deployment status: active, paused, stopped, completed, or expired';
COMMENT ON TABLE deployment_executions IS 'History of deployment executions - skips if device locked';
COMMENT ON COLUMN deployment_executions.script_result_id IS 'Link to script_results table for execution details';
COMMENT ON COLUMN deployment_executions.scheduled_at IS 'When deployment was scheduled to run';
COMMENT ON COLUMN deployment_executions.started_at IS 'When execution actually started (null if skipped)';
COMMENT ON COLUMN deployment_executions.status IS 'Execution status: running, completed, failed, or skipped';
COMMENT ON COLUMN deployment_executions.skip_reason IS 'Why execution was skipped (e.g., device_locked)';

