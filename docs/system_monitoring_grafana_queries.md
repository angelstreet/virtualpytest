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
  AND capture_folder IS NOT NULL 
  AND capture_folder != 'invalid_config'
ORDER BY timestamp
```

### Memory Usage Over Time (Per Device)
```sql
SELECT timestamp as time, 
       CONCAT(host_name, ' - ', device_name) as metric, 
       memory_percent as value 
FROM system_device_metrics 
WHERE $__timeFilter(timestamp) 
  AND capture_folder IS NOT NULL 
  AND capture_folder != 'invalid_config'
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
    AND capture_folder IS NOT NULL 
    AND capture_folder != 'invalid_config'
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

## Panel 4: Current Active Incidents (Critical Priority)

### Active Incidents - What's Broken RIGHT NOW
```sql
-- Shows incidents happening RIGHT NOW
SELECT 
    incident_id as "ID",
    device_name as "Device",
    capture_folder as "Folder",
    component as "Component",
    severity as "Severity",
    incident_type as "Type",
    ROUND(EXTRACT(EPOCH FROM (NOW() - detected_at))/60) as "Duration (min)",
    TO_CHAR(detected_at, 'HH24:MI:SS') as "Started",
    description as "Description"
FROM system_incident 
WHERE status IN ('open', 'in_progress')
  AND capture_folder IS NOT NULL 
  AND capture_folder != 'invalid_config'
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'high' THEN 2 
        WHEN 'medium' THEN 3 
        ELSE 4 
    END, 
    detected_at ASC;
```

## Panel 5: Device Availability (SLA Tracking)

### 24-Hour True Availability Percentage Per Device
```sql
-- Calculate TRUE availability accounting for both incidents and service reliability
WITH device_metrics AS (
    SELECT 
        device_name,
        capture_folder,
        COUNT(*) as total_minutes,
        -- Count minutes when both services are working properly
        COUNT(CASE 
            WHEN ffmpeg_status = 'active' AND monitor_status = 'active' 
            THEN 1 
        END) as healthy_minutes,
        -- Count minutes when services are stuck/stopped (service issues)
        COUNT(CASE 
            WHEN ffmpeg_status IN ('stuck', 'stopped', 'unknown') 
              OR monitor_status IN ('stuck', 'stopped', 'unknown')
            THEN 1 
        END) as service_issue_minutes
    FROM system_device_metrics 
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
      AND capture_folder IS NOT NULL  -- Exclude incomplete device configurations
      AND capture_folder != 'invalid_config'
    GROUP BY device_name, capture_folder
),
incident_downtime AS (
    SELECT 
        device_name,
        capture_folder,
        COALESCE(SUM(total_duration_minutes), 0) as incident_downtime_minutes
    FROM system_incident 
    WHERE detected_at >= NOW() - INTERVAL '24 hours'
      AND status IN ('resolved', 'closed')
      AND capture_folder IS NOT NULL  -- Exclude incomplete device configurations
      AND capture_folder != 'invalid_config'
    GROUP BY device_name, capture_folder
)
SELECT 
    dm.device_name as "Device",
    dm.capture_folder as "Folder",
    -- TRUE Availability = (Total Period - All Downtime) / Total Period * 100
    ROUND(((1440 - dm.service_issue_minutes - COALESCE(id.incident_downtime_minutes, 0)) * 100.0 / 1440), 2) as "Availability %",
    COALESCE(id.incident_downtime_minutes, 0) as "Incident Downtime (min)",
    dm.service_issue_minutes as "Service Issues (min)",
    (dm.service_issue_minutes + COALESCE(id.incident_downtime_minutes, 0)) as "Total Downtime (min)",
    (1440 - dm.service_issue_minutes - COALESCE(id.incident_downtime_minutes, 0)) as "Available Time (min)",
    CASE 
        WHEN ((1440 - dm.service_issue_minutes - COALESCE(id.incident_downtime_minutes, 0)) * 100.0 / 1440) >= 99.9 THEN '🟢 Excellent'
        WHEN ((1440 - dm.service_issue_minutes - COALESCE(id.incident_downtime_minutes, 0)) * 100.0 / 1440) >= 99.0 THEN '🟡 Good'
        WHEN ((1440 - dm.service_issue_minutes - COALESCE(id.incident_downtime_minutes, 0)) * 100.0 / 1440) >= 95.0 THEN '🟠 Fair'
        ELSE '🔴 Poor'
    END as "SLA Status"
FROM device_metrics dm
LEFT JOIN incident_downtime id ON dm.device_name = id.device_name 
    AND dm.capture_folder = id.capture_folder
ORDER BY "Availability %" DESC;
```

