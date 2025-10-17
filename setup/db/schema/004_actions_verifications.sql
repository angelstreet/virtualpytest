-- VirtualPyTest Actions and Verifications Tables Schema
-- This file contains tables for test actions and verification definitions

-- Drop existing tables if they exist (for clean recreation)
DROP TABLE IF EXISTS verifications_references CASCADE;

-- actions table removed - does not exist in current database

-- verifications table removed - does not exist in current database

-- Verification reference data
CREATE TABLE verifications_references (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    device_model text NOT NULL,  -- DEPRECATED: Kept for backward compatibility during migration, will be removed
    userinterface_id uuid REFERENCES userinterfaces(id),  -- NEW: References are now organized by userinterface
    reference_type text NOT NULL CHECK (reference_type = ANY (ARRAY['reference_image'::text, 'reference_text'::text])),
    area jsonb,
    r2_path text NOT NULL,  -- Path format: reference-images/{userinterface_name}/{filename} or text-references/{userinterface_name}/{filename}
    r2_url text NOT NULL,   -- URL format: https://.../reference-images/{userinterface_name}/{filename}
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Add comment to explain the migration
COMMENT ON COLUMN verifications_references.userinterface_id IS 
'Foreign key to userinterfaces table. References are now organized by userinterface instead of device_model.';

COMMENT ON COLUMN verifications_references.device_model IS 
'DEPRECATED: Kept for backward compatibility during migration. Use userinterface_id instead.';

-- verifications table foreign key removed - table does not exist

-- actions and verifications indexes removed - tables do not exist

CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);  -- DEPRECATED: Will be removed after migration
CREATE INDEX idx_verifications_references_userinterface_id ON verifications_references(userinterface_id);  -- NEW
CREATE INDEX idx_verifications_references_reference_type ON verifications_references(reference_type);

-- Add comments
COMMENT ON TABLE verifications_references IS 'Reference data for verifications (screenshots, elements, etc.)';

-- Enable Row Level Security (RLS)
ALTER TABLE verifications_references ENABLE ROW LEVEL SECURITY;

-- RLS Policies for verifications_references table (updated to match actual working database)
CREATE POLICY "verifications_references_access_policy" ON verifications_references
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true); 