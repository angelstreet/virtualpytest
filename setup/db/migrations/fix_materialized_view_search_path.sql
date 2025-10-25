-- Migration: Fix materialized view function and trigger to work with search_path = ''
-- Description: Both get_full_tree_from_mv() and refresh_tree_materialized_view() 
--              have search_path = '' which prevents them from finding mv_full_navigation_trees.
--              This migration fixes both functions to use fully qualified table names.
-- 
-- Issue: After security hardening migration, the functions fail with:
--        "relation 'mv_full_navigation_trees' does not exist"
--        because they can't find the table without schema qualification.
--
-- Fix: Update both functions to use public.mv_full_navigation_trees

-- ============================================================================
-- FIX 1: Read function (get_full_tree_from_mv)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_full_tree_from_mv(
    p_tree_id UUID,
    p_team_id UUID
)
RETURNS JSON
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT full_tree_data
    FROM public.mv_full_navigation_trees
    WHERE tree_id = p_tree_id
    AND team_id = p_team_id;
$$;

COMMENT ON FUNCTION public.get_full_tree_from_mv(UUID, UUID) IS 
'Read pre-computed tree data from materialized view. 
Extremely fast (~10ms) because data is pre-aggregated.
Uses fully qualified table names to work with empty search_path security setting.';

-- ============================================================================
-- FIX 2: Refresh trigger function (refresh_tree_materialized_view)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.refresh_tree_materialized_view()
RETURNS TRIGGER AS $$
BEGIN
    -- Refresh the materialized view (CONCURRENTLY for non-blocking updates)
    -- Note: REFRESH MATERIALIZED VIEW CONCURRENTLY requires unique index
    IF TG_OP = 'DELETE' THEN
        -- For DELETE operations, use OLD
        REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_full_navigation_trees;
        RETURN OLD;
    ELSE
        -- For INSERT/UPDATE operations, use NEW
        REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_full_navigation_trees;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SET search_path = '';

COMMENT ON FUNCTION public.refresh_tree_materialized_view() IS 
'Trigger function to automatically refresh materialized view when navigation data changes.
Uses fully qualified table names to work with empty search_path security setting.';

-- ============================================================================
-- Grant permissions (re-grant to be safe)
-- ============================================================================

GRANT SELECT ON public.mv_full_navigation_trees TO authenticated;
GRANT SELECT ON public.mv_full_navigation_trees TO service_role;
GRANT EXECUTE ON FUNCTION public.get_full_tree_from_mv(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_full_tree_from_mv(UUID, UUID) TO service_role;

