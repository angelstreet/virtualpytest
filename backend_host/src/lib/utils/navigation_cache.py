"""
Navigation graph caching system
Manages in-memory cache of NetworkX graphs for performance
"""

import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import os

# Global cache storage
_navigation_graphs_cache: Dict[str, nx.DiGraph] = {}
_cache_timestamps: Dict[str, datetime] = {}
_resolved_tree_data_cache: Dict[str, Dict] = {}  # Cache for resolved tree data (nodes + edges)

# NEW: Unified graph caching for nested trees
_unified_graphs_cache: Dict[str, nx.DiGraph] = {}      # Unified graphs with nested trees
_tree_hierarchy_cache: Dict[str, Dict] = {}            # Tree hierarchy metadata
_node_location_cache: Dict[str, str] = {}              # node_id -> tree_id mapping
_unified_cache_timestamps: Dict[str, datetime] = {}

def get_cached_graph(tree_id: str, team_id: str, force_rebuild: bool = False) -> Optional[nx.DiGraph]:
    """
    Get cached NetworkX graph for a navigation tree
    
    Args:
        tree_id: Navigation tree ID (name or UUID)
        team_id: Team ID for security
        force_rebuild: Force rebuild even if cached
        
    Returns:
        NetworkX directed graph or None if not cached
    """
    cache_key = f"{tree_id}_{team_id}"
    
    # Return cached graph if available
    if cache_key in _navigation_graphs_cache and not force_rebuild:
        print(f"[@navigation:cache:get_cached_graph] Using cached NetworkX graph for tree: {tree_id}")
        return _navigation_graphs_cache[cache_key]
    
    # If not cached, return None - no database calls during navigation
    print(f"[@navigation:cache:get_cached_graph] No cached graph found for tree: {tree_id}")
    return None

def populate_cache(tree_id: str, team_id: str, nodes: List[Dict], edges: List[Dict]) -> Optional[nx.DiGraph]:
    """
    Populate cache with tree data (called when tree is first loaded)
    
    Args:
        tree_id: Navigation tree ID (name or UUID)
        team_id: Team ID for security
        nodes: Tree nodes data (with resolved verification objects)
        edges: Tree edges data (with resolved action objects)
        
    Returns:
        NetworkX directed graph or None if failed
    """
    cache_key = f"{tree_id}_{team_id}"
    
    try:
        print(f"[@navigation:cache:populate_cache] Building NetworkX graph for tree: {tree_id}")
        
        try:
            from src.lib.utils.navigation_graph import create_networkx_graph
        except ImportError as ie:
            print(f"[@navigation:cache:populate_cache] Failed to import navigation_graph module: {ie}")
            import traceback
            traceback.print_exc()
            return None
        
        if not nodes:
            print(f"[@navigation:cache:populate_cache] No nodes found for tree: {tree_id}")
            return None
            
        # Build NetworkX graph
        print(f"[@navigation:cache:populate_cache] Creating NetworkX graph with {len(nodes)} nodes and {len(edges)} edges")
        G = create_networkx_graph(nodes, edges)
        
        if not G:
            print(f"[@navigation:cache:populate_cache] create_networkx_graph returned None for tree: {tree_id}")
            return None
        
        # Cache the NetworkX graph
        _navigation_graphs_cache[cache_key] = G
        _cache_timestamps[cache_key] = datetime.now()
        
        # Cache the resolved tree data (nodes and edges with resolved objects)
        _resolved_tree_data_cache[cache_key] = {
            'nodes': nodes,  # Resolved nodes with verification objects
            'edges': edges   # Resolved edges with action objects
        }
        
        print(f"[@navigation:cache:populate_cache] Successfully cached graph with {len(G.nodes)} nodes and {len(G.edges)} edges")
        print(f"[@navigation:cache:populate_cache] Successfully cached resolved tree data with {len(nodes)} nodes and {len(edges)} edges")
        
        # Log cache statistics
        print(f"[@navigation:cache:populate_cache] ===== CACHE STATISTICS =====")
        print(f"[@navigation:cache:populate_cache] Cache key: {cache_key}")
        print(f"[@navigation:cache:populate_cache] Total cached graphs: {len(_navigation_graphs_cache)}")
        print(f"[@navigation:cache:populate_cache] Total cached tree data: {len(_resolved_tree_data_cache)}")
        print(f"[@navigation:cache:populate_cache] All cache keys: {list(_navigation_graphs_cache.keys())}")
        
        # Log what transitions are now available for pathfinding
        print(f"[@navigation:cache:populate_cache] ===== CACHED TRANSITIONS AVAILABLE FOR PATHFINDING =====")
        for i, (from_node, to_node, edge_data) in enumerate(G.edges(data=True), 1):
            from_info = G.nodes[from_node]
            to_info = G.nodes[to_node]
            from_label = from_info.get('label', from_node)
            to_label = to_info.get('label', to_node)
            # NEW: Use default_actions from action_sets structure
            actions = edge_data.get('default_actions', [])
            action_count = len(actions) if actions else 0
            alternatives_count = edge_data.get('alternatives_count', 1)
            primary_action = edge_data.get('go_action', 'none')
            
            print(f"[@navigation:cache:populate_cache] Cached Transition {i:2d}: {from_label} → {to_label} (primary: {primary_action}, {action_count} actions, {alternatives_count} alternatives)")
        
        print(f"[@navigation:cache:populate_cache] ===== END CACHED TRANSITIONS =====")
        
        return G
        
    except Exception as e:
        print(f"[@navigation:cache:populate_cache] Error building graph: {e}")
        import traceback
        traceback.print_exc()
        return None

