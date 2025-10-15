-- ============================================================================
-- Add device_name to execution_results
-- ============================================================================
-- This migration adds device_name column to execution_results table to allow
-- filtering KPI measurements by specific device, not just device_model.
--
-- Problem: Multiple devices can share the same device_model (e.g. "Samsung S21")
-- Solution: Store device_name (unique identifier like "device-001") for precise filtering
-- ============================================================================

-- Add device_name column to execution_results
ALTER TABLE execution_results 
ADD COLUMN IF NOT EXISTS device_name text;

COMMENT ON COLUMN execution_results.device_name IS 'Device name (unique identifier) for filtering results by specific device';

-- Create index for efficient filtering by device_name
CREATE INDEX IF NOT EXISTS idx_execution_results_device_name 
ON execution_results(device_name);

-- Create composite index for common KPI query pattern (team_id + device_name + time range)
CREATE INDEX IF NOT EXISTS idx_execution_results_kpi_query
ON execution_results(team_id, device_name, executed_at) 
WHERE kpi_measurement_ms IS NOT NULL;

-- Log migration completion
SELECT 'Added device_name to execution_results for precise device filtering' as status;

