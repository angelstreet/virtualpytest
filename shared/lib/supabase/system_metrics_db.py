"""
System Metrics Database Functions

Database operations for storing and retrieving system monitoring metrics.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from shared.lib.utils.supabase_utils import get_supabase_client


def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


def process_incidents() -> dict:
    """Process incidents by calling the database function with backend-level duplicate prevention"""
    try:
        supabase = get_supabase()
        
        # Check if Supabase client is available
        if supabase is None:
            print("❌ Supabase client is None - check environment variables")
            return {'incidents_created': 0, 'incidents_resolved': 0, 'error': 'Supabase client not available'}
        
        # Backend-level duplicate prevention: Check if we recently processed incidents
        # This prevents race conditions and excessive processing
        import time
        current_time = time.time()
        
        # Use a simple in-memory cache to prevent processing more than once per minute
        if not hasattr(process_incidents, '_last_processed'):
            process_incidents._last_processed = 0
            
        time_since_last = current_time - process_incidents._last_processed
        
        # Only process if it's been at least 30 seconds since last processing
        if time_since_last < 30:
            print(f"⏳ Incident processing skipped - last processed {time_since_last:.1f}s ago")
            return {'incidents_created': 0, 'incidents_resolved': 0, 'skipped': True}
        
        # Update last processed time
        process_incidents._last_processed = current_time
        
        result = supabase.rpc('process_incidents').execute()
        
        if result.data and len(result.data) > 0:
            incident_result = result.data[0]
            print(f"🚨 Incident processing: {incident_result}")
            return incident_result
        else:
            print("⚠️ No incident processing result returned (empty data)")
            return {'incidents_created': 0, 'incidents_resolved': 0}
            
    except Exception as e:
        import traceback
        print(f"❌ Error processing incidents: {type(e).__name__}: {str(e)}")
        print(f"📋 Full error details: {traceback.format_exc()}")
        
        # Try to get more details from Supabase error
        if hasattr(e, 'details'):
            print(f"🔍 Supabase error details: {e.details}")
        if hasattr(e, 'message'):
            print(f"💬 Supabase error message: {e.message}")
            
        return {'incidents_created': 0, 'incidents_resolved': 0, 'error': str(e)}


def store_system_metrics(host_name: str, metrics_data: Dict[str, Any]) -> bool:
    """Store server metrics in system_metrics table"""
    try:
        supabase = get_supabase()
        
        insert_data = {
            'host_name': host_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'cpu_percent': metrics_data.get('cpu_percent', 0),
            'memory_percent': metrics_data.get('memory_percent', 0),
            'disk_percent': metrics_data.get('disk_percent', 0),
            'uptime_seconds': metrics_data.get('uptime_seconds', 0),
            'platform': metrics_data.get('platform', 'unknown'),
            'architecture': metrics_data.get('architecture', 'unknown'),
            'ffmpeg_status': metrics_data.get('ffmpeg_status', {}),
            'monitor_status': metrics_data.get('monitor_status', {})
        }
        
        result = supabase.table('system_metrics').insert(insert_data).execute()
        
        if result.data:
            print(f"✅ Server metrics stored: {host_name}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error storing server metrics for {host_name}: {e}")
        return False


def store_device_metrics(host_name: str, device_data: Dict[str, Any], system_stats: Dict[str, Any]) -> bool:
    """Store per-device metrics in system_device_metrics table"""
    try:
        supabase = get_supabase()
        
        insert_data = {
            'host_name': host_name,
            'device_id': device_data.get('device_id', 'unknown'),
            'device_name': device_data.get('device_name', 'Unknown Device'),
            'device_port': device_data.get('device_port') or 'unknown',
            'device_model': device_data.get('device_model', 'unknown'),
            'capture_folder': device_data.get('capture_folder', 'unknown'),
            'video_device': device_data.get('video_device', 'unknown'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'cpu_percent': system_stats.get('cpu_percent', 0),
            'memory_percent': system_stats.get('memory_percent', 0),
            'disk_percent': system_stats.get('disk_percent', 0),
            'uptime_seconds': system_stats.get('uptime_seconds', 0),
            'platform': system_stats.get('platform', 'unknown'),
            'architecture': system_stats.get('architecture', 'unknown'),
            'ffmpeg_status': device_data.get('ffmpeg_status', 'unknown'),
            'ffmpeg_uptime_seconds': device_data.get('ffmpeg_uptime_seconds', 0),
            'ffmpeg_last_activity': device_data.get('ffmpeg_last_activity'),
            'monitor_status': device_data.get('monitor_status', 'unknown'),
            'monitor_uptime_seconds': device_data.get('monitor_uptime_seconds', 0),
            'monitor_last_activity': device_data.get('monitor_last_activity')
        }
        
        result = supabase.table('system_device_metrics').insert(insert_data).execute()
        
        if result.data:
            print(f"✅ Device metrics stored: {device_data.get('device_name', 'Unknown')} ({device_data.get('capture_folder', 'unknown')})")
            
            # Process incidents after storing device metrics
            try:
                incident_result = process_incidents()
                if incident_result.get('skipped'):
                    print(f"⏳ Incident processing skipped (rate limited)")
                elif incident_result.get('incidents_created', 0) > 0 or incident_result.get('incidents_resolved', 0) > 0:
                    print(f"🚨 Incidents processed: +{incident_result.get('incidents_created', 0)} created, +{incident_result.get('incidents_resolved', 0)} resolved")
                else:
                    print(f"✅ Incident processing completed: no changes needed")
            except Exception as e:
                import traceback
                print(f"❌ Error processing incidents after device metrics: {type(e).__name__}: {str(e)}")
                print(f"📋 Traceback: {traceback.format_exc()}")
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error storing device metrics: {e}")
        return False


def get_system_metrics(host_name: Optional[str] = None, 
                      hours: int = 24) -> List[Dict[str, Any]]:
    """
    Retrieve system metrics from the database
    
    Args:
        host_name: Optional host name filter
        hours: Number of hours of data to retrieve (default: 24)
    
    Returns:
        List of system metrics records
    """
    try:
        supabase = get_supabase()
        
        # Build query
        query = supabase.table('system_metrics').select('*')
        
        if host_name:
            query = query.eq('host_name', host_name)
        
        # Filter by time range (last N hours)
        from datetime import timedelta
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        query = query.gte('timestamp', cutoff_time)
        
        # Order by timestamp descending
        query = query.order('timestamp', desc=True)
        
        # Limit to reasonable number of records
        query = query.limit(1000)
        
        result = query.execute()
        
        if result.data:
            return result.data
        else:
            return []
            
    except Exception as e:
        print(f"❌ [METRICS] Error retrieving system metrics: {e}")
        return []


def get_latest_system_metrics(host_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest system metrics for a specific host
    
    Args:
        host_name: Name of the host
    
    Returns:
        Latest metrics record or None
    """
    try:
        supabase = get_supabase()
        
        result = supabase.table('system_metrics')\
            .select('*')\
            .eq('host_name', host_name)\
            .order('timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ [METRICS] Error retrieving latest metrics for {host_name}: {e}")
        return None


def cleanup_old_metrics(days: int = 7) -> bool:
    """
    Clean up old system metrics data
    
    Args:
        days: Number of days to keep (default: 7)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase = get_supabase()
        
        # Calculate cutoff date
        from datetime import timedelta
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Delete old records
        result = supabase.table('system_metrics')\
            .delete()\
            .lt('timestamp', cutoff_date)\
            .execute()
        
        print(f"✅ [METRICS] Cleaned up metrics older than {days} days")
        return True
        
    except Exception as e:
        print(f"❌ [METRICS] Error cleaning up old metrics: {e}")
        return False
