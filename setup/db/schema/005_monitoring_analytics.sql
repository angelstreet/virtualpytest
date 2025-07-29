-- VirtualPyTest Monitoring and Analytics Tables Schema
-- This file contains tables for alerts, metrics, and analytics

-- System alerts and monitoring incidents
CREATE TABLE alerts (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    host_name text NOT NULL,
    device_id text NOT NULL COMMENT ON COLUMN alerts.device_id IS 'device1, device2, device3',
    incident_type text NOT NULL CHECK (incident_type = ANY (ARRAY['blackscreen'::text, 'freeze'::text, 'errors'::text, 'audio_loss'::text])) COMMENT ON COLUMN alerts.incident_type IS 'Type of incident: blackscreen, freeze, errors, or audio_loss',
    status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'resolved'::text])) COMMENT ON COLUMN alerts.status IS 'Current status: active or resolved',
    consecutive_count integer NOT NULL DEFAULT 1 CHECK (consecutive_count > 0) COMMENT ON COLUMN alerts.consecutive_count IS 'Number of consecutive detections that triggered this alert',
    start_time timestamp with time zone NOT NULL DEFAULT now() COMMENT ON COLUMN alerts.start_time IS 'When the incident was first detected',
    end_time timestamp with time zone COMMENT ON COLUMN alerts.end_time IS 'When the incident was resolved (NULL if still active)',
    metadata jsonb COMMENT ON COLUMN alerts.metadata IS 'Additional context about the incident (analysis results, file paths, etc.)',
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Performance heatmap data
CREATE TABLE heatmaps (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid REFERENCES teams(id) ON DELETE CASCADE,
    timestamp character varying NOT NULL,
    job_id uuid NOT NULL,
    mosaic_r2_path character varying,
    mosaic_r2_url character varying,
    metadata_r2_path character varying,
    metadata_r2_url character varying,
    html_r2_path character varying,
    html_r2_url character varying,
    hosts_included integer DEFAULT 0,
    hosts_total integer DEFAULT 0,
    incidents_count integer DEFAULT 0,
    generated_at timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);

-- Navigation node aggregated metrics (for verifications embedded in nodes)
CREATE TABLE node_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Aggregated metrics for all verifications in this node
    total_executions integer DEFAULT 0 NOT NULL,
    successful_executions integer DEFAULT 0 NOT NULL,
    failed_executions integer DEFAULT 0 NOT NULL,
    success_rate numeric(5,4) DEFAULT 0.0 NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    avg_execution_time_ms integer DEFAULT 0 NOT NULL,
    min_execution_time_ms integer DEFAULT 0 NOT NULL,
    max_execution_time_ms integer DEFAULT 0 NOT NULL,
    
    -- Verification-specific metrics
    verification_count integer DEFAULT 0 NOT NULL COMMENT ON COLUMN node_metrics.verification_count IS 'Number of verifications embedded in this node',
    verification_types jsonb DEFAULT '[]'::jsonb COMMENT ON COLUMN node_metrics.verification_types IS 'Array of verification types (image, text, adb, etc.)',
    
    -- Timestamps
    last_execution_at timestamp with time zone,
    last_success_at timestamp with time zone,
    last_failure_at timestamp with time zone,
    
    -- Device context
    device_model character varying,
    device_id character varying,
    
    -- Metadata for additional context
    metadata jsonb DEFAULT '{}'::jsonb,
    
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    
    -- Ensure unique metrics per node per team
    UNIQUE(node_id, tree_id, team_id)
);

