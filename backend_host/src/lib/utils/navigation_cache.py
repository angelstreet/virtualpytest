"""
Unified Navigation Graph Caching System
Manages in-memory cache of NetworkX graphs for nested tree navigation
"""

import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import os

# Cache TTL in seconds (24 hours)
CACHE_TTL = 86400

# Unified graph caching for nested trees (single cache system)
_unified_graphs_cache: Dict[str, nx.DiGraph] = {}      # Unified graphs with nested trees
_tree_hierarchy_cache: Dict[str, Dict] = {}            # Tree hierarchy metadata
_node_location_cache: Dict[str, str] = {}              # node_id -> tree_id mapping
_unified_cache_timestamps: Dict[str, datetime] = {}

def get_cached_unified_graph(root_tree_id: str, team_id: str) -> Optional[nx.DiGraph]:
    """
    Get cached unified NetworkX graph including all nested trees
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        
    Returns:
        Unified NetworkX directed graph or None if not cached
    """
    # Validate inputs to provide better error messages
    if root_tree_id is None:
        print(f"❌ [@navigation:cache:get_cached_unified_graph] ERROR: root_tree_id is None!")
        print(f"💡 This usually means the navigation tree was not loaded properly.")
        print(f"💡 SOLUTION: Use navigate_to() helper or call load_navigation_tree() first")
        return None
    
    if team_id is None:
        print(f"❌ [@navigation:cache:get_cached_unified_graph] ERROR: team_id is None for tree {root_tree_id}!")
        print(f"💡 This usually means the script context was not set up properly.")
        return None
    
    cache_key = f"unified_{root_tree_id}_{team_id}"
    
    if cache_key in _unified_graphs_cache:
        # Check if cache has a timestamp
        cache_time = _unified_cache_timestamps.get(cache_key)
        
        if not cache_time:
            # Cache exists but has no timestamp - this is a bug, but recover by setting timestamp
            print(f"[@navigation:cache:get_cached_unified_graph] ⚠️ Cache exists but missing timestamp for tree {root_tree_id}, setting timestamp now")
            _unified_cache_timestamps[cache_key] = datetime.now()
            return _unified_graphs_cache[cache_key]
        
        # Check if cache is still valid (24-hour TTL)
        age_seconds = (datetime.now() - cache_time).total_seconds()
        if age_seconds < CACHE_TTL:
            return _unified_graphs_cache[cache_key]
        else:
            # Cache expired - remove it
            print(f"[@navigation:cache:get_cached_unified_graph] Cache expired for root tree: {root_tree_id} (age: {age_seconds/3600:.1f}h), removing")
            _unified_graphs_cache.pop(cache_key, None)
            _unified_cache_timestamps.pop(cache_key, None)
            # Also clear related hierarchy cache
            hierarchy_key = f"hierarchy_{root_tree_id}_{team_id}"
            _tree_hierarchy_cache.pop(hierarchy_key, None)
    
    print(f"[@navigation:cache:get_cached_unified_graph] No cached unified graph found for root tree: {root_tree_id}")
    return None

