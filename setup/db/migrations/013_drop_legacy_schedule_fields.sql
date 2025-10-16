-- Migration: Drop legacy schedule_type and schedule_config columns
-- Clean implementation - no backward compatibility needed

-- Drop legacy columns completely
ALTER TABLE deployments 
  DROP COLUMN IF EXISTS schedule_type;

ALTER TABLE deployments 
  DROP COLUMN IF EXISTS schedule_config;

-- Migration complete - deployments now use only cron_expression

