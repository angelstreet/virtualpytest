# Navigation Architecture Documentation

## Overview

VirtualPyTest uses a modernized navigation architecture with embedded actions and verifications directly stored within navigation edges and nodes. This eliminates the need for separate action and verification tables, simplifying data management while preserving all action parameters including `wait_time`.

**NEW**: The architecture now supports nested navigation trees with explicit parent-child relationships, allowing for hierarchical navigation structures up to 5 levels deep. The implementation uses a **reference-based approach** with no data duplication - parent nodes maintain their original tree context while being displayed in nested trees for seamless cross-tree operations.

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

### Reference-Based Navigation Flow

The system uses a **reference-based approach** where parent nodes are displayed in nested trees without data duplication:

1. **Root Level**: User starts in root tree (depth 0)
2. **Node Double-Click**: Creates/loads subtree (depth 1)
3. **Parent Reference**: Parent node displayed in nested tree with context metadata
4. **Stack Management**: Frontend maintains navigation stack with parent tree tracking
5. **Context Tracking**: Each node knows its original tree and current viewing context
6. **Smart Save Routing**: Edits route to correct tree based on node context
7. **Breadcrumb Display**: Shows complete path through hierarchy
8. **Back Navigation**: Pop stack to return to parent levels with correct tree context

#### Reference-Based Context Flow

```
Root Tree (interface_123):
├─ Node A (node-456) ← Original location
├─ Node B (node-789)
└─ Node C (node-101)

User double-clicks Node A → Creates/loads Nested Tree:

Nested Tree (subtree_987):
├─ Node A (node-456) ← Reference with context:
│  ├─ isParentReference: true
│  ├─ originalTreeId: "interface_123"
│  ├─ currentTreeId: "subtree_987"
│  ├─ depth: 1
│  └─ parent: ["home", "main-menu"]
├─ New Node D (node-234) ← Native to nested tree
└─ New Node E (node-567) ← Native to nested tree

Edge Creation:
- Node A → Node D: Saved to subtree_987 with cross-tree reference
- Node D → Node E: Saved to subtree_987 as normal edge

Save Operations:
- Edit Node A: Saves to interface_123 (original tree)
- Edit Node D: Saves to subtree_987 (current tree)
- Create Node F: Saves to subtree_987 (current tree)
```

## Data Flow and Tree Cache Architecture

### Unified Tree Loading
The system uses a **clean, cache-first architecture** with zero redundancy:

1. **Single Loading Logic**: Both root and nested trees use identical loading mechanisms
2. **Immediate Caching**: All trees cached upon first load in NavigationContext
3. **Zero Database Reloading**: Navigation switches between cached trees instantly
4. **Context Preservation**: Full tree context maintained across navigation levels

### Tree Cache Implementation

#### NavigationContext Tree Cache
```typescript
// Tree cache stores multiple trees by treeId
const [treeCache, setTreeCache] = useState<Map<string, { 
  nodes: UINavigationNode[], 
  edges: UINavigationEdge[] 
}>>(new Map());

// Core cache management functions
const cacheTree = (treeId: string, treeData: TreeData) => void;
const getCachedTree = (treeId: string) => TreeData | null;
const switchToTree = (treeId: string) => void; // Instant display switch
```

#### Loading Flow
```typescript
// 1. Initial root tree load
loadTreeForUserInterface(userInterfaceId) {
  const treeData = await fetchFromDatabase();
  navigation.cacheTree(treeId, treeData);  // Cache it
  navigation.switchToTree(treeId);         // Display it
}

// 2. Nested tree load (identical process)
loadNestedTree(nestedTreeId) {
  const treeData = await fetchFromDatabase();
  navigation.cacheTree(nestedTreeId, treeData);  // Cache it
  navigation.switchToTree(nestedTreeId);         // Display it
}

// 3. Navigation back (zero database calls)
navigateBack() {
  const targetTreeId = getTargetTreeFromStack();
  navigation.switchToTree(targetTreeId);  // Instant switch from cache
}
```

### Clean Architecture Benefits