-- Navigation edge aggregated metrics (for actions embedded in edges)
CREATE TABLE edge_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    edge_id character varying NOT NULL,
    source_node_id character varying NOT NULL,
    target_node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Aggregated metrics for all actions in this edge
    total_executions integer DEFAULT 0 NOT NULL,
    successful_executions integer DEFAULT 0 NOT NULL,
    failed_executions integer DEFAULT 0 NOT NULL,
    success_rate numeric(5,4) DEFAULT 0.0 NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    avg_execution_time_ms integer DEFAULT 0 NOT NULL,
    min_execution_time_ms integer DEFAULT 0 NOT NULL,
    max_execution_time_ms integer DEFAULT 0 NOT NULL,
    
    -- Action-specific metrics
    action_count integer DEFAULT 0 NOT NULL COMMENT ON COLUMN edge_metrics.action_count IS 'Number of actions embedded in this edge',
    retry_action_count integer DEFAULT 0 NOT NULL COMMENT ON COLUMN edge_metrics.retry_action_count IS 'Number of retry actions embedded in this edge',
    action_types jsonb DEFAULT '[]'::jsonb COMMENT ON COLUMN edge_metrics.action_types IS 'Array of action types (tap_coordinates, click_element, etc.)',
    final_wait_time integer DEFAULT 2000 COMMENT ON COLUMN edge_metrics.final_wait_time IS 'Final wait time for this edge in milliseconds',
    
    -- Retry metrics
    retry_execution_count integer DEFAULT 0 NOT NULL COMMENT ON COLUMN edge_metrics.retry_execution_count IS 'Number of times retry actions were executed',
    retry_success_count integer DEFAULT 0 NOT NULL COMMENT ON COLUMN edge_metrics.retry_success_count IS 'Number of times retry actions succeeded',
    retry_success_rate numeric(5,4) DEFAULT 0.0 NOT NULL CHECK (retry_success_rate >= 0.0 AND retry_success_rate <= 1.0),
    
    -- Timestamps
    last_execution_at timestamp with time zone,
    last_success_at timestamp with time zone,
    last_failure_at timestamp with time zone,
    
    -- Device context
    device_model character varying,
    device_id character varying,
    
    -- Metadata for additional context
    metadata jsonb DEFAULT '{}'::jsonb,
    
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    
    -- Ensure unique metrics per edge per team
    UNIQUE(edge_id, tree_id, team_id)
);

