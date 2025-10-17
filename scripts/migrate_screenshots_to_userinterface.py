#!/usr/bin/env python3
"""
Screenshot Migration Script: device_model → userinterface

This script migrates navigation screenshots from device_model-based paths to userinterface-based paths.

Current structure:  navigation/{device_model}/{filename}.jpg
New structure:      navigation/{userinterface_name}/{filename}.jpg

Example:
  FROM: navigation/android_mobile/Home.jpg
  TO:   navigation/horizon_android_mobile/Home.jpg
  
  FROM: navigation/host_vnc/welcome.jpg (iad_gui tree)
  TO:   navigation/iad_gui/welcome.jpg

This script:
1. Queries database to build device_model → userinterface mapping
2. Copies files in R2 to new userinterface paths
3. Updates database URLs to point to new paths
4. Keeps old files as backup (can be deleted after verification)
"""

import os
import sys
from typing import Dict, List, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
from shared.src.lib.utils.app_utils import get_team_id


def get_migration_mapping() -> Tuple[Dict[str, Dict], Dict]:
    """
    Query database to build mapping of screenshot URLs to their new paths.
    
    Returns:
        Tuple of (migration_map, stats)
    """
    supabase = get_supabase_client()
    team_id = get_team_id()
    
    print("📊 [Migration] Querying database for screenshot mapping...")
    
    # Get all navigation trees with their userinterface
    trees_result = supabase.table('navigation_trees').select(
        'id, name, userinterface_id, userinterfaces(name, models)'
    ).eq('team_id', team_id).execute()
    
    # Build tree_id -> userinterface_name mapping
    tree_to_ui = {}
    for tree in trees_result.data:
        if tree.get('userinterfaces'):
            tree_to_ui[tree['id']] = tree['userinterfaces']['name']
    
    # Get all nodes with screenshots
    nodes_result = supabase.table('navigation_nodes').select(
        'id, node_id, label, data, tree_id'
    ).eq('team_id', team_id).execute()
    
    migration_map = {}
    stats = {
        'total_screenshots': 0,
        'by_userinterface': {},
        'by_device_model': {}
    }
    
    for node in nodes_result.data:
        node_data = node.get('data', {})
        old_url = node_data.get('screenshot')
        
        if not old_url or not old_url.strip():
            continue
        
        if 'navigation/' not in old_url:
            continue
        
        tree_id = node['tree_id']
        userinterface_name = tree_to_ui.get(tree_id)
        
        if not userinterface_name:
            print(f"⚠️  [Migration] Node {node['label']} has no userinterface mapping (tree_id: {tree_id})")
            continue
        
        # Extract old path segment (device_model)
        # URL format: https://.../navigation/{device_model}/{filename}
        url_parts = old_url.split('/navigation/')
        if len(url_parts) != 2:
            print(f"⚠️  [Migration] Skipping malformed URL: {old_url}")
            continue
        
        path_parts = url_parts[1].split('/', 1)
        if len(path_parts) != 2:
            print(f"⚠️  [Migration] Skipping malformed path: {url_parts[1]}")
            continue
        
        old_device_model = path_parts[0]
        filename = path_parts[1]
        
        # Build new URL
        base_url = url_parts[0]
        new_url = f"{base_url}/navigation/{userinterface_name}/{filename}"
        
        migration_map[old_url] = {
            'new_url': new_url,
            'userinterface_name': userinterface_name,
            'old_device_model': old_device_model,
            'filename': filename,
            'node_id': node['id'],
            'node_label': node['label']
        }
        
        # Update stats
        stats['total_screenshots'] += 1
        stats['by_userinterface'][userinterface_name] = stats['by_userinterface'].get(userinterface_name, 0) + 1
        stats['by_device_model'][old_device_model] = stats['by_device_model'].get(old_device_model, 0) + 1
    
    print(f"\n✅ [Migration] Found {stats['total_screenshots']} screenshots to migrate")
    print(f"\n📁 Current paths (by device_model):")
    for device_model, count in sorted(stats['by_device_model'].items()):
        print(f"   - {device_model}: {count} files")
    
    print(f"\n📁 New paths (by userinterface):")
    for ui_name, count in sorted(stats['by_userinterface'].items()):
        print(f"   - {ui_name}: {count} files")
    
    return migration_map, stats


