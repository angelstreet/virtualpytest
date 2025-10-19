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
    userinterface_name text,  -- PRIMARY: Userinterface name (e.g., 'horizon_android_tv')
    device_model text,  -- DEPRECATED: Kept for backward compatibility during migration
    userinterface_id uuid REFERENCES userinterfaces(id),  -- Foreign key reference (optional)
    reference_type text NOT NULL CHECK (reference_type = ANY (ARRAY['reference_image'::text, 'reference_text'::text])),
    area jsonb,
    r2_path text NOT NULL,  -- Path format: reference-images/{userinterface_name}/{filename} or text-references/{userinterface_name}/{filename}
    r2_url text NOT NULL,   -- URL format: https://.../reference-images/{userinterface_name}/{filename}
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT verifications_references_team_id_name_userinterface_reference_key 
        UNIQUE (team_id, name, userinterface_name, reference_type)
);

-- Add comments to explain the columns
COMMENT ON COLUMN verifications_references.userinterface_name IS 
'PRIMARY: Userinterface name string (e.g., ''horizon_android_tv''). Used for grouping and filtering references.';

COMMENT ON COLUMN verifications_references.userinterface_id IS 
'OPTIONAL: Foreign key to userinterfaces table. References are organized by userinterface_name (text) for simplicity.';

-- verifications table foreign key removed - table does not exist

-- actions and verifications indexes removed - tables do not exist

CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_userinterface_name ON verifications_references(userinterface_name);  -- PRIMARY INDEX
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);  -- DEPRECATED: Will be removed after migration
CREATE INDEX idx_verifications_references_userinterface_id ON verifications_references(userinterface_id);  -- OPTIONAL FK
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