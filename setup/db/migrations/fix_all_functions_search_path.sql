-- ====================================================================
-- COMPREHENSIVE FIX: Set search_path for ALL functions
-- Date: 2025-10-26
-- Description: Fix search_path for all database functions to prevent
--              "relation does not exist" errors with RLS-enabled tables
-- ====================================================================

-- Problem: Many functions have search_path="" (empty) or no search_path set.
-- When called by anon/authenticated roles, they can't resolve table names.
-- 
-- Solution: Set explicit search_path TO public, pg_temp for all functions.

-- ====================================================================
-- TRIGGER FUNCTIONS (already fixed in previous migration)
-- ====================================================================
-- These should already be fixed, but including for completeness

ALTER FUNCTION auto_update_edge_labels_on_node_change() 
SET search_path TO public, pg_temp;

ALTER FUNCTION auto_set_edge_label_on_insert() 
SET search_path TO public, pg_temp;

ALTER FUNCTION sync_parent_node_to_subtrees() 
SET search_path TO public, pg_temp;

ALTER FUNCTION cascade_delete_subtrees() 
SET search_path TO public, pg_temp;

ALTER FUNCTION refresh_tree_materialized_view() 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_node_subtree_counts() 
SET search_path TO public, pg_temp;

-- ====================================================================
-- NAVIGATION FUNCTIONS
-- ====================================================================

ALTER FUNCTION get_full_navigation_tree(uuid, uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION get_full_tree_from_mv(uuid, uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION get_tree_metrics_optimized(uuid, uuid)
SET search_path TO public, pg_temp;

ALTER FUNCTION get_tree_metrics_from_mv(uuid, uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION get_descendant_trees(uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION get_descendant_trees_filtered(uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION get_tree_path(uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_edge_labels() 
SET search_path TO public, pg_temp;

-- ====================================================================
-- METRICS FUNCTIONS
-- ====================================================================

ALTER FUNCTION update_metrics() 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_ai_plan_metrics(character varying, boolean, integer, uuid) 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_ai_graph_metrics(character varying, boolean, integer, uuid) 
SET search_path TO public, pg_temp;

-- ====================================================================
-- AI CACHE FUNCTIONS
-- ====================================================================

ALTER FUNCTION cleanup_ai_graph_cache(uuid, integer, numeric) 
SET search_path TO public, pg_temp;

-- ====================================================================
-- TESTCASE FUNCTIONS
-- ====================================================================

ALTER FUNCTION save_testcase_version_history() 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_testcase_updated_at() 
SET search_path TO public, pg_temp;

-- ====================================================================
-- CAMPAIGN FUNCTIONS
-- ====================================================================

ALTER FUNCTION array_append_campaign_script(uuid, uuid) 
SET search_path TO public, pg_temp;

-- ====================================================================
-- INCIDENT/ALERT FUNCTIONS
-- ====================================================================

ALTER FUNCTION detect_and_create_incidents() 
SET search_path TO public, pg_temp;

ALTER FUNCTION process_incidents() 
SET search_path TO public, pg_temp;

ALTER FUNCTION auto_resolve_incidents() 
SET search_path TO public, pg_temp;

ALTER FUNCTION update_system_incident_updated_at() 
SET search_path TO public, pg_temp;

ALTER FUNCTION delete_all_alerts() 
SET search_path TO public, pg_temp;

ALTER FUNCTION cleanup_old_resolved_alerts() 
SET search_path TO public, pg_temp;

ALTER FUNCTION preview_cleanup_old_alerts() 
SET search_path TO public, pg_temp;

-- ====================================================================
-- DEVICE FUNCTIONS
-- ====================================================================

ALTER FUNCTION upsert_device_flags(text, text, text) 
SET search_path TO public, pg_temp;

-- ====================================================================
-- VERIFICATION QUERY
-- ====================================================================

SELECT 
    proname as function_name,
    pg_get_function_identity_arguments(oid) as parameters,
    CASE 
        WHEN proconfig IS NULL THEN '❌ NO SEARCH PATH'
        WHEN 'search_path=' = ANY(proconfig::text[]) OR 'search_path=""' = ANY(proconfig::text[]) THEN '❌ EMPTY'
        WHEN 'search_path=public,pg_temp' = ANY(proconfig::text[]) THEN '✅ CORRECT'
        ELSE '⚠️ CUSTOM: ' || array_to_string(proconfig, ', ')
    END as status
FROM pg_proc 
WHERE pronamespace = 'public'::regnamespace
  AND proname IN (
    'auto_update_edge_labels_on_node_change',
    'auto_set_edge_label_on_insert',
    'sync_parent_node_to_subtrees',
    'cascade_delete_subtrees',
    'refresh_tree_materialized_view',
    'update_node_subtree_counts',
    'get_full_navigation_tree',
    'get_full_tree_from_mv',
    'get_tree_metrics_optimized',
    'get_tree_metrics_from_mv',
    'get_descendant_trees',
    'get_descendant_trees_filtered',
    'get_tree_path',
    'update_edge_labels',
    'update_metrics',
    'update_ai_plan_metrics',
    'update_ai_graph_metrics',
    'cleanup_ai_graph_cache',
    'save_testcase_version_history',
    'update_testcase_updated_at',
    'array_append_campaign_script',
    'detect_and_create_incidents',
    'process_incidents',
    'auto_resolve_incidents',
    'update_system_incident_updated_at',
    'delete_all_alerts',
    'cleanup_old_resolved_alerts',
    'preview_cleanup_old_alerts',
    'upsert_device_flags'
  )
ORDER BY 
    CASE 
        WHEN 'search_path=public,pg_temp' = ANY(proconfig::text[]) THEN 1
        WHEN proconfig IS NOT NULL AND NOT ('search_path=' = ANY(proconfig::text[]) OR 'search_path=""' = ANY(proconfig::text[])) THEN 2
        WHEN 'search_path=' = ANY(proconfig::text[]) OR 'search_path=""' = ANY(proconfig::text[]) THEN 3
        WHEN proconfig IS NULL THEN 4
    END,
    proname;

-- All functions should show ✅ CORRECT after running this migration

SELECT 'Migration: Comprehensive search_path fix applied successfully ✅' as status;

-- ====================================================================
-- NOTES
-- ====================================================================
-- - This migration is idempotent (safe to run multiple times)
-- - Fixes ALL functions that had empty or missing search_path
-- - Functions now explicitly resolve tables in public schema
-- - Prevents "relation does not exist" errors with RLS-enabled tables

