# System Monitoring Grafana Queries

SQL queries for the simplified system monitoring dashboard panels in Grafana.

## Panel 1: Server Status Overview (Stat Panels)

### Server CPU Usage
```sql
SELECT ROUND(AVG(cpu_percent), 1) as "Server CPU %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

### Server Memory Usage  
```sql
SELECT ROUND(AVG(memory_percent), 1) as "Server Memory %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

### Server Disk Usage
```sql
SELECT ROUND(AVG(disk_percent), 1) as "Server Disk %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

### Server Uptime
```sql
SELECT MAX(uptime_seconds) as "Server Uptime" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

## Panel 2: Resource Usage Over Time (Time Series)

### CPU Usage Over Time (All Systems)
```sql
SELECT timestamp as time, 
       host_name as metric, 
       cpu_percent as value 
FROM system_metrics 
WHERE $__timeFilter(timestamp) 
ORDER BY timestamp
```

### Memory Usage Over Time (All Systems)
```sql
SELECT timestamp as time, 
       host_name as metric, 
       memory_percent as value 
FROM system_metrics 
WHERE $__timeFilter(timestamp) 
ORDER BY timestamp
```

## Panel 3: Host Metrics with Process Status (Table)

### Comprehensive Host Status with FFmpeg/Monitor Uptime
```sql
WITH latest_metrics AS (
  SELECT DISTINCT ON (host_name) 
    host_name, 
    timestamp, 
    cpu_percent, 
    memory_percent, 
    disk_percent, 
    uptime_seconds, 
    ffmpeg_status, 
    monitor_status 
  FROM system_metrics 
  WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
    AND host_name != 'server' 
  ORDER BY host_name, timestamp DESC
), 
active_periods AS (
  SELECT host_name, 
         'ffmpeg' as process_type, 
         COUNT(*) * 60 as active_seconds 
  FROM system_metrics 
  WHERE host_name != 'server' 
    AND timestamp >= NOW() - INTERVAL '12 hours' 
    AND ffmpeg_status->>'status' = 'active' 
  GROUP BY host_name 
  UNION ALL 
  SELECT host_name, 
         'monitor' as process_type, 
         COUNT(*) * 60 as active_seconds 
  FROM system_metrics 
  WHERE host_name != 'server' 
    AND timestamp >= NOW() - INTERVAL '12 hours' 
    AND monitor_status->>'status' = 'active' 
  GROUP BY host_name
) 
SELECT 
  lm.host_name as "Host", 
  ROUND(lm.cpu_percent::numeric, 1) as "CPU %", 
  ROUND(lm.memory_percent::numeric, 1) as "Memory %", 
  ROUND(lm.disk_percent::numeric, 1) as "Disk %", 
  CASE 
    WHEN lm.uptime_seconds < 3600 THEN ROUND(lm.uptime_seconds/60) || 'm' 
    WHEN lm.uptime_seconds < 86400 THEN ROUND(lm.uptime_seconds/3600) || 'h' 
    ELSE ROUND(lm.uptime_seconds/86400) || 'd' 
  END as "Uptime", 
  COALESCE((lm.ffmpeg_status->>'status'), 'N/A') as "FFmpeg", 
  COALESCE(
    CASE 
      WHEN ap_ffmpeg.active_seconds < 3600 THEN ROUND(ap_ffmpeg.active_seconds/60) || 'm' 
      WHEN ap_ffmpeg.active_seconds < 86400 THEN ROUND(ap_ffmpeg.active_seconds/3600) || 'h' 
      ELSE ROUND(ap_ffmpeg.active_seconds/86400) || 'd' 
    END, '0m'
  ) as "FFmpeg Uptime", 
  COALESCE((lm.monitor_status->>'status'), 'N/A') as "Monitor", 
  COALESCE(
    CASE 
      WHEN ap_monitor.active_seconds < 3600 THEN ROUND(ap_monitor.active_seconds/60) || 'm' 
      WHEN ap_monitor.active_seconds < 86400 THEN ROUND(ap_monitor.active_seconds/3600) || 'h' 
      ELSE ROUND(ap_monitor.active_seconds/86400) || 'd' 
    END, '0m'
  ) as "Monitor Uptime", 
  TO_CHAR(lm.timestamp, 'HH24:MI:SS') as "Last Update" 
FROM latest_metrics lm 
LEFT JOIN active_periods ap_ffmpeg ON lm.host_name = ap_ffmpeg.host_name 
  AND ap_ffmpeg.process_type = 'ffmpeg' 
LEFT JOIN active_periods ap_monitor ON lm.host_name = ap_monitor.host_name 
  AND ap_monitor.process_type = 'monitor' 
ORDER BY lm.host_name
```

## Key Features

### Process Uptime Tracking
The Host Metrics table includes **FFmpeg Uptime** and **Monitor Uptime** columns that show:
- **If process is "active"**: How long it's been continuously active
- **If process is "stuck/stopped"**: How long it was active before failing

This provides **stability metrics** to understand process reliability.

### Data Synchronization
- Server and host data collection is synchronized to minute boundaries
- Eliminates timing offset issues that caused dots instead of lines in time series
- Ensures smooth line visualization when displaying multiple systems together

## Panel Configuration Notes

### Server Stat Panels (Row 1)
- **Visualization**: Stat
- **Unit**: Percent (0-100) for CPU/Memory/Disk, Seconds for Uptime
- **Thresholds**: 
  - Green: 0-70% (CPU/Memory), 0-85% (Disk)
  - Yellow: 70-90% (CPU/Memory), 85-95% (Disk)  
  - Red: 90%+ (CPU/Memory), 95%+ (Disk)
- **Data Source**: Server only (`host_name = 'server'`)

### Time Series Panels (Row 2)
- **Visualization**: Time Series
- **Y-Axis**: Percent (0-100)
- **Legend**: Show (displays each host as separate line)
- **Line Style**: Forced line rendering with `showPoints: never`
- **Data Source**: All systems (server + hosts)

### Host Metrics Table (Row 3)
- **Visualization**: Table
- **Columns**: Host, CPU%, Memory%, Disk%, Uptime, FFmpeg, FFmpeg Uptime, Monitor, Monitor Uptime, Last Update
- **Process Uptime**: Shows active time in last 12 hours
- **Data Source**: Hosts only (excludes server)

## Simplified Dashboard Layout

```
┌──────────┬──────────┬──────────┬──────────┐
│Server CPU│Server Mem│Server Dsk│Server Up │
│  (Stat)  │  (Stat)  │  (Stat)  │  (Stat)  │
└──────────┴──────────┴──────────┴──────────┘
┌─────────────────┬─────────────────────────┐
│   CPU Usage     │    Memory Usage         │
│  Over Time      │    Over Time            │
│ (Time Series)   │   (Time Series)         │
└─────────────────┴─────────────────────────┘
┌─────────────────────────────────────────────┐
│         Host Metrics & Process Status       │
│              (Comprehensive Table)          │
└─────────────────────────────────────────────┘
```

## Database Schema

The dashboard uses the `system_metrics` table with these key columns:
- `host_name`: 'server' or host identifier
- `cpu_percent`, `memory_percent`, `disk_percent`: Resource usage
- `uptime_seconds`: System uptime
- `ffmpeg_status`: JSONB with FFmpeg process status
- `monitor_status`: JSONB with monitor process status
- `timestamp`: Data collection time (synchronized to minute boundaries)