## Panel 6: Incident Summary Statistics

### High-Level Incident Metrics
```sql
-- High-level incident metrics
SELECT 
    COUNT(CASE WHEN status IN ('open', 'in_progress') THEN 1 END) as "Active Incidents",
    COUNT(CASE WHEN detected_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as "24h Incidents",
    COUNT(CASE WHEN detected_at >= NOW() - INTERVAL '7 days' THEN 1 END) as "7d Incidents",
    ROUND(AVG(CASE 
        WHEN status IN ('resolved', 'closed') AND total_duration_minutes IS NOT NULL 
        THEN total_duration_minutes 
    END), 1) as "Avg Resolution (min)",
    COUNT(CASE WHEN severity = 'critical' AND detected_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as "24h Critical"
FROM system_incident
WHERE capture_folder IS NOT NULL 
  AND capture_folder != 'invalid_config';
```

## Panel 7: Recent Incident History

### Recent Incidents with Resolution Status (Last 20)
```sql
-- Recent incidents with resolution status
SELECT 
    device_name as "Device",
    capture_folder as "Folder", 
    component as "Component",
    severity as "Severity",
    status as "Status",
    TO_CHAR(detected_at, 'MM-DD HH24:MI') as "Detected",
    CASE 
        WHEN status IN ('resolved', 'closed') THEN COALESCE(total_duration_minutes, 0) || 'm'
        ELSE ROUND(EXTRACT(EPOCH FROM (NOW() - detected_at))/60) || 'm (ongoing)'
    END as "Duration",
    COALESCE(resolution_notes, description) as "Notes"
FROM system_incident 
WHERE capture_folder IS NOT NULL 
  AND capture_folder != 'invalid_config'
ORDER BY detected_at DESC 
LIMIT 20;
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

### True Availability Calculation Methodology

The **True Availability System** provides comprehensive availability tracking that accounts for ALL types of downtime:

#### **🎯 True Availability Formula:**
```
Availability % = (Available Time / Total Period) × 100

