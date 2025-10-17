-- Migration: Add userinterface_id to verifications_references
-- Date: 2025-10-17
-- Purpose: Migrate from device_model to userinterface_id for better organization

-- Add userinterface_id column
ALTER TABLE verifications_references 
ADD COLUMN IF NOT EXISTS userinterface_id UUID REFERENCES userinterfaces(id);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_verifications_references_userinterface_id 
ON verifications_references(userinterface_id);

-- Add comment
COMMENT ON COLUMN verifications_references.userinterface_id IS 
'Foreign key to userinterfaces table. References are now organized by userinterface instead of device_model.';

