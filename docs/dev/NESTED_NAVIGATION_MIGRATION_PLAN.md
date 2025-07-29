# Nested Navigation Trees Migration Plan

## Overview
Complete implementation of nested navigation trees in the normalized architecture with explicit parent-child relationships. This plan assumes the base navigation migration has been completed and focuses solely on adding nested tree functionality.

**Target**: Clean nested tree architecture with explicit database relationships
**Timeline**: 2 weeks - Database → Backend → Frontend
**Approach**: No backward compatibility, clean implementation only

---

## Phase 1: Database Schema Enhancement

### 1.1 Add Nested Tree Relationships

```sql
-- Step 1: Add parent relationship columns to navigation_trees
ALTER TABLE navigation_trees 
ADD COLUMN parent_tree_id uuid REFERENCES navigation_trees(id) ON DELETE CASCADE;

ALTER TABLE navigation_trees 
ADD COLUMN parent_node_id text; -- References the node_id that spawned this subtree

-- Step 2: Add metadata for nested tree management
ALTER TABLE navigation_trees 
ADD COLUMN tree_depth integer DEFAULT 0; -- Depth level (0 = root, 1 = first level nested, etc.)

ALTER TABLE navigation_trees 
ADD COLUMN is_root_tree boolean DEFAULT true; -- True only for top-level trees

-- Step 3: Add nested tree navigation metadata to nodes
ALTER TABLE navigation_nodes 
ADD COLUMN has_subtree boolean DEFAULT false; -- True if this node has associated subtrees

ALTER TABLE navigation_nodes 
ADD COLUMN subtree_count integer DEFAULT 0; -- Number of subtrees linked to this node

-- Step 4: Create indexes for nested tree queries
CREATE INDEX idx_navigation_trees_parent_tree ON navigation_trees(parent_tree_id);
CREATE INDEX idx_navigation_trees_parent_node ON navigation_trees(parent_node_id);
CREATE INDEX idx_navigation_trees_depth ON navigation_trees(tree_depth);
CREATE INDEX idx_navigation_trees_is_root ON navigation_trees(is_root_tree);
CREATE INDEX idx_navigation_nodes_has_subtree ON navigation_nodes(has_subtree);

-- Step 5: Add constraints to prevent infinite nesting (max depth = 5)
ALTER TABLE navigation_trees 
ADD CONSTRAINT check_tree_depth CHECK (tree_depth >= 0 AND tree_depth <= 5);

-- Step 6: Add constraint to ensure parent relationships are valid
ALTER TABLE navigation_trees 
ADD CONSTRAINT check_parent_consistency 
CHECK (
    (parent_tree_id IS NULL AND parent_node_id IS NULL AND is_root_tree = true) OR
    (parent_tree_id IS NOT NULL AND parent_node_id IS NOT NULL AND is_root_tree = false)
);
```

### 1.2 Nested Tree Helper Functions

```sql
-- Function to get all descendant trees
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
    SELECT id, name, tree_depth, parent_tree_id, parent_node_id 
    FROM tree_hierarchy;
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

-- Function to update node subtree counts
CREATE OR REPLACE FUNCTION update_node_subtree_counts()
RETURNS TRIGGER
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
                AND parent_node_id = (SELECT node_id FROM navigation_nodes WHERE tree_id = NEW.parent_tree_id AND id = navigation_nodes.id)
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

-- Create trigger to automatically update subtree counts
CREATE TRIGGER trigger_update_subtree_counts
    AFTER INSERT OR DELETE ON navigation_trees
    FOR EACH ROW
    EXECUTE FUNCTION update_node_subtree_counts();
```

---

## Phase 2: Backend Implementation

### 2.1 Database Layer Functions

**File: `shared/lib/supabase/navigation_trees_db.py`** - Add these functions:

