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

CREATE TABLE controllers (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name character varying NOT NULL,
    controller_type character varying NOT NULL,
    device_model_id uuid,
    config jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

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

CREATE TABLE campaigns (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id character varying NOT NULL UNIQUE,
    name character varying NOT NULL,
    description text,
    test_case_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    navigation_tree_id uuid,
    prioritization_enabled boolean DEFAULT false,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    creator_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Add indexes for performance
CREATE INDEX idx_device_models_team_id ON device_models(team_id);
CREATE INDEX idx_device_team_id ON device(team_id);
CREATE INDEX idx_controllers_team_id ON controllers(team_id);
CREATE INDEX idx_controllers_device_model ON controllers(device_model_id);
CREATE INDEX idx_environment_profiles_team_id ON environment_profiles(team_id);
CREATE INDEX idx_campaigns_team_id ON campaigns(team_id);

-- Add comments
COMMENT ON TABLE device_models IS 'Device model definitions and capabilities';
COMMENT ON TABLE device IS 'Physical device instances';
COMMENT ON TABLE controllers IS 'Device controller configurations';
COMMENT ON TABLE environment_profiles IS 'Test environment configurations';
COMMENT ON TABLE campaigns IS 'Test campaign definitions';

-- Enable Row Level Security (RLS)
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE device ENABLE ROW LEVEL SECURITY;
ALTER TABLE controllers ENABLE ROW LEVEL SECURITY;
ALTER TABLE environment_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

-- RLS Policies for teams table
CREATE POLICY "teams_select_policy" ON teams
FOR SELECT 
TO public
USING (EXISTS ( SELECT 1
   FROM team_members
  WHERE ((team_members.team_id = teams.id) AND (team_members.profile_id = auth.uid()))));

CREATE POLICY "teams_insert_policy" ON teams
FOR INSERT 
TO public;

CREATE POLICY "teams_update_policy" ON teams
FOR UPDATE 
TO public
USING (EXISTS ( SELECT 1
   FROM team_members
  WHERE ((team_members.profile_id = auth.uid()) AND (team_members.team_id = teams.id) AND (team_members.role = 'admin'::text))));

CREATE POLICY "teams_delete_policy" ON teams
FOR DELETE 
TO public
USING (EXISTS ( SELECT 1
   FROM team_members
  WHERE ((team_members.profile_id = auth.uid()) AND (team_members.team_id = teams.id) AND (team_members.role = 'admin'::text))));

-- RLS Policies for device_models table
CREATE POLICY "device_models_policy" ON device_models
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

-- RLS Policies for device table
CREATE POLICY "device_policy" ON device
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))));

CREATE POLICY "Users can manage devices for their team" ON device
FOR ALL 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

-- RLS Policies for controllers table
CREATE POLICY "Users can view controllers from their teams" ON controllers
FOR SELECT 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can insert controllers for their teams" ON controllers
FOR INSERT 
TO public;

CREATE POLICY "Users can update controllers from their teams" ON controllers
FOR UPDATE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can delete controllers from their teams" ON controllers
FOR DELETE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

-- RLS Policies for environment_profiles table
CREATE POLICY "Users can view environment profiles from their teams" ON environment_profiles
FOR SELECT 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can insert environment profiles for their teams" ON environment_profiles
FOR INSERT 
TO public;

CREATE POLICY "Users can update environment profiles from their teams" ON environment_profiles
FOR UPDATE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can delete environment profiles from their teams" ON environment_profiles
FOR DELETE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

-- RLS Policies for campaigns table
CREATE POLICY "Users can view campaigns from their teams" ON campaigns
FOR SELECT 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can insert campaigns for their teams" ON campaigns
FOR INSERT 
TO public;

CREATE POLICY "Users can update campaigns from their teams" ON campaigns
FOR UPDATE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid())));

CREATE POLICY "Users can delete campaigns from their teams" ON campaigns
FOR DELETE 
TO public
USING (team_id IN ( SELECT team_members.team_id
   FROM team_members
  WHERE (team_members.profile_id = auth.uid()))); 