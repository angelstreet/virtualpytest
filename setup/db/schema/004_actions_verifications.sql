-- VirtualPyTest Actions and Verifications Tables Schema
-- This file contains tables for test actions and verification definitions

-- Test actions and commands
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    device_model VARCHAR(255) NOT NULL, -- device model this action applies to
    action_type VARCHAR(100) NOT NULL, -- click, input, swipe, wait, etc.
    command TEXT NOT NULL, -- the actual command/selector
    params JSONB DEFAULT '{}', -- action parameters
    requires_input BOOLEAN DEFAULT false, -- whether action needs user input
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    team_id UUID NOT NULL,
    created_by UUID, -- user who created the action
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, device_model, action_type, team_id)
);

-- Verification definitions and rules
CREATE TABLE verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    device_model VARCHAR(255) NOT NULL, -- device model this verification applies to
    verification_type VARCHAR(100) NOT NULL, -- element_exists, text_contains, etc.
    command TEXT NOT NULL, -- verification selector/command
    expected_value TEXT, -- expected result
    params JSONB DEFAULT '{}', -- verification parameters
    timeout_seconds INTEGER DEFAULT 30, -- verification timeout
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    team_id UUID NOT NULL,
    created_by UUID, -- user who created the verification
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, device_model, verification_type, team_id)
);

-- Verification reference data
CREATE TABLE verifications_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    device_model VARCHAR(255) NOT NULL, -- device model this reference applies to
    reference_type VARCHAR(100) NOT NULL, -- screenshot, element, property, etc.
    reference_data JSONB DEFAULT '{}', -- reference data (coordinates, text, etc.)
    file_path TEXT, -- path to reference file (screenshot, etc.)
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    team_id UUID NOT NULL,
    created_by UUID, -- user who created the reference
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, device_model, reference_type, team_id)
);

-- Add indexes for performance
CREATE INDEX idx_actions_team_id ON actions(team_id);
CREATE INDEX idx_actions_device_model ON actions(device_model);
CREATE INDEX idx_actions_action_type ON actions(action_type);
CREATE INDEX idx_actions_is_active ON actions(is_active);
CREATE INDEX idx_actions_created_by ON actions(created_by);

CREATE INDEX idx_verifications_team_id ON verifications(team_id);
CREATE INDEX idx_verifications_device_model ON verifications(device_model);
CREATE INDEX idx_verifications_verification_type ON verifications(verification_type);
CREATE INDEX idx_verifications_is_active ON verifications(is_active);
CREATE INDEX idx_verifications_created_by ON verifications(created_by);

CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);
CREATE INDEX idx_verifications_references_reference_type ON verifications_references(reference_type);
CREATE INDEX idx_verifications_references_is_active ON verifications_references(is_active);
CREATE INDEX idx_verifications_references_created_by ON verifications_references(created_by);

-- Add comments
COMMENT ON TABLE actions IS 'Test action definitions and commands';
COMMENT ON TABLE verifications IS 'Verification rules and expected outcomes';
COMMENT ON TABLE verifications_references IS 'Reference data for verifications (screenshots, elements, etc.)'; 