-- Individual action execution records (detailed history)
CREATE TABLE action_execution_history (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    edge_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Action details
    action_command character varying NOT NULL,
    action_params jsonb DEFAULT '{}'::jsonb,
    action_index integer NOT NULL COMMENT ON COLUMN action_execution_history.action_index IS 'Index of action within edge actions array',
    is_retry_action boolean DEFAULT false NOT NULL,
    
    -- Execution results
    success boolean NOT NULL,
    execution_time_ms integer NOT NULL,
    error_message text,
    error_details jsonb,
    
    -- Device context
    device_model character varying,
    device_id character varying,
    host_name character varying,
    
    -- Execution context
    execution_id character varying COMMENT ON COLUMN action_execution_history.execution_id IS 'Links to execution_results table',
    script_result_id character varying,
    script_context character varying DEFAULT 'direct',
    
    executed_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

-- Individual verification execution records (detailed history)
CREATE TABLE verification_execution_history (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Verification details
    verification_type character varying NOT NULL,
    verification_command character varying NOT NULL,
    verification_params jsonb DEFAULT '{}'::jsonb,
    verification_index integer NOT NULL COMMENT ON COLUMN verification_execution_history.verification_index IS 'Index of verification within node verifications array',
    
    -- Execution results
    success boolean NOT NULL,
    execution_time_ms integer NOT NULL,
    confidence_score numeric(5,4),
    threshold_used numeric(5,4),
    error_message text,
    error_details jsonb,
    
    -- Result artifacts
    source_image_url text,
    reference_image_url text,
    result_overlay_url text,
    extracted_text text,
    
    -- Device context
    device_model character varying,
    device_id character varying,
    host_name character varying,
    
    -- Execution context
    execution_id character varying COMMENT ON COLUMN verification_execution_history.execution_id IS 'Links to execution_results table',
    script_result_id character varying,
    script_context character varying DEFAULT 'direct',
    
    executed_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

-- Add indexes for performance
CREATE INDEX idx_alerts_incident_type ON alerts(incident_type);
CREATE INDEX idx_alerts_host_name ON alerts(host_name);
CREATE INDEX idx_alerts_start_time ON alerts(start_time);

CREATE INDEX idx_heatmaps_team_id ON heatmaps(team_id);
CREATE INDEX idx_heatmaps_generated_at ON heatmaps(generated_at);

-- Node metrics indexes
CREATE INDEX idx_node_metrics_team_id ON node_metrics(team_id);
CREATE INDEX idx_node_metrics_node_id ON node_metrics(node_id);
CREATE INDEX idx_node_metrics_tree_id ON node_metrics(tree_id);
CREATE INDEX idx_node_metrics_success_rate ON node_metrics(success_rate);
CREATE INDEX idx_node_metrics_total_executions ON node_metrics(total_executions);
CREATE INDEX idx_node_metrics_last_execution ON node_metrics(last_execution_at);
CREATE INDEX idx_node_metrics_device ON node_metrics(device_model, device_id);

-- Edge metrics indexes
CREATE INDEX idx_edge_metrics_team_id ON edge_metrics(team_id);
CREATE INDEX idx_edge_metrics_edge_id ON edge_metrics(edge_id);
CREATE INDEX idx_edge_metrics_tree_id ON edge_metrics(tree_id);
CREATE INDEX idx_edge_metrics_success_rate ON edge_metrics(success_rate);
CREATE INDEX idx_edge_metrics_total_executions ON edge_metrics(total_executions);
CREATE INDEX idx_edge_metrics_last_execution ON edge_metrics(last_execution_at);
CREATE INDEX idx_edge_metrics_nodes ON edge_metrics(source_node_id, target_node_id);
CREATE INDEX idx_edge_metrics_device ON edge_metrics(device_model, device_id);

-- Action execution history indexes
CREATE INDEX idx_action_history_edge_id ON action_execution_history(edge_id);
CREATE INDEX idx_action_history_tree_id ON action_execution_history(tree_id);
CREATE INDEX idx_action_history_team_id ON action_execution_history(team_id);
CREATE INDEX idx_action_history_executed_at ON action_execution_history(executed_at);
CREATE INDEX idx_action_history_execution_id ON action_execution_history(execution_id);
CREATE INDEX idx_action_history_success ON action_execution_history(success);
CREATE INDEX idx_action_history_command ON action_execution_history(action_command);

-- Verification execution history indexes
CREATE INDEX idx_verification_history_node_id ON verification_execution_history(node_id);
CREATE INDEX idx_verification_history_tree_id ON verification_execution_history(tree_id);
CREATE INDEX idx_verification_history_team_id ON verification_execution_history(team_id);
CREATE INDEX idx_verification_history_executed_at ON verification_execution_history(executed_at);
CREATE INDEX idx_verification_history_execution_id ON verification_execution_history(execution_id);
CREATE INDEX idx_verification_history_success ON verification_execution_history(success);
CREATE INDEX idx_verification_history_type ON verification_execution_history(verification_type);

-- Add comments
COMMENT ON TABLE alerts IS 'Stores monitoring incidents from HDMI capture analysis';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Aggregated performance metrics for navigation nodes with embedded verifications';
COMMENT ON TABLE edge_metrics IS 'Aggregated performance metrics for navigation edges with embedded actions';
COMMENT ON TABLE action_execution_history IS 'Detailed execution history for individual actions within edges';
COMMENT ON TABLE verification_execution_history IS 'Detailed execution history for individual verifications within nodes';

-- Enable Row Level Security (RLS)
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE heatmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE node_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_execution_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_execution_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for alerts table
CREATE POLICY "Allow all operations on alerts" ON alerts
FOR ALL 
TO public
USING (true);

-- RLS Policies for heatmaps table (no RLS in automai, but we'll add team-based access)
CREATE POLICY "Team members can access heatmaps" ON heatmaps
FOR ALL 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

-- RLS Policies for node_metrics table
CREATE POLICY "Team members can access node metrics" ON node_metrics
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for edge_metrics table
CREATE POLICY "Team members can access edge metrics" ON edge_metrics
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for action_execution_history table
CREATE POLICY "Team members can access action execution history" ON action_execution_history
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for verification_execution_history table
CREATE POLICY "Team members can access verification execution history" ON verification_execution_history
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- Functions to update aggregated metrics
CREATE OR REPLACE FUNCTION update_node_metrics_on_verification_execution()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO node_metrics (
        node_id, tree_id, team_id, total_executions, successful_executions, 
        failed_executions, success_rate, avg_execution_time_ms,
        min_execution_time_ms, max_execution_time_ms, last_execution_at,
        last_success_at, last_failure_at, device_model, device_id, updated_at
    )
    VALUES (
        NEW.node_id, NEW.tree_id, NEW.team_id, 1,
        CASE WHEN NEW.success THEN 1 ELSE 0 END,
        CASE WHEN NEW.success THEN 0 ELSE 1 END,
        CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
        NEW.execution_time_ms, NEW.execution_time_ms, NEW.execution_time_ms,
        NEW.executed_at,
        CASE WHEN NEW.success THEN NEW.executed_at ELSE NULL END,
        CASE WHEN NEW.success THEN NULL ELSE NEW.executed_at END,
        NEW.device_model, NEW.device_id, NOW()
    )
    ON CONFLICT (node_id, tree_id, team_id) DO UPDATE SET
        total_executions = node_metrics.total_executions + 1,
        successful_executions = node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
        failed_executions = node_metrics.failed_executions + CASE WHEN NEW.success THEN 0 ELSE 1 END,
        success_rate = (node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (node_metrics.total_executions + 1),
        avg_execution_time_ms = ((node_metrics.avg_execution_time_ms * node_metrics.total_executions) + NEW.execution_time_ms) / (node_metrics.total_executions + 1),
        min_execution_time_ms = LEAST(node_metrics.min_execution_time_ms, NEW.execution_time_ms),
        max_execution_time_ms = GREATEST(node_metrics.max_execution_time_ms, NEW.execution_time_ms),
        last_execution_at = NEW.executed_at,
        last_success_at = CASE WHEN NEW.success THEN NEW.executed_at ELSE node_metrics.last_success_at END,
        last_failure_at = CASE WHEN NEW.success THEN node_metrics.last_failure_at ELSE NEW.executed_at END,
        device_model = NEW.device_model,
        device_id = NEW.device_id,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_edge_metrics_on_action_execution()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO edge_metrics (
        edge_id, source_node_id, target_node_id, tree_id, team_id, 
        total_executions, successful_executions, failed_executions, 
        success_rate, avg_execution_time_ms, min_execution_time_ms, 
        max_execution_time_ms, last_execution_at, last_success_at, 
        last_failure_at, device_model, device_id, updated_at,
        retry_execution_count, retry_success_count
    )
    VALUES (
        NEW.edge_id, '', '', NEW.tree_id, NEW.team_id, 1,
        CASE WHEN NEW.success THEN 1 ELSE 0 END,
        CASE WHEN NEW.success THEN 0 ELSE 1 END,
        CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
        NEW.execution_time_ms, NEW.execution_time_ms, NEW.execution_time_ms,
        NEW.executed_at,
        CASE WHEN NEW.success THEN NEW.executed_at ELSE NULL END,
        CASE WHEN NEW.success THEN NULL ELSE NEW.executed_at END,
        NEW.device_model, NEW.device_id, NOW(),
        CASE WHEN NEW.is_retry_action THEN 1 ELSE 0 END,
        CASE WHEN NEW.is_retry_action AND NEW.success THEN 1 ELSE 0 END
    )
    ON CONFLICT (edge_id, tree_id, team_id) DO UPDATE SET
        total_executions = edge_metrics.total_executions + 1,
        successful_executions = edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
        failed_executions = edge_metrics.failed_executions + CASE WHEN NEW.success THEN 0 ELSE 1 END,
        success_rate = (edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (edge_metrics.total_executions + 1),
        avg_execution_time_ms = ((edge_metrics.avg_execution_time_ms * edge_metrics.total_executions) + NEW.execution_time_ms) / (edge_metrics.total_executions + 1),
        min_execution_time_ms = LEAST(edge_metrics.min_execution_time_ms, NEW.execution_time_ms),
        max_execution_time_ms = GREATEST(edge_metrics.max_execution_time_ms, NEW.execution_time_ms),
        last_execution_at = NEW.executed_at,
        last_success_at = CASE WHEN NEW.success THEN NEW.executed_at ELSE edge_metrics.last_success_at END,
        last_failure_at = CASE WHEN NEW.success THEN edge_metrics.last_failure_at ELSE NEW.executed_at END,
        retry_execution_count = edge_metrics.retry_execution_count + CASE WHEN NEW.is_retry_action THEN 1 ELSE 0 END,
        retry_success_count = edge_metrics.retry_success_count + CASE WHEN NEW.is_retry_action AND NEW.success THEN 1 ELSE 0 END,
        retry_success_rate = CASE 
            WHEN edge_metrics.retry_execution_count + CASE WHEN NEW.is_retry_action THEN 1 ELSE 0 END = 0 THEN 0.0
            ELSE (edge_metrics.retry_success_count + CASE WHEN NEW.is_retry_action AND NEW.success THEN 1 ELSE 0 END)::numeric / (edge_metrics.retry_execution_count + CASE WHEN NEW.is_retry_action THEN 1 ELSE 0 END)
        END,
        device_model = NEW.device_model,
        device_id = NEW.device_id,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER trigger_update_node_metrics
    AFTER INSERT ON verification_execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_node_metrics_on_verification_execution();

CREATE TRIGGER trigger_update_edge_metrics
    AFTER INSERT ON action_execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_edge_metrics_on_action_execution(); 