def _cache_graph_under_key(tree_id: str, team_id: str, graph: nx.DiGraph, nodes: List[Dict], edges: List[Dict]) -> None:
    """
    Cache an already-built graph under a specific key without rebuilding
    
    Args:
        tree_id: Navigation tree ID (name or UUID)
        team_id: Team ID for security
        graph: Already built NetworkX graph
        nodes: Tree nodes data (with resolved verification objects)
        edges: Tree edges data (with resolved action objects)
    """
    cache_key = f"{tree_id}_{team_id}"
    
    try:
        # Cache the NetworkX graph
        _navigation_graphs_cache[cache_key] = graph
        _cache_timestamps[cache_key] = datetime.now()
        
        # Cache the resolved tree data (nodes and edges with resolved objects)
        _resolved_tree_data_cache[cache_key] = {
            'nodes': nodes,  # Resolved nodes with verification objects
            'edges': edges   # Resolved edges with action objects
        }
        
        print(f"[@navigation:cache:_cache_graph_under_key] Cached existing graph under key: {cache_key}")
        print(f"[@navigation:cache:_cache_graph_under_key] Graph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
    except Exception as e:
        print(f"[@navigation:cache:_cache_graph_under_key] Error caching graph under key {cache_key}: {e}")

def invalidate_cache(tree_id: str, team_id: str = None):
    """
    Invalidate cache when tree is updated
    
    Args:
        tree_id: Navigation tree ID
        team_id: Team ID (optional, if None invalidates all teams for this tree)
    """
    if team_id:
        cache_key = f"{tree_id}_{team_id}"
        if cache_key in _navigation_graphs_cache:
            del _navigation_graphs_cache[cache_key]
            del _cache_timestamps[cache_key]
        if cache_key in _resolved_tree_data_cache:
            del _resolved_tree_data_cache[cache_key]
        
        # NEW: Also invalidate unified caches that might contain this tree
        invalidate_unified_caches_for_tree(tree_id, team_id)
        
        print(f"[@navigation:cache:invalidate_cache] Invalidated cache for tree: {tree_id}, team: {team_id}")
    else:
        # Invalidate all caches for this tree_id (if team_id unknown)
        keys_to_remove = [k for k in _navigation_graphs_cache.keys() if k.startswith(f"{tree_id}_")]
        for key in keys_to_remove:
            if key in _navigation_graphs_cache:
                del _navigation_graphs_cache[key]
            if key in _cache_timestamps:
                del _cache_timestamps[key]
            if key in _resolved_tree_data_cache:
                del _resolved_tree_data_cache[key]
        
        # NEW: Also invalidate unified caches
        invalidate_unified_caches_for_tree(tree_id, None)
        
        print(f"[@navigation:cache:invalidate_cache] Invalidated {len(keys_to_remove)} cache entries for tree: {tree_id}")

def invalidate_single_tree_cache_only(tree_id: str, team_id: str):
    """
    Invalidate only the single tree cache, not unified caches
    Used during force refresh when we want to preserve unified caches
    """
    if team_id:
        cache_key = f"{tree_id}_{team_id}"
        if cache_key in _navigation_graphs_cache:
            del _navigation_graphs_cache[cache_key]
            del _cache_timestamps[cache_key]
        if cache_key in _resolved_tree_data_cache:
            del _resolved_tree_data_cache[cache_key]
        
        print(f"[@navigation:cache:invalidate_single_tree_cache_only] Invalidated single tree cache for tree: {tree_id}, team: {team_id}")
    else:
        # Invalidate all caches for this tree_id (if team_id unknown)
        keys_to_remove = [k for k in _navigation_graphs_cache.keys() if k.startswith(f"{tree_id}_")]
        for key in keys_to_remove:
            if key in _navigation_graphs_cache:
                del _navigation_graphs_cache[key]
            if key in _cache_timestamps:
                del _cache_timestamps[key]
            if key in _resolved_tree_data_cache:
                del _resolved_tree_data_cache[key]
        
        print(f"[@navigation:cache:invalidate_single_tree_cache_only] Invalidated {len(keys_to_remove)} single tree cache entries for tree: {tree_id}")

def invalidate_unified_caches_for_tree(tree_id: str, team_id: str = None):
    """
    Invalidate unified caches that contain the specified tree
    
    Args:
        tree_id: Tree ID that was modified
        team_id: Team ID (optional)
    """
    # Find unified caches that need invalidation
    unified_keys_to_remove = []
    hierarchy_keys_to_remove = []
    location_keys_to_remove = []
    
    if team_id:
        # Check specific team's caches
        for cache_key in _unified_graphs_cache.keys():
            if cache_key.endswith(f"_{team_id}"):
                # Check if this unified cache contains the modified tree
                hierarchy_key = cache_key.replace("unified_", "hierarchy_")
                if hierarchy_key in _tree_hierarchy_cache:
                    hierarchy = _tree_hierarchy_cache[hierarchy_key]
                    if tree_id in hierarchy:
                        unified_keys_to_remove.append(cache_key)
                        hierarchy_keys_to_remove.append(hierarchy_key)
                        location_key = cache_key.replace("unified_", "locations_")
                        location_keys_to_remove.append(location_key)
    else:
        # Check all caches for this tree
        for cache_key in _unified_graphs_cache.keys():
            hierarchy_key = cache_key.replace("unified_", "hierarchy_")
            if hierarchy_key in _tree_hierarchy_cache:
                hierarchy = _tree_hierarchy_cache[hierarchy_key]
                if tree_id in hierarchy:
                    unified_keys_to_remove.append(cache_key)
                    hierarchy_keys_to_remove.append(hierarchy_key)
                    location_key = cache_key.replace("unified_", "locations_")
                    location_keys_to_remove.append(location_key)
    
    # Remove invalidated unified caches
    for key in unified_keys_to_remove:
        if key in _unified_graphs_cache:
            del _unified_graphs_cache[key]
        if key in _unified_cache_timestamps:
            del _unified_cache_timestamps[key]
    
    for key in hierarchy_keys_to_remove:
        if key in _tree_hierarchy_cache:
            del _tree_hierarchy_cache[key]
    
    for key in location_keys_to_remove:
        if key in _node_location_cache:
            del _node_location_cache[key]
    
    if unified_keys_to_remove:
        print(f"[@navigation:cache:invalidate_unified_caches_for_tree] Invalidated {len(unified_keys_to_remove)} unified caches containing tree: {tree_id}")

def cleanup_old_caches(max_age_hours: int = 24):
    """
    Clean up old cached graphs to prevent memory bloat
    
    Args:
        max_age_hours: Maximum age of cached graphs in hours
    """
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    
    keys_to_remove = []
    for key, timestamp in _cache_timestamps.items():
        if timestamp < cutoff:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _navigation_graphs_cache[key]
        del _cache_timestamps[key]
    
    if keys_to_remove:
        print(f"[@navigation:cache:cleanup_old_caches] Cleaned up {len(keys_to_remove)} old cached graphs")

def get_cache_stats() -> Dict:
    """
    Get cache statistics for monitoring
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        'total_cached_graphs': len(_navigation_graphs_cache),
        'cache_keys': list(_navigation_graphs_cache.keys()),
        'oldest_cache': min(_cache_timestamps.values()) if _cache_timestamps else None,
        'newest_cache': max(_cache_timestamps.values()) if _cache_timestamps else None
    }

def clear_all_cache():
    """Clear all cached graphs (useful for debugging)"""
    global _navigation_graphs_cache, _cache_timestamps, _resolved_tree_data_cache
    global _unified_graphs_cache, _tree_hierarchy_cache, _node_location_cache, _unified_cache_timestamps
    
    count = len(_navigation_graphs_cache)
    unified_count = len(_unified_graphs_cache)
    
    _navigation_graphs_cache.clear()
    _cache_timestamps.clear()
    _resolved_tree_data_cache.clear()
    
    # NEW: Clear unified caches
    _unified_graphs_cache.clear()
    _tree_hierarchy_cache.clear()
    _node_location_cache.clear()
    _unified_cache_timestamps.clear()
    
    print(f"[@navigation:cache:clear_all_cache] Cleared {count} single-tree caches and {unified_count} unified caches")

def force_refresh_cache(tree_id: str, team_id: str) -> bool:
    """
    Force refresh cache for a specific tree by invalidating and reloading
    Uses the actual tree_id (UUID) returned from save operation
    
    Args:
        tree_id: Navigation tree ID (UUID from database)
        team_id: Team ID for security
        
    Returns:
        True if cache was refreshed successfully
    """
    try:
        print(f"[@navigation:cache:force_refresh_cache] Starting cache refresh for tree: {tree_id}, team: {team_id}")
        
        # Invalidate existing cache (but preserve unified caches)
        invalidate_single_tree_cache_only(tree_id, team_id)
        print(f"[@navigation:cache:force_refresh_cache] Single tree cache invalidated for tree: {tree_id}")
        
        # Reload tree data using the actual tree_id
        try:
            from shared.src.lib.supabase.navigation_trees_db import get_full_tree
            print(f"[@navigation:cache:force_refresh_cache] Calling get_full_tree for tree: {tree_id}")
            
            result = get_full_tree(tree_id, team_id)
            print(f"[@navigation:cache:force_refresh_cache] get_full_tree result: success={result.get('success')}")
            
            if result['success']:
                # Also populate the cache with the retrieved data
                nodes = result.get('nodes', [])
                edges = result.get('edges', [])
                print(f"[@navigation:cache:force_refresh_cache] Retrieved {len(nodes)} nodes and {len(edges)} edges")
                
                # Populate cache using the retrieved data
                graph = populate_cache(tree_id, team_id, nodes, edges)
                if graph:
                    print(f"[@navigation:cache:force_refresh_cache] Successfully refreshed cache for tree: {tree_id}")
                    
                    # Check if unified cache exists and preserve it
                    try:
                        unified_cache_key = f"unified_{tree_id}_{team_id}"
                        if unified_cache_key in _unified_graphs_cache:
                            print(f"[@navigation:cache:force_refresh_cache] Preserving existing unified cache for tree: {tree_id}")
                        else:
                            print(f"[@navigation:cache:force_refresh_cache] No unified cache found for tree: {tree_id}")
                    except Exception as unified_error:
                        print(f"[@navigation:cache:force_refresh_cache] Error checking unified cache: {unified_error}")
                    
                    return True
                else:
                    print(f"[@navigation:cache:force_refresh_cache] Failed to populate cache after retrieving tree data")
                    return False
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"[@navigation:cache:force_refresh_cache] Failed to reload tree: {error_msg}")
                return False
                
        except ImportError as ie:
            print(f"[@navigation:cache:force_refresh_cache] Import error: {ie}")
            return False
        except Exception as e:
            print(f"[@navigation:cache:force_refresh_cache] Error reloading tree: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"[@navigation:cache:force_refresh_cache] Error refreshing cache: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_cached_tree_data(tree_id: str, team_id: str) -> Optional[Dict]:
    """
    Get cached resolved tree data (nodes and edges with resolved objects)
    
    Args:
        tree_id: Navigation tree ID (name or UUID)
        team_id: Team ID for security
        
    Returns:
        Dictionary with 'nodes' and 'edges' containing resolved objects, or None if not cached
    """
    cache_key = f"{tree_id}_{team_id}"
    
    if cache_key in _resolved_tree_data_cache:
        print(f"[@navigation:cache:get_cached_tree_data] Using cached resolved tree data for tree: {tree_id}")
        return _resolved_tree_data_cache[cache_key]
    
    print(f"[@navigation:cache:get_cached_tree_data] No cached resolved tree data found for tree: {tree_id}")
    return None

# NEW: Unified graph caching functions for nested trees

def get_cached_unified_graph(root_tree_id: str, team_id: str) -> Optional[nx.DiGraph]:
    """
    Get cached unified NetworkX graph including all nested trees
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        
    Returns:
        Unified NetworkX directed graph or None if not cached
    """
    cache_key = f"unified_{root_tree_id}_{team_id}"
    
    if cache_key in _unified_graphs_cache:
        print(f"[@navigation:cache:get_cached_unified_graph] Using cached unified graph for root tree: {root_tree_id}")
        return _unified_graphs_cache[cache_key]
    
    print(f"[@navigation:cache:get_cached_unified_graph] No cached unified graph found for root tree: {root_tree_id}")
    return None

def populate_unified_cache(root_tree_id: str, team_id: str, all_trees_data: List[Dict]) -> Optional[nx.DiGraph]:
    """
    Build and cache unified graph with all nested trees
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        all_trees_data: List of tree data dicts with nodes and edges
        
    Returns:
        Unified NetworkX directed graph or None if failed
    """
    cache_key = f"unified_{root_tree_id}_{team_id}"
    
    try:
        print(f"[@navigation:cache:populate_unified_cache] Building unified graph for root tree: {root_tree_id}")
        
        from src.lib.utils.navigation_graph import create_unified_networkx_graph
        
        if not all_trees_data:
            print(f"[@navigation:cache:populate_unified_cache] No tree data provided for root tree: {root_tree_id}")
            return None
        
        # Build unified NetworkX graph with cross-tree edges
        print(f"[@navigation:cache:populate_unified_cache] Creating unified graph with {len(all_trees_data)} trees")
        unified_graph = create_unified_networkx_graph(all_trees_data)
        
        if not unified_graph:
            print(f"[@navigation:cache:populate_unified_cache] create_unified_networkx_graph returned None")
            return None
        
        # Cache the unified graph
        _unified_graphs_cache[cache_key] = unified_graph
        _unified_cache_timestamps[cache_key] = datetime.now()
        
        # Build and cache node location index
        node_location_map = {}
        tree_hierarchy = {}
        
        for tree_data in all_trees_data:
            tree_id = tree_data.get('tree_id')
            tree_info = tree_data.get('tree_info', {})
            nodes = tree_data.get('nodes', [])
            
            # Index node locations
            for node in nodes:
                node_id = node.get('node_id')
                if node_id:
                    node_location_map[node_id] = tree_id
            
            # Build hierarchy metadata
            tree_hierarchy[tree_id] = {
                'tree_id': tree_id,
                'name': tree_info.get('name', ''),
                'parent_tree_id': tree_info.get('parent_tree_id'),
                'parent_node_id': tree_info.get('parent_node_id'),
                'tree_depth': tree_info.get('tree_depth', 0),
                'is_root_tree': tree_info.get('is_root_tree', False)
            }
        
        # Cache metadata
        hierarchy_cache_key = f"hierarchy_{root_tree_id}_{team_id}"
        location_cache_key = f"locations_{root_tree_id}_{team_id}"
        
        _tree_hierarchy_cache[hierarchy_cache_key] = tree_hierarchy
        _node_location_cache[location_cache_key] = node_location_map
        
        print(f"[@navigation:cache:populate_unified_cache] Successfully cached unified graph with {len(unified_graph.nodes)} nodes and {len(unified_graph.edges)} edges")
        print(f"[@navigation:cache:populate_unified_cache] Cached {len(node_location_map)} node locations across {len(tree_hierarchy)} trees")
        
        return unified_graph
        
    except Exception as e:
        print(f"[@navigation:cache:populate_unified_cache] Error building unified graph: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_node_tree_location(node_id: str, root_tree_id: str, team_id: str) -> Optional[str]:
    """
    Find which tree contains a specific node
    
    Args:
        node_id: Node identifier to locate
        root_tree_id: Root tree ID for the hierarchy
        team_id: Team ID for security
        
    Returns:
        Tree ID containing the node or None if not found
    """
    location_cache_key = f"locations_{root_tree_id}_{team_id}"
    
    if location_cache_key in _node_location_cache:
        node_locations = _node_location_cache[location_cache_key]
        tree_id = node_locations.get(node_id)
        if tree_id:
            print(f"[@navigation:cache:get_node_tree_location] Node {node_id} found in tree: {tree_id}")
            return tree_id
    
    print(f"[@navigation:cache:get_node_tree_location] Node {node_id} not found in location cache")
    return None

def get_tree_hierarchy_metadata(root_tree_id: str, team_id: str) -> Optional[Dict]:
    """
    Get cached tree hierarchy metadata
    
    Args:
        root_tree_id: Root tree ID
        team_id: Team ID for security
        
    Returns:
        Tree hierarchy metadata dict or None if not cached
    """
    hierarchy_cache_key = f"hierarchy_{root_tree_id}_{team_id}"
    
    if hierarchy_cache_key in _tree_hierarchy_cache:
        print(f"[@navigation:cache:get_tree_hierarchy_metadata] Using cached hierarchy for root tree: {root_tree_id}")
        return _tree_hierarchy_cache[hierarchy_cache_key]
    
    print(f"[@navigation:cache:get_tree_hierarchy_metadata] No cached hierarchy found for root tree: {root_tree_id}")
    return None 