-- =====================================================
-- Agent Feedback & Benchmarking System
-- =====================================================
-- Provides:
-- 1. User feedback collection per task
-- 2. Benchmark test definitions
-- 3. Benchmark run tracking
-- 4. Aggregated agent scores
-- =====================================================

-- Drop existing tables if any (for clean schema updates)
DROP TABLE IF EXISTS agent_benchmark_results CASCADE;
DROP TABLE IF EXISTS agent_benchmark_runs CASCADE;
DROP TABLE IF EXISTS agent_benchmarks CASCADE;
DROP TABLE IF EXISTS agent_feedback CASCADE;
DROP TABLE IF EXISTS agent_scores CASCADE;

-- =====================================================
-- 1. Agent Feedback Table
-- =====================================================
-- Stores user ratings after task completion

CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent reference
    agent_id VARCHAR(100) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    
    -- Task reference (from agent_execution_history)
    execution_id UUID,
    task_description TEXT,
    
    -- Rating (1-5 stars)
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    
    -- Optional feedback text
    comment TEXT,
    
    -- Categorization
    feedback_type VARCHAR(50) DEFAULT 'task_completion',  -- task_completion, bug_report, suggestion
    
    -- Metadata
    team_id UUID NOT NULL,
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for feedback queries
CREATE INDEX idx_agent_feedback_agent ON agent_feedback(agent_id, agent_version);
CREATE INDEX idx_agent_feedback_team ON agent_feedback(team_id);
CREATE INDEX idx_agent_feedback_created ON agent_feedback(created_at DESC);
CREATE INDEX idx_agent_feedback_rating ON agent_feedback(rating);

-- =====================================================
-- 2. Benchmark Definitions Table
-- =====================================================
-- Defines test cases with fixed inputs and expected outputs

CREATE TABLE agent_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Test identification
    test_id VARCHAR(50) UNIQUE NOT NULL,  -- e.g., 'bench_001_navigation'
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Test category
    category VARCHAR(50) NOT NULL,  -- navigation, detection, execution, analysis, recovery
    
    -- Test definition
    input_prompt TEXT NOT NULL,           -- The task/prompt given to agent
    expected_output JSONB NOT NULL,       -- Expected result (can be partial match)
    validation_type VARCHAR(50) NOT NULL, -- exact, contains, regex, custom
    
    -- Scoring
    max_points DECIMAL(5,2) DEFAULT 1.0,
    timeout_seconds INTEGER DEFAULT 60,
    
    -- Applicability
    applicable_agent_types TEXT[],  -- Which agent types can run this test
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_benchmarks_category ON agent_benchmarks(category);
CREATE INDEX idx_benchmarks_active ON agent_benchmarks(is_active);

-- =====================================================
-- 3. Benchmark Runs Table
-- =====================================================
-- Tracks each benchmark execution

CREATE TABLE agent_benchmark_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent being tested
    agent_id VARCHAR(100) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    
    -- Run status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    
    -- Progress
    total_tests INTEGER DEFAULT 0,
    completed_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    
    -- Scores
    score_percent DECIMAL(5,2),  -- 0-100
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error info
    error_message TEXT,
    
    -- Metadata
    team_id UUID NOT NULL,
    triggered_by UUID,  -- User who started the benchmark
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_benchmark_runs_agent ON agent_benchmark_runs(agent_id, agent_version);
CREATE INDEX idx_benchmark_runs_status ON agent_benchmark_runs(status);
CREATE INDEX idx_benchmark_runs_team ON agent_benchmark_runs(team_id);
CREATE INDEX idx_benchmark_runs_created ON agent_benchmark_runs(created_at DESC);

-- =====================================================
-- 4. Benchmark Results Table
-- =====================================================
-- Individual test results within a run

CREATE TABLE agent_benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Parent run
    run_id UUID NOT NULL REFERENCES agent_benchmark_runs(id) ON DELETE CASCADE,
    
    -- Test reference
    benchmark_id UUID NOT NULL REFERENCES agent_benchmarks(id),
    test_id VARCHAR(50) NOT NULL,
    
    -- Result
    passed BOOLEAN NOT NULL,
    points_earned DECIMAL(5,2) DEFAULT 0,
    points_possible DECIMAL(5,2) DEFAULT 1.0,
    
    -- Execution details
    actual_output JSONB,
    duration_seconds DECIMAL(10,3),
    
    -- Failure info
    failure_reason TEXT,
    
    -- Metadata
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_benchmark_results_run ON agent_benchmark_results(run_id);
CREATE INDEX idx_benchmark_results_test ON agent_benchmark_results(test_id);
CREATE INDEX idx_benchmark_results_passed ON agent_benchmark_results(passed);

