# Navigation Architecture Documentation

## Overview

VirtualPyTest uses a modernized navigation architecture with embedded actions and verifications directly stored within navigation edges and nodes. This eliminates the need for separate action and verification tables, simplifying data management while preserving all action parameters including `wait_time`.

## Database Schema

### Core Navigation Tables

#### `navigation_trees`
Stores tree metadata and configuration:
```sql
CREATE TABLE navigation_trees (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id),
    team_id uuid REFERENCES teams(id),
    description text,
    root_node_id uuid,  -- Optional reference to entry node
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);
```

#### `navigation_nodes` 
Stores individual nodes with embedded verifications:
```sql
CREATE TABLE navigation_nodes (
    id uuid PRIMARY KEY,
    node_id varchar NOT NULL,  -- ReactFlow node ID
    tree_id uuid REFERENCES navigation_trees(id),
    node_type varchar DEFAULT 'screen',
    label varchar NOT NULL,
    position_x integer DEFAULT 0,
    position_y integer DEFAULT 0,
    verifications jsonb DEFAULT '[]',  -- Embedded verifications array
    team_id uuid REFERENCES teams(id),
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);
```

#### `navigation_edges`
Stores transitions with embedded actions:
```sql
CREATE TABLE navigation_edges (
    id uuid PRIMARY KEY,
    edge_id varchar NOT NULL,  -- ReactFlow edge ID
    tree_id uuid REFERENCES navigation_trees(id),
    source_node_id varchar NOT NULL,
    target_node_id varchar NOT NULL,
    edge_type varchar DEFAULT 'navigation',
    label varchar,
    actions jsonb DEFAULT '[]',  -- Embedded actions array
    retry_actions jsonb DEFAULT '[]',  -- Embedded retry actions array
    final_wait_time integer DEFAULT 2000,  -- Wait time after all actions
    team_id uuid REFERENCES teams(id),
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);
```

### Enhanced Metrics Architecture

The new metrics system is specifically designed for the embedded architecture, providing comprehensive tracking of actions and verifications with their execution patterns.

#### `node_metrics` - Aggregated Node Performance
Tracks performance metrics for nodes with embedded verifications:
```sql
CREATE TABLE node_metrics (
    id uuid PRIMARY KEY,
    node_id varchar NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id),
    team_id uuid REFERENCES teams(id),
    
    -- Aggregated execution metrics
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    failed_executions integer DEFAULT 0,
    success_rate numeric(5,4) DEFAULT 0.0,
    avg_execution_time_ms integer DEFAULT 0,
    min_execution_time_ms integer DEFAULT 0,
    max_execution_time_ms integer DEFAULT 0,
    
    -- Verification-specific metrics
    verification_count integer DEFAULT 0,  -- Number of embedded verifications
    verification_types jsonb DEFAULT '[]',  -- Array of verification types
    
    -- Execution timestamps
    last_execution_at timestamp,
    last_success_at timestamp,
    last_failure_at timestamp,
    
    -- Device context
    device_model varchar,
    device_id varchar,
    
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now(),
    
    UNIQUE(node_id, tree_id, team_id)
);
```

**Key Benefits:**
- **Embedded Awareness**: Tracks how many verifications are embedded in each node
- **Type Analysis**: Records what types of verifications are used (image, text, adb, etc.)
- **Performance Tracking**: Comprehensive execution metrics including min/max/average times
- **Success Patterns**: Detailed success rate tracking for verification reliability

