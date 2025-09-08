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

### CPU Usage Over Time (Per Device)
```sql
SELECT timestamp as time, 
       CONCAT(host_name, ' - ', device_name) as metric, 
       cpu_percent as value 
FROM system_device_metrics 
WHERE $__timeFilter(timestamp) 
ORDER BY timestamp
```

### Memory Usage Over Time (Per Device)
```sql
SELECT timestamp as time, 
       CONCAT(host_name, ' - ', device_name) as metric, 
       memory_percent as value 
FROM system_device_metrics 
WHERE $__timeFilter(timestamp) 
ORDER BY timestamp
```

## Panel 3: Device Metrics - Per Device Status (Table)

### Individual Device Status with Separate FFmpeg/Monitor Tracking
```sql
WITH latest_device_metrics AS (
  SELECT DISTINCT ON (host_name, device_id) 
    host_name, 
    device_id, 
    device_name, 
    device_port, 
    capture_folder,
    video_device,
    device_model, 
    timestamp, 
    cpu_percent, 
    memory_percent, 
    disk_percent, 
    uptime_seconds, 
    ffmpeg_status, 
    ffmpeg_last_activity, 
    ffmpeg_uptime_seconds, 
    monitor_status, 
    monitor_last_activity, 
    monitor_uptime_seconds 
  FROM system_device_metrics 
  WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  ORDER BY host_name, device_id, timestamp DESC
) 
SELECT 
  host_name as "Host", 
  device_name as "Device Name", 
  capture_folder as "Capture Folder",
  video_device as "Video Device", 
  ROUND(cpu_percent::numeric, 1) as "CPU %", 
  ROUND(memory_percent::numeric, 1) as "Memory %", 
  ROUND(disk_percent::numeric, 1) as "Disk %", 
  CASE 
    WHEN uptime_seconds < 3600 THEN ROUND(uptime_seconds/60) || 'm' 
    WHEN uptime_seconds < 86400 THEN ROUND(uptime_seconds/3600) || 'h' 
    ELSE ROUND(uptime_seconds/86400) || 'd' 
  END as "Uptime", 
  ffmpeg_status as "FFmpeg", 
  CASE 
    WHEN ffmpeg_uptime_seconds < 3600 THEN ROUND(ffmpeg_uptime_seconds/60) || 'm' 
    WHEN ffmpeg_uptime_seconds < 86400 THEN ROUND(ffmpeg_uptime_seconds/3600) || 'h' 
    ELSE ROUND(ffmpeg_uptime_seconds/86400) || 'd' 
  END as "FFmpeg Uptime", 
  COALESCE(TO_CHAR(ffmpeg_last_activity, 'HH24:MI:SS'), 'N/A') as "FFmpeg Last", 
  monitor_status as "Monitor", 
  CASE 
    WHEN monitor_uptime_seconds < 3600 THEN ROUND(monitor_uptime_seconds/60) || 'm' 
    WHEN monitor_uptime_seconds < 86400 THEN ROUND(monitor_uptime_seconds/3600) || 'h' 
    ELSE ROUND(monitor_uptime_seconds/86400) || 'd' 
  END as "Monitor Uptime", 
  COALESCE(TO_CHAR(monitor_last_activity, 'HH24:MI:SS'), 'N/A') as "Monitor Last", 
  TO_CHAR(timestamp, 'HH24:MI:SS') as "Last Update" 
FROM latest_device_metrics 
ORDER BY host_name, capture_folder
```

## Panel 4: Incident History (Table)

### Comprehensive Incident Detection and Analysis
```sql
WITH status_transitions AS (
  SELECT 
    device_name,
    capture_folder,
    video_device,
    device_id,
    timestamp,
    ffmpeg_status,
    monitor_status,
    LAG(ffmpeg_status) OVER (PARTITION BY device_id, capture_folder ORDER BY timestamp) as prev_ffmpeg_status,
    LAG(monitor_status) OVER (PARTITION BY device_id, capture_folder ORDER BY timestamp) as prev_monitor_status,
    LAG(timestamp) OVER (PARTITION BY device_id, capture_folder ORDER BY timestamp) as prev_timestamp
  FROM system_device_metrics 
  WHERE timestamp >= NOW() - INTERVAL '24 hours'
),
incidents AS (
  SELECT 
    device_name,
    capture_folder,
    video_device,
    timestamp as incident_time,
    prev_timestamp,
    CASE 
      WHEN prev_ffmpeg_status = 'active' AND ffmpeg_status = 'stuck' THEN 'FFmpeg Got Stuck'
      WHEN prev_ffmpeg_status = 'active' AND ffmpeg_status = 'stopped' THEN 'FFmpeg Stopped'
      WHEN prev_ffmpeg_status = 'stuck' AND ffmpeg_status = 'stopped' THEN 'FFmpeg Died'
      WHEN prev_monitor_status = 'active' AND monitor_status = 'stuck' THEN 'Monitor Got Stuck'
      WHEN prev_monitor_status = 'active' AND monitor_status = 'stopped' THEN 'Monitor Stopped'
      WHEN prev_monitor_status = 'stuck' AND monitor_status = 'stopped' THEN 'Monitor Died'
    END as incident_type,
    CASE 
      WHEN prev_ffmpeg_status = 'active' AND ffmpeg_status IN ('stuck', 'stopped') THEN ffmpeg_status
      WHEN prev_ffmpeg_status = 'stuck' AND ffmpeg_status = 'stopped' THEN ffmpeg_status
      WHEN prev_monitor_status = 'active' AND monitor_status IN ('stuck', 'stopped') THEN monitor_status
      WHEN prev_monitor_status = 'stuck' AND monitor_status = 'stopped' THEN monitor_status
    END as current_status
  FROM status_transitions
  WHERE (prev_ffmpeg_status = 'active' AND ffmpeg_status IN ('stuck', 'stopped'))
     OR (prev_ffmpeg_status = 'stuck' AND ffmpeg_status = 'stopped')
     OR (prev_monitor_status = 'active' AND monitor_status IN ('stuck', 'stopped'))
     OR (prev_monitor_status = 'stuck' AND monitor_status = 'stopped')
)
SELECT 
  device_name as "Device",
  capture_folder as "Folder",
  incident_type as "Event",
  TO_CHAR(incident_time, 'HH24:MI:SS') as "When",
  CASE 
    WHEN EXTRACT(EPOCH FROM (incident_time - prev_timestamp)) < 3600 THEN 
      ROUND(EXTRACT(EPOCH FROM (incident_time - prev_timestamp))/60) || 'm'
    WHEN EXTRACT(EPOCH FROM (incident_time - prev_timestamp)) < 86400 THEN 
      ROUND(EXTRACT(EPOCH FROM (incident_time - prev_timestamp))/3600) || 'h'
    ELSE 
      ROUND(EXTRACT(EPOCH FROM (incident_time - prev_timestamp))/86400) || 'd'
  END as "Worked For"
FROM incidents
ORDER BY incident_time DESC
LIMIT 20
```

