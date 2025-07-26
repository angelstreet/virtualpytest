-- VirtualPyTest Monitoring and Analytics Tables Schema
-- This file contains tables for alerts, metrics, and analytics

-- System alerts and monitoring incidents
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL, -- critical, warning, info
    status VARCHAR(50) DEFAULT 'active', -- active, resolved, acknowledged
    incident_type VARCHAR(100) NOT NULL, -- cpu_high, memory_high, disk_full, etc.
    host_name VARCHAR(255), -- hostname where incident occurred
    device_id UUID REFERENCES device(id) ON DELETE SET NULL, -- affected device
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE, -- when incident was resolved
    resolved_by UUID, -- user who resolved the alert
    metadata JSONB DEFAULT '{}', -- additional alert data
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance heatmap data
CREATE TABLE heatmaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    heatmap_type VARCHAR(100) NOT NULL, -- performance, error_rate, usage, etc.
    time_period VARCHAR(50) NOT NULL, -- hourly, daily, weekly, monthly
    data JSONB NOT NULL, -- heatmap data points
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    start_date DATE NOT NULL, -- period start
    end_date DATE NOT NULL, -- period end
    config JSONB DEFAULT '{}', -- heatmap configuration
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Navigation node performance metrics
CREATE TABLE node_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id VARCHAR(255) NOT NULL, -- navigation node identifier
    tree_id UUID REFERENCES navigation_trees(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL, -- load_time, success_rate, error_count, etc.
    value DECIMAL(10,4) NOT NULL, -- metric value
    unit VARCHAR(50), -- milliseconds, percentage, count, etc.
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    device_id UUID REFERENCES device(id) ON DELETE SET NULL,
    execution_id VARCHAR(255), -- related test execution
    metadata JSONB DEFAULT '{}', -- additional metric data
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Navigation edge performance metrics
CREATE TABLE edge_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    edge_id VARCHAR(255) NOT NULL, -- navigation edge identifier
    from_node_id VARCHAR(255) NOT NULL, -- source node
    to_node_id VARCHAR(255) NOT NULL, -- destination node
    tree_id UUID REFERENCES navigation_trees(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL, -- transition_time, success_rate, etc.
    value DECIMAL(10,4) NOT NULL, -- metric value
    unit VARCHAR(50), -- milliseconds, percentage, count, etc.
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    device_id UUID REFERENCES device(id) ON DELETE SET NULL,
    execution_id VARCHAR(255), -- related test execution
    metadata JSONB DEFAULT '{}', -- additional metric data
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_alerts_team_id ON alerts(team_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_incident_type ON alerts(incident_type);
CREATE INDEX idx_alerts_host_name ON alerts(host_name);
CREATE INDEX idx_alerts_device_id ON alerts(device_id);
CREATE INDEX idx_alerts_start_time ON alerts(start_time);

CREATE INDEX idx_heatmaps_team_id ON heatmaps(team_id);
CREATE INDEX idx_heatmaps_type ON heatmaps(heatmap_type);
CREATE INDEX idx_heatmaps_time_period ON heatmaps(time_period);
CREATE INDEX idx_heatmaps_generated_at ON heatmaps(generated_at);
CREATE INDEX idx_heatmaps_date_range ON heatmaps(start_date, end_date);

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
COMMENT ON TABLE alerts IS 'System alerts and monitoring incidents';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Navigation node performance metrics';
COMMENT ON TABLE edge_metrics IS 'Navigation edge transition metrics'; 