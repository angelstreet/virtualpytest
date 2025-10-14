-- Migration 011: Add audio_silence_duration to zap_results table
-- Date: 2025-10-13
-- Description: Adds audio silence duration tracking for zapping detection

-- Drop existing column if it exists (for clean recreation)
ALTER TABLE zap_results 
DROP COLUMN IF EXISTS audio_silence_duration;

-- ==============================================================================
-- ADD AUDIO SILENCE DURATION COLUMN
-- ==============================================================================

-- Add audio_silence_duration column
ALTER TABLE zap_results 
ADD COLUMN audio_silence_duration numeric;

-- Add comment
COMMENT ON COLUMN zap_results.audio_silence_duration IS 'Duration of audio silence during zapping (seconds)';

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS
-- ==============================================================================
-- To rollback this migration, run:
--
-- ALTER TABLE zap_results DROP COLUMN IF EXISTS audio_silence_duration;

-- Log migration completion
SELECT 'Migration 011: audio_silence_duration column added successfully' as status;
