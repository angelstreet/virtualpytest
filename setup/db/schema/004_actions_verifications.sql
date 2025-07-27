-- VirtualPyTest Actions and Verifications Tables Schema
-- This file contains tables for test actions and verification definitions

-- Test actions and commands
CREATE TABLE actions (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name text NOT NULL,
    device_model text NOT NULL,
    action_type text NOT NULL,
    command text NOT NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    params jsonb,
    requires_input boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Verification definitions and rules
CREATE TABLE verifications (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name text NOT NULL,
    device_model text NOT NULL,
    verification_type text NOT NULL COMMENT ON COLUMN verifications.verification_type IS 'Type of verification: image, text, adb, element, etc.',
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    command text COMMENT ON COLUMN verifications.command IS 'The verification command/method to execute',
    params jsonb COMMENT ON COLUMN verifications.params IS 'Parameters specific to this verification type',
    reference_id uuid
);

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

-- Add foreign key constraint for verifications reference
ALTER TABLE verifications
ADD CONSTRAINT verifications_reference_id_fkey
FOREIGN KEY (reference_id) REFERENCES verifications_references(id) ON DELETE SET NULL;

-- Add indexes for performance
CREATE INDEX idx_actions_team_id ON actions(team_id);
CREATE INDEX idx_actions_device_model ON actions(device_model);
CREATE INDEX idx_actions_action_type ON actions(action_type);

CREATE INDEX idx_verifications_team_id ON verifications(team_id);
CREATE INDEX idx_verifications_device_model ON verifications(device_model);
CREATE INDEX idx_verifications_verification_type ON verifications(verification_type);

CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);
CREATE INDEX idx_verifications_references_reference_type ON verifications_references(reference_type);

-- Add comments
COMMENT ON TABLE actions IS 'Test action definitions and commands';
COMMENT ON TABLE verifications IS 'Stores verification definitions for UI testing - these are test assertions, not action commands';
COMMENT ON TABLE verifications_references IS 'Reference data for verifications (screenshots, elements, etc.)'; 