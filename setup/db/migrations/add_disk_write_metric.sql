-- Add disk write speed metric to system_metrics table
-- This tracks MB/s written to disk for SD card health monitoring
-- Run this in Supabase SQL Editor

ALTER TABLE system_metrics 
ADD COLUMN IF NOT EXISTS disk_write_mb_per_sec FLOAT DEFAULT 0;

-- Add comment for documentation
COMMENT ON COLUMN system_metrics.disk_write_mb_per_sec IS 'Disk write speed in MB/s - tracks SD card write activity for health monitoring';

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'system_metrics' 
  AND column_name = 'disk_write_mb_per_sec';
