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

-- Navigation node performance metrics
CREATE TABLE node_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    metric_type character varying NOT NULL,
    value numeric(10,4) NOT NULL,
    unit character varying,
    timestamp timestamp with time zone DEFAULT now(),
    device_id uuid,
    execution_id character varying,
    metadata jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now()
);

-- Navigation edge performance metrics
CREATE TABLE edge_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    edge_id character varying NOT NULL,
    from_node_id character varying NOT NULL,
    to_node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    metric_type character varying NOT NULL,
    value numeric(10,4) NOT NULL,
    unit character varying,
    timestamp timestamp with time zone DEFAULT now(),
    device_id uuid,
    execution_id character varying,
    metadata jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now()
);

-- Add indexes for performance
CREATE INDEX idx_alerts_incident_type ON alerts(incident_type);
CREATE INDEX idx_alerts_host_name ON alerts(host_name);
CREATE INDEX idx_alerts_start_time ON alerts(start_time);

CREATE INDEX idx_heatmaps_team_id ON heatmaps(team_id);
CREATE INDEX idx_heatmaps_generated_at ON heatmaps(generated_at);

CREATE INDEX idx_node_metrics_team_id ON node_metrics(team_id);
CREATE INDEX idx_node_metrics_node_id ON node_metrics(node_id);
CREATE INDEX idx_node_metrics_tree_id ON node_metrics(tree_id);
CREATE INDEX idx_node_metrics_metric_type ON node_metrics(metric_type);
CREATE INDEX idx_node_metrics_timestamp ON node_metrics(timestamp);
CREATE INDEX idx_node_metrics_device_id ON node_metrics(device_id);
CREATE INDEX idx_node_metrics_execution_id ON node_metrics(execution_id);

CREATE INDEX idx_edge_metrics_team_id ON edge_metrics(team_id);
CREATE INDEX idx_edge_metrics_edge_id ON edge_metrics(edge_id);
CREATE INDEX idx_edge_metrics_tree_id ON edge_metrics(tree_id);
CREATE INDEX idx_edge_metrics_metric_type ON edge_metrics(metric_type);
CREATE INDEX idx_edge_metrics_timestamp ON edge_metrics(timestamp);
CREATE INDEX idx_edge_metrics_device_id ON edge_metrics(device_id);
CREATE INDEX idx_edge_metrics_execution_id ON edge_metrics(execution_id);
CREATE INDEX idx_edge_metrics_nodes ON edge_metrics(from_node_id, to_node_id);

-- Add comments
COMMENT ON TABLE alerts IS 'Stores monitoring incidents from HDMI capture analysis';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Navigation node performance metrics';
COMMENT ON TABLE edge_metrics IS 'Navigation edge transition metrics'; 