```python
def get_node_sub_trees(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Get all sub-trees that belong to a specific node."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*')\
            .eq('parent_tree_id', tree_id)\
            .eq('parent_node_id', node_id)\
            .eq('team_id', team_id)\
            .order('created_at')\
            .execute()
        
        return {
            'success': True,
            'sub_trees': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_node_sub_trees] Error: {e}")
        return {'success': False, 'error': str(e)}

def create_sub_tree(parent_tree_id: str, parent_node_id: str, tree_data: Dict, team_id: str) -> Dict:
    """Create a new sub-tree linked to a parent node."""
    try:
        supabase = get_supabase()
        
        # Get parent tree depth
        parent_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', parent_tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not parent_result.data:
            return {'success': False, 'error': 'Parent tree not found'}
        
        parent_depth = parent_result.data[0]['tree_depth']
        
        # Validate depth limit
        if parent_depth >= 5:
            return {'success': False, 'error': 'Maximum nesting depth reached (5 levels)'}
        
        # Set nested tree properties
        tree_data.update({
            'parent_tree_id': parent_tree_id,
            'parent_node_id': parent_node_id,
            'tree_depth': parent_depth + 1,
            'is_root_tree': False,
            'team_id': team_id,
            'id': str(uuid4()),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        
        # Create the sub-tree
        result = supabase.table('navigation_trees').insert(tree_data).execute()
        
        print(f"[@db:navigation_trees:create_sub_tree] Created sub-tree: {tree_data['id']} for node: {parent_node_id}")
        return {'success': True, 'tree': result.data[0]}
        
    except Exception as e:
        print(f"[@db:navigation_trees:create_sub_tree] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_tree_hierarchy(root_tree_id: str, team_id: str) -> Dict:
    """Get complete tree hierarchy starting from root."""
    try:
        supabase = get_supabase()
        
        # Use the SQL function to get all descendant trees
        result = supabase.rpc('get_descendant_trees', {'root_tree_id': root_tree_id}).execute()
        
        return {
            'success': True,
            'hierarchy': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_hierarchy] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_tree_breadcrumb(tree_id: str, team_id: str) -> Dict:
    """Get breadcrumb path for a tree."""
    try:
        supabase = get_supabase()
        
        # Use the SQL function to get tree path
        result = supabase.rpc('get_tree_path', {'target_tree_id': tree_id}).execute()
        
        return {
            'success': True,
            'breadcrumb': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_breadcrumb] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_tree_cascade(tree_id: str, team_id: str) -> Dict:
    """Delete a tree and all its descendant trees."""
    try:
        supabase = get_supabase()
        
        # Get all descendant trees first
        hierarchy_result = get_tree_hierarchy(tree_id, team_id)
        if not hierarchy_result['success']:
            return hierarchy_result
        
        # Delete all trees in reverse depth order (deepest first)
        trees_to_delete = sorted(hierarchy_result['hierarchy'], key=lambda x: x['depth'], reverse=True)
        
        for tree in trees_to_delete:
            # Delete tree (cascade will handle nodes and edges)
            supabase.table('navigation_trees').delete().eq('id', tree['tree_id']).eq('team_id', team_id).execute()
            print(f"[@db:navigation_trees:delete_tree_cascade] Deleted tree: {tree['tree_id']}")
        
        return {'success': True, 'deleted_count': len(trees_to_delete)}
        
    except Exception as e:
        print(f"[@db:navigation_trees:delete_tree_cascade] Error: {e}")
        return {'success': False, 'error': str(e)}

def move_subtree(subtree_id: str, new_parent_tree_id: str, new_parent_node_id: str, team_id: str) -> Dict:
    """Move a subtree to a different parent node."""
    try:
        supabase = get_supabase()
        
        # Get new parent depth
        parent_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', new_parent_tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not parent_result.data:
            return {'success': False, 'error': 'New parent tree not found'}
        
        new_parent_depth = parent_result.data[0]['tree_depth']
        
        # Get current subtree depth to check if move is valid
        subtree_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', subtree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not subtree_result.data:
            return {'success': False, 'error': 'Subtree not found'}
        
        # Calculate new depth and validate
        depth_difference = subtree_result.data[0]['tree_depth'] - new_parent_depth - 1
        if new_parent_depth + 1 + depth_difference > 5:
            return {'success': False, 'error': 'Move would exceed maximum nesting depth'}
        
        # Update subtree parent relationships
        result = supabase.table('navigation_trees').update({
            'parent_tree_id': new_parent_tree_id,
            'parent_node_id': new_parent_node_id,
            'tree_depth': new_parent_depth + 1,
            'updated_at': datetime.now().isoformat()
        }).eq('id', subtree_id).eq('team_id', team_id).execute()
        
        print(f"[@db:navigation_trees:move_subtree] Moved subtree: {subtree_id} to node: {new_parent_node_id}")
        return {'success': True, 'tree': result.data[0]}
        
    except Exception as e:
        print(f"[@db:navigation_trees:move_subtree] Error: {e}")
        return {'success': False, 'error': str(e)}
```

### 2.2 API Routes Implementation

**File: `backend_server/src/routes/server_navigation_trees_routes.py`** - Add these endpoints:

```python
# ============================================================================
# NESTED TREE ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/getNodeSubTrees/<tree_id>/<node_id>', methods=['GET'])
def get_node_sub_trees_api(tree_id, node_id):
    """Get all sub-trees for a specific node."""
    try:
        team_id = get_team_id()
        result = get_node_sub_trees(tree_id, node_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_node_sub_trees] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<parent_tree_id>/nodes/<parent_node_id>/subtrees', methods=['POST'])
def create_sub_tree_api(parent_tree_id, parent_node_id):
    """Create a new sub-tree for a specific node."""
    try:
        team_id = get_team_id()
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        result = create_sub_tree(parent_tree_id, parent_node_id, tree_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:create_sub_tree] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/hierarchy', methods=['GET'])
def get_tree_hierarchy_api(tree_id):
    """Get complete tree hierarchy starting from root."""
    try:
        team_id = get_team_id()
        result = get_tree_hierarchy(tree_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_hierarchy] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/breadcrumb', methods=['GET'])
def get_tree_breadcrumb_api(tree_id):
    """Get breadcrumb path for a tree."""
    try:
        team_id = get_team_id()
        result = get_tree_breadcrumb(tree_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_breadcrumb] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/cascade', methods=['DELETE'])
def delete_tree_cascade_api(tree_id):
    """Delete a tree and all its descendant trees."""
    try:
        team_id = get_team_id()
        result = delete_tree_cascade(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete_cascade] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<subtree_id>/move', methods=['PUT'])
def move_subtree_api(subtree_id):
    """Move a subtree to a different parent node."""
    try:
        team_id = get_team_id()
        data = request.get_json()
        
        if not data or 'new_parent_tree_id' not in data or 'new_parent_node_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required fields: new_parent_tree_id, new_parent_node_id'
            }), 400
        
        result = move_subtree(
            subtree_id, 
            data['new_parent_tree_id'], 
            data['new_parent_node_id'], 
            team_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:move_subtree] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500
```

---

## Phase 3: Frontend Implementation

### 3.1 Enhanced Navigation Context

**File: `frontend/src/contexts/navigation/NavigationConfigContext.tsx`** - Add nested tree methods:

```typescript
interface NavigationConfigContextType {
  // ... existing methods ...
  
  // Nested tree operations
  loadNodeSubTrees: (treeId: string, nodeId: string) => Promise<NavigationTree[]>;
  createSubTree: (parentTreeId: string, parentNodeId: string, treeData: any) => Promise<NavigationTree>;
  getTreeHierarchy: (treeId: string) => Promise<TreeHierarchy[]>;
  getTreeBreadcrumb: (treeId: string) => Promise<BreadcrumbItem[]>;
  deleteTreeCascade: (treeId: string) => Promise<void>;
  moveSubtree: (subtreeId: string, newParentTreeId: string, newParentNodeId: string) => Promise<void>;
}

export const NavigationConfigProvider: React.FC = ({ children }) => {
  // ... existing state ...

  const loadNodeSubTrees = async (treeId: string, nodeId: string): Promise<NavigationTree[]> => {
    const response = await fetch(`/server/navigationTrees/getNodeSubTrees/${treeId}/${nodeId}`);
    const result = await response.json();
    
    if (result.success) {
      return result.sub_trees;
    } else {
      throw new Error(result.error);
    }
  };

  const createSubTree = async (parentTreeId: string, parentNodeId: string, treeData: any): Promise<NavigationTree> => {
    const response = await fetch(`/server/navigationTrees/${parentTreeId}/nodes/${parentNodeId}/subtrees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(treeData)
    });
    
    const result = await response.json();
    if (result.success) {
      return result.tree;
    } else {
      throw new Error(result.error);
    }
  };

  const getTreeHierarchy = async (treeId: string): Promise<TreeHierarchy[]> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/hierarchy`);
    const result = await response.json();
    
    if (result.success) {
      return result.hierarchy;
    } else {
      throw new Error(result.error);
    }
  };

  const getTreeBreadcrumb = async (treeId: string): Promise<BreadcrumbItem[]> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/breadcrumb`);
    const result = await response.json();
    
    if (result.success) {
      return result.breadcrumb;
    } else {
      throw new Error(result.error);
    }
  };

  const deleteTreeCascade = async (treeId: string): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/${treeId}/cascade`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  const moveSubtree = async (subtreeId: string, newParentTreeId: string, newParentNodeId: string): Promise<void> => {
    const response = await fetch(`/server/navigationTrees/${subtreeId}/move`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_parent_tree_id: newParentTreeId,
        new_parent_node_id: newParentNodeId
      })
    });
    
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error);
    }
  };

  return (
    <NavigationConfigContext.Provider value={{
      // ... existing values ...
      loadNodeSubTrees,
      createSubTree,
      getTreeHierarchy,
      getTreeBreadcrumb,
      deleteTreeCascade,
      moveSubtree
    }}>
      {children}
    </NavigationConfigContext.Provider>
  );
};
```

