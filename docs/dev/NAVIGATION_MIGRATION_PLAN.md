# Navigation Architecture Migration Plan

## Overview
Complete migration from monolithic JSONB navigation trees to normalized tables with embedded actions/verifications.

**Target**: Clean, scalable architecture without backward compatibility
**Timeline**: 3 phases - Database → Backend → Frontend

---

## Phase 1: Database Migration

### 1.1 Create New Schema

```sql
-- Step 1: Create new navigation tables
CREATE TABLE navigation_trees_new (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    userinterface_id uuid REFERENCES userinterfaces(id),
    team_id uuid REFERENCES teams(id),
    description text,
    root_node_id text, -- Reference to node_id, not UUID
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);

CREATE TABLE navigation_nodes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id uuid REFERENCES navigation_trees_new(id) ON DELETE CASCADE,
    node_id text NOT NULL, -- Frontend identifier like "home-screen"
    label text NOT NULL,
    node_type text NOT NULL,
    description text,
    position_x integer,
    position_y integer,
    parent_node_ids text[] DEFAULT '{}',
    is_root boolean DEFAULT false,
    
    -- Embedded verifications
    verifications jsonb DEFAULT '[]',
    
    -- Additional node data
    screenshot text,
    depth integer DEFAULT 0,
    priority text DEFAULT 'p3',
    menu_type text,
    
    metadata jsonb DEFAULT '{}',
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now(),
    
    UNIQUE(tree_id, node_id)
);

CREATE TABLE navigation_edges (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id uuid REFERENCES navigation_trees_new(id) ON DELETE CASCADE,
    edge_id text NOT NULL, -- Frontend identifier
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    description text,
    
    -- Embedded actions
    actions jsonb DEFAULT '[]',
    retry_actions jsonb DEFAULT '[]',
    final_wait_time integer DEFAULT 2000,
    
    -- Edge properties
    edge_type text DEFAULT 'horizontal',
    priority text DEFAULT 'p3',
    threshold integer DEFAULT 0,
    
    metadata jsonb DEFAULT '{}',
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now(),
    
    UNIQUE(tree_id, edge_id),
    FOREIGN KEY (tree_id, source_node_id) REFERENCES navigation_nodes(tree_id, node_id),
    FOREIGN KEY (tree_id, target_node_id) REFERENCES navigation_nodes(tree_id, node_id)
);

-- Indexes for performance
CREATE INDEX idx_navigation_nodes_tree_id ON navigation_nodes(tree_id);
CREATE INDEX idx_navigation_nodes_node_id ON navigation_nodes(node_id);
CREATE INDEX idx_navigation_edges_tree_id ON navigation_edges(tree_id);
CREATE INDEX idx_navigation_edges_source ON navigation_edges(source_node_id);
CREATE INDEX idx_navigation_edges_target ON navigation_edges(target_node_id);
```

### 1.2 Data Migration Script

