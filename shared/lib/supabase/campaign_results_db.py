#!/usr/bin/env python3
"""
Campaign Results Database Functions

This module provides database operations for campaign execution tracking,
including campaign results and script execution mapping.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from shared.lib.utils.supabase_utils import get_supabase_client


def get_supabase():
    """Get Supabase client"""
    return get_supabase_client()


def record_campaign_execution_start(
    team_id: str,
    campaign_id: str,
    campaign_execution_id: str,
    name: str,
    description: Optional[str] = None,
    script_configurations: Optional[List[Dict]] = None,
    execution_config: Optional[Dict] = None,
    executed_by: Optional[str] = None
) -> Optional[str]:
    """Record campaign execution start in database."""
    try:
        campaign_result_id = str(uuid4())
        
        campaign_data = {
            'id': campaign_result_id,
            'team_id': team_id,
            'campaign_id': campaign_id,
            'campaign_execution_id': campaign_execution_id,
            'name': name,
            'description': description,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'total_scripts': len(script_configurations) if script_configurations else 0,
            'completed_scripts': 0,
            'successful_scripts': 0,
            'failed_scripts': 0,
            'script_configurations': script_configurations or [],
            'execution_config': execution_config or {},
            'overall_success': False,
            'executed_by': executed_by
        }
        
        print(f"[@db:campaign_results:record_campaign_execution_start] Starting campaign execution:")
        print(f"  - campaign_result_id: {campaign_result_id}")
        print(f"  - team_id: {team_id}")
        print(f"  - campaign_id: {campaign_id}")
        print(f"  - campaign_execution_id: {campaign_execution_id}")
        print(f"  - name: {name}")
        print(f"  - total_scripts: {len(script_configurations) if script_configurations else 0}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_results').insert(campaign_data).execute()
        
        if result.data:
            print(f"[@db:campaign_results:record_campaign_execution_start] Success: {campaign_result_id}")
            return campaign_result_id
        else:
            print(f"[@db:campaign_results:record_campaign_execution_start] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:campaign_results:record_campaign_execution_start] Error: {str(e)}")
        return None


def update_campaign_execution_result(
    campaign_result_id: str,
    status: Optional[str] = None,
    end_time: Optional[datetime] = None,
    total_duration_ms: Optional[int] = None,
    total_scripts: Optional[int] = None,
    completed_scripts: Optional[int] = None,
    successful_scripts: Optional[int] = None,
    failed_scripts: Optional[int] = None,
    overall_success: Optional[bool] = None,
    error_message: Optional[str] = None,
    html_report_r2_path: Optional[str] = None,
    html_report_r2_url: Optional[str] = None
) -> bool:
    """Update campaign execution result in database."""
    try:
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        # Add provided fields to update
        if status is not None:
            update_data['status'] = status
        if end_time is not None:
            update_data['end_time'] = end_time.isoformat()
        if total_duration_ms is not None:
            update_data['total_duration_ms'] = total_duration_ms
        if total_scripts is not None:
            update_data['total_scripts'] = total_scripts
        if completed_scripts is not None:
            update_data['completed_scripts'] = completed_scripts
        if successful_scripts is not None:
            update_data['successful_scripts'] = successful_scripts
        if failed_scripts is not None:
            update_data['failed_scripts'] = failed_scripts
        if overall_success is not None:
            update_data['overall_success'] = overall_success
        if error_message is not None:
            update_data['error_message'] = error_message
        if html_report_r2_path is not None:
            update_data['html_report_r2_path'] = html_report_r2_path
        if html_report_r2_url is not None:
            update_data['html_report_r2_url'] = html_report_r2_url
        
        print(f"[@db:campaign_results:update_campaign_execution_result] Updating campaign result:")
        print(f"  - campaign_result_id: {campaign_result_id}")
        print(f"  - status: {status}")
        print(f"  - overall_success: {overall_success}")
        print(f"  - completed_scripts: {completed_scripts}")
        print(f"  - successful_scripts: {successful_scripts}")
        print(f"  - failed_scripts: {failed_scripts}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_results').update(update_data).eq('id', campaign_result_id).execute()
        
        if result.data:
            print(f"[@db:campaign_results:update_campaign_execution_result] Success")
            return True
        else:
            print(f"[@db:campaign_results:update_campaign_execution_result] Failed")
            return False
            
    except Exception as e:
        print(f"[@db:campaign_results:update_campaign_execution_result] Error: {str(e)}")
        return False


def record_campaign_script_execution(
    campaign_result_id: str,
    execution_order: int,
    script_name: str,
    script_type: str,
    userinterface_name: Optional[str],
    host_name: str,
    device_name: str,
    script_config: Optional[Dict] = None,
    status: str = "pending"
) -> Optional[str]:
    """Record campaign script execution start in database."""
    try:
        record_id = str(uuid4())
        
        # We'll link to script_results when the actual script execution creates that record
        # For now, we create a placeholder entry
        script_execution_data = {
            'id': record_id,
            'campaign_result_id': campaign_result_id,
            'script_result_id': None,  # Will be updated when script actually executes
            'execution_order': execution_order,
            'script_name': script_name,
            'script_type': script_type,
            'userinterface_name': userinterface_name,
            'host_name': host_name,
            'device_name': device_name,
            'script_config': script_config or {},
            'status': status,
            'start_time': datetime.now().isoformat(),
            'success': False
        }
        
        print(f"[@db:campaign_results:record_campaign_script_execution] Recording script execution:")
        print(f"  - record_id: {record_id}")
        print(f"  - campaign_result_id: {campaign_result_id}")
        print(f"  - execution_order: {execution_order}")
        print(f"  - script_name: {script_name}")
        print(f"  - script_type: {script_type}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_script_executions').insert(script_execution_data).execute()
        
        if result.data:
            print(f"[@db:campaign_results:record_campaign_script_execution] Success: {record_id}")
            return record_id
        else:
            print(f"[@db:campaign_results:record_campaign_script_execution] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:campaign_results:record_campaign_script_execution] Error: {str(e)}")
        return None


def update_campaign_script_execution(
    record_id: str,
    script_result_id: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    execution_time_ms: Optional[int] = None,
    success: Optional[bool] = None,
    error_message: Optional[str] = None
) -> bool:
    """Update campaign script execution record."""
    try:
        update_data = {}
        
        if script_result_id is not None:
            update_data['script_result_id'] = script_result_id
        if status is not None:
            update_data['status'] = status
        if start_time is not None:
            update_data['start_time'] = start_time.isoformat()
        if end_time is not None:
            update_data['end_time'] = end_time.isoformat()
        if execution_time_ms is not None:
            update_data['execution_time_ms'] = execution_time_ms
        if success is not None:
            update_data['success'] = success
        if error_message is not None:
            update_data['error_message'] = error_message
        
        print(f"[@db:campaign_results:update_campaign_script_execution] Updating script execution:")
        print(f"  - record_id: {record_id}")
        print(f"  - status: {status}")
        print(f"  - success: {success}")
        print(f"  - execution_time_ms: {execution_time_ms}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_script_executions').update(update_data).eq('id', record_id).execute()
        
        if result.data:
            print(f"[@db:campaign_results:update_campaign_script_execution] Success")
            return True
        else:
            print(f"[@db:campaign_results:update_campaign_script_execution] Failed")
            return False
            
    except Exception as e:
        print(f"[@db:campaign_results:update_campaign_script_execution] Error: {str(e)}")
        return False


def get_campaign_results(
    team_id: str,
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> Dict:
    """Get campaign results with filtering."""
    try:
        print(f"[@db:campaign_results:get_campaign_results] Getting campaign results:")
        print(f"  - team_id: {team_id}")
        print(f"  - campaign_id: {campaign_id}")
        print(f"  - status: {status}")
        print(f"  - limit: {limit}")
        
        supabase = get_supabase()
        query = supabase.table('campaign_results').select('*').eq('team_id', team_id)
        
        # Add filters
        if campaign_id:
            query = query.eq('campaign_id', campaign_id)
        if status:
            query = query.eq('status', status)
        
        # Execute query with ordering and limit
        result = query.order('created_at', desc=True).limit(limit).execute()
        
        print(f"[@db:campaign_results:get_campaign_results] Found {len(result.data)} campaign results")
        return {
            'success': True,
            'campaign_results': result.data,
            'count': len(result.data)
        }
        
    except Exception as e:
        print(f"[@db:campaign_results:get_campaign_results] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'campaign_results': [],
            'count': 0
        }


def get_campaign_script_executions(
    campaign_result_id: str
) -> Dict:
    """Get script executions for a specific campaign result."""
    try:
        print(f"[@db:campaign_results:get_campaign_script_executions] Getting script executions:")
        print(f"  - campaign_result_id: {campaign_result_id}")
        
        supabase = get_supabase()
        
        # Get script executions with linked script results
        query = """
        SELECT 
            cse.*,
            sr.success as script_success,
            sr.execution_time_ms as script_execution_time_ms,
            sr.html_report_r2_url,
            sr.error_msg as script_error_msg,
            sr.metadata as script_metadata
        FROM campaign_script_executions cse
        LEFT JOIN script_results sr ON cse.script_result_id = sr.id
        WHERE cse.campaign_result_id = %s
        ORDER BY cse.execution_order ASC
        """
        
        result = supabase.rpc('execute_sql', {
            'query': query,
            'params': [campaign_result_id]
        }).execute()
        
        script_executions = result.data if result.data else []
        
        print(f"[@db:campaign_results:get_campaign_script_executions] Found {len(script_executions)} script executions")
        return {
            'success': True,
            'script_executions': script_executions,
            'count': len(script_executions)
        }
        
    except Exception as e:
        print(f"[@db:campaign_results:get_campaign_script_executions] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'script_executions': [],
            'count': 0
        }


def get_campaign_execution_summary(
    team_id: str,
    campaign_result_id: str
) -> Dict:
    """Get comprehensive campaign execution summary."""
    try:
        print(f"[@db:campaign_results:get_campaign_execution_summary] Getting campaign summary:")
        print(f"  - team_id: {team_id}")
        print(f"  - campaign_result_id: {campaign_result_id}")
        
        supabase = get_supabase()
        
        # Get campaign result
        campaign_result = supabase.table('campaign_results').select('*').eq('id', campaign_result_id).eq('team_id', team_id).execute()
        
        if not campaign_result.data:
            return {
                'success': False,
                'error': 'Campaign result not found',
                'campaign_result': None,
                'script_executions': []
            }
        
        # Get script executions
        script_executions_result = get_campaign_script_executions(campaign_result_id)
        
        return {
            'success': True,
            'campaign_result': campaign_result.data[0],
            'script_executions': script_executions_result.get('script_executions', [])
        }
        
    except Exception as e:
        print(f"[@db:campaign_results:get_campaign_execution_summary] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'campaign_result': None,
            'script_executions': []
        }