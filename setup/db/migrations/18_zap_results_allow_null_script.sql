-- Migration: Allow script_result_id to be NULL for automatic zapping detection
-- When zapping is detected automatically during monitoring (not part of a script),
-- script_result_id will be NULL.

ALTER TABLE zap_results 
    ALTER COLUMN script_result_id DROP NOT NULL;

-- Add comments to clarify usage
COMMENT ON COLUMN zap_results.script_result_id IS 'References script execution. NULL for automatic zapping detection during monitoring.';
COMMENT ON COLUMN zap_results.detection_method IS 'Detection method: automatic (system action) or manual (user IR remote)';

