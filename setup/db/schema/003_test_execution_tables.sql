-- VirtualPyTest Test Execution Tables Schema
-- This file contains tables for test cases, executions, and results

-- Test case definitions
CREATE TABLE test_cases (
    test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    test_type VARCHAR(100) NOT NULL, -- unit, integration, e2e, etc.
    start_node VARCHAR(255), -- starting navigation node
    steps JSONB DEFAULT '[]', -- test steps array
    device_id UUID REFERENCES device(id) ON DELETE SET NULL,
    environment_profile_id UUID REFERENCES environment_profiles(id) ON DELETE SET NULL,
    verification_conditions JSONB DEFAULT '[]', -- verification steps
    expected_results JSONB DEFAULT '{}', -- expected outcomes
    execution_config JSONB DEFAULT '{}', -- execution parameters
    tags TEXT[] DEFAULT '{}', -- test tags for categorization
    priority INTEGER DEFAULT 1, -- 1=high, 2=medium, 3=low
    estimated_duration INTEGER DEFAULT 60, -- in seconds
    team_id UUID NOT NULL,
    creator_id UUID, -- user who created the test
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test execution records
CREATE TABLE test_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID REFERENCES test_cases(test_id) ON DELETE CASCADE,
    execution_id VARCHAR(255) NOT NULL, -- unique execution identifier
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTEGER, -- execution time in seconds
    device_id UUID REFERENCES device(id) ON DELETE SET NULL,
    environment_profile_id UUID REFERENCES environment_profiles(id) ON DELETE SET NULL,
    team_id UUID NOT NULL,
    executed_by UUID, -- user who executed the test
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test results
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES test_executions(id) ON DELETE CASCADE,
    test_id UUID REFERENCES test_cases(test_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL, -- passed, failed, skipped, error
    result_data JSONB DEFAULT '{}', -- detailed result information
    error_message TEXT,
    stack_trace TEXT,
    screenshots TEXT[] DEFAULT '{}', -- array of screenshot URLs
    logs TEXT,
    metrics JSONB DEFAULT '{}', -- performance metrics
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Detailed execution results (legacy support)
CREATE TABLE execution_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) NOT NULL,
    test_id UUID REFERENCES test_cases(test_id) ON DELETE CASCADE,
    tree_id UUID REFERENCES navigation_trees(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL,
    result_data JSONB DEFAULT '{}',
    execution_time INTEGER, -- in seconds
    error_details TEXT,
    team_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Script execution results
CREATE TABLE script_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_name VARCHAR(255) NOT NULL,
    script_type VARCHAR(100) NOT NULL, -- python, shell, etc.
    status VARCHAR(50) NOT NULL, -- success, failure, timeout
    result_data JSONB DEFAULT '{}',
    output TEXT, -- script output
    error_output TEXT, -- error messages
    exit_code INTEGER,
    execution_time INTEGER, -- in seconds
    discard BOOLEAN DEFAULT false, -- mark for cleanup
    team_id UUID NOT NULL,
    executed_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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