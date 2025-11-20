-- =============================================================================
-- VirtualPyTest Database Schema Backup
-- Generated: 2024-01-XX
-- Description: Complete backup of current database schema including tables,
--              functions, triggers, and RLS policies
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLES
-- =============================================================================

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

-- Device models table
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

-- Device table
CREATE TABLE device (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    model text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    controller_configs jsonb
);

-- User interfaces table (UPDATED SCHEMA)
CREATE TABLE userinterfaces (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    models text[] DEFAULT '{}'::text[],  -- UPDATED: Array of compatible device models
    min_version character varying,       -- UPDATED: Minimum version support
    max_version character varying,       -- UPDATED: Maximum version support
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Navigation trees table (UPDATED SCHEMA)
CREATE TABLE navigation_trees (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name character varying NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    description text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    root_node_id uuid,  -- UPDATED: Changed from text to uuid
    
    -- Nested tree relationship columns
    parent_tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    parent_node_id text, -- References the node_id that spawned this subtree
    tree_depth integer DEFAULT 0, -- Depth level (0 = root, 1 = first level nested, etc.)
    is_root_tree boolean DEFAULT true, -- True only for top-level trees
    
    -- React Flow viewport position fields
    viewport_x double precision DEFAULT 0, -- React Flow viewport X position for restoring view state
    viewport_y double precision DEFAULT 0, -- React Flow viewport Y position for restoring view state  
    viewport_zoom double precision DEFAULT 1, -- React Flow viewport zoom level for restoring view state
    
    -- Constraints for nested trees
    CONSTRAINT check_tree_depth CHECK (tree_depth >= 0 AND tree_depth <= 5),
    CONSTRAINT check_parent_consistency 
    CHECK (
        (parent_tree_id IS NULL AND parent_node_id IS NULL AND is_root_tree = true) OR
        (parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL AND is_root_tree = false)
    )
);

-- Navigation trees history table (UPDATED SCHEMA)
CREATE TABLE navigation_trees_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    version_number integer NOT NULL,  -- UPDATED: More specific naming
    modification_type text NOT NULL CHECK (modification_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'restore'::text])),  -- UPDATED: Added enum constraint
    modified_by uuid,  -- UPDATED: Renamed from changed_by_user_id
    tree_data jsonb NOT NULL,  -- UPDATED: Made NOT NULL
    changes_summary text,  -- UPDATED: Renamed from change_description
    created_at timestamp with time zone DEFAULT now(),
    restored_from_version integer  -- UPDATED: Added for restore tracking
);

-- Environment profiles table
CREATE TABLE environment_profiles (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name character varying NOT NULL,
    description text,
    config jsonb DEFAULT '{}'::jsonb,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Test cases table (UPDATED SCHEMA)
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

-- TestCase Definitions table (from TestCase Builder)
CREATE TABLE testcase_definitions (
    testcase_id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    testcase_name character varying(255) NOT NULL,
    description text,
    userinterface_name character varying(255),
    graph_json jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(255),
    is_active boolean DEFAULT true,
    creation_method character varying(10) DEFAULT 'visual'::character varying CHECK (creation_method IN ('visual', 'ai')),
    ai_prompt text,
    ai_analysis text,
    folder_id integer DEFAULT 0,  -- UPDATED: Added for unified test organization
    CONSTRAINT unique_testcase_per_team UNIQUE (team_id, testcase_name)
);

-- Folders table (Unified Test Organization)
CREATE TABLE folders (
    folder_id SERIAL PRIMARY KEY,
    name character varying(255) NOT NULL UNIQUE,
    created_at timestamp with time zone DEFAULT now()
);

-- Tags table (Unified Test Organization)
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name character varying(50) NOT NULL UNIQUE,
    color character varying(7) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- Executable Tags Mapping (Unified for Scripts and Testcases)
CREATE TABLE executable_tags (
    executable_type character varying(10) NOT NULL CHECK (executable_type IN ('script', 'testcase')),
    executable_id character varying(255) NOT NULL,
    tag_id integer NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    PRIMARY KEY (executable_type, executable_id, tag_id)
);

-- Scripts Metadata table (For Unified Listing)
CREATE TABLE scripts (
    script_id SERIAL PRIMARY KEY,
    name character varying(255) NOT NULL UNIQUE,
    display_name character varying(255),
    description text,
    folder_id integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);

-- Test executions table
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

-- Test results table
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

-- Verifications references table
CREATE TABLE verifications_references (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    device_model text NOT NULL,  -- DEPRECATED: Kept for backward compatibility during migration, will be removed
    userinterface_id uuid REFERENCES userinterfaces(id) ON DELETE CASCADE,  -- NEW: References are now organized by userinterface
    reference_type text NOT NULL CHECK (reference_type = ANY (ARRAY['reference_image'::text, 'reference_text'::text])),
    area jsonb,
    r2_path text NOT NULL,  -- Path format: reference-images/{userinterface_name}/{filename} or text-references/{userinterface_name}/{filename}
    r2_url text NOT NULL,   -- URL format: https://.../reference-images/{userinterface_name}/{filename}
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Alerts table (UPDATED SCHEMA)
CREATE TABLE alerts (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    host_name text NOT NULL,
    device_id text NOT NULL,
    incident_type text NOT NULL CHECK (incident_type = ANY (ARRAY['blackscreen'::text, 'freeze'::text, 'errors'::text, 'audio_loss'::text, 'macroblocks'::text])),
    status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'resolved'::text])),
    consecutive_count integer NOT NULL DEFAULT 1 CHECK (consecutive_count > 0),
    start_time timestamp with time zone NOT NULL DEFAULT now(),
    end_time timestamp with time zone,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Additional fields
    checked boolean DEFAULT false,
    check_type character varying,
    discard boolean DEFAULT false,
    discard_type character varying,
    discard_comment text
);

