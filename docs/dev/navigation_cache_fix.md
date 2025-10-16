# Navigation Tree Cache Fix

## Problem

After editing and saving edges (or nodes), users encountered the error:
```
Navigation tree [tree-id] not loaded. Please reload the NavigationEditor to populate the navigation cache.
```

This error persisted until the page was refreshed, preventing proper navigation and tree operations.

## Root Cause

The navigation system maintains a tree cache (`treeCache`) for nested navigation and breadcrumb functionality. When a tree is initially loaded, it's cached using `cacheAndSwitchToTree()`. However, when edges or nodes were saved:

1. The local state (`nodes` and `edges`) was updated correctly
2. The database was updated correctly
3. **BUT** the tree cache was **NOT** updated with the new state

This meant that:
- Any subsequent operations relying on the cache (nested navigation, breadcrumbs, etc.) would see stale data
- The cache would be out of sync with the actual displayed state
- Navigation operations would fail because they couldn't find the updated tree in the cache

## Solution

Added `cacheTree()` calls to all state modification methods to keep the cache synchronized with the current state:

### 1. Edge Save (`saveEdgeWithStateUpdate`)
After updating edges with server response, update the cache:
```typescript
// UPDATE TREE CACHE: Keep cache synchronized with current state
if (navigationConfig?.actualTreeId) {
  cacheTree(navigationConfig.actualTreeId, { nodes, edges: updatedEdges });
  console.log('[@NavigationContext] Updated tree cache after edge save');
}
```

### 2. Node Save (`saveNodeWithStateUpdate`)
After saving a node, update both the current tree cache and (if applicable) the original tree cache for parent references:
```typescript
// UPDATE TREE CACHE: Keep cache synchronized with current state
if (isParentReference && updatedNodeData.data.originalTreeId) {
  // Update cache for the original parent tree
  const originalTreeCache = getCachedTree(updatedNodeData.data.originalTreeId);
  if (originalTreeCache) {
    const updatedOriginalNodes = originalTreeCache.nodes.map((node) =>
      node.id === updatedNodeData.id ? updatedNodeData : node
    );
    cacheTree(updatedNodeData.data.originalTreeId, { 
      nodes: updatedOriginalNodes, 
      edges: originalTreeCache.edges 
    });
  }
}

// Always update current tree cache
cacheTree(navigationConfig.actualTreeId, { nodes, edges });
```

### 3. Full Tree Save (`saveTreeWithStateUpdate`)
After saving the entire tree, update the cache:
```typescript
// UPDATE TREE CACHE: Keep cache synchronized with current state after full tree save
cacheTree(treeId, { nodes: nodes as UINavigationNode[], edges: edges as UINavigationEdge[] });
console.log('[@NavigationContext] Updated tree cache after tree save');
```

### 4. Edge Direction Deletion (`deleteEdgeDirection`)
After deleting an edge direction (or entire edge), update the cache:
```typescript
// When deleting entire edge
if (bothDirectionsEmpty) {
  const filteredEdges = edges.filter(e => e.id !== edgeId);
  setEdges(filteredEdges);
  
  // UPDATE TREE CACHE
  if (navigationConfig?.actualTreeId) {
    cacheTree(navigationConfig.actualTreeId, { nodes, edges: filteredEdges });
  }
}

// When updating edge direction
else {
  const updatedEdges = edges.map((e) => e.id === edge.id ? updatedEdgeFromServer : e);
  setEdges(updatedEdges);
  
  // UPDATE TREE CACHE
  if (navigationConfig?.actualTreeId) {
    cacheTree(navigationConfig.actualTreeId, { nodes, edges: updatedEdges });
  }
}
```

## Benefits

1. **Cache Consistency**: Tree cache is always in sync with displayed state
2. **No More Errors**: Navigation operations work correctly after saves without requiring page refresh
3. **Better UX**: Users can continue editing without interruption
4. **Nested Navigation**: Breadcrumb and nested navigation work correctly after saves

## Testing

To verify the fix:
1. Open NavigationEditor
2. Edit and save an edge
3. Try navigating or using breadcrumbs - should work without errors
4. Check console logs for "Updated tree cache after..." messages
5. No page refresh should be needed

## Files Modified

- `frontend/src/contexts/navigation/NavigationContext.tsx`
  - `saveEdgeWithStateUpdate` - Added cache update after edge save
  - `saveNodeWithStateUpdate` - Added cache update after node save (with parent reference handling)
  - `saveTreeWithStateUpdate` - Added cache update after full tree save
  - `deleteEdgeDirection` - Added cache update after edge deletion/update

## Architecture Notes

The tree cache (`treeCache: Map<string, { nodes, edges }>`) is managed by NavigationContext and provides:
- Fast tree switching for nested navigation
- Breadcrumb navigation support
- State preservation when navigating between trees

The cache is updated via:
- `cacheTree(treeId, data)` - Updates cache without switching
- `cacheAndSwitchToTree(treeId, data)` - Updates cache AND switches display
- `switchToTree(treeId)` - Switches to cached tree without updating

This fix ensures the cache remains the single source of truth for tree data across all navigation operations.

