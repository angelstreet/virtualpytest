#!/usr/bin/env python3
"""
Campaign Executions Database Operations

Simplified single-table approach for campaign tracking that links to script_results.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.supabase_utils import get_supabase_client


def get_supabase():
    """Get Supabase client"""
    return get_supabase_client()


def record_campaign_execution_start(
    team_id: str,
    campaign_name: str,
    campaign_execution_id: str,
    userinterface_name: Optional[str] = None,
    host_name: str = "",
    device_name: str = "",
    description: Optional[str] = None,
    script_configurations: Optional[List[Dict]] = None,
    execution_config: Optional[Dict] = None,
    executed_by: Optional[str] = None
) -> Optional[str]:
    """Record campaign execution start in database."""
    try:
        campaign_execution_id_uuid = str(uuid4())
        
        campaign_data = {
            'id': campaign_execution_id_uuid,
            'team_id': team_id,
            'campaign_name': campaign_name,
            'campaign_description': description,
            'campaign_execution_id': campaign_execution_id,
            'userinterface_name': userinterface_name,
            'host_name': host_name,
            'device_name': device_name,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'success': False,
            'script_configurations': script_configurations or [],
            'execution_config': execution_config or {},
            'script_result_ids': [],
            'executed_by': executed_by
        }
        
        print(f"[@db:campaign_executions:record_start] Starting campaign execution:")
        print(f"  - campaign_execution_id_uuid: {campaign_execution_id_uuid}")
        print(f"  - team_id: {team_id}")
        print(f"  - campaign_name: {campaign_name}")
        print(f"  - campaign_execution_id: {campaign_execution_id}")
        print(f"  - total_scripts: {len(script_configurations) if script_configurations else 0}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_executions').insert(campaign_data).execute()
        
        if result.data:
            print(f"[@db:campaign_executions:record_start] Success: {campaign_execution_id_uuid}")
            return campaign_execution_id_uuid
        else:
            print(f"[@db:campaign_executions:record_start] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:campaign_executions:record_start] Error: {str(e)}")
        return None


def add_script_result_to_campaign(
    campaign_execution_id_uuid: str,
    script_result_id: str
) -> bool:
    """Add a script result ID to the campaign's script_result_ids array."""
    try:
        supabase = get_supabase()
        
        # Use PostgreSQL array_append function to add the script_result_id
        result = supabase.rpc('array_append_campaign_script', {
            'campaign_id': campaign_execution_id_uuid,
            'script_id': script_result_id
        }).execute()
        
        if result.data:
            print(f"[@db:campaign_executions:add_script] Added script {script_result_id} to campaign {campaign_execution_id_uuid}")
            return True
        else:
            # Fallback: fetch current array, append, and update
            current = supabase.table('campaign_executions').select('script_result_ids').eq('id', campaign_execution_id_uuid).execute()
            if current.data:
                current_ids = current.data[0]['script_result_ids'] or []
                if script_result_id not in current_ids:
                    current_ids.append(script_result_id)
                    update_result = supabase.table('campaign_executions').update({
                        'script_result_ids': current_ids
                    }).eq('id', campaign_execution_id_uuid).execute()
                    return bool(update_result.data)
            return False
            
    except Exception as e:
        print(f"[@db:campaign_executions:add_script] Error: {str(e)}")
        # Fallback approach
        try:
            supabase = get_supabase()
            current = supabase.table('campaign_executions').select('script_result_ids').eq('id', campaign_execution_id_uuid).execute()
            if current.data:
                current_ids = current.data[0]['script_result_ids'] or []
                if script_result_id not in current_ids:
                    current_ids.append(script_result_id)
                    update_result = supabase.table('campaign_executions').update({
                        'script_result_ids': current_ids
                    }).eq('id', campaign_execution_id_uuid).execute()
                    return bool(update_result.data)
            return False
        except Exception as fallback_e:
            print(f"[@db:campaign_executions:add_script] Fallback error: {str(fallback_e)}")
            return False


def update_campaign_execution_result(
    campaign_execution_id_uuid: str,
    status: Optional[str] = None,
    completed_at: Optional[datetime] = None,
    execution_time_ms: Optional[int] = None,
    success: Optional[bool] = None,
    error_message: Optional[str] = None,
    html_report_r2_path: Optional[str] = None,
    html_report_r2_url: Optional[str] = None
) -> bool:
    """Update campaign execution result in database."""
    try:
        update_data = {}
        
        if status is not None:
            update_data['status'] = status
        if completed_at is not None:
            update_data['completed_at'] = completed_at.isoformat()
        if execution_time_ms is not None:
            update_data['execution_time_ms'] = execution_time_ms
        if success is not None:
            update_data['success'] = success
        if error_message is not None:
            update_data['error_message'] = error_message
        if html_report_r2_path is not None:
            update_data['html_report_r2_path'] = html_report_r2_path
        if html_report_r2_url is not None:
            update_data['html_report_r2_url'] = html_report_r2_url
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        print(f"[@db:campaign_executions:update_result] Updating campaign: {campaign_execution_id_uuid}")
        print(f"  - status: {status}")
        print(f"  - success: {success}")
        
        supabase = get_supabase()
        result = supabase.table('campaign_executions').update(update_data).eq('id', campaign_execution_id_uuid).execute()
        
        if result.data:
            print(f"[@db:campaign_executions:update_result] Success")
            return True
        else:
            print(f"[@db:campaign_executions:update_result] Failed")
            return False
            
    except Exception as e:
        print(f"[@db:campaign_executions:update_result] Error: {str(e)}")
        return False


def get_campaign_execution_with_scripts(campaign_execution_id: str) -> Optional[Dict]:
    """Get campaign execution with all linked script results."""
    try:
        supabase = get_supabase()
        
        # First get the campaign execution
        campaign_result = supabase.table('campaign_executions').select('*').eq('campaign_execution_id', campaign_execution_id).execute()
        
        if not campaign_result.data:
            return None
            
        campaign = campaign_result.data[0]
        script_result_ids = campaign.get('script_result_ids', [])
        
        # Get all linked script results
        script_results = []
        if script_result_ids:
            scripts_result = supabase.table('script_results').select('*').in_('id', script_result_ids).execute()
            if scripts_result.data:
                script_results = scripts_result.data
        
        campaign['script_results'] = script_results
        return campaign
        
    except Exception as e:
        print(f"[@db:campaign_executions:get_with_scripts] Error: {str(e)}")
        return None