```python
# migration_script.py
import json
from datetime import datetime

def migrate_navigation_data():
    """Migrate from old JSONB structure to new normalized tables"""
    
    # Get all existing trees
    old_trees = supabase.table('navigation_trees').select('*').execute()
    
    for old_tree in old_trees.data:
        try:
            # Create new tree record
            new_tree_data = {
                'name': old_tree['name'],
                'userinterface_id': old_tree['userinterface_id'],
                'team_id': old_tree['team_id'],
                'description': old_tree.get('description'),
                'created_at': old_tree['created_at'],
                'updated_at': datetime.now().isoformat()
            }
            
            new_tree = supabase.table('navigation_trees_new').insert(new_tree_data).execute()
            new_tree_id = new_tree.data[0]['id']
            
            # Parse old metadata
            metadata = old_tree.get('metadata', {})
            nodes = metadata.get('nodes', [])
            edges = metadata.get('edges', [])
            
            # Migrate nodes
            root_node_id = None
            for node in nodes:
                node_data = {
                    'tree_id': new_tree_id,
                    'node_id': node['id'],
                    'label': node.get('data', {}).get('label', ''),
                    'node_type': node.get('data', {}).get('type', 'screen'),
                    'description': node.get('data', {}).get('description', ''),
                    'position_x': node.get('position', {}).get('x', 0),
                    'position_y': node.get('position', {}).get('y', 0),
                    'parent_node_ids': node.get('data', {}).get('parent', []),
                    'is_root': node.get('data', {}).get('is_root', False),
                    'verifications': node.get('data', {}).get('verifications', []),
                    'screenshot': node.get('data', {}).get('screenshot'),
                    'depth': node.get('data', {}).get('depth', 0),
                    'priority': node.get('data', {}).get('priority', 'p3'),
                    'menu_type': node.get('data', {}).get('menu_type'),
                }
                
                if node_data['is_root']:
                    root_node_id = node_data['node_id']
                
                supabase.table('navigation_nodes').insert(node_data).execute()
            
            # Update tree with root_node_id
            if root_node_id:
                supabase.table('navigation_trees_new').update({
                    'root_node_id': root_node_id
                }).eq('id', new_tree_id).execute()
            
            # Migrate edges
            for edge in edges:
                edge_data = {
                    'tree_id': new_tree_id,
                    'edge_id': edge['id'],
                    'source_node_id': edge['source'],
                    'target_node_id': edge['target'],
                    'description': edge.get('data', {}).get('description', ''),
                    'actions': edge.get('data', {}).get('actions', []),
                    'retry_actions': edge.get('data', {}).get('retryActions', []),
                    'final_wait_time': edge.get('data', {}).get('finalWaitTime', 2000),
                    'edge_type': edge.get('data', {}).get('edgeType', 'horizontal'),
                    'priority': edge.get('data', {}).get('priority', 'p3'),
                    'threshold': edge.get('data', {}).get('threshold', 0),
                }
                
                supabase.table('navigation_edges').insert(edge_data).execute()
            
            print(f"Migrated tree: {old_tree['name']} ({len(nodes)} nodes, {len(edges)} edges)")
            
        except Exception as e:
            print(f"Error migrating tree {old_tree['name']}: {e}")
            continue

def cleanup_old_tables():
    """Remove old tables after successful migration"""
    # Backup first!
    # DROP TABLE navigation_trees;
    # DROP TABLE actions;
    # DROP TABLE verifications;
    # DROP TABLE edge_actions;
    # DROP TABLE node_verifications;
    # RENAME TABLE navigation_trees_new TO navigation_trees;
    pass
```

---

## Phase 2: Backend Migration

### 2.1 Database Layer Changes

**Files to Modify:**

1. **`shared/lib/supabase/navigation_trees_db.py`** - Complete rewrite
2. **`shared/lib/supabase/actions_db.py`** - DELETE (no longer needed)
3. **`shared/lib/supabase/verifications_db.py`** - DELETE (no longer needed)

#### New Navigation Database Module

