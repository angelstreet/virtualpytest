-- VirtualPyTest Core Tables Schema
-- This file contains the main tables for the VirtualPyTest system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Teams table (referenced by most other tables)
CREATE TABLE teams (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name text NOT NULL,
    description text,
    tenant_id uuid NOT NULL,
    created_by uuid,
    is_default boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- Core device and controller tables
CREATE TABLE device_models (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name character varying NOT NULL CHECK (length(TRIM(BOTH FROM name)) > 0),
    types jsonb DEFAULT '[]'::jsonb NOT NULL CHECK (jsonb_typeof(types) = 'array'::text),
    controllers jsonb DEFAULT '{"av": "", "power": "", "remote": "", "network": ""}'::jsonb NOT NULL CHECK (jsonb_typeof(controllers) = 'object'::text),
    version character varying,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE device (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    model text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    controller_configs jsonb COMMENT ON COLUMN device.controller_configs IS 'controller config'
);

-- controllers table removed - does not exist in current database

-- Environment and campaign tables
CREATE TABLE environment_profiles (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name character varying NOT NULL,
    description text,
    config jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- campaigns table removed - does not exist in current database

-- Campaign executions table (exists in database but was not previously documented)
CREATE TABLE campaign_executions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    campaign_name character varying NOT NULL,
    campaign_description text,
    campaign_execution_id character varying NOT NULL,
    userinterface_name character varying,
    host_name character varying NOT NULL,
    device_name character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    execution_time_ms integer,
    success boolean NOT NULL DEFAULT false,
    error_message text,
    script_configurations jsonb NOT NULL DEFAULT '[]'::jsonb,
    execution_config jsonb DEFAULT '{}'::jsonb,
    script_result_ids uuid[] DEFAULT '{}'::uuid[],
    html_report_r2_path text,
    html_report_r2_url text,
    executed_by uuid,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now())
);

-- Add indexes for performance
CREATE INDEX idx_device_models_team_id ON device_models(team_id);
CREATE INDEX idx_device_team_id ON device(team_id);
-- controllers indexes removed - table does not exist
CREATE INDEX idx_environment_profiles_team_id ON environment_profiles(team_id);
CREATE INDEX idx_campaign_executions_team_id ON campaign_executions(team_id);
CREATE INDEX idx_campaign_executions_campaign_name ON campaign_executions(campaign_name);
CREATE INDEX idx_campaign_executions_host_name ON campaign_executions(host_name);
CREATE INDEX idx_campaign_executions_status ON campaign_executions(status);

-- Add comments
COMMENT ON TABLE device_models IS 'Device model definitions and capabilities';
COMMENT ON TABLE device IS 'Physical device instances';
-- controllers and campaigns table comments removed - tables do not exist
COMMENT ON TABLE environment_profiles IS 'Test environment configurations';
COMMENT ON TABLE campaign_executions IS 'Campaign execution tracking and results';

-- Enable Row Level Security (RLS)
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE device ENABLE ROW LEVEL SECURITY;
-- controllers and campaigns RLS removed - tables do not exist
ALTER TABLE environment_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_executions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for teams table (updated to match actual working database)
CREATE POLICY "teams_access_policy" ON teams
FOR ALL 
TO public
USING (true);

-- RLS Policies for device_models table (updated to match actual working database)
CREATE POLICY "device_models_access_policy" ON device_models
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for device table (updated to match actual working database)
CREATE POLICY "device_access_policy" ON device
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- controllers table RLS policies removed - table does not exist

-- RLS Policies for environment_profiles table (updated to match actual working database)
CREATE POLICY "environment_profiles_access_policy" ON environment_profiles
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- campaigns table RLS policies removed - table does not exist

-- RLS Policies for campaign_executions table (updated to match actual working database)
CREATE POLICY "campaign_executions_access_policy" ON campaign_executions
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true); 