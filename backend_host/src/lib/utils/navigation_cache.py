"""
Unified Navigation Graph Caching System
Manages in-memory cache of NetworkX graphs for nested tree navigation
"""

import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import os
import pickle

# Import cache config from shared
from shared.src.lib.config.constants import CACHE_CONFIG
CACHE_TTL = CACHE_CONFIG['LONG_TTL']  # 24 hours
CACHE_DIR = "/tmp/nav_cache"

# Unified graph caching for nested trees (single cache system)
_unified_graphs_cache: Dict[str, nx.DiGraph] = {}      # Unified graphs with nested trees
_tree_hierarchy_cache: Dict[str, Dict] = {}            # Tree hierarchy metadata
_node_location_cache: Dict[str, str] = {}              # node_id -> tree_id mapping
_unified_cache_timestamps: Dict[str, datetime] = {}

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cached_unified_graph(root_tree_id: str, team_id: str) -> Optional[nx.DiGraph]:
    """
    Get cached unified NetworkX graph - checks file cache (shared across processes)
    """
    if not root_tree_id or not team_id:
        return None
    
    cache_key = f"unified_{root_tree_id}_{team_id}"
    cache_file = f"{CACHE_DIR}/{cache_key}.pkl"
    
    # Check file cache (works across processes)
    if os.path.exists(cache_file):
        try:
            file_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if file_age < CACHE_TTL:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                print(f"[@navigation:cache:get_cached_unified_graph] ✅ File Cache HIT: {cache_key} (age: {file_age:.1f}s)")
                return cached_data['graph']
            else:
                os.remove(cache_file)  # Expired
                print(f"[@navigation:cache:get_cached_unified_graph] Cache expired, removed: {cache_key}")
        except Exception as e:
            print(f"[@navigation:cache:get_cached_unified_graph] Error reading cache: {e}")
    
    print(f"[@navigation:cache:get_cached_unified_graph] ❌ Cache MISS: {cache_key}")
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
    Build and cache unified graph - saves to file (shared across processes)
    """
    cache_key = f"unified_{root_tree_id}_{team_id}"
    cache_file = f"{CACHE_DIR}/{cache_key}.pkl"
    
    try:
        from  backend_host.src.lib.utils.navigation_graph import create_unified_networkx_graph
        
        if not all_trees_data:
            return None
        
        unified_graph = create_unified_networkx_graph(all_trees_data)
        if not unified_graph:
            return None
        
        # Save to file cache (accessible by all processes)
        cache_data = {'graph': unified_graph, 'timestamp': datetime.now()}
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        print(f"[@navigation:cache:populate_unified_cache] ✅ Cached to file: {cache_key} ({len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges)")
        return unified_graph
        
    except Exception as e:
        print(f"[@navigation:cache:populate_unified_cache] Error: {e}")
        return None

def save_unified_cache(root_tree_id: str, team_id: str, graph: nx.DiGraph) -> bool:
    """
    Save existing unified graph to file cache (incremental update)
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        graph: NetworkX graph to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    cache_key = f"unified_{root_tree_id}_{team_id}"
    cache_file = f"{CACHE_DIR}/{cache_key}.pkl"
    
    try:
        cache_data = {'graph': graph, 'timestamp': datetime.now()}
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        print(f"[@navigation:cache:save_unified_cache] ✅ Saved graph to file: {cache_key} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
        return True
        
    except Exception as e:
        print(f"[@navigation:cache:save_unified_cache] Error: {e}")
        return False

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
    """Clear both in-memory and file caches"""
    if root_tree_id and team_id:
        cache_key = f"unified_{root_tree_id}_{team_id}"
        
        # Clear in-memory cache
        if cache_key in _unified_graphs_cache:
            del _unified_graphs_cache[cache_key]
        if cache_key in _unified_cache_timestamps:
            del _unified_cache_timestamps[cache_key]
        if cache_key in _tree_hierarchy_cache:
            del _tree_hierarchy_cache[cache_key]
        
        # Clear file cache
        cache_file = f"{CACHE_DIR}/{cache_key}.pkl"
        if os.path.exists(cache_file):
            os.remove(cache_file)
        
        print(f"[@navigation:cache:clear_unified_cache] Cleared in-memory + file cache for tree: {root_tree_id}")
    else:
        # Clear all in-memory caches
        _unified_graphs_cache.clear()
        _unified_cache_timestamps.clear()
        _tree_hierarchy_cache.clear()
        _node_location_cache.clear()
        
        # Clear all file caches
        for f in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, f))
        
        print(f"[@navigation:cache:clear_unified_cache] Cleared ALL in-memory + file caches")

def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics from files"""
    cached_files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')]
    return {
        'cache_type': 'File',
        'cached_graphs': len(cached_files),
        'cache_dir': CACHE_DIR
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