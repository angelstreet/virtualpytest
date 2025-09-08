"""
System Metrics Database Functions

Database operations for storing and retrieving system monitoring metrics.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from .supabase_client import get_supabase_client


def store_system_metrics(host_name: str, metrics_data: Dict[str, Any]) -> bool:
    """
    Store system metrics in the database
    
    Args:
        host_name: Name of the host
        metrics_data: Enhanced system stats from get_enhanced_system_stats()
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate missing GB values if needed (for server metrics)
        memory_used_gb = metrics_data.get('memory_used_gb', 0)
        memory_total_gb = metrics_data.get('memory_total_gb', 0)
        disk_used_gb = metrics_data.get('disk_used_gb', 0)
        disk_total_gb = metrics_data.get('disk_total_gb', 0)
        
        if memory_used_gb == 0 or memory_total_gb == 0:
            try:
                import psutil
                memory = psutil.virtual_memory()
                memory_used_gb = round(memory.used / (1024**3), 2)
                memory_total_gb = round(memory.total / (1024**3), 2)
            except:
                pass
        
        if disk_used_gb == 0 or disk_total_gb == 0:
            try:
                import psutil
                disk = psutil.disk_usage('/')
                disk_used_gb = round(disk.used / (1024**3), 2)
                disk_total_gb = round(disk.total / (1024**3), 2)
            except:
                pass
        
        # Prepare data for insertion
        insert_data = {
            'host_name': host_name,
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': metrics_data.get('cpu_percent', 0),
            'memory_percent': metrics_data.get('memory_percent', 0),
            'memory_used_gb': memory_used_gb,
            'memory_total_gb': memory_total_gb,
            'disk_percent': metrics_data.get('disk_percent', 0),
            'disk_used_gb': disk_used_gb,
            'disk_total_gb': disk_total_gb,
            'uptime_seconds': metrics_data.get('uptime_seconds', 0),
            'platform': metrics_data.get('platform', 'unknown'),
            'architecture': metrics_data.get('architecture', 'unknown'),
            'ffmpeg_status': json.dumps(metrics_data.get('ffmpeg_status', {})),
            'monitor_status': json.dumps(metrics_data.get('monitor_status', {}))
        }
        
        # Insert into database
        result = supabase.table('system_metrics').insert(insert_data).execute()
        
        if result.data:
            print(f"✅ [METRICS] Stored system metrics for {host_name}")
            return True
        else:
            print(f"❌ [METRICS] Failed to store metrics for {host_name}: No data returned")
            return False
            
    except Exception as e:
        print(f"❌ [METRICS] Error storing system metrics for {host_name}: {e}")
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
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table('system_metrics').select('*')
        
        if host_name:
            query = query.eq('host_name', host_name)
        
        # Filter by time range (last N hours)
        from datetime import datetime, timedelta
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
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
        supabase = get_supabase_client()
        
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
        supabase = get_supabase_client()
        
        # Calculate cutoff date
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
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
