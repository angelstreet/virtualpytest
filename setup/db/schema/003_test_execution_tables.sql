-- VirtualPyTest Test Execution Tables Schema
-- This file contains tables for test cases, executions, and results

-- Test case definitions
CREATE TABLE test_cases (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    test_id character varying NOT NULL UNIQUE,
    name character varying NOT NULL,
    test_type character varying NOT NULL CHECK (test_type::text = ANY (ARRAY['functional'::character varying::text, 'performance'::character varying::text, 'endurance'::character varying::text, 'robustness'::character varying::text])),
    start_node character varying NOT NULL,
    steps jsonb DEFAULT '[]'::jsonb NOT NULL,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    creator_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    device_id uuid COMMENT ON COLUMN test_cases.device_id IS 'Reference to the device under test',
    environment_profile_id uuid REFERENCES environment_profiles(id) ON DELETE SET NULL COMMENT ON COLUMN test_cases.environment_profile_id IS 'Reference to environment profile with controller setup',
    verification_conditions jsonb DEFAULT '[]'::jsonb COMMENT ON COLUMN test_cases.verification_conditions IS 'Array of verification conditions to check during execution',
    expected_results jsonb DEFAULT '{}'::jsonb COMMENT ON COLUMN test_cases.expected_results IS 'Expected outcomes and verification criteria',
    execution_config jsonb DEFAULT '{}'::jsonb COMMENT ON COLUMN test_cases.execution_config IS 'Test execution configuration and parameters',
    tags text[] DEFAULT '{}'::text[] COMMENT ON COLUMN test_cases.tags IS 'Tags for categorization and filtering',
    priority integer DEFAULT 1 CHECK (priority >= 1 AND priority <= 5) COMMENT ON COLUMN test_cases.priority IS 'Test priority (1=lowest, 5=highest)',
    estimated_duration integer DEFAULT 60 COMMENT ON COLUMN test_cases.estimated_duration IS 'Estimated execution time in seconds'
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

-- Detailed execution results (legacy support)
CREATE TABLE execution_results (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    execution_id character varying NOT NULL,
    test_id uuid REFERENCES test_cases(test_id) ON DELETE CASCADE,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE SET NULL,
    status character varying NOT NULL,
    result_data jsonb DEFAULT '{}'::jsonb,
    execution_time integer, -- in seconds
    error_details text,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now()
);

-- Script execution results
CREATE TABLE script_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    script_name character varying NOT NULL,
    script_type character varying NOT NULL,
    status character varying NOT NULL,
    result_data jsonb DEFAULT '{}'::jsonb,
    output text,
    error_output text,
    exit_code integer,
    execution_time integer, -- in seconds
    discard boolean DEFAULT false,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    executed_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
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
CREATE INDEX idx_execution_results_execution_id ON execution_results(execution_id);
CREATE INDEX idx_script_results_team_id ON script_results(team_id);
CREATE INDEX idx_script_results_script_name ON script_results(script_name);
CREATE INDEX idx_script_results_status ON script_results(status);
CREATE INDEX idx_script_results_discard ON script_results(discard);

-- Add comments
COMMENT ON TABLE test_cases IS 'Test case definitions and configurations';
COMMENT ON TABLE test_executions IS 'Test execution tracking records';
COMMENT ON TABLE test_results IS 'Test execution results and outcomes';
COMMENT ON TABLE execution_results IS 'Legacy detailed execution results';
COMMENT ON TABLE script_results IS 'Script execution results and logs'; 