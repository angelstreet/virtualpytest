"""
Server Requirements Routes - Requirements management operations

This module handles requirements CRUD operations and linkage to testcases/scripts.
Follows the same pattern as server_testcase_routes.py
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.database.requirements_db import (
    create_requirement,
    get_requirement,
    get_requirement_by_code,
    update_requirement,
    list_requirements,
    link_testcase_to_requirement,
    unlink_testcase_from_requirement,
    get_testcase_requirements,
    link_script_to_requirement,
    unlink_script_from_requirement,
    get_script_requirements,
    get_requirement_coverage,
    get_coverage_summary,
    get_uncovered_requirements,
    get_available_testcases_for_requirement,
    get_requirement_coverage_counts
)

server_requirements_bp = Blueprint('server_requirements', __name__, url_prefix='/server/requirements')


# ================================================
# Requirements CRUD
# ================================================

@server_requirements_bp.route('/create', methods=['POST'])
def requirements_create():
    """Create a new requirement"""
    try:
        data = request.get_json()
        team_id = data.get('team_id') or request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        requirement_code = data.get('requirement_code')
        requirement_name = data.get('requirement_name')
        
        if not requirement_code or not requirement_name:
            return jsonify({'success': False, 'error': 'requirement_code and requirement_name are required'}), 400
        
        requirement_id = create_requirement(
            team_id=team_id,
            requirement_code=requirement_code,
            requirement_name=requirement_name,
            category=data.get('category'),
            priority=data.get('priority', 'P2'),
            description=data.get('description'),
            acceptance_criteria=data.get('acceptance_criteria'),
            app_type=data.get('app_type', 'all'),
            device_model=data.get('device_model', 'all'),
            status=data.get('status', 'active'),
            source_document=data.get('source_document'),
            created_by=data.get('created_by')
        )
        
        if requirement_id == 'DUPLICATE_CODE':
            return jsonify({'success': False, 'error': f'Requirement code already exists: {requirement_code}'}), 409
        
        if requirement_id:
            return jsonify({'success': True, 'requirement_id': requirement_id})
        else:
            return jsonify({'success': False, 'error': 'Failed to create requirement'}), 500
        
    except Exception as e:
        print(f"[@server_requirements:create] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/list', methods=['GET'])
def requirements_list():
    """List all requirements for a team with optional filters"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        category = request.args.get('category')
        priority = request.args.get('priority')
        app_type = request.args.get('app_type')
        device_model = request.args.get('device_model')
        status = request.args.get('status', 'active')
        
        requirements = list_requirements(
            team_id=team_id,
            category=category,
            priority=priority,
            app_type=app_type,
            device_model=device_model,
            status=status
        )
        
        return jsonify({'success': True, 'requirements': requirements, 'count': len(requirements)})
        
    except Exception as e:
        print(f"[@server_requirements:list] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/<requirement_id>', methods=['GET'])
def requirements_get(requirement_id):
    """Get requirement by ID"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        requirement = get_requirement(requirement_id, team_id)
        
        if requirement:
            return jsonify({'success': True, 'requirement': requirement})
        else:
            return jsonify({'success': False, 'error': 'Requirement not found'}), 404
            
    except Exception as e:
        print(f"[@server_requirements:get] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/by-code/<requirement_code>', methods=['GET'])
def requirements_get_by_code(requirement_code):
    """Get requirement by code"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        requirement = get_requirement_by_code(requirement_code, team_id)
        
        if requirement:
            return jsonify({'success': True, 'requirement': requirement})
        else:
            return jsonify({'success': False, 'error': 'Requirement not found'}), 404
            
    except Exception as e:
        print(f"[@server_requirements:get_by_code] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/<requirement_id>', methods=['PUT'])
def requirements_update(requirement_id):
    """Update requirement"""
    try:
        data = request.get_json()
        team_id = data.get('team_id') or request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        success = update_requirement(
            requirement_id=requirement_id,
            team_id=team_id,
            requirement_code=data.get('requirement_code'),
            requirement_name=data.get('requirement_name'),
            category=data.get('category'),
            description=data.get('description'),
            priority=data.get('priority'),
            status=data.get('status'),
            acceptance_criteria=data.get('acceptance_criteria'),
            app_type=data.get('app_type'),
            device_model=data.get('device_model')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update requirement'}), 500
            
    except Exception as e:
        print(f"[@server_requirements:update] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================
# TestCase-Requirement Linkage
# ================================================

@server_requirements_bp.route('/link-testcase', methods=['POST'])
def requirements_link_testcase():
    """Link testcase to requirement"""
    try:
        data = request.get_json()
        
        testcase_id = data.get('testcase_id')
        requirement_id = data.get('requirement_id')
        
        if not testcase_id or not requirement_id:
            return jsonify({'success': False, 'error': 'testcase_id and requirement_id are required'}), 400
        
        success = link_testcase_to_requirement(
            testcase_id=testcase_id,
            requirement_id=requirement_id,
            coverage_type=data.get('coverage_type', 'full'),
            coverage_notes=data.get('coverage_notes'),
            created_by=data.get('created_by')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to link testcase'}), 500
            
    except Exception as e:
        print(f"[@server_requirements:link_testcase] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/unlink-testcase', methods=['POST'])
def requirements_unlink_testcase():
    """Unlink testcase from requirement"""
    try:
        data = request.get_json()
        
        testcase_id = data.get('testcase_id')
        requirement_id = data.get('requirement_id')
        
        if not testcase_id or not requirement_id:
            return jsonify({'success': False, 'error': 'testcase_id and requirement_id are required'}), 400
        
        success = unlink_testcase_from_requirement(testcase_id, requirement_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to unlink testcase'}), 500
            
    except Exception as e:
        print(f"[@server_requirements:unlink_testcase] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/testcase/<testcase_id>/requirements', methods=['GET'])
def testcase_get_requirements(testcase_id):
    """Get all requirements linked to a testcase"""
    try:
        requirements = get_testcase_requirements(testcase_id)
        return jsonify({'success': True, 'requirements': requirements, 'count': len(requirements)})
        
    except Exception as e:
        print(f"[@server_requirements:testcase_get_requirements] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================
# Script-Requirement Linkage
# ================================================

@server_requirements_bp.route('/link-script', methods=['POST'])
def requirements_link_script():
    """Link script to requirement"""
    try:
        data = request.get_json()
        
        script_name = data.get('script_name')
        requirement_id = data.get('requirement_id')
        
        if not script_name or not requirement_id:
            return jsonify({'success': False, 'error': 'script_name and requirement_id are required'}), 400
        
        success = link_script_to_requirement(
            script_name=script_name,
            requirement_id=requirement_id,
            coverage_type=data.get('coverage_type', 'full'),
            coverage_notes=data.get('coverage_notes'),
            created_by=data.get('created_by')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to link script'}), 500
            
    except Exception as e:
        print(f"[@server_requirements:link_script] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/unlink-script', methods=['POST'])
def requirements_unlink_script():
    """Unlink script from requirement"""
    try:
        data = request.get_json()
        
        script_name = data.get('script_name')
        requirement_id = data.get('requirement_id')
        
        if not script_name or not requirement_id:
            return jsonify({'success': False, 'error': 'script_name and requirement_id are required'}), 400
        
        success = unlink_script_from_requirement(script_name, requirement_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to unlink script'}), 500
            
    except Exception as e:
        print(f"[@server_requirements:unlink_script] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/script/<script_name>/requirements', methods=['GET'])
def script_get_requirements(script_name):
    """Get all requirements linked to a script"""
    try:
        requirements = get_script_requirements(script_name)
        return jsonify({'success': True, 'requirements': requirements, 'count': len(requirements)})
        
    except Exception as e:
        print(f"[@server_requirements:script_get_requirements] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================
# Coverage Reporting
# ================================================

@server_requirements_bp.route('/<requirement_id>/coverage', methods=['GET'])
def requirements_get_coverage(requirement_id):
    """Get detailed coverage for a requirement (testcases, scripts, executions)"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        coverage = get_requirement_coverage(team_id, requirement_id)
        
        if coverage:
            return jsonify({'success': True, 'coverage': coverage})
        else:
            return jsonify({'success': False, 'error': 'Requirement not found'}), 404
            
    except Exception as e:
        print(f"[@server_requirements:get_coverage] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/coverage/summary', methods=['GET'])
def requirements_coverage_summary():
    """Get coverage summary across all requirements"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        category = request.args.get('category')
        priority = request.args.get('priority')
        
        summary = get_coverage_summary(
            team_id=team_id,
            category=category,
            priority=priority
        )
        
        return jsonify({'success': True, 'summary': summary})
        
    except Exception as e:
        print(f"[@server_requirements:coverage_summary] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/uncovered', methods=['GET'])
def requirements_uncovered():
    """Get all active requirements without coverage"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        uncovered = get_uncovered_requirements(team_id)
        
        return jsonify({'success': True, 'requirements': uncovered, 'count': len(uncovered)})
        
    except Exception as e:
        print(f"[@server_requirements:uncovered] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/<requirement_id>/available-testcases', methods=['GET'])
def requirements_available_testcases(requirement_id):
    """Get available testcases for linking to requirement"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        userinterface_name = request.args.get('userinterface_name')
        
        testcases = get_available_testcases_for_requirement(
            team_id=team_id,
            requirement_id=requirement_id,
            userinterface_name=userinterface_name
        )
        
        return jsonify({'success': True, 'testcases': testcases, 'count': len(testcases)})
        
    except Exception as e:
        print(f"[@server_requirements:available_testcases] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_requirements_bp.route('/coverage-counts', methods=['GET'])
def requirements_coverage_counts():
    """Get coverage counts for all requirements (for list view)"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        counts = get_requirement_coverage_counts(team_id)
        
        return jsonify({'success': True, 'coverage_counts': counts})
        
    except Exception as e:
        print(f"[@server_requirements:coverage_counts] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