```python
# shared/lib/supabase/navigation_trees_db.py - COMPLETE REWRITE

def get_tree_metadata(tree_id: str, team_id: str) -> Dict:
    """Get tree basic information"""
    result = supabase.table('navigation_trees').select('*').eq('id', tree_id).eq('team_id', team_id).execute()
    
    if result.data:
        return {'success': True, 'tree': result.data[0]}
    else:
        return {'success': False, 'error': 'Tree not found'}

def get_tree_nodes(tree_id: str, team_id: str, page: int = 0, limit: int = 100) -> Dict:
    """Get nodes for a tree with pagination"""
    offset = page * limit
    
    result = supabase.table('navigation_nodes').select('*')\
        .eq('tree_id', tree_id)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    return {'success': True, 'nodes': result.data}

def get_tree_edges(tree_id: str, team_id: str, node_ids: List[str] = None) -> Dict:
    """Get edges for a tree, optionally filtered by node IDs"""
    query = supabase.table('navigation_edges').select('*').eq('tree_id', tree_id)
    
    if node_ids:
        # Get edges that connect to any of the specified nodes
        query = query.or_(f'source_node_id.in.({",".join(node_ids)}),target_node_id.in.({",".join(node_ids)})')
    
    result = query.execute()
    return {'success': True, 'edges': result.data}

def save_node(tree_id: str, node_data: Dict, team_id: str) -> Dict:
    """Save a single node"""
    node_data['tree_id'] = tree_id
    node_data['updated_at'] = datetime.now().isoformat()
    
    # Check if node exists
    existing = supabase.table('navigation_nodes').select('id')\
        .eq('tree_id', tree_id)\
        .eq('node_id', node_data['node_id']).execute()
    
    if existing.data:
        # Update existing
        result = supabase.table('navigation_nodes').update(node_data)\
            .eq('tree_id', tree_id)\
            .eq('node_id', node_data['node_id']).execute()
    else:
        # Insert new
        result = supabase.table('navigation_nodes').insert(node_data).execute()
    
    return {'success': True, 'node': result.data[0]}

def save_edge(tree_id: str, edge_data: Dict, team_id: str) -> Dict:
    """Save a single edge"""
    edge_data['tree_id'] = tree_id
    edge_data['updated_at'] = datetime.now().isoformat()
    
    # Check if edge exists
    existing = supabase.table('navigation_edges').select('id')\
        .eq('tree_id', tree_id)\
        .eq('edge_id', edge_data['edge_id']).execute()
    
    if existing.data:
        # Update existing
        result = supabase.table('navigation_edges').update(edge_data)\
            .eq('tree_id', tree_id)\
            .eq('edge_id', edge_data['edge_id']).execute()
    else:
        # Insert new
        result = supabase.table('navigation_edges').insert(edge_data).execute()
    
    return {'success': True, 'edge': result.data[0]}

def delete_node(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Delete a node and all connected edges"""
    # Delete connected edges first
    supabase.table('navigation_edges').delete()\
        .eq('tree_id', tree_id)\
        .or_(f'source_node_id.eq.{node_id},target_node_id.eq.{node_id}').execute()
    
    # Delete node
    result = supabase.table('navigation_nodes').delete()\
        .eq('tree_id', tree_id)\
        .eq('node_id', node_id).execute()
    
    return {'success': True}

def delete_edge(tree_id: str, edge_id: str, team_id: str) -> Dict:
    """Delete an edge"""
    result = supabase.table('navigation_edges').delete()\
        .eq('tree_id', tree_id)\
        .eq('edge_id', edge_id).execute()
    
    return {'success': True}
```

### 2.2 API Routes Changes

**Files to Modify:**

1. **`backend_server/src/routes/server_navigation_trees_routes.py`** - Major rewrite
2. **`backend_server/src/routes/server_actions_routes.py`** - DELETE most endpoints
3. **`backend_server/src/routes/server_verification_*_routes.py`** - DELETE verification endpoints

#### New Navigation API Routes

```python
# backend_server/src/routes/server_navigation_trees_routes.py - MAJOR REWRITE

@server_navigation_trees_bp.route('/trees/<tree_id>/metadata', methods=['GET'])
def get_tree_metadata(tree_id):
    """Get tree basic information"""
    team_id = get_team_id()
    result = get_tree_metadata(tree_id, team_id)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/nodes', methods=['GET'])
def get_tree_nodes_api(tree_id):
    """Get nodes with pagination"""
    team_id = get_team_id()
    page = int(request.args.get('page', 0))
    limit = int(request.args.get('limit', 100))
    
    result = get_tree_nodes(tree_id, team_id, page, limit)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/edges', methods=['GET'])
def get_tree_edges_api(tree_id):
    """Get edges, optionally filtered by nodes"""
    team_id = get_team_id()
    node_ids = request.args.getlist('node_ids')
    
    result = get_tree_edges(tree_id, team_id, node_ids if node_ids else None)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/nodes', methods=['POST'])
def save_node_api(tree_id):
    """Save a single node"""
    team_id = get_team_id()
    node_data = request.get_json()
    
    result = save_node(tree_id, node_data, team_id)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/edges', methods=['POST'])
def save_edge_api(tree_id):
    """Save a single edge"""
    team_id = get_team_id()
    edge_data = request.get_json()
    
    result = save_edge(tree_id, edge_data, team_id)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/nodes/<node_id>', methods=['DELETE'])
def delete_node_api(tree_id, node_id):
    """Delete a node"""
    team_id = get_team_id()
    result = delete_node(tree_id, node_id, team_id)
    return jsonify(result)

@server_navigation_trees_bp.route('/trees/<tree_id>/edges/<edge_id>', methods=['DELETE'])
def delete_edge_api(tree_id, edge_id):
    """Delete an edge"""
    team_id = get_team_id()
    result = delete_edge(tree_id, edge_id, team_id)
    return jsonify(result)
```

