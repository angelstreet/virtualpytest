-- VirtualPyTest Test Execution Tables Schema
-- This file contains tables for test cases, executions, and results

-- Test case definitions (UPDATED SCHEMA)
CREATE TABLE test_cases (
    test_id uuid DEFAULT gen_random_uuid() PRIMARY KEY,  -- UPDATED: Changed from id to test_id
    name character varying NOT NULL,
    test_type character varying NOT NULL CHECK (test_type::text = ANY (ARRAY['functional'::character varying::text, 'performance'::character varying::text, 'endurance'::character varying::text, 'robustness'::character varying::text])),
    start_node character varying NOT NULL,
    steps jsonb DEFAULT '[]'::jsonb NOT NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    creator_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    device_id uuid,
    environment_profile_id uuid REFERENCES environment_profiles(id) ON DELETE SET NULL,
    verification_conditions jsonb DEFAULT '[]'::jsonb,
    expected_results jsonb DEFAULT '{}'::jsonb,
    execution_config jsonb DEFAULT '{}'::jsonb,
    tags text[] DEFAULT '{}'::text[],
    priority integer DEFAULT 1 CHECK (priority >= 1 AND priority <= 5),
    estimated_duration integer DEFAULT 60,
    -- UPDATED: AI-related columns
    creator character varying DEFAULT 'manual'::character varying CHECK (creator::text = ANY (ARRAY['ai'::character varying, 'manual'::character varying]::text[])),
    original_prompt text,
    ai_analysis jsonb DEFAULT '{}'::jsonb,
    compatible_devices jsonb DEFAULT '["all"]'::jsonb,
    compatible_userinterfaces jsonb DEFAULT '["all"]'::jsonb,
    device_adaptations jsonb DEFAULT '{}'::jsonb
);

-- Test execution records
CREATE TABLE test_executions (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_id uuid REFERENCES test_cases(test_id) ON DELETE CASCADE,
    execution_id character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying,
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    duration integer,
    device_id uuid,
    environment_profile_id uuid REFERENCES environment_profiles(id) ON DELETE SET NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    executed_by uuid,
    created_at timestamp with time zone DEFAULT now()
);

-- Test results
CREATE TABLE test_results (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    execution_id uuid REFERENCES test_executions(id) ON DELETE CASCADE,
    test_id uuid REFERENCES test_cases(test_id) ON DELETE CASCADE,
    status character varying NOT NULL,
    result_data jsonb DEFAULT '{}'::jsonb,
    error_message text,
    stack_trace text,
    screenshots text[] DEFAULT '{}'::text[],
    logs text,
    metrics jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now()
);

-- Detailed execution results (updated to match automai schema exactly)
CREATE TABLE execution_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE SET NULL,
    edge_id text,
    node_id text,
    execution_type text NOT NULL,
    host_name text NOT NULL,
    device_model text,
    success boolean NOT NULL,
    execution_time_ms integer,
    message text,
    error_details jsonb,
    executed_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    script_result_id uuid,
    script_context text DEFAULT 'direct'::text,
    action_set_id text  -- UPDATED: Added for bidirectional edge tracking
);

-- Script execution results (UPDATED SCHEMA)
CREATE TABLE script_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    script_name text NOT NULL,
    script_type text NOT NULL,
    userinterface_name text,
    host_name text NOT NULL,
    device_name text NOT NULL,
    success boolean NOT NULL,
    execution_time_ms integer,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone NOT NULL,
    html_report_r2_path text,
    html_report_r2_url text,
    discard boolean DEFAULT false,
    error_msg text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    -- UPDATED: Additional fields
    logs_r2_path text,
    logs_r2_url text,
    checked boolean DEFAULT false,
    check_type character varying,
    discard_comment text
);

-- Zap results table (moved from 001_core_tables.sql to fix dependency)
CREATE TABLE zap_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    script_result_id uuid REFERENCES script_results(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    host_name text NOT NULL,
    device_name text NOT NULL,
    device_model text,
    execution_date timestamp with time zone NOT NULL,
    iteration_index integer NOT NULL,
    action_command text NOT NULL,
    duration_seconds numeric NOT NULL,
    motion_detected boolean DEFAULT false,
    subtitles_detected boolean DEFAULT false,
    audio_speech_detected boolean DEFAULT false,
    blackscreen_freeze_detected boolean DEFAULT false,
    subtitle_language text,
    subtitle_text text,
    audio_language text,
    audio_transcript text,
    blackscreen_freeze_duration_seconds numeric,
    detection_method text,
    channel_name text,
    channel_number text,
    program_name text,
    program_start_time text,
    program_end_time text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    userinterface_name text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);

-- Add indexes for performance
CREATE INDEX idx_test_cases_team_id ON test_cases(team_id);
CREATE INDEX idx_test_cases_test_type ON test_cases(test_type);
CREATE INDEX idx_test_cases_device_id ON test_cases(device_id);
CREATE INDEX idx_test_cases_priority ON test_cases(priority);
CREATE INDEX idx_test_executions_team_id ON test_executions(team_id);
CREATE INDEX idx_test_executions_test_id ON test_executions(test_id);
CREATE INDEX idx_test_executions_status ON test_executions(status);
CREATE INDEX idx_test_executions_start_time ON test_executions(start_time);
CREATE INDEX idx_test_results_team_id ON test_results(team_id);
CREATE INDEX idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX idx_test_results_status ON test_results(status);
CREATE INDEX idx_execution_results_team_id ON execution_results(team_id);
CREATE INDEX idx_execution_results_tree_id ON execution_results(tree_id);
CREATE INDEX idx_execution_results_host_name ON execution_results(host_name);
CREATE INDEX idx_execution_results_executed_at ON execution_results(executed_at);
CREATE INDEX idx_script_results_team_id ON script_results(team_id);
CREATE INDEX idx_script_results_script_name ON script_results(script_name);
CREATE INDEX idx_script_results_host_name ON script_results(host_name);
CREATE INDEX idx_script_results_discard ON script_results(discard);
CREATE INDEX idx_zap_results_team_id ON zap_results(team_id);
CREATE INDEX idx_zap_results_script_result_id ON zap_results(script_result_id);
CREATE INDEX idx_zap_results_host_name ON zap_results(host_name);
CREATE INDEX idx_zap_results_execution_date ON zap_results(execution_date);

-- Add comments
COMMENT ON TABLE test_cases IS 'Test case definitions and configurations';
COMMENT ON TABLE test_executions IS 'Test execution tracking records';
COMMENT ON TABLE test_results IS 'Test execution results and outcomes';
COMMENT ON TABLE execution_results IS 'Detailed execution results matching automai schema';
COMMENT ON TABLE script_results IS 'Script execution results matching automai schema';
COMMENT ON TABLE zap_results IS 'Individual zap iteration results with detailed analysis data';

-- Enable Row Level Security (RLS)
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE script_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE zap_results ENABLE ROW LEVEL SECURITY;

-- RLS Policies for test_cases table (updated to match actual working database)
CREATE POLICY "test_cases_access_policy" ON test_cases
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for test_executions table (updated to match actual working database)
CREATE POLICY "test_executions_access_policy" ON test_executions
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for test_results table (updated to match actual working database)
CREATE POLICY "test_results_access_policy" ON test_results
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for execution_results table (updated to match actual working database)
CREATE POLICY "execution_results_access_policy" ON execution_results
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for script_results table (updated to match actual working database)
CREATE POLICY "script_results_access_policy" ON script_results
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- RLS Policies for zap_results table
CREATE POLICY "zap_results_access_policy" ON zap_results
FOR ALL 
TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true); 