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

-- action_execution_history table removed - does not exist in current database

-- verification_execution_history table removed - does not exist in current database

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

-- action_execution_history and verification_execution_history indexes removed - tables do not exist

-- Add comments
COMMENT ON TABLE alerts IS 'Stores monitoring incidents from HDMI capture analysis';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Aggregated performance metrics for navigation nodes with embedded verifications';
COMMENT ON TABLE edge_metrics IS 'Aggregated performance metrics for navigation edges with embedded actions';

-- Enable Row Level Security (RLS)
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE heatmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE node_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_metrics ENABLE ROW LEVEL SECURITY;
-- action_execution_history and verification_execution_history RLS removed - tables do not exist

-- RLS Policies updated to match actual working database
CREATE POLICY "alerts_access_policy" ON alerts
FOR ALL 
TO public
USING (true);

CREATE POLICY "heatmaps_access_policy" ON heatmaps
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

CREATE POLICY "node_metrics_access_policy" ON node_metrics
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

CREATE POLICY "edge_metrics_access_policy" ON edge_metrics
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Functions and triggers removed - they reference non-existent tables (verification_execution_history, action_execution_history) 