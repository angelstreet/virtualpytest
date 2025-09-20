# Navigation Pathfinding System

## Overview

The navigation pathfinding system uses NetworkX graphs to find optimal paths between nodes in the navigation tree. It supports both single-tree and cross-tree navigation with proper bidirectional edge handling.

## Core Concepts

### Graph Structure
- **Nodes**: Represent UI states (e.g., `live`, `live_menu`, `live_menu_audio`)
- **Edges**: Represent navigation transitions with executable actions
- **Unified Graph**: Combines multiple navigation trees for cross-tree pathfinding

### Edge Types

#### Forward Edges
- Created when action set index 0 has actions
- Direction: `source_node → target_node`
- Used by pathfinding algorithm

#### Reverse Edges  
- Created when action set index 1 has actions
- Direction: `target_node → source_node`
- Enables return navigation
- Edge ID: `{original_edge_id}_reverse`

## Bidirectional Edge Handling

### Problem Solved
Previously, edges were created even when they had no forward actions, causing pathfinding to find unusable paths.

### Current Solution
```python
# Only create forward edge if it has forward actions
if has_forward_actions:
    G.add_edge(source_id, target_id, forward_edge_data)

# Only create reverse edge if it has reverse actions  
if has_reverse_actions:
    G.add_edge(target_id, source_id, reverse_edge_data)
```

### Example
Original edge configuration:
```json
{
  "source": "live_menu",
  "target": "live_menu_audio", 
  "action_sets": [
    {"id": "forward", "actions": [{"command": "press_key", "params": {"key": "OK"}}]},
    {"id": "reverse", "actions": [{"command": "press_key", "params": {"key": "BACK"}}]}
  ]
}
```

Results in two separate graph edges:
- `live_menu → live_menu_audio` (forward actions)
- `live_menu_audio → live_menu` (reverse actions)

## Pathfinding Algorithm

### Process
1. **Weight Assignment**: All edges get weight = 1 (uniform cost)
2. **Shortest Path**: Uses NetworkX `shortest_path()` for optimal route
3. **Action Extraction**: Uses forward action set (index 0) from each edge
4. **Cross-Tree Support**: Handles navigation between different navigation trees

### Path Resolution
For navigation from `live_menu_audio` to `live_menu_subtitles`:

**Before Fix**: 
- Direct path `live_menu_audio → live_menu_subtitles` (0 actions) ❌

**After Fix**:
- Multi-step path: `live_menu_audio → live_menu → live_menu_subtitles` ✅
- Each step has executable actions

## Key Files

- `shared/lib/utils/navigation_graph.py` - Graph construction and bidirectional edge creation
- `backend_host/src/services/navigation/navigation_pathfinding.py` - Pathfinding algorithms
- `shared/lib/utils/navigation_cache.py` - Graph caching for performance

## Usage Examples

### Basic Navigation
```python
from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path

# Find path to target node
path = find_shortest_path(tree_id, "live_menu_audio", team_id, start_node_id)
```

### Audio Menu Navigation
The audio menu analyzer automatically benefits from proper pathfinding:
```python
# This now works correctly via multi-step path
goto_node(host, device, "live_menu_audio", tree_id, team_id, context)
goto_node(host, device, "live_menu_subtitles", tree_id, team_id, context)
```

## Debugging

### Graph Inspection
Check transition summary in logs:
```
[@navigation:graph:create_networkx_graph] ===== ALL POSSIBLE TRANSITIONS SUMMARY =====
[@navigation:graph:create_networkx_graph] Transition  1: live → live_menu (forward actions: 1)
[@navigation:graph:create_networkx_graph] Transition  2: live_menu → live (reverse actions: 1)
```

### Pathfinding Logs
Monitor path resolution:
```
[@navigation:pathfinding:find_shortest_path_unified] Found path with 3 nodes
[@navigation:pathfinding:find_shortest_path_unified] Path nodes: live_menu_audio → live_menu → live_menu_subtitles
```

## Best Practices

1. **Action Requirements**: Ensure each direction has appropriate actions defined
2. **Bidirectional Design**: Use reverse actions for return navigation
3. **Graph Validation**: Check transition summaries for missing paths
4. **Performance**: Leverage unified graph caching for cross-tree navigation

## Troubleshooting

### "No path found" Errors
- Check if target node exists in graph
- Verify edges have forward actions in the required direction
- Ensure unified graph cache is populated

### Missing Return Paths
- Add reverse action sets to enable bidirectional navigation
- Check that reverse actions are properly defined

### Performance Issues
- Use unified graph caching
- Avoid rebuilding graphs unnecessarily
- Monitor graph size and complexity
