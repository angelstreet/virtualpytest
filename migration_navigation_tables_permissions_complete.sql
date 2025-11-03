-- ============================================================================
-- COMPLETE MIGRATION: Navigation Tables Permissions and RLS Policies
-- ============================================================================
-- Description: Sets up all permissions and RLS policies for navigation tables
-- Source: virtualpytest (working instance)
-- Target: Apply to any Supabase project to enable full access to navigation
-- ============================================================================

-- ============================================================================
-- STEP 1: Enable RLS on Navigation Tables (if not already enabled)
-- ============================================================================

ALTER TABLE public.navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.navigation_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.navigation_edges ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 2: Drop existing policies (if they exist)
-- ============================================================================

DROP POLICY IF EXISTS navigation_trees_access_policy ON public.navigation_trees;
DROP POLICY IF EXISTS navigation_nodes_access_policy ON public.navigation_nodes;
DROP POLICY IF EXISTS navigation_edges_access_policy ON public.navigation_edges;

-- ============================================================================
-- STEP 3: Create RLS Policies (Permissive ALL access)
-- ============================================================================

-- Policy for navigation_trees
CREATE POLICY navigation_trees_access_policy ON public.navigation_trees
FOR ALL
TO public
USING (
    (auth.uid() IS NULL) 
    OR (auth.role() = 'service_role') 
    OR true
);

-- Policy for navigation_nodes
CREATE POLICY navigation_nodes_access_policy ON public.navigation_nodes
FOR ALL
TO public
USING (
    (auth.uid() IS NULL) 
    OR (auth.role() = 'service_role') 
    OR true
);

-- Policy for navigation_edges
CREATE POLICY navigation_edges_access_policy ON public.navigation_edges
FOR ALL
TO public
USING (
    (auth.uid() IS NULL) 
    OR (auth.role() = 'service_role') 
    OR true
);

-- ============================================================================
-- STEP 4: Grant ALL permissions to all roles
-- ============================================================================

-- Grants for navigation_trees
GRANT ALL ON public.navigation_trees TO anon;
GRANT ALL ON public.navigation_trees TO authenticated;
GRANT ALL ON public.navigation_trees TO service_role;

-- Grants for navigation_nodes
GRANT ALL ON public.navigation_nodes TO anon;
GRANT ALL ON public.navigation_nodes TO authenticated;
GRANT ALL ON public.navigation_nodes TO service_role;

-- Grants for navigation_edges
GRANT ALL ON public.navigation_edges TO anon;
GRANT ALL ON public.navigation_edges TO authenticated;
GRANT ALL ON public.navigation_edges TO service_role;

-- ============================================================================
-- STEP 5: Grant USAGE on sequences (for INSERT operations)
-- ============================================================================

-- Grant usage on sequences if they exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'navigation_trees_id_seq') THEN
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_trees_id_seq TO anon;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_trees_id_seq TO authenticated;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_trees_id_seq TO service_role;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'navigation_nodes_id_seq') THEN
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_nodes_id_seq TO anon;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_nodes_id_seq TO authenticated;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_nodes_id_seq TO service_role;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'navigation_edges_id_seq') THEN
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_edges_id_seq TO anon;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_edges_id_seq TO authenticated;
        GRANT USAGE, SELECT ON SEQUENCE public.navigation_edges_id_seq TO service_role;
    END IF;
END $$;

-- ============================================================================
-- STEP 6: Add comments for documentation
-- ============================================================================

COMMENT ON POLICY navigation_trees_access_policy ON public.navigation_trees IS 
'Allows all operations (SELECT, INSERT, UPDATE, DELETE) for all users including anonymous. 
Required for navigation tree management in the frontend application.';

COMMENT ON POLICY navigation_nodes_access_policy ON public.navigation_nodes IS 
'Allows all operations (SELECT, INSERT, UPDATE, DELETE) for all users including anonymous. 
Required for navigation node management in the frontend application.';

COMMENT ON POLICY navigation_edges_access_policy ON public.navigation_edges IS 
'Allows all operations (SELECT, INSERT, UPDATE, DELETE) for all users including anonymous. 
Required for navigation edge management in the frontend application.';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- All navigation tables now have:
-- ✅ RLS enabled
-- ✅ Permissive policies for all operations
-- ✅ Full grants (ALL privileges) to anon, authenticated, and service_role
-- ✅ Sequence usage permissions for INSERT operations
--
-- Users should now be able to:
-- - Create new navigation trees
-- - Add/edit/delete navigation nodes
-- - Add/edit/delete navigation edges
-- ============================================================================

