-- ============================================================================
-- Add device_name to alerts
-- ============================================================================
-- This migration adds device_name column to alerts table to store the
-- human-readable device name alongside device_id.
--
-- Context: Code is trying to insert device_name but column doesn't exist
-- Related: Similar to add_device_name_to_execution_results.sql
-- ============================================================================

-- Add device_name column to alerts
ALTER TABLE alerts 
ADD COLUMN IF NOT EXISTS device_name text;

COMMENT ON COLUMN alerts.device_name IS 'Device name (human-readable identifier) for the device that generated this alert';

-- Create index for efficient filtering by device_name
CREATE INDEX IF NOT EXISTS idx_alerts_device_name 
ON alerts(device_name);

-- Log migration completion
SELECT 'Added device_name to alerts table' as status;

