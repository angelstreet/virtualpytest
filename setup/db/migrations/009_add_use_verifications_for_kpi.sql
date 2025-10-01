-- Migration: Add use_verifications_for_kpi column to navigation_nodes
-- Purpose: Allow nodes to use verifications[] for KPI measurement instead of kpi_references[]
-- Date: 2025-10-01

-- Add the boolean column with default FALSE (backward compatible)
ALTER TABLE navigation_nodes
ADD COLUMN use_verifications_for_kpi BOOLEAN DEFAULT FALSE NOT NULL;

-- Add column comment
COMMENT ON COLUMN navigation_nodes.use_verifications_for_kpi IS 
'When TRUE, uses verifications[] for KPI measurement instead of kpi_references[]. Allows reusing existing verifications for performance measurement without duplication.';

-- Create index for filtering nodes that use verifications for KPI
CREATE INDEX idx_navigation_nodes_use_verifications_for_kpi 
ON navigation_nodes(use_verifications_for_kpi) 
WHERE use_verifications_for_kpi = TRUE;

-- Migration complete
-- Run this in Supabase SQL Editor

