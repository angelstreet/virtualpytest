-- VirtualPyTest Monitoring and Analytics Tables Schema
-- This file contains tables for alerts, metrics, and analytics
-- Also includes database functions for efficient bulk operations
--
-- PERFORMANCE OPTIMIZATION (Oct 2025):
-- - Added critical indexes for alerts table (status, start_time, composite)
-- - Split queries into separate active/resolved for better performance
-- - Added automatic 7-day cleanup for resolved alerts
-- - Query performance improved from 60+ seconds to <1ms

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
    device_name text,
    incident_type text NOT NULL CHECK (incident_type = ANY (ARRAY['blackscreen'::text, 'freeze'::text, 'errors'::text, 'audio_loss'::text, 'macroblocks'::text])),
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

-- Function to delete resolved alerts older than 7 days (automatic cleanup)
CREATE OR REPLACE FUNCTION cleanup_old_resolved_alerts()
RETURNS TABLE(deleted_count INTEGER, oldest_kept TIMESTAMP WITH TIME ZONE)
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
    v_oldest_kept TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Delete resolved alerts older than 7 days
    WITH deleted AS (
        DELETE FROM alerts
        WHERE status = 'resolved'
        AND start_time < NOW() - INTERVAL '7 days'
        RETURNING *
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;
    
    -- Get the oldest remaining resolved alert
    SELECT MIN(start_time) INTO v_oldest_kept
    FROM alerts
    WHERE status = 'resolved';
    
    RAISE NOTICE 'Cleanup completed: Deleted % resolved alerts older than 7 days', v_deleted_count;
    
    RETURN QUERY SELECT v_deleted_count, v_oldest_kept;
END;
$$;

COMMENT ON FUNCTION cleanup_old_resolved_alerts() IS 'Deletes resolved alerts older than 7 days, keeps all active alerts regardless of age';

-- Function to preview what would be deleted (dry run)
CREATE OR REPLACE FUNCTION preview_cleanup_old_alerts()
RETURNS TABLE(
    alert_count INTEGER,
    oldest_alert TIMESTAMP WITH TIME ZONE,
    newest_alert TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as alert_count,
        MIN(start_time) as oldest_alert,
        MAX(start_time) as newest_alert
    FROM alerts
    WHERE status = 'resolved'
    AND start_time < NOW() - INTERVAL '7 days';
END;
$$;

COMMENT ON FUNCTION preview_cleanup_old_alerts() IS 'Preview how many alerts would be deleted without actually deleting them';

-- Add indexes for performance (UPDATED: Added missing critical indexes)
CREATE INDEX idx_alerts_incident_type ON alerts(incident_type);
CREATE INDEX idx_alerts_host_name ON alerts(host_name);
CREATE INDEX idx_alerts_device_id ON alerts(device_id);
CREATE INDEX idx_alerts_device_name ON alerts(device_name);
CREATE INDEX idx_alerts_start_time ON alerts(start_time DESC);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_status_start_time ON alerts(status, start_time DESC);

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

-- =============================================================================
-- METRICS AGGREGATION TRIGGER FUNCTION
-- =============================================================================
-- Automatically aggregates execution results into node_metrics and edge_metrics
-- Uses fully qualified table names (public.*) to work with search_path = ''
-- This function is called by trigger on execution_results table

CREATE OR REPLACE FUNCTION public.update_metrics()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    -- Update edge metrics (with fully qualified table name)
    IF NEW.edge_id IS NOT NULL THEN
        INSERT INTO public.edge_metrics (
            edge_id, 
            tree_id, 
            team_id, 
            action_set_id,
            total_executions,
            successful_executions,
            success_rate,
            avg_execution_time_ms,
            total_kpi_measurements,
            successful_kpi_measurements,
            avg_kpi_ms,
            min_kpi_ms,
            max_kpi_ms,
            kpi_success_rate
        )
        VALUES (
            NEW.edge_id,
            NEW.tree_id,
            NEW.team_id,
            NEW.action_set_id,
            1,
            CASE WHEN NEW.success THEN 1 ELSE 0 END,
            CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
            COALESCE(NEW.execution_time_ms, 0),
            CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END,
            CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END,
            COALESCE(NEW.kpi_measurement_ms, 0),
            NEW.kpi_measurement_ms,
            NEW.kpi_measurement_ms,
            CASE WHEN NEW.kpi_measurement_success THEN 1.0 ELSE 0.0 END
        )
        ON CONFLICT (edge_id, tree_id, action_set_id) 
        DO UPDATE SET
            total_executions = public.edge_metrics.total_executions + 1,
            successful_executions = public.edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (public.edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (public.edge_metrics.total_executions + 1),
            avg_execution_time_ms = ((public.edge_metrics.avg_execution_time_ms * public.edge_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (public.edge_metrics.total_executions + 1),
            total_kpi_measurements = public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END,
            successful_kpi_measurements = public.edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END,
            avg_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    ((public.edge_metrics.avg_kpi_ms * public.edge_metrics.total_kpi_measurements) + NEW.kpi_measurement_ms) / (public.edge_metrics.total_kpi_measurements + 1)
                ELSE public.edge_metrics.avg_kpi_ms
            END,
            min_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    LEAST(COALESCE(public.edge_metrics.min_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE public.edge_metrics.min_kpi_ms
            END,
            max_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    GREATEST(COALESCE(public.edge_metrics.max_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE public.edge_metrics.max_kpi_ms
            END,
            kpi_success_rate = CASE
                WHEN public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END > 0 THEN
                    (public.edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END)::numeric / 
                    (public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END)
                ELSE 0
            END;
    END IF;

    -- Update node metrics (with fully qualified table name)
    IF NEW.node_id IS NOT NULL THEN
        INSERT INTO public.node_metrics (
            node_id,
            tree_id,
            team_id,
            total_executions,
            successful_executions,
            success_rate,
            avg_execution_time_ms
        )
        VALUES (
            NEW.node_id,
            NEW.tree_id,
            NEW.team_id,
            1,
            CASE WHEN NEW.success THEN 1 ELSE 0 END,
            CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
            COALESCE(NEW.execution_time_ms, 0)
        )
        ON CONFLICT (node_id, tree_id, team_id) 
        DO UPDATE SET
            total_executions = public.node_metrics.total_executions + 1,
            successful_executions = public.node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (public.node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (public.node_metrics.total_executions + 1),
            avg_execution_time_ms = ((public.node_metrics.avg_execution_time_ms * public.node_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (public.node_metrics.total_executions + 1);
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.update_metrics() IS 'Aggregates execution results into node_metrics and edge_metrics tables. Uses fully qualified table names to work with search_path = "" security setting.';

-- Trigger on execution_results table
-- Note: This trigger is created in migration files (trigger_update_metrics)
-- Kept here for reference:
-- CREATE TRIGGER trigger_update_metrics
--     AFTER INSERT ON execution_results
--     FOR EACH ROW
--     EXECUTE FUNCTION update_metrics();

-- ============================================================================
-- OPTIMIZED METRICS FETCH FUNCTION (from optimize_metrics_fetch_function.sql migration)
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

-- Backward compatibility alias
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