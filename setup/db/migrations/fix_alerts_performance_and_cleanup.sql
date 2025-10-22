-- ============================================================================
-- Fix Alerts Query Performance and Add Automatic Cleanup
-- ============================================================================
-- This migration:
-- 1. Adds missing critical indexes for fast queries
-- 2. Sets up automatic 7-day cleanup for resolved alerts
-- ============================================================================

-- ============================================================================
-- PART 1: Add Missing Indexes
-- ============================================================================

-- Index for sorting by start_time (main query performance)
CREATE INDEX IF NOT EXISTS idx_alerts_start_time ON alerts(start_time DESC);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- Composite index for combined status + time queries (most efficient)
CREATE INDEX IF NOT EXISTS idx_alerts_status_start_time ON alerts(status, start_time DESC);

-- Index for device_id filtering
CREATE INDEX IF NOT EXISTS idx_alerts_device_id ON alerts(device_id);

COMMENT ON INDEX idx_alerts_start_time IS 'Speeds up queries ordered by start_time';
COMMENT ON INDEX idx_alerts_status IS 'Speeds up filtering by active/resolved status';
COMMENT ON INDEX idx_alerts_status_start_time IS 'Optimized for status-filtered time-sorted queries';

-- ============================================================================
-- PART 2: Automatic 7-Day Cleanup for Resolved Alerts
-- ============================================================================

-- Function to delete resolved alerts older than 7 days
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

COMMENT ON FUNCTION cleanup_old_resolved_alerts() IS 'Deletes resolved alerts older than 7 days, keeps all active alerts';

-- ============================================================================
-- PART 3: Schedule Automatic Cleanup (PostgreSQL Cron Extension)
-- ============================================================================

-- Enable pg_cron extension (if available in Supabase)
-- Note: This may require Supabase to have pg_cron extension enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule cleanup to run daily at 2 AM UTC
-- If pg_cron is not available, you'll need to run this manually or use Supabase Edge Functions
DO $$
BEGIN
    -- Try to schedule the cleanup job
    -- This will fail gracefully if pg_cron is not available
    BEGIN
        PERFORM cron.schedule(
            'cleanup-old-alerts',           -- Job name
            '0 2 * * *',                     -- Every day at 2 AM UTC
            'SELECT cleanup_old_resolved_alerts();'
        );
        RAISE NOTICE 'Automatic cleanup scheduled successfully';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Could not schedule automatic cleanup - pg_cron may not be available';
            RAISE NOTICE 'You can run cleanup manually: SELECT cleanup_old_resolved_alerts();';
    END;
END $$;

-- ============================================================================
-- PART 4: Manual Cleanup Helper Functions
-- ============================================================================

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

-- ============================================================================
-- Run initial cleanup to remove existing old alerts
-- ============================================================================

-- Preview what will be deleted
DO $$
DECLARE
    preview_result RECORD;
BEGIN
    SELECT * INTO preview_result FROM preview_cleanup_old_alerts();
    RAISE NOTICE 'About to delete % resolved alerts older than 7 days', preview_result.alert_count;
    
    IF preview_result.alert_count > 0 THEN
        RAISE NOTICE 'Oldest alert to delete: %', preview_result.oldest_alert;
        RAISE NOTICE 'Newest alert to delete: %', preview_result.newest_alert;
    END IF;
END $$;

-- Uncomment the line below to run the cleanup immediately
-- SELECT cleanup_old_resolved_alerts();