#### `edge_metrics` - Aggregated Edge Performance
Tracks performance metrics for edges with embedded actions:
```sql
CREATE TABLE edge_metrics (
    id uuid PRIMARY KEY,
    edge_id varchar NOT NULL,
    source_node_id varchar NOT NULL,
    target_node_id varchar NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id),
    team_id uuid REFERENCES teams(id),
    
    -- Aggregated execution metrics
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    failed_executions integer DEFAULT 0,
    success_rate numeric(5,4) DEFAULT 0.0,
    avg_execution_time_ms integer DEFAULT 0,
    min_execution_time_ms integer DEFAULT 0,
    max_execution_time_ms integer DEFAULT 0,
    
    -- Action-specific metrics
    action_count integer DEFAULT 0,  -- Number of embedded actions
    retry_action_count integer DEFAULT 0,  -- Number of embedded retry actions
    action_types jsonb DEFAULT '[]',  -- Array of action types
    final_wait_time integer DEFAULT 2000,  -- Final wait time setting
    
    -- Retry execution metrics
    retry_execution_count integer DEFAULT 0,
    retry_success_count integer DEFAULT 0,
    retry_success_rate numeric(5,4) DEFAULT 0.0,
    
    -- Execution timestamps
    last_execution_at timestamp,
    last_success_at timestamp,
    last_failure_at timestamp,
    
    -- Device context
    device_model varchar,
    device_id varchar,
    
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now(),
    
    UNIQUE(edge_id, tree_id, team_id)
);
```

**Key Benefits:**
- **Action Tracking**: Monitors embedded actions and retry actions separately
- **Type Analysis**: Records action types (tap_coordinates, click_element, etc.)
- **Retry Intelligence**: Separate metrics for retry action effectiveness
- **Timing Analysis**: Tracks `final_wait_time` and its impact on performance

#### `action_execution_history` - Detailed Action History
Records individual action executions for detailed analysis:
```sql
CREATE TABLE action_execution_history (
    id uuid PRIMARY KEY,
    edge_id varchar NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id),
    team_id uuid REFERENCES teams(id),
    
    -- Action details
    action_command varchar NOT NULL,  -- e.g., 'tap_coordinates', 'click_element'
    action_params jsonb DEFAULT '{}',  -- Full action parameters including wait_time
    action_index integer NOT NULL,  -- Position in actions array
    is_retry_action boolean DEFAULT false,
    
    -- Execution results
    success boolean NOT NULL,
    execution_time_ms integer NOT NULL,
    error_message text,
    error_details jsonb,
    
    -- Context
    device_model varchar,
    device_id varchar,
    host_name varchar,
    execution_id varchar,  -- Links to execution_results
    
    executed_at timestamp DEFAULT now()
);
```

**Key Benefits:**
- **Parameter Preservation**: Full `action_params` including `wait_time` preserved
- **Index Tracking**: Knows exactly which action in the sequence was executed
- **Retry Distinction**: Clearly separates regular actions from retry actions
- **Granular Analysis**: Individual action performance for optimization

#### `verification_execution_history` - Detailed Verification History
Records individual verification executions for detailed analysis:
```sql
CREATE TABLE verification_execution_history (
    id uuid PRIMARY KEY,
    node_id varchar NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id),
    team_id uuid REFERENCES teams(id),
    
    -- Verification details
    verification_type varchar NOT NULL,  -- e.g., 'image', 'text', 'adb'
    verification_command varchar NOT NULL,  -- e.g., 'image_verification', 'text_search'
    verification_params jsonb DEFAULT '{}',  -- Full verification parameters
    verification_index integer NOT NULL,  -- Position in verifications array
    
    -- Execution results
    success boolean NOT NULL,
    execution_time_ms integer NOT NULL,
    confidence_score numeric(5,4),  -- For image/text verifications
    threshold_used numeric(5,4),  -- Threshold that was applied
    error_message text,
    error_details jsonb,
    
    -- Result artifacts
    source_image_url text,
    reference_image_url text,
    result_overlay_url text,
    extracted_text text,
    
    -- Context
    device_model varchar,
    device_id varchar,
    host_name varchar,
    execution_id varchar,  -- Links to execution_results
    
    executed_at timestamp DEFAULT now()
);
```

**Key Benefits:**
- **Verification Intelligence**: Tracks confidence scores and thresholds used
- **Result Artifacts**: Preserves image URLs and extracted text for analysis
- **Type-Specific Data**: Different fields for different verification types
- **Parameter Tracking**: Full verification parameters preserved

#### Auto-Updating Triggers
The system includes PostgreSQL triggers that automatically update aggregated metrics:

```sql
-- Auto-update node metrics when verification executions are recorded
CREATE TRIGGER trigger_update_node_metrics
    AFTER INSERT ON verification_execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_node_metrics_on_verification_execution();

-- Auto-update edge metrics when action executions are recorded  
CREATE TRIGGER trigger_update_edge_metrics
    AFTER INSERT ON action_execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_edge_metrics_on_action_execution();
```

**Benefits:**
- **Real-Time Updates**: Metrics update automatically with each execution
- **Consistency**: No risk of metrics getting out of sync
- **Performance**: Aggregated data is pre-calculated for fast queries

## Data Flow and Caching

### Loading Navigation Trees
1. **Metadata First**: Load tree metadata from `navigation_trees`
2. **Nodes**: Load all nodes with embedded verifications from `navigation_nodes`
3. **Edges**: Load all edges with embedded actions from `navigation_edges`
4. **Metrics Integration**: Optionally load metrics for performance visualization

### Caching Strategy
- **Tree-Level Caching**: Full trees cached in memory with embedded data
- **NetworkX Graph**: Cached graph representation for pathfinding
- **Metrics Caching**: Aggregated metrics cached with tree data for UI display

### Metrics Integration in Frontend
The frontend now receives embedded actions/verifications with their metrics:

```typescript
interface UINavigationEdgeData {
  actions: EdgeAction[];  // Embedded actions with preserved wait_time
  retryActions: EdgeAction[];
  final_wait_time: number;
  metrics?: {
    volume: number;           // total_executions
    success_rate: number;     // success_rate (0.0-1.0)
    avg_execution_time: number; // avg_execution_time_ms
  };
}

interface UINavigationNodeData {
  verifications: NodeVerification[];  // Embedded verifications
  metrics?: {
    volume: number;
    success_rate: number;
    avg_execution_time: number;
  };
}
```

## CRUD Operations

### Create Operations
- **New Trees**: Insert into `navigation_trees`
- **New Nodes**: Insert into `navigation_nodes` with embedded verifications
- **New Edges**: Insert into `navigation_edges` with embedded actions
- **Metrics Initialization**: Use `update_*_metrics_from_embedded_*` functions

### Read Operations
- **Full Trees**: Single query per table, client-side joining
- **Metrics**: Bulk query using `get_tree_metrics(node_ids, edge_ids)`
- **History**: Detailed execution history via `get_*_execution_history`

### Update Operations
- **Embedded Data**: Update JSONB arrays directly in node/edge records
- **Metrics**: Auto-updated via triggers or manual refresh functions
- **Preserve Parameters**: All action parameters including `wait_time` maintained

### Delete Operations
- **Cascade Deletion**: Tree deletion cascades to nodes/edges/metrics
- **Soft Deletion**: Option to mark as deleted while preserving metrics history

## Performance Benefits

### Reduced Query Complexity
- **Before**: Multiple joins across actions/verifications tables
- **After**: Single table queries with embedded data

### Improved Data Locality
- **Before**: Related data scattered across multiple tables
- **After**: Actions with edges, verifications with nodes

### Enhanced Metrics
- **Granular Tracking**: Individual action/verification performance
- **Aggregated Views**: Fast access to summary metrics
- **Historical Analysis**: Detailed execution history preserved

### Parameter Preservation
- **Complete Fidelity**: All action parameters including `wait_time` preserved
- **No Data Loss**: Embedded structure prevents parameter loss
- **Type Safety**: JSONB validation ensures data integrity

## Migration Benefits

### Simplified Architecture
- **Fewer Tables**: Eliminated separate actions/verifications tables
- **Cleaner Relationships**: Direct embedding reduces complexity
- **Better Performance**: Fewer joins, faster queries

### Enhanced Metrics
- **Embedded Awareness**: Metrics understand embedded structure
- **Automatic Updates**: Triggers maintain consistency
- **Rich Context**: Device, host, and execution context preserved

### Preserved Functionality
- **All Features**: Complete feature parity with previous architecture
- **Parameter Integrity**: `wait_time` and all other parameters preserved
- **Historical Data**: Execution history and metrics maintained 