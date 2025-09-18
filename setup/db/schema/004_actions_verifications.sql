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
    device_model text NOT NULL,
    reference_type text NOT NULL CHECK (reference_type = ANY (ARRAY['reference_image'::text, 'reference_text'::text])),
    area jsonb,
    r2_path text NOT NULL,
    r2_url text NOT NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- verifications table foreign key removed - table does not exist

-- actions and verifications indexes removed - tables do not exist

CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);
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