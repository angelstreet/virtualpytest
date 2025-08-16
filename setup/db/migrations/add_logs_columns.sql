-- Add logs columns to script_results table
-- Execute this in Supabase SQL Editor to add log upload functionality

-- Add logs columns to script_results table
ALTER TABLE script_results 
ADD COLUMN IF NOT EXISTS logs_r2_path text,
ADD COLUMN IF NOT EXISTS logs_r2_url text;

-- Add comment for the new columns
COMMENT ON COLUMN script_results.logs_r2_path IS 'R2 storage path for script execution logs';
COMMENT ON COLUMN script_results.logs_r2_url IS 'Public R2 URL for script execution logs';

-- Verify the columns were added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'script_results' 
AND column_name IN ('logs_r2_path', 'logs_r2_url');
