-- VirtualPyTest Monitoring and Analytics Tables Schema
-- This file contains tables for alerts, metrics, and analytics
-- Also includes database functions for efficient bulk operations

-- Drop existing tables if they exist (for clean recreation)
DROP TABLE IF EXISTS edge_metrics CASCADE;
DROP TABLE IF EXISTS node_metrics CASCADE;
DROP TABLE IF EXISTS heatmaps CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;

-- System alerts and monitoring incidents (UPDATED SCHEMA)
CREATE TABLE alerts (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    host_name text NOT NULL,
    device_id text NOT NULL,
    incident_type text NOT NULL CHECK (incident_type = ANY (ARRAY['blackscreen'::text, 'freeze'::text, 'errors'::text, 'audio_loss'::text])),
    status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'resolved'::text])),
    consecutive_count integer NOT NULL DEFAULT 1 CHECK (consecutive_count > 0),
    start_time timestamp with time zone NOT NULL DEFAULT now(),
    end_time timestamp with time zone,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Additional fields
    checked boolean DEFAULT false,
    check_type character varying,
    discard boolean DEFAULT false,
    discard_type character varying,
    discard_comment text
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

-- Navigation node aggregated metrics (UPDATED SCHEMA - SIMPLIFIED)
CREATE TABLE node_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Simplified metrics structure
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    success_rate numeric DEFAULT 0,
    avg_execution_time_ms integer DEFAULT 0,
    -- UNIQUE constraint for ON CONFLICT in update_metrics() trigger
    CONSTRAINT node_metrics_unique UNIQUE (node_id, tree_id, team_id)
);

-- Navigation edge aggregated metrics (UPDATED SCHEMA - SIMPLIFIED)
CREATE TABLE edge_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    edge_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Simplified metrics structure + action_set_id
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    success_rate numeric DEFAULT 0,
    avg_execution_time_ms integer DEFAULT 0,
    action_set_id character varying,  -- UPDATED: Added for bidirectional edge tracking
    -- KPI measurement metrics
    total_kpi_measurements integer DEFAULT 0,
    successful_kpi_measurements integer DEFAULT 0,
    avg_kpi_ms integer DEFAULT 0,
    min_kpi_ms integer,
    max_kpi_ms integer,
    kpi_success_rate numeric DEFAULT 0,
    -- UNIQUE constraint for ON CONFLICT in update_metrics() trigger
    CONSTRAINT edge_metrics_edge_id_tree_id_action_set_id_key UNIQUE (edge_id, tree_id, action_set_id)
);

-- action_execution_history table removed - does not exist in current database

-- verification_execution_history table removed - does not exist in current database

-- Database Functions
-- Function to efficiently delete all alerts without returning data to client
CREATE OR REPLACE FUNCTION delete_all_alerts()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  deleted_count integer;
BEGIN
  -- Count before deletion
  SELECT COUNT(*) INTO deleted_count FROM alerts;
  
  -- Delete all records with WHERE clause (required by some DB configs)
  -- Using "WHERE true" matches all rows while satisfying the WHERE requirement
  DELETE FROM alerts WHERE true;
  
  -- Return result as JSON (text-based format works better with Supabase Python client)
  RETURN json_build_object(
    'success', true,
    'deleted_count', deleted_count,
    'message', 'Successfully deleted ' || deleted_count || ' alerts'
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN json_build_object(
      'success', false,
      'error', SQLERRM,
      'deleted_count', 0
    );
END;
$$;

COMMENT ON FUNCTION delete_all_alerts() IS 'Efficiently deletes all alerts from the database without returning data to the client, preventing timeout issues with large datasets';

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

-- Edge metrics indexes
CREATE INDEX idx_edge_metrics_team_id ON edge_metrics(team_id);
CREATE INDEX idx_edge_metrics_edge_id ON edge_metrics(edge_id);
CREATE INDEX idx_edge_metrics_tree_id ON edge_metrics(tree_id);

-- action_execution_history and verification_execution_history indexes removed - tables do not exist

-- Add comments
COMMENT ON TABLE alerts IS 'Stores monitoring incidents from HDMI capture analysis';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Aggregated performance metrics for navigation nodes with embedded verifications';
COMMENT ON TABLE edge_metrics IS 'Aggregated performance metrics for navigation edges with embedded actions and KPI measurements';
COMMENT ON COLUMN edge_metrics.total_kpi_measurements IS 'Total number of KPI measurements attempted';
COMMENT ON COLUMN edge_metrics.successful_kpi_measurements IS 'Number of successful KPI measurements';
COMMENT ON COLUMN edge_metrics.avg_kpi_ms IS 'Average KPI measurement time in milliseconds';
COMMENT ON COLUMN edge_metrics.min_kpi_ms IS 'Minimum KPI measurement time';
COMMENT ON COLUMN edge_metrics.max_kpi_ms IS 'Maximum KPI measurement time';
COMMENT ON COLUMN edge_metrics.kpi_success_rate IS 'KPI measurement success rate (0-1)';

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