### 3.2 Enhanced Navigation Stack Context

**File: `frontend/src/contexts/navigation/NavigationStackContext.tsx`** - Add breadcrumb support:

```typescript
interface TreeLevel {
  treeId: string;
  treeName: string;
  parentNodeId: string;
  parentNodeLabel: string;
  depth: number; // Add depth tracking
}

interface NavigationStackContextType {
  stack: TreeLevel[];
  currentLevel: TreeLevel | null;
  breadcrumb: BreadcrumbItem[]; // Add breadcrumb
  pushLevel: (treeId: string, parentNodeId: string, treeName: string, parentNodeLabel: string, depth: number) => void;
  popLevel: () => void;
  jumpToLevel: (targetIndex: number) => void;
  jumpToRoot: () => void;
  loadBreadcrumb: (treeId: string) => Promise<void>; // Load breadcrumb from server
  isNested: boolean;
  depth: number;
}

export const NavigationStackProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [stack, setStack] = useState<TreeLevel[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([]);
  const navigationConfig = useNavigationConfig();

  const pushLevel = useCallback(
    (treeId: string, parentNodeId: string, treeName: string, parentNodeLabel: string, depth: number) => {
      setStack((prev) => [...prev, { treeId, treeName, parentNodeId, parentNodeLabel, depth }]);
    },
    [],
  );

  const loadBreadcrumb = useCallback(async (treeId: string) => {
    try {
      const breadcrumbData = await navigationConfig.getTreeBreadcrumb(treeId);
      setBreadcrumb(breadcrumbData);
    } catch (error) {
      console.error('Failed to load breadcrumb:', error);
      setBreadcrumb([]);
    }
  }, [navigationConfig]);

  const currentLevel = stack[stack.length - 1] || null;
  const isNested = stack.length > 0;
  const depth = currentLevel?.depth || 0;

  return (
    <NavigationStackContext.Provider
      value={{
        stack,
        currentLevel,
        breadcrumb,
        pushLevel,
        popLevel,
        jumpToLevel,
        jumpToRoot,
        loadBreadcrumb,
        isNested,
        depth,
      }}
    >
      {children}
    </NavigationStackContext.Provider>
  );
};
```

### 3.3 Enhanced Nested Navigation Hook

**File: `frontend/src/hooks/navigation/useNestedNavigation.ts`** - Complete rewrite:

