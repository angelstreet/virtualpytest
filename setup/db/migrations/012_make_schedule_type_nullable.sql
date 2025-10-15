-- Migration: Make old schedule_type and schedule_config nullable
-- These columns are kept for backward compatibility but are now optional

-- Make schedule_type nullable (was required before)
ALTER TABLE deployments 
  ALTER COLUMN schedule_type DROP NOT NULL;

-- Make schedule_config nullable (was required before)
ALTER TABLE deployments 
  ALTER COLUMN schedule_config DROP NOT NULL;

-- Add comment
COMMENT ON COLUMN deployments.schedule_type IS 'Legacy: Old schedule type (hourly, daily, weekly) - kept for backward compatibility, use cron_expression instead';
COMMENT ON COLUMN deployments.schedule_config IS 'Legacy: Old schedule configuration - kept for backward compatibility, use cron_expression instead';

