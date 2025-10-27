"""
Unified Executable Routes - Scripts and Testcases
Provides a unified API for listing and organizing both scripts and testcases
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.database.testcase_db import list_testcases
from shared.src.lib.database.folder_tag_db import (
    list_all_folders,
    list_all_tags,
    get_executable_tags
)
from backend_server.src.lib.utils.script_utils import list_available_scripts

server_executable_bp = Blueprint('server_executable', __name__, url_prefix='/server/executable')


@server_executable_bp.route('/list', methods=['GET'])
def list_executables():
    """
    Unified endpoint to list both scripts and testcases organized by folders.
    
    Query params:
        - team_id: Team identifier (automatically added by frontend buildServerUrl)
        - folder: Filter by folder name
        - tags: Comma-separated tag names to filter by
        - search: Search query for name/description
    
    Note: This endpoint does NOT require host_name since it only lists available
    executables, not executing them. Execution requires host_name separately.
    
    Returns:
        {
            "success": true,
            "folders": [
                {
                    "id": 1,
                    "name": "Navigation",
                    "items": [
                        {
                            "type": "script",
                            "id": "goto.py",
                            "name": "Go to channel",
                            "description": "...",
                            "tags": []
                        },
                        {
                            "type": "testcase",
                            "id": "tc_uuid",
                            "name": "Navigate EPG grid",
                            "tags": ["smoke"],
                            "userinterface": "android_tv"
                        }
                    ]
                }
            ],
            "all_tags": [{tag_id, name, color}, ...],
            "all_folders": ["(Root)", "Navigation", ...]
        }
    """
    try:
        # Get team_id from query params (automatically added by buildServerUrl)
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get filter parameters
        filter_folder = request.args.get('folder')
        filter_tags = request.args.get('tags', '').split(',') if request.args.get('tags') else []
        search_query = request.args.get('search', '').lower()
        
        # Get all folders and tags from database (for test cases)
        all_folders = list_all_folders()
        all_tags = list_all_tags()
        
        # Get scripts from filesystem (includes subfolder paths like "gw/smartping")
        available_scripts = list_available_scripts()
        
        # Get testcases from database
        testcases = list_testcases(team_id)
        
        # Build folder structure
        # Use a dict with folder name as key for easy lookup
        folder_map = {}
        
        # Initialize folders from database (for test cases)
        for folder in all_folders:
            folder_map[folder['name']] = {
                'id': folder['folder_id'],
                'name': folder['name'],
                'items': []
            }
        
        # Process scripts - extract folder from filesystem path
        for script in available_scripts:
            # Parse folder from script path (e.g., "gw/smartping" -> folder="gw", name="smartping")
            if '/' in script:
                folder_name, script_name = script.rsplit('/', 1)
                script_display = f"{script}.py"
                display_name = script_name.replace('_', ' ').title()
            else:
                folder_name = 'Root'
                script_name = script
                script_display = f"{script}.py"
                display_name = script.replace('_', ' ').title()
            
            # Get tags for this script
            script_tags = get_executable_tags('script', script_display)
            tag_names = [tag['name'] for tag in script_tags]
            
            # Apply filters
            if filter_folder and filter_folder != folder_name:
                continue
            
            if filter_tags and not any(tag in tag_names for tag in filter_tags):
                continue
            
            if search_query and search_query not in script_display.lower() and search_query not in display_name.lower():
                continue
            
            # Create script item
            script_item = {
                'type': 'script',
                'id': script_display,
                'name': display_name,
                'description': f'Execute {script_name}',
                'tags': tag_names
            }
            
            # Ensure folder exists in map
            if folder_name not in folder_map:
                # Create dynamic folder for filesystem folders not in database
                folder_id = hash(folder_name) % 10000  # Simple hash for ID
                folder_map[folder_name] = {
                    'id': folder_id,
                    'name': folder_name,
                    'items': []
                }
            
            folder_map[folder_name]['items'].append(script_item)
        
        # Process testcases - use database folder_id
        for testcase in testcases:
            folder_id = testcase.get('folder_id', 0)
            
            # Get folder name from database
            folder_name = next((f['name'] for f in all_folders if f['folder_id'] == folder_id), 'Root')
            
            # Get tags for this testcase
            tc_tags = get_executable_tags('testcase', testcase['testcase_id'])
            tag_names = [tag['name'] for tag in tc_tags]
            
            # Apply filters
            if filter_folder and folder_name != filter_folder:
                continue
            
            if filter_tags and not any(tag in tag_names for tag in filter_tags):
                continue
            
            if search_query and search_query not in testcase['testcase_name'].lower():
                continue
            
            # Create testcase item
            testcase_item = {
                'type': 'testcase',
                'id': testcase['testcase_id'],
                'name': testcase['testcase_name'],
                'description': testcase.get('description', ''),
                'tags': tag_names,
                'userinterface': testcase.get('userinterface_name'),
                'created_at': testcase.get('created_at')
            }
            
            # Ensure folder exists in map
            if folder_name not in folder_map:
                folder_map[folder_name] = {
                    'id': folder_id,
                    'name': folder_name,
                    'items': []
                }
            
            folder_map[folder_name]['items'].append(testcase_item)
        
        # Convert to list and filter out empty folders
        folders = [folder for folder in folder_map.values() if len(folder['items']) > 0]
        
        # Sort folders by name (Root first, then alphabetical)
        folders.sort(key=lambda f: (f['name'] != 'Root', f['name'].lower()))
        
        # Get all unique folder names for the filter dropdown
        all_folder_names = sorted(set(folder_map.keys()))
        # Ensure Root is first
        if 'Root' in all_folder_names:
            all_folder_names.remove('Root')
            all_folder_names = ['Root'] + all_folder_names
        
        return jsonify({
            'success': True,
            'folders': folders,
            'all_tags': all_tags,
            'all_folders': all_folder_names
        })
        
    except Exception as e:
        print(f"[@server_executable:list] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

