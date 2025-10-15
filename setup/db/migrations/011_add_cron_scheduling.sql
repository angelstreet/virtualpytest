-- Migration: Add cron-based scheduling with optional constraints
-- This adds cron expression support while keeping backward compatibility

-- Step 1: Add new columns to deployments table
ALTER TABLE deployments 
  -- Core scheduling (required)
  ADD COLUMN IF NOT EXISTS cron_expression TEXT,
  
  -- Optional constraints
  ADD COLUMN IF NOT EXISTS start_date TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS end_date TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS max_executions INTEGER,
  
  -- Execution tracking
  ADD COLUMN IF NOT EXISTS execution_count INTEGER DEFAULT 0 NOT NULL,
  ADD COLUMN IF NOT EXISTS last_executed_at TIMESTAMP WITH TIME ZONE;

-- Step 2: Update status check constraint to include new statuses
ALTER TABLE deployments 
  DROP CONSTRAINT IF EXISTS deployments_status_check;
  
ALTER TABLE deployments 
  ADD CONSTRAINT deployments_status_check 
  CHECK (status IN ('active', 'paused', 'stopped', 'completed', 'expired'));

-- Step 3: Migrate existing deployments to cron format
-- Convert schedule_type + schedule_config to cron_expression
UPDATE deployments 
SET cron_expression = CASE
  WHEN schedule_type = 'hourly' THEN 
    COALESCE((schedule_config->>'minute')::text, '0') || ' * * * *'
  WHEN schedule_type = 'daily' THEN 
    COALESCE((schedule_config->>'minute')::text, '0') || ' ' || 
    COALESCE((schedule_config->>'hour')::text, '0') || ' * * *'
  WHEN schedule_type = 'weekly' THEN 
    COALESCE((schedule_config->>'minute')::text, '0') || ' ' ||
    COALESCE((schedule_config->>'hour')::text, '0') || ' * * ' ||
    COALESCE((schedule_config->>'day')::text, '0')
  ELSE '0 * * * *'  -- Default to hourly if unknown
END
WHERE cron_expression IS NULL;

-- Step 4: Make cron_expression required after migration
ALTER TABLE deployments 
  ALTER COLUMN cron_expression SET NOT NULL;

-- Step 5: Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_deployments_cron ON deployments(cron_expression) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_deployments_next_run ON deployments(last_executed_at) WHERE status = 'active';

-- Step 6: Add comments for new columns
COMMENT ON COLUMN deployments.cron_expression IS 'Cron expression for scheduling (e.g., */10 * * * * for every 10 minutes)';
COMMENT ON COLUMN deployments.start_date IS 'Optional: When to start scheduling (NULL = start immediately)';
COMMENT ON COLUMN deployments.end_date IS 'Optional: When to stop scheduling (NULL = run forever)';
COMMENT ON COLUMN deployments.max_executions IS 'Optional: Maximum number of executions (NULL = unlimited)';
COMMENT ON COLUMN deployments.execution_count IS 'Number of times this deployment has executed';
COMMENT ON COLUMN deployments.last_executed_at IS 'Timestamp of last execution';
COMMENT ON TABLE deployments IS 'Periodic Deployment System - scheduled script executions managed by APScheduler with cron expressions';

-- Optional: Keep old columns for backward compatibility during transition
-- You can drop them later when all systems are updated:
-- ALTER TABLE deployments DROP COLUMN IF EXISTS schedule_type;
-- ALTER TABLE deployments DROP COLUMN IF EXISTS schedule_config;

-- Migration complete!
-- Old deployments have been converted to cron expressions
-- New deployments can use cron + optional start/end dates and max executions