-- Heatmaps table
CREATE TABLE heatmaps (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid REFERENCES teams(id) ON DELETE CASCADE,
    timestamp character varying NOT NULL,
    job_id uuid NOT NULL,
    mosaic_r2_path character varying,
    mosaic_r2_url character varying,
    metadata_r2_path character varying,
    metadata_r2_url character varying,
    html_r2_path character varying,
    html_r2_url character varying,
    hosts_included integer DEFAULT 0,
    hosts_total integer DEFAULT 0,
    incidents_count integer DEFAULT 0,
    generated_at timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);

-- Node metrics table (UPDATED SCHEMA)
CREATE TABLE node_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    node_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Simplified metrics structure
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    success_rate numeric DEFAULT 0,
    avg_execution_time_ms integer DEFAULT 0
);

-- Edge metrics table (UPDATED SCHEMA)
CREATE TABLE edge_metrics (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    edge_id character varying NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Simplified metrics structure + action_set_id
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    success_rate numeric DEFAULT 0,
    avg_execution_time_ms integer DEFAULT 0,
    action_set_id character varying  -- UPDATED: Added for bidirectional edge tracking
);

-- Execution results table (UPDATED SCHEMA)
CREATE TABLE execution_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE SET NULL,
    edge_id text,
    node_id text,
    execution_type text NOT NULL,
    host_name text NOT NULL,
    device_model text,
    device_name text,  -- UPDATED: Added for device-specific filtering
    success boolean NOT NULL,
    execution_time_ms integer,
    message text,
    error_details jsonb,
    executed_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    script_result_id uuid,
    script_context text DEFAULT 'direct'::text,
    action_set_id text,  -- UPDATED: Added for bidirectional edge tracking
    kpi_measurement_ms integer,  -- KPI: Measured time from action to visual confirmation
    kpi_measurement_success boolean,  -- KPI: Whether measurement succeeded
    kpi_measurement_error text  -- KPI: Error message if measurement failed
);

-- Script results table (UPDATED SCHEMA)
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

-- Navigation nodes table (UPDATED SCHEMA)
CREATE TABLE navigation_nodes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    node_id text NOT NULL,
    label text NOT NULL,
    position_x double precision NOT NULL DEFAULT 0,
    position_y double precision NOT NULL DEFAULT 0,
    node_type text NOT NULL DEFAULT 'default'::text,
    style jsonb DEFAULT '{}'::jsonb,
    data jsonb DEFAULT '{}'::jsonb,
    verifications jsonb DEFAULT '[]'::jsonb,  -- Embedded verification objects
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Nested tree metadata
    has_subtree boolean DEFAULT false,
    subtree_count integer DEFAULT 0,
    UNIQUE(tree_id, node_id)
);

-- Navigation edges table (UPDATED SCHEMA - NO LEGACY SUPPORT)
CREATE TABLE navigation_edges (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tree_id uuid NOT NULL REFERENCES navigation_trees(id) ON DELETE CASCADE,
    edge_id text NOT NULL,
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    label text,
    data jsonb DEFAULT '{}'::jsonb,
    final_wait_time integer DEFAULT 0,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- UPDATED: Action sets structure (NO LEGACY SUPPORT)
    action_sets jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(action_sets) = 'array'::text),
    default_action_set_id text NOT NULL,
    UNIQUE(tree_id, edge_id)
);

-- Campaign executions table (UPDATED SCHEMA)
CREATE TABLE campaign_executions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    campaign_name character varying NOT NULL,
    campaign_description text,
    campaign_execution_id character varying NOT NULL UNIQUE,  -- UPDATED: Added UNIQUE constraint
    userinterface_name character varying,
    host_name character varying NOT NULL,
    device_name character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[])),  -- UPDATED: Added enum constraint
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

-- AI analysis cache table (NEW TABLE)
CREATE TABLE ai_analysis_cache (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    prompt text NOT NULL,
    analysis_result jsonb NOT NULL,
    compatibility_matrix jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone DEFAULT (now() + '01:00:00'::interval)
);

