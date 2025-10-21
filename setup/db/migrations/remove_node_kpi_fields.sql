-- Migration: Remove KPI measurement fields from navigation_nodes
-- Date: 2025-10-21
-- Description: Move KPI measurement from node-level to action_set-level

-- Remove KPI fields from navigation_nodes table
ALTER TABLE navigation_nodes 
  DROP COLUMN IF EXISTS kpi_references CASCADE,
  DROP COLUMN IF EXISTS use_verifications_for_kpi CASCADE;

-- Note: No data migration - clean deletion as per requirement
-- KPI configuration will now be stored in action_sets within navigation_edges

