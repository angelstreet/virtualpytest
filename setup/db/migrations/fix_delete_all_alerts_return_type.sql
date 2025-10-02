-- Fix delete_all_alerts function to return json instead of jsonb
-- This resolves serialization issues with Supabase Python client

-- Drop the existing function first (required when changing return type)
DROP FUNCTION IF EXISTS delete_all_alerts();

-- Recreate with corrected return type
CREATE OR REPLACE FUNCTION delete_all_alerts()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  deleted_count integer;
BEGIN
  -- Count before deletion
  SELECT COUNT(*) INTO deleted_count FROM alerts;
  
  -- Delete all records with WHERE clause (required by some DB configs)
  -- Using "WHERE true" matches all rows while satisfying the WHERE requirement
  DELETE FROM alerts WHERE true;
  
  -- Return result as JSON (text-based format works better with Supabase Python client)
  RETURN json_build_object(
    'success', true,
    'deleted_count', deleted_count,
    'message', 'Successfully deleted ' || deleted_count || ' alerts'
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN json_build_object(
      'success', false,
      'error', SQLERRM,
      'deleted_count', 0
    );
END;
$$;

COMMENT ON FUNCTION delete_all_alerts() IS 'Efficiently deletes all alerts from the database without returning data to the client, preventing timeout issues with large datasets';
