"""
Database operations for zap_results table
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4
from shared.src.lib.utils.supabase_utils import get_supabase_client


def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


def record_zap_iteration(
    script_result_id: Optional[str],  # ✅ Now nullable for automatic zapping
    team_id: str,
    host_name: str,
    device_name: str,
    device_model: str,
    userinterface_name: str,
    iteration_index: int,
    action_command: str,
    started_at: datetime,
    completed_at: datetime,
    duration_seconds: float,
    motion_detected: bool = False,
    subtitles_detected: bool = False,
    audio_speech_detected: bool = False,
    blackscreen_freeze_detected: bool = False,
    subtitle_language: Optional[str] = None,
    subtitle_text: Optional[str] = None,
    audio_language: Optional[str] = None,
    audio_transcript: Optional[str] = None,
    blackscreen_freeze_duration_seconds: Optional[float] = None,
    detection_method: Optional[str] = None,
    channel_name: Optional[str] = None,
    channel_number: Optional[str] = None,
    program_name: Optional[str] = None,
    program_start_time: Optional[str] = None,
    program_end_time: Optional[str] = None
) -> Optional[str]:
    """
    Record a single zap iteration result in database.
    
    Args:
        script_result_id: UUID of parent script execution. 
                         Can be None for automatic zapping detection during monitoring.
        ... (other args)
    """
    try:
        zap_result_id = str(uuid4())
        
        zap_data = {
            'id': zap_result_id,
            'script_result_id': script_result_id,
            'team_id': team_id,
            'host_name': host_name,
            'device_name': device_name,
            'device_model': device_model,
            'userinterface_name': userinterface_name,
            'execution_date': datetime.now(timezone.utc).isoformat(),
            'iteration_index': iteration_index,
            'action_command': action_command,
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'duration_seconds': duration_seconds,
            'motion_detected': motion_detected,
            'subtitles_detected': subtitles_detected,
            'audio_speech_detected': audio_speech_detected,
            'blackscreen_freeze_detected': blackscreen_freeze_detected,
            'subtitle_language': subtitle_language,
            'subtitle_text': subtitle_text,
            'audio_language': audio_language,
            'audio_transcript': audio_transcript,
            'blackscreen_freeze_duration_seconds': blackscreen_freeze_duration_seconds,
            'detection_method': detection_method,
            'channel_name': channel_name,
            'channel_number': channel_number,
            'program_name': program_name,
            'program_start_time': program_start_time,
            'program_end_time': program_end_time
        }
        
        print(f"[@db:zap_results:record_zap_iteration] Recording zap iteration:")
        print(f"  - zap_result_id: {zap_result_id}")
        print(f"  - script_result_id: {script_result_id}")
        print(f"  - userinterface: {userinterface_name}")
        print(f"  - iteration: {iteration_index}")
        print(f"  - action: {action_command}")
        print(f"  - started_at: {started_at.isoformat()}")
        print(f"  - completed_at: {completed_at.isoformat()}")
        print(f"  - duration: {duration_seconds}s")
        print(f"  - motion: {motion_detected}, subtitles: {subtitles_detected}, audio: {audio_speech_detected}, blackscreen/freeze: {blackscreen_freeze_detected}")
        print(f"  - channel_name: '{channel_name}', channel_number: '{channel_number}', program_name: '{program_name}'")
        print(f"  - program_start_time: '{program_start_time}', program_end_time: '{program_end_time}'")
        
        supabase = get_supabase()
        result = supabase.table('zap_results').insert(zap_data).execute()
        
        if result.data:
            print(f"[@db:zap_results:record_zap_iteration] Success: {zap_result_id}")
            return zap_result_id
        else:
            print(f"[@db:zap_results:record_zap_iteration] Failed")
            return None
            
    except Exception as e:
        print(f"[@db:zap_results:record_zap_iteration] Error: {str(e)}")
        return None


def get_zap_results(
    team_id: str,
    script_result_id: Optional[str] = None,
    host_name: Optional[str] = None,
    device_name: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get zap results with filtering."""
    try:
        print(f"[@db:zap_results:get_zap_results] Getting zap results:")
        print(f"  - team_id: {team_id}")
        print(f"  - script_result_id: {script_result_id}")
        print(f"  - host_name: {host_name}")
        print(f"  - device_name: {device_name}")
        print(f"  - limit: {limit}")
        
        supabase = get_supabase()
        query = supabase.table('zap_results').select('*').eq('team_id', team_id)
        
        # Add filters
        if script_result_id:
            query = query.eq('script_result_id', script_result_id)
        if host_name:
            query = query.eq('host_name', host_name)
        if device_name:
            query = query.eq('device_name', device_name)
        
        # Execute query with ordering and limit
        result = query.order('execution_date', desc=True).order('iteration_index', desc=False).limit(limit).execute()
        
        print(f"[@db:zap_results:get_zap_results] Found {len(result.data)} zap results")
        return {
            'success': True,
            'zap_results': result.data,
            'count': len(result.data)
        }
        
    except Exception as e:
        print(f"[@db:zap_results:get_zap_results] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'zap_results': [],
            'count': 0
        }


def get_zap_summary_for_script(script_result_id: str) -> Dict[str, Any]:
    """Get zap summary data for generating summary table."""
    try:
        print(f"[@db:zap_results:get_zap_summary_for_script] Getting summary for script: {script_result_id}")
        
        supabase = get_supabase()
        result = supabase.table('zap_results').select('*').eq('script_result_id', script_result_id).order('iteration_index', desc=False).execute()
        
        if result.data:
            print(f"[@db:zap_results:get_zap_summary_for_script] Found {len(result.data)} zap iterations")
            return {
                'success': True,
                'zap_iterations': result.data,
                'count': len(result.data)
            }
        else:
            print(f"[@db:zap_results:get_zap_summary_for_script] No zap results found")
            return {
                'success': True,
                'zap_iterations': [],
                'count': 0
            }
            
    except Exception as e:
        print(f"[@db:zap_results:get_zap_summary_for_script] Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'zap_iterations': [],
            'count': 0
        }
