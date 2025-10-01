-- ============================================================================
-- KPI MEASUREMENT SYSTEM - Migration
-- ============================================================================
-- Adds support for measuring time from navigation action to visual confirmation
-- using post-processing of 5 FPS FFmpeg captures.
--
-- Architecture:
-- - Node stores kpi_references (same format as verifications)
-- - Navigation executor queues KPI measurements after each step
-- - Background KPI executor scans captures and measures timing
-- - Results stored in execution_results, aggregated in edge_metrics

-- ----------------------------------------------------------------------------
-- 1. Add kpi_references to navigation_nodes
-- ----------------------------------------------------------------------------
ALTER TABLE navigation_nodes 
ADD COLUMN IF NOT EXISTS kpi_references jsonb DEFAULT '[]';

COMMENT ON COLUMN navigation_nodes.kpi_references IS 'KPI measurement references (image/OCR) to measure navigation performance - same format as verifications';

CREATE INDEX IF NOT EXISTS idx_navigation_nodes_kpi_references 
ON navigation_nodes USING GIN (kpi_references);

-- ----------------------------------------------------------------------------
-- 2. Add KPI measurement fields to execution_results
-- ----------------------------------------------------------------------------
ALTER TABLE execution_results 
ADD COLUMN IF NOT EXISTS kpi_measurement_ms integer,
ADD COLUMN IF NOT EXISTS kpi_measurement_success boolean,
ADD COLUMN IF NOT EXISTS kpi_measurement_error text;

COMMENT ON COLUMN execution_results.kpi_measurement_ms IS 'Measured time from action to visual confirmation (KPI)';
COMMENT ON COLUMN execution_results.kpi_measurement_success IS 'Whether KPI measurement succeeded';
COMMENT ON COLUMN execution_results.kpi_measurement_error IS 'Error message if KPI measurement failed';

CREATE INDEX IF NOT EXISTS idx_execution_results_kpi_success 
ON execution_results(kpi_measurement_success) WHERE kpi_measurement_success IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_execution_results_kpi_ms 
ON execution_results(kpi_measurement_ms) WHERE kpi_measurement_ms IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. Add KPI aggregation fields to edge_metrics
-- ----------------------------------------------------------------------------
ALTER TABLE edge_metrics
ADD COLUMN IF NOT EXISTS total_kpi_measurements integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS successful_kpi_measurements integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_kpi_ms integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS min_kpi_ms integer,
ADD COLUMN IF NOT EXISTS max_kpi_ms integer,
ADD COLUMN IF NOT EXISTS kpi_success_rate numeric DEFAULT 0;

COMMENT ON COLUMN edge_metrics.total_kpi_measurements IS 'Total number of KPI measurements attempted';
COMMENT ON COLUMN edge_metrics.successful_kpi_measurements IS 'Number of successful KPI measurements';
COMMENT ON COLUMN edge_metrics.avg_kpi_ms IS 'Average KPI measurement time in milliseconds';
COMMENT ON COLUMN edge_metrics.min_kpi_ms IS 'Minimum KPI measurement time';
COMMENT ON COLUMN edge_metrics.max_kpi_ms IS 'Maximum KPI measurement time';
COMMENT ON COLUMN edge_metrics.kpi_success_rate IS 'KPI measurement success rate (0-1)';

-- ----------------------------------------------------------------------------
-- 4. Update metrics aggregation trigger to include KPI
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update edge metrics
    IF NEW.edge_id IS NOT NULL THEN
        INSERT INTO edge_metrics (
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
            total_executions = edge_metrics.total_executions + 1,
            successful_executions = edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (edge_metrics.total_executions + 1),
            avg_execution_time_ms = ((edge_metrics.avg_execution_time_ms * edge_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (edge_metrics.total_executions + 1),
            total_kpi_measurements = edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END,
            successful_kpi_measurements = edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END,
            avg_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    ((edge_metrics.avg_kpi_ms * edge_metrics.total_kpi_measurements) + NEW.kpi_measurement_ms) / (edge_metrics.total_kpi_measurements + 1)
                ELSE edge_metrics.avg_kpi_ms
            END,
            min_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    LEAST(COALESCE(edge_metrics.min_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE edge_metrics.min_kpi_ms
            END,
            max_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    GREATEST(COALESCE(edge_metrics.max_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE edge_metrics.max_kpi_ms
            END,
            kpi_success_rate = CASE
                WHEN edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END > 0 THEN
                    (edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END)::numeric / 
                    (edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END)
                ELSE 0
            END;
    END IF;

    -- Update node metrics
    IF NEW.node_id IS NOT NULL THEN
        INSERT INTO node_metrics (
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
        ON CONFLICT (node_id, tree_id) 
        DO UPDATE SET
            total_executions = node_metrics.total_executions + 1,
            successful_executions = node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (node_metrics.total_executions + 1),
            avg_execution_time_ms = ((node_metrics.avg_execution_time_ms * node_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (node_metrics.total_executions + 1);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_update_metrics ON execution_results;

-- Create trigger on execution_results to update metrics
CREATE TRIGGER trigger_update_metrics
    AFTER INSERT ON execution_results
    FOR EACH ROW
    EXECUTE FUNCTION update_metrics();

-- Log migration completion
SELECT 'KPI Measurement System migration completed successfully' as status;
