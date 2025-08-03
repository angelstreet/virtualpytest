-- Migration: Remove node_type column from navigation_nodes table
-- Since we now use data.type exclusively for node types (screen, menu, action)
-- The node_type column in the table is redundant

-- Step 1: Add a data.type field to existing nodes that don't have it
-- Update any existing nodes to ensure they have data.type set
UPDATE navigation_nodes 
SET data = jsonb_set(
    COALESCE(data, '{}'), 
    '{type}', 
    to_jsonb(COALESCE(node_type, 'screen'))
) 
WHERE data->>'type' IS NULL OR data->>'type' = '';

-- Step 2: Remove the node_type column
ALTER TABLE navigation_nodes DROP COLUMN IF EXISTS node_type;

-- Step 3: Add a comment to document the change
COMMENT ON TABLE navigation_nodes IS 'Navigation nodes table - node type is stored in data.type field (screen, menu, action)';