#### Zero Redundancy
- **Single Source Loading**: Both root and nested trees use same database APIs
- **No Conversion Duplication**: Unified data transformation pipeline  
- **Instant Navigation**: Cache switching eliminates database round-trips
- **Memory Efficient**: Trees loaded once, reused across navigation levels

#### Performance Optimization
- **Instant Switching**: Navigation between trees takes ~0ms (cache lookup)
- **Reduced Database Load**: Each tree loaded exactly once per session
- **Memory Coherence**: Single Map structure maintains all tree data
- **Zero Latency Back Navigation**: Stack-based tree switching

#### Code Simplification
- **Unified Loading Logic**: No separate root vs nested loading paths
- **Clean State Management**: React state handles all tree display
- **No Legacy Fallbacks**: Modern architecture with zero backward compatibility
- **Predictable Behavior**: Same loading pattern for all tree types

### Navigation Functions Implementation

#### Clean Navigation Back
```typescript
const handleNavigateBack = useCallback(() => {
  popLevel(); // Remove current level from stack
  
  // Determine target tree from navigation stack
  const newCurrentLevel = stack.length > 1 ? stack[stack.length - 2] : null;
  const targetTreeId = newCurrentLevel ? newCurrentLevel.treeId : actualUserInterfaceId;
  
  // Instant switch to cached tree (zero database calls)
  setActualTreeId(targetTreeId);
  navigation.switchToTree(targetTreeId);
  
  console.log(`Navigation completed - switched to cached tree: ${targetTreeId}`);
}, [popLevel, stack, actualUserInterfaceId, setActualTreeId, navigation]);
```

#### Clean Breadcrumb Navigation
```typescript
const handleNavigateToLevel = useCallback((levelIndex: number) => {
  jumpToLevel(levelIndex); // Adjust stack to target level
  
  // Determine target tree from navigation stack
  const targetLevel = stack[levelIndex];
  const targetTreeId = targetLevel ? targetLevel.treeId : actualUserInterfaceId;
  
  // Instant switch to cached tree (zero database calls)
  setActualTreeId(targetTreeId);
  navigation.switchToTree(targetTreeId);
  
  console.log(`Navigation to level ${levelIndex} completed - switched to cached tree: ${targetTreeId}`);
}, [jumpToLevel, stack, actualUserInterfaceId, setActualTreeId, navigation]);
```

#### Architecture Principles
- **No Database Reloading**: All navigation uses cached tree data
- **Stack-Based Logic**: Navigation state determines target tree
- **Instant Switching**: Cache lookups provide immediate tree display
- **Clean Error Handling**: No fallback code, clean failure modes
- **Zero Legacy Support**: Modern React patterns only

## Reference-Based Implementation

### Key Components

#### 1. NavigationStackContext
Manages the navigation hierarchy with parent tree tracking:

```typescript
interface TreeLevel {
  treeId: string; // Current nested tree ID
  treeName: string; // Display name
  parentNodeId: string; // Node that spawned this tree
  parentNodeLabel: string; // Node display label
  parentTreeId?: string; // NEW: Tree where parent node lives
  depth: number; // Nesting level
}
```

**Key Functions:**
- `pushLevel()`: Add new nested level with parent tree context
- `popLevel()`: Return to parent level, restore tree context
- `jumpToLevel()`: Navigate directly to specific level
- `jumpToRoot()`: Return to root tree

#### 2. useNestedNavigation Hook
Handles nested tree entry and context management:

**Responsibilities:**
- Create/load subtrees on node double-click
- Add context metadata to parent nodes
- Update `actualTreeId` for current operation context
- Maintain parent tree references for cross-tree operations

**Context Enhancement:**
```typescript
// Parent nodes get enhanced context in nested trees
const parentWithContext = {
  id: originalNodeId,
  data: {
    ...originalData,
    // Reference context
    isParentReference: true,
    originalTreeId: parentTreeId,
    currentTreeId: nestedTreeId,
    depth: nestedDepth,
    parent: originalParentChain,
  }
}
```

#### 3. Smart Save Routing
NavigationContext routes saves based on node context:

```typescript
// Determine save target
const isParentReference = node.data.isParentReference;
const targetTreeId = isParentReference 
  ? node.data.originalTreeId  // Save to original tree
  : navigationConfig.actualTreeId; // Save to current tree

await navigationConfig.saveNode(targetTreeId, normalizedNode);
```

