-- Migration: Add audio_silence_duration to zap_results table
-- Date: 2025-10-13
-- Description: Adds audio silence duration tracking for zapping detection

-- Add audio_silence_duration column
ALTER TABLE zap_results 
ADD COLUMN IF NOT EXISTS audio_silence_duration numeric;

-- Add comment
COMMENT ON COLUMN zap_results.audio_silence_duration IS 'Duration of audio silence during zapping (seconds)';

-- Verify column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'zap_results' 
AND column_name = 'audio_silence_duration';

