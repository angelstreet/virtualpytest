# Navigation Architecture Documentation

## Overview

VirtualPyTest uses a modernized navigation architecture with embedded actions and verifications directly stored within navigation edges and nodes. This eliminates the need for separate action and verification tables, simplifying data management while preserving all action parameters including `wait_time`.

**NEW**: The architecture now supports nested navigation trees with explicit parent-child relationships, allowing for hierarchical navigation structures up to 5 levels deep.

## Database Schema

### Core Navigation Tables

#### `navigation_trees`
Stores tree metadata and configuration with nested tree support:
```sql
CREATE TABLE navigation_trees (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id),
    team_id uuid REFERENCES teams(id),
    description text,
    root_node_id uuid,  -- Optional reference to entry node
    
    -- Nested tree relationship columns
    parent_tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    parent_node_id text, -- References the node_id that spawned this subtree
    tree_depth integer DEFAULT 0, -- Depth level (0 = root, 1 = first level nested, etc.)
    is_root_tree boolean DEFAULT true, -- True only for top-level trees
    
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now(),
    
    -- Constraints for nested trees
    CONSTRAINT check_tree_depth CHECK (tree_depth >= 0 AND tree_depth <= 5),
    CONSTRAINT check_parent_consistency 
    CHECK (
        (parent_tree_id IS NULL AND parent_node_id IS NULL AND is_root_tree = true) OR
        (parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL AND is_root_tree = false)
    )
);
```

**Key Features:**
- **Explicit Parent-Child Relationships**: `parent_tree_id` and `parent_node_id` create clear nested relationships
- **Depth Control**: `tree_depth` tracks nesting level with maximum 5-level constraint
- **Root Tree Identification**: `is_root_tree` distinguishes top-level trees from nested subtrees
- **Data Integrity**: Constraints ensure consistent parent-child relationships

#### `navigation_nodes` 
Stores individual nodes with embedded verifications and nested tree metadata:
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
    
    -- Nested tree metadata
    has_subtree boolean DEFAULT false, -- True if this node has associated subtrees
    subtree_count integer DEFAULT 0, -- Number of subtrees linked to this node
    
    team_id uuid REFERENCES teams(id),
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);
```

**Key Features:**
- **Subtree Indicators**: `has_subtree` and `subtree_count` show which nodes spawn nested trees
- **Automatic Updates**: Triggers maintain accurate subtree counts
- **UI Integration**: Frontend can display visual indicators for nodes with subtrees

#### `navigation_edges`
Stores transitions with embedded actions (unchanged):
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

### Nested Tree Helper Functions

#### `get_descendant_trees(root_tree_id uuid)`
Returns all descendant trees in a hierarchy:
```sql
SELECT tree_id, tree_name, depth, parent_tree_id, parent_node_id 
FROM get_descendant_trees('root-tree-uuid');
```

**Use Cases:**
- Delete tree cascade operations
- Hierarchy visualization
- Bulk operations on tree families

#### `get_tree_path(target_tree_id uuid)`
Returns breadcrumb path from root to target tree:
```sql
SELECT tree_id, tree_name, depth, node_id 
FROM get_tree_path('nested-tree-uuid');
```

**Use Cases:**
- Breadcrumb navigation
- Context display
- Parent tree traversal

#### Automatic Subtree Count Management
Trigger function `update_node_subtree_counts()` automatically maintains:
- `has_subtree` boolean flag
- `subtree_count` accurate counts
- Triggered on tree INSERT/DELETE operations

### Enhanced Metrics Architecture

The metrics system works seamlessly with nested trees, tracking performance across the entire hierarchy.

#### `node_metrics` - Aggregated Node Performance
Now includes nested tree context:
```sql
CREATE TABLE node_metrics (
    id uuid PRIMARY KEY,
    node_id varchar NOT NULL,
    tree_id uuid REFERENCES navigation_trees(id),
    team_id uuid REFERENCES teams(id),
    
    -- Nested tree context
    tree_depth integer, -- Depth of the tree containing this node
    is_nested_tree boolean, -- Whether this node is in a nested tree
    parent_tree_path text[], -- Array of parent tree names for context
    
    -- Aggregated execution metrics
    total_executions integer DEFAULT 0,
    successful_executions integer DEFAULT 0,
    failed_executions integer DEFAULT 0,
    success_rate numeric(5,4) DEFAULT 0.0,
    avg_execution_time_ms integer DEFAULT 0,
    min_execution_time_ms integer DEFAULT 0,
    max_execution_time_ms integer DEFAULT 0,
    
    -- ... existing fields ...
);
```

## Nested Tree Operations

### Creating Nested Trees

1. **Identify Parent Node**: User double-clicks a node to create subtree
2. **Validate Depth**: Check current tree depth < 5
3. **Create Subtree**: Insert new tree with parent relationships
4. **Update Metadata**: Trigger automatically updates parent node counts

```sql
-- Example: Create subtree for node "settings-menu" in tree "main-ui"
INSERT INTO navigation_trees (
    name, userinterface_id, team_id,
    parent_tree_id, parent_node_id, 
    tree_depth, is_root_tree
) VALUES (
    'Settings Submenu', 'ui-123', 'team-123',
    'main-ui-tree-id', 'settings-menu', 
    1, false
);
```

### Querying Nested Structures

```sql
-- Get all subtrees for a specific node
SELECT * FROM navigation_trees 
WHERE parent_tree_id = 'main-tree-id' 
AND parent_node_id = 'settings-node';