```typescript
export const useNestedNavigation = ({
  setNodes,
  setEdges,
  openNodeDialog,
}: NestedNavigationHookParams) => {
  const { pushLevel, stack, loadBreadcrumb } = useNavigationStack();
  const { actualTreeId } = useNavigationConfig();
  const navigationConfig = useNavigationConfig();

  const handleNodeDoubleClick = async (_event: React.MouseEvent, node: any) => {
    // 1. Skip entry type nodes
    if (node.data?.type === 'entry') {
      return;
    }

    // 2. Infinite loop protection
    const nodeId = node.id;
    const isAlreadyInThisNode = stack.some((level) => level.parentNodeId === nodeId);

    if (isAlreadyInThisNode) {
      console.warn(
        `[@useNestedNavigation] Prevented infinite loop: Already in sub-tree of node "${node.data.label}" (ID: ${nodeId})`,
      );
      openNodeDialog(node);
      return;
    }

    // 3. Check for existing sub-trees
    try {
      const subTrees = await navigationConfig.loadNodeSubTrees(actualTreeId, node.id);

      if (subTrees.length > 0) {
        // 4a. Load existing sub-tree
        const primarySubTree = subTrees[0];
        const treeData = await navigationConfig.loadTreeData(primarySubTree.id);

        if (treeData.success) {
          // Convert to frontend format
          const frontendNodes = (treeData.nodes || []).map((node: any) => ({
            id: node.node_id,
            type: 'uiScreen',
            position: { x: node.position_x, y: node.position_y },
            data: {
              label: node.label,
              type: node.node_type,
              description: node.description,
              verifications: node.verifications,
              has_subtree: node.has_subtree,
              subtree_count: node.subtree_count,
              ...node.data
            }
          }));

          const frontendEdges = (treeData.edges || []).map((edge: any) => ({
            id: edge.edge_id,
            source: edge.source_node_id,
            target: edge.target_node_id,
            type: 'uiNavigation',
            data: {
              description: edge.description,
              actions: edge.actions,
              retryActions: edge.retry_actions,
              final_wait_time: edge.final_wait_time,
              ...edge.data
            }
          }));

          // 5. Push to navigation stack with depth
          pushLevel(
            primarySubTree.id, 
            node.id, 
            primarySubTree.name, 
            node.data.label,
            primarySubTree.tree_depth
          );

          // Load breadcrumb for the new tree
          await loadBreadcrumb(primarySubTree.id);

          // Set nodes and edges
          setTimeout(() => {
            setNodes(frontendNodes);
            setEdges(frontendEdges);
          }, 10);

          console.log(`[@useNestedNavigation] Loaded existing sub-tree: ${primarySubTree.name}`);
        }
      } else {
        // 4b. Create new sub-tree
        await createNewSubTree(node);
      }
    } catch (error) {
      console.error('[@useNestedNavigation] Error handling node double-click:', error);
      // Fallback to node dialog
      openNodeDialog(node);
    }
  };

  const createNewSubTree = async (parentNode: any) => {
    try {
      const newTreeData = {
        name: `${parentNode.data.label} - Subtree`,
        userinterface_id: actualTreeId, // Use same interface
        description: `Sub-navigation for ${parentNode.data.label}`,
      };

      const newTree = await navigationConfig.createSubTree(actualTreeId, parentNode.id, newTreeData);

      // Create initial entry node for the new subtree
      const entryNodeData = {
        node_id: 'entry-node',
        label: 'Entry Point',
        node_type: 'entry',
        position_x: 100,
        position_y: 100,
        verifications: [],
        is_root: true
      };

      await navigationConfig.saveNode(newTree.id, entryNodeData);

      // Load the new subtree
      const treeData = await navigationConfig.loadTreeData(newTree.id);
      
      if (treeData.success) {
        const frontendNodes = (treeData.nodes || []).map((node: any) => ({
          id: node.node_id,
          type: 'uiScreen',
          position: { x: node.position_x, y: node.position_y },
          data: {
            label: node.label,
            type: node.node_type,
            description: node.description,
            verifications: node.verifications,
            ...node.data
          }
        }));

        // Push to navigation stack
        pushLevel(newTree.id, parentNode.id, newTree.name, parentNode.data.label, newTree.tree_depth);

        // Load breadcrumb
        await loadBreadcrumb(newTree.id);

        // Set nodes
        setTimeout(() => {
          setNodes(frontendNodes);
          setEdges([]);
        }, 10);

        console.log(`[@useNestedNavigation] Created new sub-tree: ${newTree.name}`);
      }
    } catch (error) {
      console.error('[@useNestedNavigation] Error creating sub-tree:', error);
      throw error;
    }
  };

  return {
    handleNodeDoubleClick,
    createNewSubTree
  };
};
```

### 3.4 Enhanced Type Definitions

**File: `frontend/src/types/pages/Navigation_Types.ts`** - Add nested tree types:

```typescript
export interface NavigationTree {
  id: string;
  name: string;
  userinterface_id: string;
  team_id: string;
  description?: string;
  parent_tree_id?: string;
  parent_node_id?: string;
  tree_depth: number;
  is_root_tree: boolean;
  root_node_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TreeHierarchy {
  tree_id: string;
  tree_name: string;
  depth: number;
  parent_tree_id?: string;
  parent_node_id?: string;
}

export interface BreadcrumbItem {
  tree_id: string;
  tree_name: string;
  depth: number;
  node_id?: string;
}

export interface UINavigationNodeData {
  // ... existing properties ...
  
  // Nested tree properties
  has_subtree?: boolean;
  subtree_count?: number;
}

// Nested tree operations
export interface NestedTreeOperations {
  loadNodeSubTrees: (treeId: string, nodeId: string) => Promise<NavigationTree[]>;
  createSubTree: (parentTreeId: string, parentNodeId: string, treeData: any) => Promise<NavigationTree>;
  getTreeHierarchy: (treeId: string) => Promise<TreeHierarchy[]>;
  getTreeBreadcrumb: (treeId: string) => Promise<BreadcrumbItem[]>;
  deleteTreeCascade: (treeId: string) => Promise<void>;
  moveSubtree: (subtreeId: string, newParentTreeId: string, newParentNodeId: string) => Promise<void>;
}
```