-- =====================================================
-- 5. Agent Scores Table
-- =====================================================
-- Aggregated scores per agent/version (cached for performance)

CREATE TABLE agent_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent reference
    agent_id VARCHAR(100) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    
    -- Component scores (0-100)
    benchmark_score DECIMAL(5,2) DEFAULT 0,      -- From benchmark runs
    user_rating_score DECIMAL(5,2) DEFAULT 0,    -- From feedback (1-5 → 0-100)
    success_rate_score DECIMAL(5,2) DEFAULT 0,   -- From execution history
    cost_efficiency_score DECIMAL(5,2) DEFAULT 0, -- Tokens/complexity ratio
    
    -- Overall weighted score
    overall_score DECIMAL(5,2) DEFAULT 0,
    
    -- Raw metrics
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    total_feedback_count INTEGER DEFAULT 0,
    avg_user_rating DECIMAL(3,2) DEFAULT 0,  -- 1-5 scale
    avg_duration_seconds DECIMAL(10,2) DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Benchmark metrics
    last_benchmark_run_id UUID,
    last_benchmark_score DECIMAL(5,2),
    benchmark_run_count INTEGER DEFAULT 0,
    
    -- Ranking
    rank_overall INTEGER,
    rank_in_category INTEGER,
    
    -- Trend (compared to previous period)
    score_trend VARCHAR(10),  -- up, down, stable
    score_change DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    team_id UUID NOT NULL,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(agent_id, agent_version, team_id)
);

-- Indexes
CREATE INDEX idx_agent_scores_agent ON agent_scores(agent_id, agent_version);
CREATE INDEX idx_agent_scores_team ON agent_scores(team_id);
CREATE INDEX idx_agent_scores_overall ON agent_scores(overall_score DESC);
CREATE INDEX idx_agent_scores_rank ON agent_scores(rank_overall);

-- =====================================================
-- 6. Insert Default Benchmark Tests
-- =====================================================

INSERT INTO agent_benchmarks (test_id, name, description, category, input_prompt, expected_output, validation_type, timeout_seconds, applicable_agent_types) VALUES