def refresh_cache_timestamp(root_tree_id: str, team_id: str) -> bool:
    """
    Refresh the timestamp for an existing cache entry to prevent TTL expiry
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        
    Returns:
        True if timestamp was refreshed, False if cache doesn't exist
    """
    cache_key = f"unified_{root_tree_id}_{team_id}"
    
    if cache_key in _unified_graphs_cache:
        _unified_cache_timestamps[cache_key] = datetime.now()
        print(f"[@navigation:cache:refresh_cache_timestamp] Refreshed timestamp for tree {root_tree_id}")
        return True
    
    return False

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
        from  backend_host.src.lib.utils.navigation_graph import create_unified_networkx_graph
        
        if not all_trees_data:
            return None
        
        # Build unified NetworkX graph with cross-tree edges
        unified_graph = create_unified_networkx_graph(all_trees_data)
        
        if not unified_graph:
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
        _tree_hierarchy_cache[hierarchy_cache_key] = tree_hierarchy
        
        # Cache node location mapping
        location_cache_key = f"locations_{root_tree_id}_{team_id}"
        _node_location_cache[location_cache_key] = node_location_map
        
        print(f"[@navigation:cache:populate_unified_cache] Successfully cached unified graph: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
        print(f"[@navigation:cache:populate_unified_cache] Cached hierarchy for {len(tree_hierarchy)} trees")
        print(f"[@navigation:cache:populate_unified_cache] Cached location mapping for {len(node_location_map)} nodes")
        
        return unified_graph
        
    except Exception as e:
        print(f"[@navigation:cache:populate_unified_cache] Error building unified graph for root tree {root_tree_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_node_tree_location(node_id: str, root_tree_id: str, team_id: str) -> Optional[str]:
    """
    Get which tree a node belongs to in the unified hierarchy
    
    Args:
        node_id: Node ID to locate
        root_tree_id: Root tree ID for the hierarchy
        team_id: Team ID for security
        
    Returns:
        Tree ID containing the node or None if not found
    """
    location_cache_key = f"locations_{root_tree_id}_{team_id}"
    node_location_map = _node_location_cache.get(location_cache_key, {})
    return node_location_map.get(node_id)

def get_tree_hierarchy_metadata(root_tree_id: str, team_id: str) -> Optional[Dict]:
    """
    Get tree hierarchy metadata for the unified cache
    
    Args:
        root_tree_id: Root tree ID
        team_id: Team ID for security
        
    Returns:
        Dictionary of tree hierarchy metadata or None if not cached
    """
    hierarchy_cache_key = f"hierarchy_{root_tree_id}_{team_id}"
    return _tree_hierarchy_cache.get(hierarchy_cache_key)

def clear_unified_cache(root_tree_id: str = None, team_id: str = None):
    """
    Clear unified cache entries
    
    Args:
        root_tree_id: Specific root tree to clear (if None, clears all)
        team_id: Team ID for security (if None with root_tree_id, clears all teams)
    """
    if root_tree_id and team_id:
        # Clear specific tree
        cache_key = f"unified_{root_tree_id}_{team_id}"
        hierarchy_key = f"hierarchy_{root_tree_id}_{team_id}"
        location_key = f"locations_{root_tree_id}_{team_id}"
        
        _unified_graphs_cache.pop(cache_key, None)
        _unified_cache_timestamps.pop(cache_key, None)
        _tree_hierarchy_cache.pop(hierarchy_key, None)
        _node_location_cache.pop(location_key, None)
        
        print(f"[@navigation:cache:clear_unified_cache] Cleared cache for tree: {root_tree_id}")
    else:
        # Clear all caches
        _unified_graphs_cache.clear()
        _unified_cache_timestamps.clear()
        _tree_hierarchy_cache.clear()
        _node_location_cache.clear()
        
        print(f"[@navigation:cache:clear_unified_cache] Cleared all unified caches")

def get_cache_stats() -> Dict[str, int]:
    """
    Get unified cache statistics
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        'unified_graphs': len(_unified_graphs_cache),
        'hierarchy_metadata': len(_tree_hierarchy_cache),
        'node_locations': len(_node_location_cache),
        'total_cached_items': len(_unified_graphs_cache) + len(_tree_hierarchy_cache) + len(_node_location_cache)
    }

# Backward compatibility aliases (deprecated - use unified functions directly)
def get_cached_graph(tree_id: str, team_id: str, force_rebuild: bool = False) -> Optional[nx.DiGraph]:
    """
    DEPRECATED: Use get_cached_unified_graph instead
    Backward compatibility wrapper for legacy code
    """
    print(f"⚠️  [@navigation:cache:get_cached_graph] DEPRECATED: Use get_cached_unified_graph instead")
    return get_cached_unified_graph(tree_id, team_id)

def populate_cache(tree_id: str, team_id: str, nodes: List[Dict], edges: List[Dict]) -> Optional[nx.DiGraph]:
    """
    DEPRECATED: Use populate_unified_cache instead
    Backward compatibility wrapper for legacy code
    """
    print(f"⚠️  [@navigation:cache:populate_cache] DEPRECATED: Use populate_unified_cache instead")
    
    # Convert single tree to unified format
    tree_data_for_unified = [{
        'tree_id': tree_id,
        'tree_info': {
            'name': f'Tree {tree_id}',
            'is_root_tree': True,
            'tree_depth': 0,
            'parent_tree_id': None,
            'parent_node_id': None
        },
        'nodes': nodes,
        'edges': edges
    }]
    
    return populate_unified_cache(tree_id, team_id, tree_data_for_unified)