#### 4. actualTreeId Management
Tracks current operational context:

- **Root Tree**: `actualTreeId = "interface_123"`
- **Enter Nested**: `actualTreeId = "subtree_987"`
- **Back Navigation**: `actualTreeId = "interface_123"` (restored)

### Cross-Tree Operations

#### Edge Creation
Edges between parent and child nodes are stored in the nested tree:

```typescript
// Edge from parent node (original tree) to child node (nested tree)
const crossTreeEdge = {
  id: "edge-456-234",
  source: "node-456", // Parent node ID (lives in original tree)
  target: "node-234", // Child node ID (lives in nested tree)
  // Saved to: subtree_987 (current actualTreeId)
}
```

#### Node Editing
Node edits route to the correct tree automatically:

- **Parent Node**: Edit dialog → Save → Routes to `originalTreeId`
- **Child Node**: Edit dialog → Save → Routes to `currentTreeId`
- **No Special Handling**: Same UI, same user experience

#### Navigation Preservation
Full context maintained for "Go To" operations:

```typescript
// Complete path preserved in navigation stack
const fullPath = [
  { treeId: "interface_123", label: "root" },
  { treeId: "subtree_987", label: "live_fullscreen", parentTreeId: "interface_123" }
];
```

### Frontend Integration
The frontend uses enhanced node data with reference-based context tracking:

```typescript
interface UINavigationNodeData {
  // ... existing properties ...
  
  // Nested tree properties (database-stored)
  has_subtree?: boolean;
  subtree_count?: number;
  
  // Reference-based context (runtime-computed)
  isParentReference?: boolean; // True if this node is a reference to a parent tree
  originalTreeId?: string; // Tree ID where this node actually lives
  currentTreeId?: string; // Tree ID where we're currently viewing it
  parentNodeId?: string; // Immediate parent node ID
  depth?: number; // Depth in nested structure (from navigation stack)
  parent?: string[]; // Full parent chain from original tree
}

interface NavigationStackLevel {
  treeId: string; // Current nested tree ID
  treeName: string; // Current nested tree name
  parentNodeId: string; // Parent node that spawned this tree
  parentNodeLabel: string; // Parent node display label
  parentTreeId?: string; // Tree where parent node actually lives
  depth: number; // Nesting depth level
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

### Reference-Based Advantages
- **No Data Duplication**: Parent nodes maintain single source of truth
- **Seamless Cross-Tree Operations**: Edit parent nodes from nested contexts
- **Efficient Memory Usage**: No redundant node storage across trees
- **Consistent State Management**: All changes propagate to original source

### Nested Tree Advantages
- **Explicit Relationships**: Clear database-enforced parent-child links
- **Depth Control**: Built-in constraints prevent infinite nesting
- **Efficient Queries**: Indexed parent relationships for fast lookups
- **Automatic Maintenance**: Triggers handle metadata consistency
- **Smart Context Routing**: Operations automatically target correct tree

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

### Reference-Based Architecture
- **Zero Data Duplication**: Parent nodes referenced, not copied
- **Seamless User Experience**: Edit any node from any context
- **Automatic Context Routing**: Saves target correct tree automatically
- **Preserved Relationships**: Full parent-child context maintained
- **Cross-Tree Operations**: Edges and navigation work across tree boundaries

### Enhanced Architecture
- **Scalable Nesting**: Support for complex hierarchical structures up to 5 levels
- **Data Integrity**: Database constraints ensure consistency
- **Performance Optimized**: Indexed queries and cached relationships
- **Smart Context Management**: Frontend automatically handles tree context
- **User Experience**: Intuitive nested navigation with complete breadcrumb trails

### Preserved Functionality
- **Complete Compatibility**: All existing features work unchanged
- **Unified Save Behavior**: Same manual save flow for all nodes
- **Parameter Integrity**: `wait_time` and all action parameters preserved
- **Metrics Integration**: Enhanced metrics with nested tree context
- **Historical Data**: Execution history includes hierarchy information

## Nested Tree Pathfinding Implementation

### Unified Graph Pathfinding Architecture

**NEW**: The navigation system supports seamless pathfinding across nested trees using a unified graph approach with reference-based parent nodes.

#### Key Concept: Reference-Based Cross-Tree Pathfinding

The system solves the cross-tree navigation challenge using a **unified graph** that connects parent nodes (in root trees) to child nodes (in subtrees) without duplicating data:

```
Root Tree:                    Subtree:
├─ live (node-123) ──────────→ live_chup (node-456)
├─ live_fullscreen (node-789) → live_fullscreen_chup (node-101)
└─ home (node-001)
```

#### Core Components

##### 1. Unified Graph Building (`navigation_graph.py`)
```python
def create_unified_networkx_graph(all_trees_data: List[Dict]) -> nx.DiGraph:
    """Create unified NetworkX graph with cross-tree edge restoration"""
