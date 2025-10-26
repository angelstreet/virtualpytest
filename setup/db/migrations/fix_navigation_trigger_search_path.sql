-- ====================================================================
-- Migration: Fix Search Path for Navigation Trigger Functions
-- Date: 2025-10-26
-- Description: Set explicit search_path for all navigation trigger functions
--              to prevent "relation does not exist" errors when RLS is enabled
-- ====================================================================

-- Problem:
-- When trigger functions run in the context of roles with RLS enabled (anon, authenticated),
-- they may fail to resolve table names like navigation_edges, navigation_trees, etc.
-- This causes PostgreSQL to throw "relation does not exist" errors (code 42P01).
--
-- Solution:
-- Set explicit search_path to 'public, pg_temp' for all trigger functions,
-- ensuring they always look in the public schema regardless of caller's context.

-- ====================================================================
-- FIX TRIGGER FUNCTIONS
-- ====================================================================

-- Fix 1: auto_update_edge_labels_on_node_change
-- This function updates edge labels when a node's label changes
ALTER FUNCTION auto_update_edge_labels_on_node_change() 
SET search_path TO public, pg_temp;

-- Fix 2: sync_parent_node_to_subtrees
-- This function syncs parent node changes to nested subtrees
ALTER FUNCTION sync_parent_node_to_subtrees() 
SET search_path TO public, pg_temp;

-- Fix 3: cascade_delete_subtrees
-- This function cascade deletes subtrees when parent node is deleted
ALTER FUNCTION cascade_delete_subtrees() 
SET search_path TO public, pg_temp;

-- Fix 4: refresh_tree_materialized_view
-- This function refreshes the materialized view (already has search_path='', update it)
ALTER FUNCTION refresh_tree_materialized_view() 
SET search_path TO public, pg_temp;

-- Fix 5: auto_set_edge_label_on_insert
-- This function auto-sets edge labels on insert by querying navigation_nodes
ALTER FUNCTION auto_set_edge_label_on_insert() 
SET search_path TO public, pg_temp;

-- Fix 6: update_node_subtree_counts (if exists)
-- This function updates subtree count metadata
ALTER FUNCTION update_node_subtree_counts() 
SET search_path TO public, pg_temp;

-- Fix 7: sync_parent_label_screenshot (if exists - legacy)
-- This function syncs parent label and screenshot
ALTER FUNCTION sync_parent_label_screenshot() 
SET search_path TO public, pg_temp;

-- ====================================================================
-- VERIFY THE FIX
-- ====================================================================

SELECT 
    proname as function_name,
    proconfig as config_settings,
    CASE 
        WHEN proconfig IS NULL THEN '❌ NO SEARCH PATH SET'
        WHEN 'search_path=public,pg_temp' = ANY(proconfig) THEN '✅ CORRECT'
        ELSE '⚠️ CUSTOM: ' || array_to_string(proconfig, ', ')
    END as status
FROM pg_proc 
WHERE proname IN (
    'auto_update_edge_labels_on_node_change',
    'auto_set_edge_label_on_insert',
    'sync_parent_node_to_subtrees',
    'cascade_delete_subtrees',
    'refresh_tree_materialized_view',
    'update_node_subtree_counts',
    'sync_parent_label_screenshot'
)
ORDER BY proname;

-- Log completion
SELECT 'Migration: Navigation trigger search path fix applied successfully ✅' as status;

-- ====================================================================
-- NOTES
-- ====================================================================
-- - This migration is idempotent (safe to run multiple times)
-- - No data is modified, only function metadata
-- - Functions will now explicitly resolve tables in public schema
-- - Alternative solution would be SECURITY DEFINER, but search_path is cleaner

