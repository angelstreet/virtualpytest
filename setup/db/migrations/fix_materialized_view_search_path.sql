-- Migration: Fix materialized view function to work with search_path = ''
-- Description: The get_full_tree_from_mv() function has SECURITY DEFINER with search_path = ''
--              which prevents it from finding mv_full_navigation_trees. This migration fixes
--              the function to use fully qualified table names.
-- 
-- Issue: After security hardening migration, the function fails with:
--        "relation 'mv_full_navigation_trees' does not exist"
--        because it can't find the table without schema qualification.
--
-- Fix: Update function to use public.mv_full_navigation_trees

-- Drop and recreate the function with fully qualified table names
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

-- Grant permissions (re-grant to be safe)
GRANT SELECT ON public.mv_full_navigation_trees TO authenticated;
GRANT SELECT ON public.mv_full_navigation_trees TO service_role;
GRANT EXECUTE ON FUNCTION public.get_full_tree_from_mv(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_full_tree_from_mv(UUID, UUID) TO service_role;