### 3.5 Breadcrumb Navigation Component

**File: `frontend/src/components/navigation/NavigationBreadcrumb.tsx`** - New component:

```typescript
import React from 'react';
import { useNavigationStack } from '../../contexts/navigation/NavigationStackContext';

export const NavigationBreadcrumb: React.FC = () => {
  const { breadcrumb, jumpToLevel, jumpToRoot, isNested } = useNavigationStack();

  if (!isNested || breadcrumb.length === 0) {
    return null;
  }

  return (
    <div className="navigation-breadcrumb">
      <button 
        onClick={jumpToRoot}
        className="breadcrumb-item root"
      >
        🏠 Root
      </button>
      
      {breadcrumb.map((item, index) => (
        <React.Fragment key={item.tree_id}>
          <span className="breadcrumb-separator">›</span>
          <button
            onClick={() => jumpToLevel(index)}
            className={`breadcrumb-item ${index === breadcrumb.length - 1 ? 'current' : ''}`}
          >
            {item.tree_name}
          </button>
        </React.Fragment>
      ))}
      
      <div className="breadcrumb-info">
        Depth: {breadcrumb[breadcrumb.length - 1]?.depth || 0}/5
      </div>
    </div>
  );
};
```

---

## Phase 4: UI Enhancements

### 4.1 Node Visual Indicators

Add visual indicators for nodes with subtrees:

```typescript
// In node rendering logic
const NodeComponent = ({ data }) => {
  return (
    <div className={`navigation-node ${data.has_subtree ? 'has-subtree' : ''}`}>
      <div className="node-label">{data.label}</div>
      
      {data.has_subtree && (
        <div className="subtree-indicator">
          <span className="subtree-icon">📁</span>
          <span className="subtree-count">{data.subtree_count}</span>
        </div>
      )}
    </div>
  );
};
```

### 4.2 Context Menu for Nested Operations

```typescript
const NestedTreeContextMenu = ({ node, onCreateSubtree, onManageSubtrees }) => {
  return (
    <div className="context-menu">
      <button onClick={() => onCreateSubtree(node)}>
        Create Subtree
      </button>
      
      {node.data.has_subtree && (
        <button onClick={() => onManageSubtrees(node)}>
          Manage Subtrees ({node.data.subtree_count})
        </button>
      )}
    </div>
  );
};
```

---

## Migration Timeline

### Week 1: Database Migration
- **Day 1-2**: Create database schema changes and helper functions
- **Day 3-4**: Test database functions and constraints
- **Day 5**: Deploy database changes to development environment

### Week 2: Backend & Frontend Implementation
- **Day 1-2**: Implement backend database layer and API routes
- **Day 3-4**: Update frontend contexts and hooks
- **Day 5**: Create UI components and test end-to-end functionality

---

## Testing Strategy

### Database Testing
```sql
-- Test nested tree creation
INSERT INTO navigation_trees (name, userinterface_id, team_id, parent_tree_id, parent_node_id, tree_depth, is_root_tree)
VALUES ('Test Subtree', 'ui-123', 'team-123', 'parent-tree-123', 'parent-node-123', 1, false);

-- Test depth constraint
SELECT * FROM get_descendant_trees('root-tree-id');
SELECT * FROM get_tree_path('nested-tree-id');
```

### API Testing
```bash
# Test subtree creation
curl -X POST /server/navigationTrees/parent-tree-id/nodes/parent-node-id/subtrees \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Subtree", "description": "Test subtree creation"}'

# Test hierarchy retrieval
curl /server/navigationTrees/tree-id/hierarchy
```

### Frontend Testing
- Test double-click navigation into subtrees
- Test breadcrumb navigation
- Test infinite loop prevention
- Test depth limit enforcement
- Test subtree creation and management

---

## Benefits of This Implementation

1. **Explicit Relationships**: Clear parent-child relationships in database
2. **Depth Control**: Built-in depth limits prevent infinite nesting
3. **Performance**: Efficient queries with proper indexing
4. **Scalability**: Can handle large numbers of nested trees
5. **Data Integrity**: Constraints ensure consistent relationships
6. **User Experience**: Visual indicators and breadcrumb navigation
7. **Clean Architecture**: No legacy code, modern implementation

This plan provides a complete, production-ready nested navigation tree system that integrates seamlessly with the refactored navigation architecture. 