```

**Key Process:**
1. **Load All Trees**: Combines nodes/edges from root tree + all subtrees
2. **Detect Orphaned Edges**: Finds subtree edges that reference missing parent nodes
3. **Restore Cross-Tree Connections**: Creates edges from parent nodes (root tree) to child nodes (subtrees)
4. **Preserve Actions**: Maintains all action sets and navigation logic from original edges

##### 2. Cross-Tree Edge Types
- **CROSS_TREE**: Direct navigation from parent node to child node with preserved actions
- **ENTER_SUBTREE**: Virtual navigation entry points (optional)  
- **EXIT_SUBTREE**: Virtual navigation exit points (optional)

##### 3. Reference-Based Architecture Benefits
- **No Data Duplication**: Parent nodes exist only in root trees
- **Action Preservation**: All `live_fullscreen_chup` actions accessible from `live_fullscreen` node
- **Seamless Navigation**: Scripts can execute actions across tree boundaries transparently
- **Database Integrity**: Clean separation between root and subtree data

#### Usage Example

When a script executes `live_fullscreen_chup` from the `live_fullscreen` node:

1. **Unified Graph Loads**: All trees combined with cross-tree edges restored
2. **Action Lookup**: Finds `live_fullscreen_chup` action on edge from `live_fullscreen` → child nodes
3. **Cross-Tree Execution**: Executes action seamlessly across tree boundary
4. **No Manual Navigation**: Script doesn't need to know about tree boundaries

This enables the reference-based architecture to work transparently for both frontend display and backend script execution.

## Implementation Summary

The clean tree cache architecture with reference-based nesting and unified pathfinding provides:

### Core Architecture Benefits
1. **Zero Redundancy**: Single loading mechanism for all tree types
2. **Instant Navigation**: Cache-first approach eliminates database round-trips  
3. **Clean Code**: No legacy fallbacks, no backward compatibility, modern React patterns only
4. **Unified Loading**: Same API and conversion logic for root and nested trees
5. **Memory Efficiency**: Each tree loaded once, cached in NavigationContext Map
6. **Cross-Tree Pathfinding**: Seamless navigation across any nested tree level
7. **Unified Graph Performance**: NetworkX algorithms work across entire tree hierarchy
8. **Smart Tree Context**: Automatic tree context switching during cross-tree navigation

### Reference-Based Features
1. **No Data Duplication**: Parent nodes referenced, not copied across trees
2. **Smart Save Routing**: Edits automatically route to correct tree based on node context
3. **Transparent Operations**: Users edit any node from any context seamlessly
4. **Full Context Preservation**: Complete navigation paths maintained for "Go To" operations
5. **Cross-Tree Edges**: Connections work across tree boundaries automatically

### Performance Characteristics
- **Tree Loading**: Database call only on first access
- **Navigation**: ~0ms switching via cache lookups
- **Memory Usage**: Linear growth with unique trees accessed
- **Database Load**: Minimal - each tree fetched exactly once per session
- **User Experience**: Instant response times for all navigation operations

This architecture maintains the performance and simplicity of the embedded action/verification design while adding powerful hierarchical navigation capabilities that scale to complex nested structures without data redundancy, database overhead, or user complexity. The clean implementation ensures maintainability and predictable behavior across all navigation scenarios. 