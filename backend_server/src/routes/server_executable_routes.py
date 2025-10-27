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
        
        # Get all folders and tags
        all_folders = list_all_folders()
        all_tags = list_all_tags()
        
        # Get scripts from filesystem
        available_scripts = list_available_scripts()
        
        # Get testcases from database
        testcases = list_testcases(team_id)
        
        # Build folder structure
        folder_map = {}
        
        # Initialize folders
        for folder in all_folders:
            folder_map[folder['folder_id']] = {
                'id': folder['folder_id'],
                'name': folder['name'],
                'items': []
            }
        
        # Add scripts to folders (scripts don't have folder info in DB yet, all go to root)
        for script in available_scripts:
            # Get tags for this script
            script_tags = get_executable_tags('script', f"{script}.py")
            tag_names = [tag['name'] for tag in script_tags]
            
            # Apply filters
            if filter_folder and filter_folder != '(Root)':
                continue  # Skip scripts not in filtered folder (scripts are in root)
            
            if filter_tags and not any(tag in tag_names for tag in filter_tags):
                continue
            
            script_display = f"{script}.py"
            if search_query and search_query not in script_display.lower():
                continue
            
            # Add to root folder
            script_item = {
                'type': 'script',
                'id': script_display,
                'name': script.replace('_', ' ').title(),
                'description': f'Execute {script}',
                'tags': tag_names
            }
            
            if 0 in folder_map:
                folder_map[0]['items'].append(script_item)
        
        # Add testcases to folders
        for testcase in testcases:
            folder_id = testcase.get('folder_id', 0)
            
            # Get tags for this testcase
            tc_tags = get_executable_tags('testcase', testcase['testcase_id'])
            tag_names = [tag['name'] for tag in tc_tags]
            
            # Apply filters
            if filter_folder:
                folder_name = next((f['name'] for f in all_folders if f['folder_id'] == folder_id), '(Root)')
                if folder_name != filter_folder:
                    continue
            
            if filter_tags and not any(tag in tag_names for tag in filter_tags):
                continue
            
            if search_query and search_query not in testcase['testcase_name'].lower():
                continue
            
            # Add to appropriate folder
            testcase_item = {
                'type': 'testcase',
                'id': testcase['testcase_id'],
                'name': testcase['testcase_name'],
                'description': testcase.get('description', ''),
                'tags': tag_names,
                'userinterface': testcase.get('userinterface_name'),
                'created_at': testcase.get('created_at')
            }
            
            if folder_id in folder_map:
                folder_map[folder_id]['items'].append(testcase_item)
        
        # Convert to list and filter out empty folders
        folders = [folder for folder in folder_map.values() if len(folder['items']) > 0]
        
        # Sort folders by name (Root first, then alphabetical)
        folders.sort(key=lambda f: (f['name'] != '(Root)', f['name']))
        
        return jsonify({
            'success': True,
            'folders': folders,
            'all_tags': all_tags,
            'all_folders': [f['name'] for f in all_folders]
        })
        
    except Exception as e:
        print(f"[@server_executable:list] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

