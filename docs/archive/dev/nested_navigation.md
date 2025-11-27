# Nested Navigation Architecture

## Overview
VirtualPyTest's navigation uses a hierarchical tree structure with embedded actions and verifications. Trees can nest up to 5 levels deep using explicit parent-child relationships, without node duplication. Pathfinding uses a unified graph with virtual cross-tree edges for seamless navigation.

## Database Schema

### navigation_trees
Stores tree metadata with nesting support:
```sql
CREATE TABLE navigation_trees (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id),
    team_id uuid REFERENCES teams(id),
    description text,
    root_node_id text,
    parent_tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    parent_node_id text,  -- References parent tree's node_id
    tree_depth integer DEFAULT 0 CHECK (tree_depth >= 0 AND tree_depth <= 5),
    is_root_tree boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT check_parent_consistency CHECK (
        (parent_tree_id IS NULL AND parent_node_id IS NULL AND is_root_tree) OR
        (parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL AND NOT is_root_tree)
    )
);
```

### navigation_nodes
Individual nodes with embedded verifications and subtree metadata:
```sql
CREATE TABLE navigation_nodes (
    id uuid PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    node_id text NOT NULL,
    label text NOT NULL,
    position_x float DEFAULT 0,
    position_y float DEFAULT 0,
    node_type text NOT NULL,
    style jsonb DEFAULT '{}',
    data jsonb DEFAULT '{}',
    verifications jsonb DEFAULT '[]',  -- Embedded verifications
    team_id uuid REFERENCES teams(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    has_subtree boolean DEFAULT false,
    subtree_count integer DEFAULT 0,
    UNIQUE(tree_id, node_id)
);
```

### navigation_edges
Edges with embedded actions, supporting nesting:
```sql
CREATE TABLE navigation_edges (
    id uuid PRIMARY KEY,
    tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE,
    edge_id text NOT NULL,
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    label text,
    data jsonb DEFAULT '{}',
    final_wait_time integer DEFAULT 2000,
    team_id uuid REFERENCES teams(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    action_sets jsonb DEFAULT '[]' CHECK (jsonb_typeof(action_sets) = 'array'),  -- Embedded action sets
    default_action_set_id text,
    UNIQUE(tree_id, edge_id)
);
```

## Nested Tree Operations
- **Creating Subtrees**: Insert with `parent_tree_id`, `parent_node_id`, incremented `tree_depth`.
- **Hierarchy Queries**:
  - `get_descendant_trees(root_tree_id)`: All descendant trees.
  - `get_tree_path(target_tree_id)`: Breadcrumb from root.
- **Automatic Updates**: Triggers maintain `has_subtree` and `subtree_count` on parent nodes.

## Pathfinding System

### How It Works
The pathfinding system creates a **unified graph** from all trees in a hierarchy, enabling seamless navigation across tree boundaries:

1. **Unified Graph Creation** (`create_unified_networkx_graph`):
   - Loads all trees: root tree + all descendant subtrees
   - Merges nodes and edges from all trees into single NetworkX graph
   - Creates **virtual cross-tree edges** automatically

2. **Virtual Cross-Tree Edge Logic**:
   - For each subtree with `parent_tree_id` and `parent_node_id`:
   - Creates `ENTER_SUBTREE` edge: `parent_node_id` → first node in subtree
   - Enables pathfinding from parent tree into subtree seamlessly
   - No manual tree switching required

3. **Parent Node Requirements**:
   - **Critical**: Parent node MUST exist in subtree with same `node_id`
   - **Handle Pattern**: Edges from parent node must use **bottom handles** (`bottom-right-menu-source`)
   - This creates the visual connection point for subtree navigation

4. **Path Structure**: 
   - Includes `transition_type` ('NORMAL', 'ENTER_SUBTREE', 'EXIT_SUBTREE')
   - Tracks tree context changes during navigation
   - Handles cross-tree transitions automatically

## Frontend Integration
- **Navigation Stack**: Tracks tree levels with parent context.
- **Reference-Based Display**: Parent nodes shown in subtrees with context metadata (e.g., `isParentReference: true`, `originalTreeId`).
- **Smart Saving**: Routes edits to node's original tree.
- **Breadcrumb**: Displays hierarchy path.
- **Cache**: Stores trees by ID for instant switching.

## Benefits
- **No Duplication**: Single source of truth for nodes.
- **Scalable**: Up to 5 nesting levels.
- **Efficient**: Indexed queries, cached hierarchies.
- **Seamless**: Cross-tree navigation without manual switching.

## Troubleshooting: Common Nested Navigation Issues

### Issue: "No path found" Error in Subtree Navigation

**Symptoms:**
- Error: `"No path found from 'ENTRY (uuid)' to 'target_node (uuid)' in unified graph"`
- Some subtree nodes unreachable while others work fine
- Inconsistent behavior between similar subtrees