-- Zap results table (NEW TABLE)
CREATE TABLE zap_results (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    script_result_id uuid REFERENCES script_results(id) ON DELETE CASCADE, -- NULL for automatic zapping detection during monitoring
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
    detection_method text, -- 'automatic' or 'manual' for zapping detection
    channel_name text,
    channel_number text,
    program_name text,
    program_start_time text,
    program_end_time text,
    audio_silence_duration numeric, -- Duration of audio silence during zapping (seconds)
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    userinterface_name text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Core table indexes
CREATE INDEX idx_device_models_team_id ON device_models(team_id);
CREATE INDEX idx_device_team_id ON device(team_id);
CREATE INDEX idx_environment_profiles_team_id ON environment_profiles(team_id);
CREATE INDEX idx_testcase_team ON testcase_definitions(team_id);
CREATE INDEX idx_testcase_name ON testcase_definitions(testcase_name);
CREATE INDEX idx_testcase_active ON testcase_definitions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_testcase_ui ON testcase_definitions(userinterface_name);
CREATE INDEX idx_campaign_executions_team_id ON campaign_executions(team_id);
CREATE INDEX idx_campaign_executions_campaign_name ON campaign_executions(campaign_name);
CREATE INDEX idx_campaign_executions_host_name ON campaign_executions(host_name);
CREATE INDEX idx_campaign_executions_status ON campaign_executions(status);

-- Navigation table indexes
CREATE INDEX idx_navigation_trees_userinterface ON navigation_trees(userinterface_id);
CREATE INDEX idx_navigation_trees_team ON navigation_trees(team_id);
CREATE INDEX idx_navigation_trees_name ON navigation_trees(name);
CREATE INDEX idx_navigation_trees_parent_tree ON navigation_trees(parent_tree_id);
CREATE INDEX idx_navigation_trees_parent_node ON navigation_trees(parent_node_id);
CREATE INDEX idx_navigation_trees_depth ON navigation_trees(tree_depth);
CREATE INDEX idx_navigation_trees_is_root ON navigation_trees(is_root_tree);
CREATE INDEX idx_navigation_trees_viewport ON navigation_trees(viewport_x, viewport_y, viewport_zoom);

CREATE INDEX idx_navigation_nodes_tree ON navigation_nodes(tree_id);
CREATE INDEX idx_navigation_nodes_node_id ON navigation_nodes(node_id);
CREATE INDEX idx_navigation_nodes_team ON navigation_nodes(team_id);
CREATE INDEX idx_navigation_nodes_position ON navigation_nodes(position_x, position_y);
CREATE INDEX idx_navigation_nodes_has_subtree ON navigation_nodes(has_subtree);

CREATE INDEX idx_navigation_edges_tree ON navigation_edges(tree_id);
CREATE INDEX idx_navigation_edges_edge_id ON navigation_edges(edge_id);
CREATE INDEX idx_navigation_edges_source ON navigation_edges(source_node_id);
CREATE INDEX idx_navigation_edges_target ON navigation_edges(target_node_id);
CREATE INDEX idx_navigation_edges_action_sets ON navigation_edges USING GIN (action_sets);
CREATE INDEX idx_navigation_edges_default_action_set ON navigation_edges(default_action_set_id);
CREATE INDEX idx_navigation_edges_team ON navigation_edges(team_id);

CREATE INDEX idx_navigation_trees_history_tree ON navigation_trees_history(tree_id);
CREATE INDEX idx_navigation_trees_history_team ON navigation_trees_history(team_id);

-- Test execution indexes
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
CREATE INDEX idx_execution_results_device_name ON execution_results(device_name);
CREATE INDEX idx_execution_results_kpi_query ON execution_results(team_id, device_name, executed_at) WHERE kpi_measurement_ms IS NOT NULL;
CREATE INDEX idx_execution_results_kpi_success ON execution_results(kpi_measurement_success) WHERE kpi_measurement_success IS NOT NULL;
CREATE INDEX idx_execution_results_kpi_ms ON execution_results(kpi_measurement_ms) WHERE kpi_measurement_ms IS NOT NULL;
CREATE INDEX idx_script_results_team_id ON script_results(team_id);
CREATE INDEX idx_script_results_script_name ON script_results(script_name);
CREATE INDEX idx_script_results_host_name ON script_results(host_name);
CREATE INDEX idx_script_results_discard ON script_results(discard);

-- Verification indexes
CREATE INDEX idx_verifications_references_team_id ON verifications_references(team_id);
CREATE INDEX idx_verifications_references_device_model ON verifications_references(device_model);  -- DEPRECATED: Will be removed after migration
CREATE INDEX idx_verifications_references_userinterface_id ON verifications_references(userinterface_id);  -- NEW
CREATE INDEX idx_verifications_references_reference_type ON verifications_references(reference_type);

-- Monitoring indexes
CREATE INDEX idx_alerts_incident_type ON alerts(incident_type);
CREATE INDEX idx_alerts_host_name ON alerts(host_name);
CREATE INDEX idx_alerts_start_time ON alerts(start_time);
CREATE INDEX idx_heatmaps_team_id ON heatmaps(team_id);
CREATE INDEX idx_heatmaps_generated_at ON heatmaps(generated_at);
CREATE INDEX idx_node_metrics_team_id ON node_metrics(team_id);
CREATE INDEX idx_node_metrics_node_id ON node_metrics(node_id);
CREATE INDEX idx_node_metrics_tree_id ON node_metrics(tree_id);
CREATE INDEX idx_edge_metrics_team_id ON edge_metrics(team_id);
CREATE INDEX idx_edge_metrics_edge_id ON edge_metrics(edge_id);
CREATE INDEX idx_edge_metrics_tree_id ON edge_metrics(tree_id);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp for testcase_definitions
CREATE OR REPLACE FUNCTION update_testcase_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to append script to campaign execution
CREATE OR REPLACE FUNCTION array_append_campaign_script(campaign_id uuid, script_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE campaign_executions 
    SET script_result_ids = array_append(script_result_ids, script_id),
        updated_at = timezone('utc'::text, now())
    WHERE id = campaign_id
    AND NOT (script_id = ANY(script_result_ids)); -- Only add if not already present
END;
$$;

-- Function to efficiently delete all alerts without returning data to client
CREATE OR REPLACE FUNCTION delete_all_alerts()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  deleted_count integer;
BEGIN
  -- Count before deletion
  SELECT COUNT(*) INTO deleted_count FROM alerts;
  
  -- Delete all records with WHERE clause (required by some DB configs)
  -- Using "WHERE true" matches all rows while satisfying the WHERE requirement
  DELETE FROM alerts WHERE true;
  
  -- Return result as JSON
  RETURN jsonb_build_object(
    'success', true,
    'deleted_count', deleted_count,
    'message', 'Successfully deleted ' || deleted_count || ' alerts'
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM,
      'deleted_count', 0
    );
END;
$$;

COMMENT ON FUNCTION delete_all_alerts() IS 'Efficiently deletes all alerts from the database without returning data to the client, preventing timeout issues with large datasets';

-- Function to auto-set edge label on insert
CREATE OR REPLACE FUNCTION auto_set_edge_label_on_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- Set the label for the new edge if it's not already set
    IF NEW.label IS NULL OR NEW.label = '' THEN
        SELECT source_node.label || '→' || target_node.label INTO NEW.label
        FROM navigation_nodes source_node, navigation_nodes target_node
        WHERE NEW.tree_id = source_node.tree_id 
          AND NEW.source_node_id = source_node.node_id
          AND NEW.tree_id = target_node.tree_id 
          AND NEW.target_node_id = target_node.node_id;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Function to auto-update edge labels when node changes
CREATE OR REPLACE FUNCTION auto_update_edge_labels_on_node_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- Update all edges where this node is the source
    UPDATE navigation_edges 
    SET label = NEW.label || '→' || target_node.label,
        updated_at = now()
    FROM navigation_nodes target_node
    WHERE navigation_edges.tree_id = NEW.tree_id 
      AND navigation_edges.source_node_id = NEW.node_id
      AND navigation_edges.tree_id = target_node.tree_id 
      AND navigation_edges.target_node_id = target_node.node_id;
    
    -- Update all edges where this node is the target
    UPDATE navigation_edges 
    SET label = source_node.label || '→' || NEW.label,
        updated_at = now()
    FROM navigation_nodes source_node
    WHERE navigation_edges.tree_id = NEW.tree_id 
      AND navigation_edges.target_node_id = NEW.node_id
      AND navigation_edges.tree_id = source_node.tree_id 
      AND navigation_edges.source_node_id = source_node.node_id;
    
    RETURN NEW;
END;
$$;

-- Function to cascade delete subtrees when parent node is deleted
CREATE OR REPLACE FUNCTION cascade_delete_subtrees()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- When a parent node is deleted, delete all its subtrees
    DELETE FROM navigation_trees 
    WHERE parent_node_id = OLD.node_id 
    AND team_id = OLD.team_id;
    
    -- Log cascade delete
    RAISE NOTICE 'Deleted subtrees for parent node %', OLD.node_id;
    
    RETURN OLD;
END;
$$;

-- Function to get descendant trees
CREATE OR REPLACE FUNCTION get_descendant_trees(root_tree_id uuid)
RETURNS TABLE(tree_id uuid, tree_name text, depth integer, parent_tree_id uuid, parent_node_id text)
LANGUAGE sql
AS $$
    WITH RECURSIVE tree_hierarchy AS (
        -- Base case: start with the root tree
        SELECT id, name, tree_depth, parent_tree_id, parent_node_id
        FROM navigation_trees 
        WHERE id = root_tree_id
        
        UNION ALL
        
        -- Recursive case: find children
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id
        FROM navigation_trees nt
        INNER JOIN tree_hierarchy th ON nt.parent_tree_id = th.id
    )
    SELECT 
        id AS tree_id, 
        name AS tree_name, 
        tree_depth AS depth, 
        parent_tree_id, 
        parent_node_id 
    FROM tree_hierarchy;
$$;

-- Function to get descendant trees filtered by userinterface
CREATE OR REPLACE FUNCTION get_descendant_trees_filtered(root_tree_id uuid)
RETURNS TABLE(id uuid, name character varying, tree_depth integer, parent_tree_id uuid, parent_node_id text)
LANGUAGE sql
AS $$
    WITH RECURSIVE tree_hierarchy AS (
        -- Base case: start with the root tree
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id, nt.userinterface_id
        FROM navigation_trees nt
        WHERE nt.id = root_tree_id
        
        UNION ALL
        
        -- Recursive case: find children, but only include trees that either:
        -- 1. Have the same userinterface_id as root, OR
        -- 2. Have userinterface_id = NULL (inherit from parent)
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id, nt.userinterface_id
        FROM navigation_trees nt
        INNER JOIN tree_hierarchy th ON nt.parent_tree_id = th.id
        WHERE (nt.userinterface_id = th.userinterface_id OR nt.userinterface_id IS NULL)
    )
    SELECT th.id, th.name, th.tree_depth, th.parent_tree_id, th.parent_node_id 
    FROM tree_hierarchy th;
$$;

-- Function to get tree path (breadcrumb)
CREATE OR REPLACE FUNCTION get_tree_path(target_tree_id uuid)
RETURNS TABLE(tree_id uuid, tree_name text, depth integer, node_id text)
LANGUAGE sql
AS $$
    WITH RECURSIVE tree_path AS (
        -- Base case: start with target tree
        SELECT id, name, tree_depth, parent_tree_id, parent_node_id
        FROM navigation_trees 
        WHERE id = target_tree_id
        
        UNION ALL
        
        -- Recursive case: go up to parents
        SELECT nt.id, nt.name, nt.tree_depth, nt.parent_tree_id, nt.parent_node_id
        FROM navigation_trees nt
        INNER JOIN tree_path tp ON nt.id = tp.parent_tree_id
    )
    SELECT id, name, tree_depth, parent_node_id 
    FROM tree_path 
    ORDER BY tree_depth ASC;
$$;

-- Function to sync parent node label, screenshot, and verifications to subtrees
CREATE OR REPLACE FUNCTION sync_parent_node_to_subtrees()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only sync if this node is referenced as a parent by subtrees
    IF EXISTS(
        SELECT 1 FROM navigation_trees 
        WHERE parent_node_id = NEW.node_id 
        AND team_id = NEW.team_id
    ) THEN
        -- Update label, screenshot, and verifications in all subtree duplicates
        UPDATE navigation_nodes 
        SET 
            label = NEW.label,
            data = jsonb_set(
                COALESCE(data, '{}'), 
                '{screenshot}', 
                to_jsonb(NEW.data->>'screenshot')
            ),
            verifications = NEW.verifications,
            updated_at = NOW()
        WHERE 
            node_id = NEW.node_id
            AND team_id = NEW.team_id
            AND tree_id IN (
                SELECT id FROM navigation_trees 
                WHERE parent_node_id = NEW.node_id 
                AND team_id = NEW.team_id
            );
            
        -- Log sync operation
        RAISE NOTICE 'Synced label/screenshot/verifications for parent node % to subtrees', NEW.node_id;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Function to update edge labels
CREATE OR REPLACE FUNCTION update_edge_labels()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Update all edges where label is NULL or empty
    UPDATE navigation_edges 
    SET label = source_node.label || '→' || target_node.label,
        updated_at = now()
    FROM navigation_nodes source_node, navigation_nodes target_node
    WHERE navigation_edges.tree_id = source_node.tree_id 
      AND navigation_edges.source_node_id = source_node.node_id
      AND navigation_edges.tree_id = target_node.tree_id 
      AND navigation_edges.target_node_id = target_node.node_id
      AND (navigation_edges.label IS NULL OR navigation_edges.label = '');
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RAISE NOTICE 'Updated % edge labels', updated_count;
    RETURN updated_count;
END;
$$;

-- Function to update metrics
CREATE OR REPLACE FUNCTION public.update_metrics()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    -- Update edge metrics (with fully qualified table name)
    IF NEW.edge_id IS NOT NULL THEN
        INSERT INTO public.edge_metrics (
            edge_id, 
            tree_id, 
            team_id, 
            action_set_id,
            total_executions,
            successful_executions,
            success_rate,
            avg_execution_time_ms,
            total_kpi_measurements,
            successful_kpi_measurements,
            avg_kpi_ms,
            min_kpi_ms,
            max_kpi_ms,
            kpi_success_rate
        )
        VALUES (
            NEW.edge_id,
            NEW.tree_id,
            NEW.team_id,
            NEW.action_set_id,
            1,
            CASE WHEN NEW.success THEN 1 ELSE 0 END,
            CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
            COALESCE(NEW.execution_time_ms, 0),
            CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END,
            CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END,
            COALESCE(NEW.kpi_measurement_ms, 0),
            NEW.kpi_measurement_ms,
            NEW.kpi_measurement_ms,
            CASE WHEN NEW.kpi_measurement_success THEN 1.0 ELSE 0.0 END
        )
        ON CONFLICT (edge_id, tree_id, action_set_id) 
        DO UPDATE SET
            total_executions = public.edge_metrics.total_executions + 1,
            successful_executions = public.edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (public.edge_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (public.edge_metrics.total_executions + 1),
            avg_execution_time_ms = ((public.edge_metrics.avg_execution_time_ms * public.edge_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (public.edge_metrics.total_executions + 1),
            total_kpi_measurements = public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END,
            successful_kpi_measurements = public.edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END,
            avg_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    ((public.edge_metrics.avg_kpi_ms * public.edge_metrics.total_kpi_measurements) + NEW.kpi_measurement_ms) / (public.edge_metrics.total_kpi_measurements + 1)
                ELSE public.edge_metrics.avg_kpi_ms
            END,
            min_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    LEAST(COALESCE(public.edge_metrics.min_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE public.edge_metrics.min_kpi_ms
            END,
            max_kpi_ms = CASE 
                WHEN NEW.kpi_measurement_ms IS NOT NULL THEN
                    GREATEST(COALESCE(public.edge_metrics.max_kpi_ms, NEW.kpi_measurement_ms), NEW.kpi_measurement_ms)
                ELSE public.edge_metrics.max_kpi_ms
            END,
            kpi_success_rate = CASE
                WHEN public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END > 0 THEN
                    (public.edge_metrics.successful_kpi_measurements + CASE WHEN NEW.kpi_measurement_success THEN 1 ELSE 0 END)::numeric / 
                    (public.edge_metrics.total_kpi_measurements + CASE WHEN NEW.kpi_measurement_ms IS NOT NULL THEN 1 ELSE 0 END)
                ELSE 0
            END;
    END IF;

    -- Update node metrics (with fully qualified table name)
    IF NEW.node_id IS NOT NULL THEN
        INSERT INTO public.node_metrics (
            node_id,
            tree_id,
            team_id,
            total_executions,
            successful_executions,
            success_rate,
            avg_execution_time_ms
        )
        VALUES (
            NEW.node_id,
            NEW.tree_id,
            NEW.team_id,
            1,
            CASE WHEN NEW.success THEN 1 ELSE 0 END,
            CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END,
            COALESCE(NEW.execution_time_ms, 0)
        )
        ON CONFLICT (node_id, tree_id, team_id) 
        DO UPDATE SET
            total_executions = public.node_metrics.total_executions + 1,
            successful_executions = public.node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END,
            success_rate = (public.node_metrics.successful_executions + CASE WHEN NEW.success THEN 1 ELSE 0 END)::numeric / (public.node_metrics.total_executions + 1),
            avg_execution_time_ms = ((public.node_metrics.avg_execution_time_ms * public.node_metrics.total_executions) + COALESCE(NEW.execution_time_ms, 0)) / (public.node_metrics.total_executions + 1);
    END IF;

    RETURN NEW;
END;
$$;

-- Function to update node subtree counts
CREATE OR REPLACE FUNCTION update_node_subtree_counts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update parent node's subtree information
        UPDATE navigation_nodes 
        SET 
            has_subtree = true,
            subtree_count = (
                SELECT COUNT(*) 
                FROM navigation_trees 
                WHERE parent_tree_id = NEW.parent_tree_id 
                AND parent_node_id = NEW.parent_node_id
            )
        WHERE tree_id = NEW.parent_tree_id 
        AND node_id = NEW.parent_node_id;
        
        RETURN NEW;
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        -- Update parent node's subtree information
        UPDATE navigation_nodes 
        SET 
            subtree_count = (
                SELECT COUNT(*) 
                FROM navigation_trees 
                WHERE parent_tree_id = OLD.parent_tree_id 
                AND parent_node_id = OLD.parent_node_id
            )
        WHERE tree_id = OLD.parent_tree_id 
        AND node_id = OLD.parent_node_id;
        
        -- If no more subtrees, set has_subtree to false
        UPDATE navigation_nodes 
        SET has_subtree = false
        WHERE tree_id = OLD.parent_tree_id 
        AND node_id = OLD.parent_node_id
        AND subtree_count = 0;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger to update metrics on execution results insert
CREATE TRIGGER metrics_trigger 
    AFTER INSERT ON execution_results 
    FOR EACH ROW 
    EXECUTE FUNCTION update_metrics();

-- Trigger to update updated_at timestamp for testcase_definitions
CREATE TRIGGER testcase_definitions_updated_at
    BEFORE UPDATE ON testcase_definitions
    FOR EACH ROW
    EXECUTE FUNCTION update_testcase_updated_at();

-- Trigger to auto-set edge label on insert
CREATE TRIGGER trigger_auto_set_edge_label_on_insert 
    BEFORE INSERT ON navigation_edges 
    FOR EACH ROW 
    EXECUTE FUNCTION auto_set_edge_label_on_insert();

-- Trigger to cascade delete subtrees when parent node is deleted
CREATE TRIGGER cascade_delete_subtrees_trigger 
    AFTER DELETE ON navigation_nodes 
    FOR EACH ROW 
    EXECUTE FUNCTION cascade_delete_subtrees();

-- Trigger to sync parent node label, screenshot, and verifications to subtrees
CREATE TRIGGER sync_parent_node_to_subtrees_trigger 
    AFTER UPDATE ON navigation_nodes 
    FOR EACH ROW 
    WHEN (
        OLD.label IS DISTINCT FROM NEW.label OR
        OLD.data->>'screenshot' IS DISTINCT FROM NEW.data->>'screenshot' OR
        OLD.verifications IS DISTINCT FROM NEW.verifications
    )
    EXECUTE FUNCTION sync_parent_node_to_subtrees();

-- Trigger to auto-update edge labels when node label changes
CREATE TRIGGER trigger_auto_update_edge_labels_on_node_change 
    AFTER UPDATE OF label ON navigation_nodes 
    FOR EACH ROW 
    WHEN (OLD.label IS DISTINCT FROM NEW.label) 
    EXECUTE FUNCTION auto_update_edge_labels_on_node_change();

-- Trigger to update subtree counts
CREATE TRIGGER trigger_update_subtree_counts 
    AFTER INSERT OR DELETE ON navigation_trees 
    FOR EACH ROW 
    EXECUTE FUNCTION update_node_subtree_counts();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE device ENABLE ROW LEVEL SECURITY;
ALTER TABLE userinterfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE navigation_trees_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE environment_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE verifications_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE heatmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE node_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE script_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE zap_results ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

-- Teams policies
CREATE POLICY "teams_access_policy" ON teams
FOR ALL TO public
USING (true);

-- Device models policies
CREATE POLICY "device_models_access_policy" ON device_models
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Device policies
CREATE POLICY "device_access_policy" ON device
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- User interfaces policies
CREATE POLICY "userinterfaces_open_access" ON userinterfaces
FOR ALL TO public
USING (true);

-- Navigation trees policies
CREATE POLICY "navigation_trees_access_policy" ON navigation_trees
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Navigation nodes policies
CREATE POLICY "navigation_nodes_access_policy" ON navigation_nodes
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Navigation edges policies
CREATE POLICY "navigation_edges_access_policy" ON navigation_edges
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Navigation trees history policies
CREATE POLICY "navigation_trees_history_access_policy" ON navigation_trees_history
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Environment profiles policies
CREATE POLICY "environment_profiles_access_policy" ON environment_profiles
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Test cases policies
CREATE POLICY "test_cases_access_policy" ON test_cases
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Test executions policies
CREATE POLICY "test_executions_access_policy" ON test_executions
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Test results policies
CREATE POLICY "test_results_access_policy" ON test_results
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Verifications references policies
CREATE POLICY "verifications_references_access_policy" ON verifications_references
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Alerts policies
CREATE POLICY "alerts_access_policy" ON alerts
FOR ALL TO public
USING (true);

-- Heatmaps policies
CREATE POLICY "heatmaps_access_policy" ON heatmaps
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Node metrics policies
CREATE POLICY "node_metrics_access_policy" ON node_metrics
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Edge metrics policies
CREATE POLICY "edge_metrics_access_policy" ON edge_metrics
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Execution results policies
CREATE POLICY "execution_results_access_policy" ON execution_results
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Script results policies
CREATE POLICY "script_results_access_policy" ON script_results
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Campaign executions policies
CREATE POLICY "campaign_executions_access_policy" ON campaign_executions
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- AI analysis cache policies
CREATE POLICY "ai_analysis_cache_access_policy" ON ai_analysis_cache
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- Zap results policies
CREATE POLICY "zap_results_access_policy" ON zap_results
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- TestCase Definitions policies
CREATE POLICY "service_role_all_testcase_definitions" ON testcase_definitions
FOR ALL TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "testcase_definitions_access_policy" ON testcase_definitions
FOR ALL TO public
USING ((auth.uid() IS NULL) OR (auth.role() = 'service_role'::text) OR true);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE teams IS 'Team management and organization';
COMMENT ON TABLE device_models IS 'Device model definitions and capabilities';
COMMENT ON TABLE device IS 'Physical device instances';
COMMENT ON TABLE userinterfaces IS 'User interface definitions with device compatibility';
COMMENT ON TABLE navigation_trees IS 'Navigation tree metadata containers - simplified structure with nodes/edges in separate tables';
COMMENT ON TABLE navigation_nodes IS 'Individual navigation nodes with embedded verifications';
COMMENT ON TABLE navigation_edges IS 'Navigation edges connecting nodes with embedded actions';
COMMENT ON TABLE navigation_trees_history IS 'Version history for navigation trees';
COMMENT ON TABLE environment_profiles IS 'Test environment configurations';
COMMENT ON TABLE test_cases IS 'Test case definitions and configurations';
COMMENT ON TABLE testcase_definitions IS 'Test case definitions from TestCase Builder (visual or AI-generated)';
COMMENT ON TABLE test_executions IS 'Test execution tracking records';
COMMENT ON TABLE test_results IS 'Test execution results and outcomes';
COMMENT ON TABLE verifications_references IS 'Reference data for verifications (screenshots, elements, etc.)';
COMMENT ON TABLE alerts IS 'Stores monitoring incidents from HDMI capture analysis';
COMMENT ON TABLE heatmaps IS 'Performance heatmap data and analytics';
COMMENT ON TABLE node_metrics IS 'Aggregated performance metrics for navigation nodes with embedded verifications';
COMMENT ON TABLE edge_metrics IS 'Aggregated performance metrics for navigation edges with embedded actions';
COMMENT ON TABLE execution_results IS 'Detailed execution results matching automai schema';
COMMENT ON TABLE script_results IS 'Script execution results matching automai schema';
COMMENT ON TABLE campaign_executions IS 'Campaign execution tracking with references to individual script results';
COMMENT ON TABLE ai_analysis_cache IS 'Caches AI analysis results for the two-step test case generation process.';
COMMENT ON TABLE zap_results IS 'Individual zap iteration results with detailed analysis data';
COMMENT ON COLUMN zap_results.script_result_id IS 'References script execution. NULL for automatic zapping detection during monitoring';
COMMENT ON COLUMN zap_results.detection_method IS 'Detection method: automatic (system action) or manual (user IR remote)';

-- Column comments
COMMENT ON COLUMN alerts.device_id IS 'device1, device2, device3';
COMMENT ON COLUMN alerts.incident_type IS 'Type of incident: blackscreen, freeze, errors, audio_loss, or macroblocks';
COMMENT ON COLUMN alerts.status IS 'Current status: active or resolved';
COMMENT ON COLUMN alerts.consecutive_count IS 'Number of consecutive detections that triggered this alert';
COMMENT ON COLUMN alerts.start_time IS 'When the incident was first detected';
COMMENT ON COLUMN alerts.end_time IS 'When the incident was resolved (NULL if still active)';
COMMENT ON COLUMN alerts.metadata IS 'Additional context about the incident (analysis results, file paths, etc.)';

COMMENT ON COLUMN device.controller_configs IS 'controller config';

COMMENT ON COLUMN navigation_nodes.verifications IS 'JSONB array of verification objects: [{"name": "check_element", "device_model": "android_mobile", "command": "element_exists", "params": {"element_id": "button"}}]';

COMMENT ON COLUMN navigation_edges.final_wait_time IS 'Wait time in milliseconds after all edge actions complete';

COMMENT ON COLUMN test_cases.device_id IS 'Reference to the device under test';
COMMENT ON COLUMN test_cases.environment_profile_id IS 'Reference to environment profile with controller setup';
COMMENT ON COLUMN test_cases.verification_conditions IS 'Array of verification conditions to check during execution';
COMMENT ON COLUMN test_cases.expected_results IS 'Expected outcomes and verification criteria';
COMMENT ON COLUMN test_cases.execution_config IS 'Test execution configuration and parameters';
COMMENT ON COLUMN test_cases.tags IS 'Tags for categorization and filtering';
COMMENT ON COLUMN test_cases.priority IS 'Test priority (1=lowest, 5=highest)';
COMMENT ON COLUMN test_cases.estimated_duration IS 'Estimated execution time in seconds';
COMMENT ON COLUMN test_cases.creator IS 'Creator type: ai or manual';
COMMENT ON COLUMN test_cases.original_prompt IS 'Original natural language prompt for AI-generated test cases';
COMMENT ON COLUMN test_cases.ai_analysis IS 'AI analysis results including feasibility, reasoning, capabilities';
COMMENT ON COLUMN test_cases.compatible_devices IS 'Array of compatible device models or ["all"]';
COMMENT ON COLUMN test_cases.compatible_userinterfaces IS 'Array of compatible userinterface names or ["all"]';
COMMENT ON COLUMN test_cases.device_adaptations IS 'Device-specific adaptations (e.g., mobile->live_fullscreen)';

COMMENT ON COLUMN testcase_definitions.graph_json IS 'React Flow graph: {nodes: [...], edges: [...]}';
COMMENT ON COLUMN testcase_definitions.testcase_name IS 'Used as script_name in script_results for unified tracking';
COMMENT ON COLUMN testcase_definitions.creation_method IS 'How test case was created: visual (drag-drop) or ai (prompt)';
COMMENT ON COLUMN testcase_definitions.ai_prompt IS 'Original natural language prompt if AI-generated';
COMMENT ON COLUMN testcase_definitions.ai_analysis IS 'AI reasoning and analysis if AI-generated';


COMMENT ON COLUMN execution_results.action_set_id IS 'ID of the specific action set executed for bidirectional edges (e.g., "home_to_live" or "live_to_home")';
COMMENT ON COLUMN execution_results.device_name IS 'Device name (unique identifier) for filtering results by specific device instance';
COMMENT ON COLUMN execution_results.kpi_measurement_ms IS 'KPI: Measured time from action to visual confirmation';
COMMENT ON COLUMN execution_results.kpi_measurement_success IS 'KPI: Whether measurement succeeded';
COMMENT ON COLUMN execution_results.kpi_measurement_error IS 'KPI: Error message if measurement failed';

COMMENT ON COLUMN script_results.logs_r2_path IS 'R2 storage path for script execution logs';
COMMENT ON COLUMN script_results.logs_r2_url IS 'Public R2 URL for script execution logs';

COMMENT ON COLUMN ai_analysis_cache.analysis_result IS 'Full AI analysis result, including understanding, complexity, etc.';
COMMENT ON COLUMN ai_analysis_cache.compatibility_matrix IS 'Detailed compatibility breakdown for various user interfaces.';

COMMENT ON COLUMN zap_results.userinterface_name IS 'User interface name for filtering and analysis';
COMMENT ON COLUMN zap_results.started_at IS 'Zap iteration start timestamp (matches script_results format)';
COMMENT ON COLUMN zap_results.completed_at IS 'Zap iteration completion timestamp (matches script_results format)';

-- =============================================================================
-- END OF BACKUP
-- =============================================================================

SELECT 'Database schema backup completed successfully' as status;