-- Get complete hierarchy
SELECT * FROM get_descendant_trees('root-tree-id');

-- Get breadcrumb path
SELECT * FROM get_tree_path('deeply-nested-tree-id');
```

### Navigation Flow

1. **Root Level**: User starts in root tree (depth 0)
2. **Node Double-Click**: Creates/loads subtree (depth 1)
3. **Stack Management**: Frontend maintains navigation stack
4. **Breadcrumb Display**: Shows current path through hierarchy
5. **Back Navigation**: Pop stack to return to parent levels

## Data Flow and Caching

### Loading Nested Navigation Trees
1. **Metadata First**: Load tree metadata from `navigation_trees`
2. **Hierarchy Check**: Determine if tree has parent/children
3. **Nodes & Edges**: Load tree content with subtree indicators
4. **Breadcrumb Data**: Load path information for nested trees
5. **Stack Update**: Update navigation stack with current position

### Caching Strategy
- **Tree-Level Caching**: Full trees cached with nested metadata
- **Hierarchy Caching**: Parent-child relationships cached
- **Breadcrumb Caching**: Path information cached per tree
- **Stack Persistence**: Navigation stack maintained across sessions

### Frontend Integration
The frontend receives enhanced node data:

```typescript
interface UINavigationNodeData {
  // ... existing properties ...
  
  // Nested tree properties
  has_subtree?: boolean;
  subtree_count?: number;
  tree_depth?: number;
  is_nested_tree?: boolean;
  parent_tree_name?: string;
}

interface UINavigationTreeData {
  // ... existing properties ...
  
  // Nested tree properties
  parent_tree_id?: string;
  parent_node_id?: string;
  tree_depth: number;
  is_root_tree: boolean;
  breadcrumb?: BreadcrumbItem[];
}
```

## CRUD Operations

### Create Operations
- **New Root Trees**: Insert with `is_root_tree = true`, `tree_depth = 0`
- **New Subtrees**: Insert with parent relationships and incremented depth
- **Automatic Counts**: Triggers update parent node metadata

### Read Operations
- **Hierarchy Queries**: Use recursive functions for tree traversal
- **Filtered Reads**: Query by depth, parent relationships
- **Breadcrumb Data**: Use `get_tree_path()` for navigation context

### Update Operations
- **Tree Movement**: Update parent relationships (with depth validation)
- **Metadata Sync**: Triggers maintain count consistency
- **Cascade Updates**: Parent changes propagate to children

### Delete Operations
- **Cascade Deletion**: Tree deletion removes all descendants
- **Count Updates**: Triggers update parent node counts
- **Orphan Prevention**: Constraints prevent invalid relationships

## Performance Benefits

### Nested Tree Advantages
- **Explicit Relationships**: Clear database-enforced parent-child links
- **Depth Control**: Built-in constraints prevent infinite nesting
- **Efficient Queries**: Indexed parent relationships for fast lookups
- **Automatic Maintenance**: Triggers handle metadata consistency

### Query Optimization
- **Recursive Functions**: Efficient hierarchy traversal
- **Indexed Lookups**: Fast parent/child relationship queries
- **Cached Breadcrumbs**: Pre-computed navigation paths
- **Batch Operations**: Bulk hierarchy operations supported

### UI Performance
- **Visual Indicators**: Immediate feedback for nodes with subtrees
- **Lazy Loading**: Load subtrees only when accessed
- **Stack Management**: Efficient navigation state management
- **Breadcrumb Navigation**: Fast parent tree access

## Migration Benefits

### Enhanced Architecture
- **Scalable Nesting**: Support for complex hierarchical structures
- **Data Integrity**: Database constraints ensure consistency
- **Performance Optimized**: Indexed queries and cached relationships
- **User Experience**: Intuitive nested navigation with visual feedback

### Preserved Functionality
- **Complete Compatibility**: All existing features work unchanged
- **Parameter Integrity**: `wait_time` and all action parameters preserved
- **Metrics Integration**: Enhanced metrics with nested tree context
- **Historical Data**: Execution history includes hierarchy information

The nested tree architecture provides a powerful, scalable foundation for complex navigation structures while maintaining the performance and simplicity of the embedded action/verification approach. 