### 2.3 Navigation Cache Removal

**Files to Modify/Delete:**

1. **`shared/lib/utils/navigation_cache.py`** - DELETE (no longer needed)
2. **`shared/lib/utils/navigation_graph.py`** - Simplify to work with new structure
3. **`backend_core/src/services/navigation/navigation_pathfinding.py`** - Update to use new APIs

---

## Phase 3: Frontend Migration

### 3.1 Context Layer Changes

**Files to Modify:**

1. **`frontend/src/contexts/navigation/NavigationConfigContext.tsx`** - Major rewrite
2. **`frontend/src/contexts/navigation/NavigationContext.tsx`** - Update state management
3. **`frontend/src/contexts/device/DeviceDataContext.tsx`** - Remove action/verification loading

#### New Navigation Config Context

```typescript
// frontend/src/contexts/navigation/NavigationConfigContext.tsx - MAJOR REWRITE

interface NavigationConfigContextType {
  // Tree operations
  loadTreeMetadata: (treeId: string) => Promise<TreeMetadata>;
  loadTreeNodes: (treeId: string, page?: number, limit?: number) => Promise<NavigationNode[]>;
  loadTreeEdges: (treeId: string, nodeIds?: string[]) => Promise<NavigationEdge[]>;
  
  // Node operations
  saveNode: (treeId: string, node: NavigationNode) => Promise<void>;
  deleteNode: (treeId: string, nodeId: string) => Promise<void>;
  
  // Edge operations
  saveEdge: (treeId: string, edge: NavigationEdge) => Promise<void>;
  deleteEdge: (treeId: string, edgeId: string) => Promise<void>;
  
  // State
  currentTree: TreeMetadata | null;
  isLoading: boolean;
  error: string | null;
}

export const NavigationConfigProvider: React.FC = ({ children }) => {
  const [currentTree, setCurrentTree] = useState<TreeMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTreeMetadata = async (treeId: string): Promise<TreeMetadata> => {
    setIsLoading(true);
    try {
      const response = await fetch(`/server/navigationTrees/trees/${treeId}/metadata`);
      const result = await response.json();
      
      if (result.success) {
        setCurrentTree(result.tree);
        return result.tree;
      } else {
        throw new Error(result.error);
      }
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const loadTreeNodes = async (treeId: string, page = 0, limit = 100): Promise<NavigationNode[]> => {
    const response = await fetch(`/server/navigationTrees/trees/${treeId}/nodes?page=${page}&limit=${limit}`);
    const result = await response.json();
    
    if (result.success) {
      return result.nodes;
    } else {
      throw new Error(result.error);
    }
  };

  const loadTreeEdges = async (treeId: string, nodeIds?: string[]): Promise<NavigationEdge[]> => {
    const url = new URL(`/server/navigationTrees/trees/${treeId}/edges`, window.location.origin);
    if (nodeIds) {
      nodeIds.forEach(id => url.searchParams.append('node_ids', id));
    }
    
    const response = await fetch(url.toString());
    const result = await response.json();
    
    if (result.success) {
      return result.edges;
    } else {
      throw new Error(result.error);
    }
  };

  const saveNode = async (treeId: string, node: NavigationNode): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/trees/${treeId}/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const saveEdge = async (treeId: string, edge: NavigationEdge): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/trees/${treeId}/edges`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(edge)
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const deleteNode = async (treeId: string, nodeId: string): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/trees/${treeId}/nodes/${nodeId}`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const deleteEdge = async (treeId: string, edgeId: string): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/trees/${treeId}/edges/${edgeId}`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  return (
    <NavigationConfigContext.Provider value={{
      loadTreeMetadata,
      loadTreeNodes,
      loadTreeEdges,
      saveNode,
      deleteNode,
      saveEdge,
      deleteEdge,
      currentTree,
      isLoading,
      error
    }}>
      {children}
    </NavigationConfigContext.Provider>
  );
};
```

### 3.2 Hook Changes

**Files to Modify:**

1. **`frontend/src/hooks/navigation/useNavigationEditor.ts`** - Update to use new APIs
2. **`frontend/src/hooks/navigation/useEdgeEdit.ts`** - Simplify action handling
3. **`frontend/src/hooks/navigation/useNode.ts`** - Simplify verification handling
4. **`frontend/src/hooks/navigation/useNestedNavigation.ts`** - Update tree loading

#### Updated Navigation Editor Hook

```typescript
// frontend/src/hooks/navigation/useNavigationEditor.ts - MAJOR UPDATES