def copy_files_in_r2(migration_map: Dict) -> Tuple[List[str], List[str]]:
    """
    Copy files in R2 from old paths to new paths.
    
    Returns:
        Tuple of (successful_urls, failed_urls)
    """
    print("\n📦 [Migration] Starting R2 file copy...")
    
    cloudflare = get_cloudflare_utils()
    successful = []
    failed = []
    
    # Group by userinterface for cleaner logging
    by_ui = {}
    for old_url, mapping in migration_map.items():
        ui_name = mapping['userinterface_name']
        if ui_name not in by_ui:
            by_ui[ui_name] = []
        by_ui[ui_name].append((old_url, mapping))
    
    for ui_name, urls in sorted(by_ui.items()):
        print(f"\n   📂 Copying to {ui_name}/ ({len(urls)} files)")
        
        for old_url, mapping in urls:
            old_path = f"navigation/{mapping['old_device_model']}/{mapping['filename']}"
            new_path = f"navigation/{mapping['userinterface_name']}/{mapping['filename']}"
            
            try:
                # Copy file in R2 (this will use the cloudflare utility to copy)
                result = cloudflare.copy_file(old_path, new_path)
                
                if result.get('success'):
                    successful.append(old_url)
                    print(f"      ✅ {mapping['filename']}")
                else:
                    failed.append(old_url)
                    print(f"      ❌ {mapping['filename']}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed.append(old_url)
                print(f"      ❌ {mapping['filename']}: {str(e)}")
    
    print(f"\n✅ [Migration] R2 copy complete: {len(successful)} succeeded, {len(failed)} failed")
    
    return successful, failed


def update_database_urls(migration_map: Dict, successful_urls: List[str]) -> Tuple[int, int]:
    """
    Update navigation_nodes.data.screenshot URLs to point to new paths.
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    print("\n🗄️  [Migration] Updating database URLs...")
    
    supabase = get_supabase_client()
    successful_count = 0
    failed_count = 0
    
    for old_url in successful_urls:
        if old_url not in migration_map:
            continue
        
        mapping = migration_map[old_url]
        node_id = mapping['node_id']
        new_url = mapping['new_url']
        node_label = mapping['node_label']
        
        try:
            # Get current node data
            node_result = supabase.table('navigation_nodes').select('data').eq('id', node_id).single().execute()
            
            if not node_result.data:
                failed_count += 1
                print(f"   ❌ Node not found: {node_label}")
                continue
            
            # Update the screenshot URL in the data JSONB
            current_data = node_result.data['data']
            current_data['screenshot'] = new_url
            
            # Update the node
            update_result = supabase.table('navigation_nodes').update({
                'data': current_data
            }).eq('id', node_id).execute()
            
            if update_result.data:
                successful_count += 1
                print(f"   ✅ Updated: {node_label}")
            else:
                failed_count += 1
                print(f"   ❌ Failed to update: {node_label}")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error updating {node_label}: {str(e)}")
    
    print(f"\n✅ [Migration] Database update complete: {successful_count} succeeded, {failed_count} failed")
    
    return successful_count, failed_count


def main():
    """Main migration execution."""
    print("=" * 80)
    print("🚀 Screenshot Migration: device_model → userinterface")
    print("=" * 80)
    
    try:
        # Step 1: Build migration mapping
        migration_map, stats = get_migration_mapping()
        
        if not migration_map:
            print("\n⚠️  No screenshots found to migrate. Exiting.")
            return
        
        # Step 2: Confirm migration
        print("\n" + "=" * 80)
        print("⚠️  MIGRATION PLAN:")
        print("=" * 80)
        print(f"This will:")
        print(f"1. Copy {stats['total_screenshots']} files in R2 to new userinterface paths")
        print(f"2. Update {stats['total_screenshots']} database URLs")
        print(f"3. Keep original files as backup (not deleted)")
        print("\nPress ENTER to continue or Ctrl+C to cancel...")
        input()
        
        # Step 3: Copy files in R2
        successful_urls, failed_urls = copy_files_in_r2(migration_map)
        
        if failed_urls:
            print(f"\n⚠️  Warning: {len(failed_urls)} files failed to copy in R2")
            print("Only updating database for successfully copied files...")
        
        # Step 4: Update database URLs
        db_success, db_failed = update_database_urls(migration_map, successful_urls)
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print(f"R2 Files:     {len(successful_urls)}/{stats['total_screenshots']} copied")
        print(f"Database:     {db_success}/{len(successful_urls)} updated")
        if failed_urls:
            print(f"\n⚠️  Failed URLs: {len(failed_urls)}")
            for url in failed_urls[:5]:
                print(f"   - {url}")
            if len(failed_urls) > 5:
                print(f"   ... and {len(failed_urls) - 5} more")
        
        print("\n📝 Next steps:")
        print("1. Verify screenshots are accessible in the UI")
        print("2. Update code to use userinterface_name (see code changes)")
        print("3. After verification, old files can be deleted from R2")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