-- Navigation tests
('bench_nav_001', 'List User Interfaces', 'Can agent list available user interfaces?', 'navigation',
 'List all available user interfaces in the system',
 '{"contains": ["userinterfaces", "list"]}',
 'contains', 30, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager', 'qa-manager']),

('bench_nav_002', 'Navigate to Node', 'Can agent navigate to a specific UI node?', 'navigation',
 'Navigate to the Settings menu',
 '{"contains": ["navigate", "settings"]}',
 'contains', 60, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager']),

-- Detection tests
('bench_det_001', 'Device Status Check', 'Can agent check device status?', 'detection',
 'Check the status of all connected devices',
 '{"contains": ["device", "status"]}',
 'contains', 30, ARRAY['monitoring-manager', 'qa-manager']),

('bench_det_002', 'Health Check', 'Can agent perform health check?', 'detection',
 'Perform a health check on the system',
 '{"contains": ["health", "check"]}',
 'contains', 45, ARRAY['monitoring-manager']),

-- Execution tests
('bench_exec_001', 'List Test Cases', 'Can agent list available test cases?', 'execution',
 'List all available test cases',
 '{"contains": ["testcases", "list"]}',
 'contains', 30, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager', 'qa-manager', 'executor']),

('bench_exec_002', 'Load Test Case', 'Can agent load test case details?', 'execution',
 'Load the details of test case TC_001',
 '{"contains": ["testcase", "TC_001"]}',
 'contains', 30, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager', 'executor']),

-- Analysis tests
('bench_ana_001', 'Coverage Summary', 'Can agent get coverage summary?', 'analysis',
 'Get the test coverage summary for requirements',
 '{"contains": ["coverage", "summary"]}',
 'contains', 30, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager', 'qa-manager']),

('bench_ana_002', 'List Requirements', 'Can agent list requirements?', 'analysis',
 'List all requirements in the system',
 '{"contains": ["requirements", "list"]}',
 'contains', 30, ARRAY['qa-manager']),

-- Recovery tests
('bench_rec_001', 'Handle Invalid Input', 'Can agent handle invalid input gracefully?', 'recovery',
 'Navigate to non-existent-node-xyz-12345',
 '{"contains": ["error", "not found"]}',
 'contains', 30, ARRAY['qa-web-manager', 'qa-mobile-manager', 'qa-stb-manager']),

('bench_rec_002', 'Timeout Recovery', 'Can agent handle timeouts?', 'recovery',
 'Execute a task that will timeout',
 '{"contains": ["timeout", "retry"]}',
 'contains', 120, ARRAY['qa-manager', 'executor']);

-- =====================================================
-- 7. View for Leaderboard
-- =====================================================

CREATE OR REPLACE VIEW agent_leaderboard AS
SELECT 
    agent_id,
    agent_version,
    overall_score,
    benchmark_score,
    user_rating_score,
    success_rate_score,
    avg_user_rating,
    total_executions,
    benchmark_run_count,
    score_trend,
    score_change,
    rank_overall,
    team_id,
    calculated_at
FROM agent_scores
WHERE overall_score > 0
ORDER BY overall_score DESC;

-- =====================================================
-- 8. Function to Recalculate Agent Scores
-- =====================================================

CREATE OR REPLACE FUNCTION recalculate_agent_score(
    p_agent_id VARCHAR(100),
    p_agent_version VARCHAR(20),
    p_team_id UUID
) RETURNS VOID AS $$
DECLARE
    v_benchmark_score DECIMAL(5,2);
    v_user_rating_avg DECIMAL(3,2);
    v_user_rating_score DECIMAL(5,2);
    v_success_rate DECIMAL(5,2);
    v_total_executions INTEGER;
    v_successful_executions INTEGER;
    v_feedback_count INTEGER;
    v_overall_score DECIMAL(5,2);
BEGIN
    -- Get latest benchmark score
    SELECT score_percent INTO v_benchmark_score
    FROM agent_benchmark_runs
    WHERE agent_id = p_agent_id 
      AND agent_version = p_agent_version
      AND status = 'completed'
    ORDER BY completed_at DESC
    LIMIT 1;
    
    v_benchmark_score := COALESCE(v_benchmark_score, 0);
    
    -- Get average user rating
    SELECT AVG(rating), COUNT(*) 
    INTO v_user_rating_avg, v_feedback_count
    FROM agent_feedback
    WHERE agent_id = p_agent_id 
      AND agent_version = p_agent_version
      AND team_id = p_team_id;
    
    v_user_rating_avg := COALESCE(v_user_rating_avg, 0);
    v_feedback_count := COALESCE(v_feedback_count, 0);
    -- Convert 1-5 rating to 0-100 score
    v_user_rating_score := (v_user_rating_avg - 1) * 25;
    
    -- Get success rate from execution history
    SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'completed')
    INTO v_total_executions, v_successful_executions
    FROM agent_execution_history
    WHERE agent_id = p_agent_id 
      AND version = p_agent_version
      AND team_id = p_team_id;
    
    v_total_executions := COALESCE(v_total_executions, 0);
    v_successful_executions := COALESCE(v_successful_executions, 0);
    
    IF v_total_executions > 0 THEN
        v_success_rate := (v_successful_executions::DECIMAL / v_total_executions) * 100;
    ELSE
        v_success_rate := 0;
    END IF;
    
    -- Calculate overall score (weighted)
    -- 40% benchmark + 30% user rating + 20% success rate + 10% cost efficiency (TBD)
    v_overall_score := (v_benchmark_score * 0.4) + 
                       (v_user_rating_score * 0.3) + 
                       (v_success_rate * 0.2) +
                       (0 * 0.1);  -- Cost efficiency TBD
    
    -- Upsert score
    INSERT INTO agent_scores (
        agent_id, agent_version, team_id,
        benchmark_score, user_rating_score, success_rate_score,
        overall_score, avg_user_rating, total_feedback_count,
        total_executions, successful_executions,
        calculated_at
    ) VALUES (
        p_agent_id, p_agent_version, p_team_id,
        v_benchmark_score, v_user_rating_score, v_success_rate,
        v_overall_score, v_user_rating_avg, v_feedback_count,
        v_total_executions, v_successful_executions,
        NOW()
    )
    ON CONFLICT (agent_id, agent_version, team_id) 
    DO UPDATE SET
        benchmark_score = EXCLUDED.benchmark_score,
        user_rating_score = EXCLUDED.user_rating_score,
        success_rate_score = EXCLUDED.success_rate_score,
        overall_score = EXCLUDED.overall_score,
        avg_user_rating = EXCLUDED.avg_user_rating,
        total_feedback_count = EXCLUDED.total_feedback_count,
        total_executions = EXCLUDED.total_executions,
        successful_executions = EXCLUDED.successful_executions,
        calculated_at = NOW();
        
END;
$$ LANGUAGE plpgsql;