export const useNavigationEditor = () => {
  const navigationConfig = useNavigationConfig();
  const navigation = useContext(NavigationContext);

  // Load tree data with pagination
  const loadTreeData = useCallback(async (treeId: string) => {
    try {
      // Load metadata first
      const tree = await navigationConfig.loadTreeMetadata(treeId);
      
      // Load first page of nodes
      const nodes = await navigationConfig.loadTreeNodes(treeId, 0, 100);
      
      // Load edges for loaded nodes
      const nodeIds = nodes.map(n => n.node_id);
      const edges = await navigationConfig.loadTreeEdges(treeId, nodeIds);
      
      // Convert to frontend format
      const frontendNodes = nodes.map(node => ({
        id: node.node_id,
        type: 'uiScreen',
        position: { x: node.position_x, y: node.position_y },
        data: {
          label: node.label,
          type: node.node_type,
          description: node.description,
          verifications: node.verifications, // Directly from DB
          is_root: node.is_root,
          parent: node.parent_node_ids,
          screenshot: node.screenshot,
          depth: node.depth,
          priority: node.priority,
          menu_type: node.menu_type
        }
      }));

      const frontendEdges = edges.map(edge => ({
        id: edge.edge_id,
        source: edge.source_node_id,
        target: edge.target_node_id,
        type: 'uiNavigation',
        data: {
          description: edge.description,
          actions: edge.actions, // Directly from DB
          retryActions: edge.retry_actions,
          final_wait_time: edge.final_wait_time,
          edge_type: edge.edge_type,
          priority: edge.priority,
          threshold: edge.threshold
        }
      }));

      navigation.setNodes(frontendNodes);
      navigation.setEdges(frontendEdges);
      
    } catch (error) {
      navigation.setError(`Failed to load tree: ${error.message}`);
    }
  }, [navigationConfig, navigation]);

  // Save node changes
  const handleNodeFormSubmit = useCallback(async (nodeForm: any) => {
    try {
      const nodeData = {
        node_id: nodeForm.id || `node-${Date.now()}`,
        label: nodeForm.label,
        node_type: nodeForm.type,
        description: nodeForm.description,
        position_x: nodeForm.position?.x || 0,
        position_y: nodeForm.position?.y || 0,
        parent_node_ids: nodeForm.parent || [],
        is_root: nodeForm.is_root || false,
        verifications: nodeForm.verifications || [], // Save directly
        screenshot: nodeForm.screenshot,
        depth: nodeForm.depth || 0,
        priority: nodeForm.priority || 'p3',
        menu_type: nodeForm.menu_type
      };

      await navigationConfig.saveNode(navigation.currentTreeId, nodeData);
      
      // Reload tree data
      await loadTreeData(navigation.currentTreeId);
      
      navigation.setIsNodeDialogOpen(false);
      
    } catch (error) {
      navigation.setError(`Failed to save node: ${error.message}`);
    }
  }, [navigationConfig, navigation, loadTreeData]);

  // Save edge changes
  const handleEdgeFormSubmit = useCallback(async (edgeForm: any) => {
    try {
      const edgeData = {
        edge_id: edgeForm.edgeId,
        source_node_id: edgeForm.source,
        target_node_id: edgeForm.target,
        description: edgeForm.description,
        actions: edgeForm.actions || [], // Save directly
        retry_actions: edgeForm.retryActions || [],
        final_wait_time: edgeForm.final_wait_time || 2000,
        edge_type: edgeForm.edge_type || 'horizontal',
        priority: edgeForm.priority || 'p3',
        threshold: edgeForm.threshold || 0
      };

      await navigationConfig.saveEdge(navigation.currentTreeId, edgeData);
      
      // Reload tree data
      await loadTreeData(navigation.currentTreeId);
      
      navigation.setIsEdgeDialogOpen(false);
      
    } catch (error) {
      navigation.setError(`Failed to save edge: ${error.message}`);
    }
  }, [navigationConfig, navigation, loadTreeData]);

  return {
    ...navigation,
    loadTreeData,
    handleNodeFormSubmit,
    handleEdgeFormSubmit,
    // ... other methods
  };
};
```

### 3.3 Component Changes

**Files to Modify:**

1. **`frontend/src/components/actions/ActionItem.tsx`** - No changes needed (still uses params.wait_time)
2. **`frontend/src/components/verification/*`** - Update to work with embedded verifications
3. **`frontend/src/components/navigation/Navigation_*`** - Update to use new data structure

### 3.4 Type Definition Updates

**Files to Modify:**

1. **`frontend/src/types/pages/Navigation_Types.ts`** - Update interfaces
2. **`frontend/src/types/controller/Action_Types.ts`** - Simplify (no separate action table)

```typescript
// frontend/src/types/pages/Navigation_Types.ts - UPDATES

export interface NavigationNode {
  id: string; // node_id from database
  node_id: string;
  label: string;
  node_type: string;
  description?: string;
  position_x: number;
  position_y: number;
  parent_node_ids: string[];
  is_root: boolean;
  verifications: Verification[]; // Embedded verifications
  screenshot?: string;
  depth: number;
  priority: string;
  menu_type?: string;
  metadata: any;
}

export interface NavigationEdge {
  id: string; // edge_id from database
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  description?: string;
  actions: Action[]; // Embedded actions
  retry_actions: Action[];
  final_wait_time: number;
  edge_type: string;
  priority: string;
  threshold: number;
  metadata: any;
}

export interface Action {
  command: string;
  params: {
    wait_time?: number;
    [key: string]: any;
  };
}

export interface Verification {
  type: string;
  command: string;
  params: {
    timeout?: number;
    [key: string]: any;
  };
}
```

---

## Impact Analysis

### Files to DELETE
```
backend_server/src/routes/server_actions_routes.py (most endpoints)
backend_server/src/routes/server_verification_*.py
shared/lib/supabase/actions_db.py
shared/lib/supabase/verifications_db.py
shared/lib/utils/navigation_cache.py
```

### Files to MAJOR REWRITE
```
shared/lib/supabase/navigation_trees_db.py
backend_server/src/routes/server_navigation_trees_routes.py
frontend/src/contexts/navigation/NavigationConfigContext.tsx
frontend/src/hooks/navigation/useNavigationEditor.ts
frontend/src/types/pages/Navigation_Types.ts
```

### Files to UPDATE
```
frontend/src/hooks/navigation/useEdgeEdit.ts
frontend/src/hooks/navigation/useNode.ts
frontend/src/hooks/navigation/useNestedNavigation.ts
frontend/src/contexts/navigation/NavigationContext.tsx
frontend/src/contexts/device/DeviceDataContext.tsx
shared/lib/utils/navigation_graph.py
backend_core/src/services/navigation/navigation_pathfinding.py
```

### Files UNCHANGED
```
frontend/src/components/actions/ActionItem.tsx (wait_time handling stays same)
Most verification components (just data source changes)
```

---

## Migration Timeline

### Week 1: Database Migration
- Create new tables
- Write and test migration script
- Migrate development data

### Week 2: Backend Migration
- Rewrite database layer
- Update API routes
- Test new endpoints

### Week 3: Frontend Migration
- Update contexts and hooks
- Test navigation functionality
- Update type definitions

### Week 4: Testing & Cleanup
- End-to-end testing
- Performance validation
- Remove old code
- Documentation updates

This plan completely eliminates the JSONB bottleneck and creates a clean, scalable architecture that can handle massive navigation trees efficiently. 