-- Migration: Add network speed and disk usage monitoring
-- Date: 2025-10-02
-- Description: Adds network speed fields to system_metrics and disk usage to system_device_metrics

-- Add network speed columns to system_metrics (host + server level)
ALTER TABLE system_metrics 
ADD COLUMN IF NOT EXISTS download_mbps numeric,
ADD COLUMN IF NOT EXISTS upload_mbps numeric,
ADD COLUMN IF NOT EXISTS speedtest_last_run timestamp with time zone,
ADD COLUMN IF NOT EXISTS speedtest_age_seconds integer;

-- Add disk usage column to system_device_metrics (per-device level)
ALTER TABLE system_device_metrics 
ADD COLUMN IF NOT EXISTS disk_usage_capture text;

-- Add comments for documentation
COMMENT ON COLUMN system_metrics.download_mbps IS 'Download speed in Mbps from speedtest (cached 10 min)';
COMMENT ON COLUMN system_metrics.upload_mbps IS 'Upload speed in Mbps from speedtest (cached 10 min)';
COMMENT ON COLUMN system_metrics.speedtest_last_run IS 'UTC timestamp when speedtest was last executed';
COMMENT ON COLUMN system_metrics.speedtest_age_seconds IS 'Age of cached speedtest data in seconds';
COMMENT ON COLUMN system_device_metrics.disk_usage_capture IS 'Disk usage for capture folder (e.g., "2.5G", "850M") from du -sh command';

-- Add indexes for performance (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_system_metrics_speedtest_last_run ON system_metrics(speedtest_last_run);