**Root Causes & Solutions:**

#### 1. **Missing Parent Node in Subtree**
**Problem**: Subtree has artificial "entry" node instead of actual parent node.

**Diagnosis**:
```sql
-- Check for artificial entry nodes
SELECT node_id, label FROM navigation_nodes 
WHERE tree_id = 'subtree_id' AND label LIKE '%entry%';
```

**Fix**: Replace artificial node with actual parent node:
```sql
UPDATE navigation_nodes 
SET node_id = 'actual_parent_node_id', label = 'parent_label'
WHERE tree_id = 'subtree_id' AND node_id = 'artificial_entry_node_id';

UPDATE navigation_edges 
SET source_node_id = 'actual_parent_node_id'
WHERE tree_id = 'subtree_id' AND source_node_id = 'artificial_entry_node_id';
```

#### 2. **Incorrect Handle Connections**
**Problem**: Parent node edges use wrong handle pattern (top instead of bottom).

**Diagnosis**:
```sql
-- Check handle patterns in subtree vs working reference
SELECT source_node_id, target_node_id, 
       data->>'sourceHandle' as source_handle
FROM navigation_edges 
WHERE tree_id = 'subtree_id' AND source_node_id = 'parent_node_id';
```

**Expected Pattern**: All edges from parent node should use:
- `sourceHandle: "bottom-right-menu-source"` (bottom handle)
- `targetHandle: "top-right-menu-target"` (top handle)

**Fix**: Update incorrect handle patterns:
```sql
UPDATE navigation_edges 
SET data = jsonb_set(
    jsonb_set(data, '{sourceHandle}', '"bottom-right-menu-source"'),
    '{targetHandle}', '"top-right-menu-target"'
)
WHERE tree_id = 'subtree_id' AND source_node_id = 'parent_node_id';
```

#### 3. **Cache Invalidation Required**
After fixing data issues, always clear the navigation cache:
```bash
curl -X POST http://localhost:8082/server/pathfinding/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"tree_id": "root_tree_id"}'
```

## Synchronization Requirements

### Fields That Need Syncing
With parent node duplication, these fields should stay synchronized between parent tree and subtree:

**Critical Fields:**
- `label` - Node display name
- `data.screenshot` - Visual reference image  
- `data.description` - Node description
- `verifications` - Node validation rules

**Example Current State** (shows sync issue):
```sql
-- Parent node (rich data)
SELECT label, data->>'screenshot', data->>'description' 
FROM navigation_nodes 
WHERE tree_id = 'parent_tree_id' AND node_id = 'parent_node_id';
-- Result: "live", "screenshot.jpg", "Live TV playback screen"

-- Subtree duplicate (minimal data)  
SELECT label, data->>'screenshot', data->>'description'
FROM navigation_nodes
WHERE tree_id = 'subtree_id' AND node_id = 'parent_node_id'; 
-- Result: "live", null, null
```

### ✅ Implemented: Automatic Database Sync
✅ **Database triggers now handle sync automatically**:
- **Label changes**: When parent node label is updated → automatically syncs to all subtrees
- **Screenshot changes**: When parent node screenshot is updated → automatically syncs to all subtrees  
- **Cascade delete**: When parent node is deleted → automatically deletes all subtrees

**Implementation**: PostgreSQL triggers in `002_ui_navigation_tables.sql` and migration `006_parent_node_sync_triggers.sql`

### Recommended Sync Implementation
Add sync logic to `save_node()` function:

```python
def save_node_with_sync(tree_id: str, node_data: Dict, team_id: str) -> Dict:
    # Save to current tree
    result = save_node(tree_id, node_data, team_id)
    
    # If this is a parent node, sync to all subtrees
    if result['success']:
        sync_parent_node_to_subtrees(node_data['node_id'], node_data, team_id)
    
    return result

def sync_parent_node_to_subtrees(parent_node_id: str, updated_data: Dict, team_id: str):
    """Sync parent node changes to all subtrees that reference it"""
    # Find all subtrees that have this parent node
    subtrees = get_subtrees_with_parent_node(parent_node_id, team_id)
    
    # Update the duplicate node in each subtree
    sync_fields = ['label', 'data', 'verifications']  # Don't sync position
    sync_data = {k: v for k, v in updated_data.items() if k in sync_fields}
    
    for subtree_id in subtrees:
        save_node(subtree_id, {**sync_data, 'node_id': parent_node_id}, team_id)
```

### Prevention Tips
- ✅ Always duplicate parent node in subtrees (don't create artificial entries)
- ✅ Use consistent handle patterns: bottom → top connections  
- ✅ **Implement sync mechanism** before heavy parent node editing
- ✅ Test pathfinding after creating new subtrees
- ✅ Compare edge patterns with working subtrees when debugging

For implementation details, see code in `shared/lib/supabase/navigation_trees_db.py` and `backend_host/src/services/navigation/`.
