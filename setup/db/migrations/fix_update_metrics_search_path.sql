-- ============================================================================
-- Fix update_metrics() function to work with search_path = ''
-- ============================================================================
-- Issue: Migration 20251024080404 set search_path = '' for security
-- But the function uses unqualified table names (edge_metrics, node_metrics)
-- This causes "relation does not exist" errors
--
-- Solution: Update function to use fully qualified table names (public.*)
-- ============================================================================

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

-- Log completion
SELECT 'Fixed update_metrics() function to use fully qualified table names' as status;