Where:
Available Time = Total Period - Total Downtime
Total Downtime = Incident Downtime + Service Issues Time
```

#### **📊 Availability Components:**

1. **Total Period**: 24 hours (1440 minutes)
2. **Incident Downtime**: Duration of formal incidents (resolved/closed)
3. **Service Issues Time**: Time when services are stuck/stopped/unknown
4. **Available Time**: Time when both FFmpeg AND Monitor are "active"

#### **🔍 Service Status Classification:**
- **✅ Available**: `ffmpeg_status='active' AND monitor_status='active'`
- **❌ Service Issues**: Either service is `stuck`, `stopped`, or `unknown`
- **📋 Incident Downtime**: Formal incidents with tracked resolution time

#### **📈 Example Calculation:**
```
Device: sunri-pi1_Host
- Total Period: 1440 minutes (24 hours)
- Service Issues: 336 minutes (services stuck/stopped)
- Incident Downtime: 0 minutes (no formal incidents)
- Total Downtime: 336 minutes
- Available Time: 1104 minutes
- Availability: (1104 / 1440) × 100 = 76.67%
```

#### **💡 Why This Approach:**
- **Realistic**: Reflects actual service functionality, not just process existence
- **Comprehensive**: Accounts for both formal incidents AND service reliability issues
- **Actionable**: Clearly separates incident management from service reliability problems
- **Transparent**: Shows exactly where time is lost (incidents vs service issues)

#### **📊 New Table Columns:**
- **Device**: Device name
- **Folder**: Capture folder (capture1, capture2, etc.)
- **Availability %**: True availability percentage using formula above
- **Incident Downtime (min)**: Time lost to formal tracked incidents
- **Service Issues (min)**: Time lost to stuck/stopped services
- **Total Downtime (min)**: Incident Downtime + Service Issues
- **Available Time (min)**: Time when services were working properly
- **SLA Status**: Color-coded status based on availability percentage

### Incident Management System
The **New Incident Management System** provides complete incident lifecycle tracking:

#### **Incident Status Lifecycle**:
- **`open`**: Incident detected and needs attention
- **`in_progress`**: Incident is being actively worked on
- **`resolved`**: Issue fixed, service recovered
- **`closed`**: Incident confirmed resolved and documented

#### **Incident Types and Severity**:
- **FFmpeg Failure**: `critical` (stopped) or `high` (stuck)
- **Monitor Failure**: `critical` (stopped) or `high` (stuck)
- **Auto-Detection**: Prevents duplicate incidents for ongoing issues
- **Auto-Resolution**: Automatically resolves when services recover

#### **Real-Time Capabilities**:
- **Active Incidents**: Shows what's broken RIGHT NOW
- **Availability Tracking**: Real uptime percentages (99.9%, 99.0%, etc.)
- **SLA Compliance**: Color-coded availability status
- **MTTR Metrics**: Average resolution time tracking

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

### Device Availability Table (Row 5)
- **Visualization**: Table
- **Columns**: Device, Folder, Availability %, Incident Downtime (min), Service Issues (min), Total Downtime (min), Available Time (min), SLA Status
- **True Availability**: Accounts for both formal incidents AND service reliability issues
- **Transparent Breakdown**: Shows exactly where time is lost (incidents vs service problems)
- **Actionable Metrics**: Separates incident management from service reliability tracking
- **Data Source**: system_device_metrics + system_incident tables (combined analysis)

## New Dashboard Layout

```
┌──────────┬──────────┬──────────┬──────────┐
│Server CPU│Server Mem│Server Dsk│Server Up │  [Row 1: Server Stats]
│  (Stat)  │  (Stat)  │  (Stat)  │  (Stat)  │
└──────────┴──────────┴──────────┴──────────┘
┌─────────────────┬─────────────────────────┐
│   CPU Usage     │    Memory Usage         │  [Row 2: Time Series]
│  Over Time      │    Over Time            │
│ (Time Series)   │   (Time Series)         │
└─────────────────┴─────────────────────────┘
┌─────────────────────────────────────────────┐
│         Host Metrics & Process Status       │  [Row 3: Device Table]
│              (Comprehensive Table)          │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│          🚨 ACTIVE INCIDENTS 🚨             │  [Row 4: Critical - What's Broken NOW]
│               (Priority Table)              │
└─────────────────────────────────────────────┘
┌─────────────────┬─────────────────────────┐
│ Device Availability │  Incident Statistics │  [Row 5: SLA & Metrics]
│   (SLA Tracking)    │    (Summary Stats)   │
└─────────────────────┴─────────────────────┘
┌─────────────────────────────────────────────┐
│            Recent Incident History          │  [Row 6: Historical View]
│                  (Last 20)                  │
└─────────────────────────────────────────────┘
```

## Database Schema

The dashboard uses three main tables:

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

### `system_incident` (Incident Management) **NEW**
- `incident_id`: Primary key, auto-increment
- `incident_uuid`: Unique UUID for external references
- `host_name`, `device_id`, `device_name`, `capture_folder`: Device identification
- `incident_type`: 'ffmpeg_failure', 'monitor_failure', 'system_failure'
- `severity`: 'critical', 'high', 'medium', 'low'
- `component`: 'ffmpeg', 'monitor', 'system'
- `status`: 'open', 'in_progress', 'resolved', 'closed'
- `detected_at`: When incident was first detected
- `resolved_at`: When incident was resolved (auto or manual)
- `total_duration_minutes`: Complete incident duration
- `description`: Auto-generated incident description
- `resolution_notes`: How the incident was resolved