## Key Features

### Per-Device Granular Tracking
The new system provides **individual device monitoring** with complete separation:
- **Real Device Names**: Shows actual device names (e.g., "Samsung TV Living Room", "Fire TV Bedroom")
- **Separate FFmpeg/Monitor Status**: Each device shows independent FFmpeg and Monitor status
- **Individual Timing**: Separate last activity and uptime tracking for FFmpeg and Monitor per device
- **Capture Folder Tracking**: Shows which capture folder (capture, capture1, capture2) each device uses for FFmpeg/Monitor processes
- **Video Hardware Tracking**: Shows which video device (/dev/video0, /dev/video2) each device uses for hardware identification

This enables precise identification of which specific device and process is having issues.

### Process Uptime Tracking
The Host Metrics table includes **FFmpeg Uptime** and **Monitor Uptime** columns that show:
- **Database-Based Calculation**: Analyzes historical status changes from `system_device_metrics`
- **Working Duration**: How long the process was continuously active before getting stuck
- **Stability Metrics**: Understand process reliability and failure patterns

### Incident History Analysis
The **Incident History** panel provides comprehensive forensic analysis:

#### **Status Detection Logic**:
- **`active`**: Process running AND creating files (working normally)
- **`stuck`**: Process running BUT no files created (process stuck)
- **`stopped`**: Process not running (service down)

#### **Incident Types Detected**:
- **"FFmpeg Got Stuck"**: `active` → `stuck` (process running but stopped creating files)
- **"FFmpeg Stopped"**: `active` → `stopped` (process died while working)
- **"FFmpeg Died"**: `stuck` → `stopped` (stuck process finally died)
- **"Monitor Got Stuck"**: `active` → `stuck` (monitor running but no JSON files)
- **"Monitor Stopped"**: `active` → `stopped` (monitor process died)
- **"Monitor Died"**: `stuck` → `stopped` (stuck monitor finally died)

#### **Timeline Analysis**:
- **"When"**: Exact time the incident was detected in database
- **"Worked For"**: How long the process worked before the incident
- **24-hour History**: Complete incident timeline for forensic analysis
- **Per-Device Tracking**: Separate incident tracking for each device and capture folder

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

### Device Metrics Table (Row 3)
- **Visualization**: Table
- **Columns**: Host, Device Name, Capture Folder, Video Device, CPU%, Memory%, Disk%, Uptime, FFmpeg, FFmpeg Uptime, FFmpeg Last, Monitor, Monitor Uptime, Monitor Last, Last Update
- **Per-Device Tracking**: Each row represents one device with individual status
- **Separate Timing**: FFmpeg and Monitor have independent last activity and uptime tracking
- **Real Names**: Uses actual device names from device registration
- **Data Source**: system_device_metrics table (per-device records)

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

The dashboard uses two main tables:

### `system_metrics` (Server Data)
- `host_name`: 'server' only
- `cpu_percent`, `memory_percent`, `disk_percent`: Server resource usage
- `uptime_seconds`: Server system uptime
- `timestamp`: Data collection time (synchronized to minute boundaries)

### `system_device_metrics` (Per-Device Data)
- `host_name`: Host machine identifier (sunri-pi1, sunri-pi3, etc.)
- `device_id`: Technical device ID (device1, device2, etc.)
- `device_name`: Real device name (Samsung TV Living Room, Fire TV Bedroom, etc.)
- `device_port`: Device port number
- `capture_folder`: Capture folder name (capture, capture1, capture2, etc.)
- `video_device`: Video hardware device path (/dev/video0, /dev/video2, etc.)
- `device_model`: Device model (samsung_tv, fire_tv, etc.)
- `cpu_percent`, `memory_percent`, `disk_percent`: Host resource usage (shared across devices)
- `uptime_seconds`: Host system uptime
- `ffmpeg_status`: Per-device FFmpeg status (active, stuck, stopped)
- `ffmpeg_uptime_seconds`: Duration FFmpeg was continuously active
- `ffmpeg_last_activity`: Timestamp when FFmpeg last created files
- `monitor_status`: Per-device Monitor status (active, stuck, stopped)
- `monitor_uptime_seconds`: Duration Monitor was continuously active
- `monitor_last_activity`: Timestamp when Monitor last created JSON files
- `timestamp`: Data collection time (synchronized to minute boundaries)
