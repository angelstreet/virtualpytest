"""
Test Case Database Operations

This module provides functions for managing test cases in the database.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from src.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def save_test_case(test_case: Dict, team_id: str, creator_id: str = None) -> Dict:
    """Save test case to Supabase test_cases table."""
    test_case['test_id'] = test_case.get('test_id', str(uuid4()))
    
    supabase = get_supabase()
    
    # Prepare data for insertion/update
    test_case_data = {
        'test_id': test_case['test_id'],
        'name': test_case['name'],
        'test_type': test_case.get('test_type', 'functional'),
        'start_node': test_case.get('start_node', ''),
        'steps': json.dumps(test_case.get('steps', [])),  # Keep for backward compatibility
        'team_id': team_id,
        'creator_id': creator_id,
        # Existing Phase 2 fields
        'device_id': test_case.get('device_id'),
        'environment_profile_id': test_case.get('environment_profile_id'),
        'verification_conditions': json.dumps(test_case.get('verification_conditions', [])),
        'expected_results': json.dumps(test_case.get('expected_results', {})),
        'execution_config': json.dumps(test_case.get('execution_config', {})),
        'tags': test_case.get('tags', []),
        'priority': test_case.get('priority', 1),
        'estimated_duration': test_case.get('estimated_duration', 60),
        # NEW: AI-specific fields
        'creator': test_case.get('creator', 'manual'),
        'original_prompt': test_case.get('original_prompt'),
        'ai_plan': json.dumps(test_case.get('ai_plan')) if test_case.get('ai_plan') else None,  # Store AIPlan directly
        'ai_analysis': json.dumps(test_case.get('ai_analysis')) if test_case.get('ai_analysis') else None,
        'compatible_devices': test_case.get('compatible_devices', []),
        'compatible_userinterfaces': test_case.get('compatible_userinterfaces', []),
        'device_adaptations': json.dumps(test_case.get('device_adaptations', {}))
    }
    
    try:
        result = supabase.table('test_cases').insert(test_case_data).execute()
        if result.data:
            saved_test_case = dict(result.data[0])
            # Parse JSON fields back
            saved_test_case['steps'] = json.loads(saved_test_case['steps']) if saved_test_case['steps'] else []
            saved_test_case['ai_analysis'] = json.loads(saved_test_case['ai_analysis']) if saved_test_case['ai_analysis'] else None
            saved_test_case['device_adaptations'] = json.loads(saved_test_case['device_adaptations']) if saved_test_case['device_adaptations'] else {}
            return saved_test_case
    except Exception:
        # Update existing test case
        update_data = test_case_data.copy()
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        del update_data['test_id']  # Don't update the ID
        
        result = supabase.table('test_cases').update(update_data).eq('test_id', test_case['test_id']).eq('team_id', team_id).execute()
        if result.data:
            updated_test_case = dict(result.data[0])
            # Parse JSON fields back
            updated_test_case['steps'] = json.loads(updated_test_case['steps']) if updated_test_case['steps'] else []
            updated_test_case['ai_analysis'] = json.loads(updated_test_case['ai_analysis']) if updated_test_case['ai_analysis'] else None
            updated_test_case['device_adaptations'] = json.loads(updated_test_case['device_adaptations']) if updated_test_case['device_adaptations'] else {}
            return updated_test_case
    
    return test_case

def get_test_case(test_id: str, team_id: str) -> Optional[Dict]:
    """Retrieve test case by test_id from Supabase."""
    supabase = get_supabase()
    result = supabase.table('test_cases').select(
        'test_id', 'name', 'test_type', 'start_node', 'steps', 'created_at', 'updated_at',
        'device_id', 'environment_profile_id', 'verification_conditions', 'expected_results',
        'execution_config', 'tags', 'priority', 'estimated_duration',
        # NEW: AI-specific fields
        'creator', 'original_prompt', 'ai_plan', 'ai_analysis', 'compatible_devices', 
        'compatible_userinterfaces', 'device_adaptations'
    ).eq('test_id', test_id).eq('team_id', team_id).execute()
    
    if result.data:
        test_case = dict(result.data[0])
        # Parse JSON fields
        test_case['steps'] = json.loads(test_case['steps']) if test_case['steps'] else []
        test_case['verification_conditions'] = json.loads(test_case['verification_conditions']) if test_case['verification_conditions'] else []
        test_case['expected_results'] = json.loads(test_case['expected_results']) if test_case['expected_results'] else {}
        test_case['execution_config'] = json.loads(test_case['execution_config']) if test_case['execution_config'] else {}
        test_case['ai_plan'] = json.loads(test_case['ai_plan']) if test_case['ai_plan'] else None  # Parse stored AIPlan
        test_case['ai_analysis'] = json.loads(test_case['ai_analysis']) if test_case['ai_analysis'] else None
        test_case['device_adaptations'] = json.loads(test_case['device_adaptations']) if test_case['device_adaptations'] else {}
        return test_case
    return None

def get_all_test_cases(team_id: str) -> List[Dict]:
    """Retrieve all test cases for a team from Supabase."""
    supabase = get_supabase()
    result = supabase.table('test_cases').select(
        'test_id', 'name', 'test_type', 'start_node', 'steps', 'created_at', 'updated_at',
        'device_id', 'environment_profile_id', 'verification_conditions', 'expected_results',
        'execution_config', 'tags', 'priority', 'estimated_duration',
        # NEW: AI-specific fields
        'creator', 'original_prompt', 'ai_plan', 'ai_analysis', 'compatible_devices', 
        'compatible_userinterfaces', 'device_adaptations'
    ).eq('team_id', team_id).order('created_at', desc=True).execute()
    
    test_cases = []
    for test_case in result.data:
        test_case = dict(test_case)
        # Parse JSON fields
        test_case['steps'] = json.loads(test_case['steps']) if test_case['steps'] else []
        test_case['verification_conditions'] = json.loads(test_case['verification_conditions']) if test_case['verification_conditions'] else []
        test_case['expected_results'] = json.loads(test_case['expected_results']) if test_case['expected_results'] else {}
        test_case['execution_config'] = json.loads(test_case['execution_config']) if test_case['execution_config'] else {}
        test_case['ai_plan'] = json.loads(test_case['ai_plan']) if test_case['ai_plan'] else None  # Parse stored AIPlan
        test_case['ai_analysis'] = json.loads(test_case['ai_analysis']) if test_case['ai_analysis'] else None
        test_case['device_adaptations'] = json.loads(test_case['device_adaptations']) if test_case['device_adaptations'] else {}
        test_cases.append(test_case)
    return test_cases

def delete_test_case(test_id: str, team_id: str) -> bool:
    """Delete test case from Supabase."""
    supabase = get_supabase()
    result = supabase.table('test_cases').delete().eq('test_id', test_id).eq('team_id', team_id).execute()
    return len(result.data) > 0

def save_result(test_id: str, name: str, test_type: str, node: str, outcome: str, 
               duration: float, steps: List[Dict], team_id: str) -> None:
    """Save test result to Supabase test_executions table."""
    supabase = get_supabase()
    supabase.table('test_executions').insert({
        'test_id': test_id,
        'name': name,
        'test_type': test_type,
        'node': node,
        'outcome': outcome,
        'duration': duration,
        'steps': json.dumps(steps),
        'team_id': team_id
    }).execute()

def get_failure_rates(team_id: str) -> Dict:
    """Get failure rates and statistics from test results."""
    supabase = get_supabase()
    try:
        # Get total test results
        total_result = supabase.table('test_results').select('id', count='exact').eq('team_id', team_id).execute()
        total_tests = total_result.count or 0
        
        # Get failed test results
        failed_result = supabase.table('test_results').select('id', count='exact').eq('team_id', team_id).eq('status', 'failed').execute()
        failed_tests = failed_result.count or 0
        
        # Get passed test results
        passed_result = supabase.table('test_results').select('id', count='exact').eq('team_id', team_id).eq('status', 'passed').execute()
        passed_tests = passed_result.count or 0
        
        failure_rate = (failed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'failure_rate': round(failure_rate, 2)
        }
    except Exception as e:
        print(f"Error getting failure rates: {e}")
        return {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'failure_rate': 0
        } 