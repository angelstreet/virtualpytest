-- VirtualPyTest Core Tables Schema
-- This file contains the main tables for the VirtualPyTest system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core device and controller tables
CREATE TABLE device_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    manufacturer VARCHAR(255),
    model_type VARCHAR(100) NOT NULL, -- phone, tablet, tv, desktop, etc.
    os_type VARCHAR(100), -- android, ios, linux, windows, etc.
    min_version VARCHAR(50),
    max_version VARCHAR(50),
    capabilities JSONB DEFAULT '{}', -- device capabilities
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, team_id)
);

CREATE TABLE device (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    device_model_id UUID REFERENCES device_models(id) ON DELETE CASCADE,
    ip_address INET,
    port INTEGER,
    status VARCHAR(50) DEFAULT 'offline', -- online, offline, busy, error
    connection_config JSONB DEFAULT '{}', -- ADB, SSH, etc. config
    capabilities JSONB DEFAULT '{}',
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE controllers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    controller_type VARCHAR(100) NOT NULL, -- adb, appium, playwright, etc.
    device_model_id UUID REFERENCES device_models(id) ON DELETE CASCADE,
    config JSONB DEFAULT '{}', -- controller-specific configuration
    is_active BOOLEAN DEFAULT true,
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Environment and campaign tables
CREATE TABLE environment_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}', -- environment variables, settings
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, team_id)
);

CREATE TABLE campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    device_ids UUID[] DEFAULT '{}', -- array of device IDs
    environment_profile_id UUID REFERENCES environment_profiles(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, paused, completed
    config JSONB DEFAULT '{}',
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_device_models_team_id ON device_models(team_id);
CREATE INDEX idx_device_team_id ON device(team_id);
CREATE INDEX idx_device_status ON device(status);
CREATE INDEX idx_controllers_team_id ON controllers(team_id);
CREATE INDEX idx_controllers_device_model ON controllers(device_model_id);
CREATE INDEX idx_environment_profiles_team_id ON environment_profiles(team_id);
CREATE INDEX idx_campaigns_team_id ON campaigns(team_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- Add comments
COMMENT ON TABLE device_models IS 'Device model definitions and capabilities';
COMMENT ON TABLE device IS 'Physical device instances';
COMMENT ON TABLE controllers IS 'Device controller configurations';
COMMENT ON TABLE environment_profiles IS 'Test environment configurations';
COMMENT ON TABLE campaigns IS 'Test campaign definitions'; 