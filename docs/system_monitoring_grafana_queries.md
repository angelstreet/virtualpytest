# System Monitoring Grafana Dashboards

Updated documentation for the **System Server Monitoring** and **System Host Monitoring** dashboards.

## Dashboard Architecture

We have **two separate dashboards** that monitor different aspects of the system:

### 1. System Server Monitoring
- **Focus**: Backend server infrastructure monitoring
- **UID**: `system-monitoring`
- **Data Source**: `system_metrics` table (server-only data)
- **Panels**: 20 panels focused on server performance and availability

### 2. System Host Monitoring  
- **Focus**: Host machines and device availability monitoring
- **UID**: `fe85e054-7760-4133-8118-3dfe663dee66`
- **Data Source**: `system_metrics` + `system_device_metrics` tables
- **Panels**: 25 panels focused on host performance and device availability

## System Server Monitoring Dashboard

### Server Status Overview (Top Row - Stat Panels)

#### Server CPU Usage
```sql
SELECT ROUND(AVG(cpu_percent), 1) as "Server CPU %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

#### Server Memory Usage  
```sql
SELECT ROUND(AVG(memory_percent), 1) as "Server Memory %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

#### Server Disk Usage
```sql
SELECT ROUND(AVG(disk_percent), 1) as "Server Disk %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
```

#### Server Uptime
```sql
SELECT uptime_seconds as "Server Uptime"
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name = 'server'
ORDER BY timestamp DESC
LIMIT 1
```

### Server Availability Metrics (Time-Based Calculation)

#### Server Availability Formula
```
Expected Pings = Time Period × 60 minutes/hour × 24 hours/day
Available Pings = COUNT(records where server is responsive)
Availability % = (Available Pings / Expected Pings) × 100
```

#### Daily Server Availability (24h = 1,440 expected pings)
```sql
WITH server_availability AS (
    SELECT COUNT(*) as available_pings
    FROM system_metrics 
    WHERE host_name = 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
)
SELECT ROUND((available_pings * 100.0 / 1440), 0) as "Availability %"
FROM server_availability
```

#### Weekly Server Availability (7d = 10,080 expected pings)
```sql
WITH server_availability AS (
    SELECT COUNT(*) as available_pings
    FROM system_metrics 
    WHERE host_name = 'server'
      AND timestamp >= NOW() - INTERVAL '7 days'
)
SELECT ROUND((available_pings * 100.0 / 10080), 0) as "Availability %"
FROM server_availability
```

## System Host Monitoring Dashboard

### Host Status Overview (Top Row - Stat Panels)

#### Host CPU Usage (Average across all hosts)
```sql
SELECT ROUND(AVG(cpu_percent), 1) as "Host CPU %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name != 'server'
```

#### Host Memory Usage (Average across all hosts)
```sql
SELECT ROUND(AVG(memory_percent), 1) as "Host Memory %" 
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '5 minutes' 
  AND host_name != 'server'
```

#### Host Uptime (Latest uptime from any host)
```sql
WITH latest_host_metrics AS (
    SELECT DISTINCT ON (host_name) 
        host_name,
        uptime_seconds,
        timestamp
    FROM system_metrics 
    WHERE host_name != 'server'
    ORDER BY host_name, timestamp DESC
)
SELECT uptime_seconds as "Host Uptime"
FROM latest_host_metrics
ORDER BY uptime_seconds DESC
LIMIT 1
```

### Device Availability Monitoring (Core Feature)

The **Device Availability System** uses **time-based ping calculations** with **sophisticated service status logic**.

#### Device Availability Logic
```
Expected Pings Per Period:
- Daily (24h): 1,440 pings (24 × 60)
- Weekly (7d): 10,080 pings (7 × 24 × 60)  
- Monthly (30d): 43,200 pings (30 × 24 × 60)
- Yearly (365d): 525,600 pings (365 × 24 × 60)

Available Pings = COUNT(pings where ffmpeg_status = 'active' AND monitor_status = 'active')
Availability % = (Available Pings / Expected Pings) × 100
```

#### Device Status Classification
- **✅ Available**: `ffmpeg_status = 'active' AND monitor_status = 'active'`
- **❌ Unavailable**: Any other status (`stuck`, `inactive`, `stopped`, `NULL`)
- **Missing Pings**: Count as downtime (device not reporting)

#### Daily Device Availability (Left Panel)
```sql
WITH device_availability AS (
    SELECT 
        device_name,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY device_name
)
SELECT 
    device_name as "Device",
    ROUND((available_pings * 100.0 / 1440), 0) as "Availability %"
FROM device_availability
ORDER BY device_name
```

#### Daily Device Uptime/Downtime (Right Panel - Stacked)
```sql
WITH device_availability AS (
    SELECT 
        device_name,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY device_name
)
SELECT 
    device_name as "Device",
    ROUND((available_pings * 24.0 / 1440), 0) as "Uptime",
    ROUND(24 - (available_pings * 24.0 / 1440), 0) as "Downtime"
FROM device_availability
ORDER BY device_name
```

### Debug Tables

#### Host Debug Data
```sql
SELECT 
    host_name as "Host",
    TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI:SS') as "Last Update",
    uptime_seconds as "Uptime (sec)",
    CASE 
        WHEN uptime_seconds < 3600 THEN ROUND(uptime_seconds/60) || 'm' 
        WHEN uptime_seconds < 86400 THEN ROUND(uptime_seconds/3600, 1) || 'h' 
        ELSE ROUND(uptime_seconds/86400, 1) || 'd' 
    END as "Uptime (formatted)",
    cpu_percent as "CPU %",
    memory_percent as "Memory %",
    disk_percent as "Disk %",
    CASE 
        WHEN uptime_seconds > 0 THEN '✅ Online' 
        ELSE '❌ Offline' 
    END as "Host Status"
FROM system_metrics 
WHERE host_name != 'server'
ORDER BY timestamp DESC
LIMIT 10
```

#### Device Availability Debug Data
```sql
WITH latest_device_status AS (
    SELECT DISTINCT ON (device_name, host_name)
        device_name,
        host_name,
        timestamp as last_ping,
        ffmpeg_status as current_ffmpeg,
        monitor_status as current_monitor
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    ORDER BY device_name, host_name, timestamp DESC
),
device_availability_stats AS (
    SELECT 
        device_name,
        host_name,
        COUNT(*) as total_pings_received,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings,
        MAX(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN timestamp END) as last_available
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY device_name, host_name
)
SELECT 
    l.device_name as "Device",
    l.host_name as "Host",
    TO_CHAR(l.last_ping, 'YYYY-MM-DD HH24:MI:SS') as "Last Ping",
    TO_CHAR(s.last_available, 'YYYY-MM-DD HH24:MI:SS') as "Last Available",
    l.current_ffmpeg as "FFmpeg Status",
    l.current_monitor as "Monitor Status",
    s.total_pings_received as "Pings Received",
    1440 as "Expected Pings (24h)",
    s.available_pings as "Available Pings",
    ROUND((s.available_pings * 100.0 / 1440), 1) as "Availability % (24h)",
    CASE 
        WHEN l.current_ffmpeg = 'active' AND l.current_monitor = 'active' THEN '✅ Available' 
        ELSE '❌ Unavailable' 
    END as "Current Status",
    CASE 
        WHEN s.last_available IS NOT NULL 
        THEN ROUND(EXTRACT(EPOCH FROM (NOW() - s.last_available))/60, 1)
        ELSE NULL
    END as "Minutes Since Available"
FROM latest_device_status l
JOIN device_availability_stats s ON l.device_name = s.device_name AND l.host_name = s.host_name
ORDER BY l.last_ping DESC
```

## Key Features

### 1. Separated Monitoring Domains
- **Server Monitoring**: Backend infrastructure health and availability
- **Host Monitoring**: Host machines and device service availability
- **Clear Separation**: Different data sources and calculation methods

### 2. Time-Based Availability Calculation
- **Expected Pings**: Based on theoretical maximum (1 ping per minute)
- **Available Pings**: Only when both FFmpeg AND Monitor are active
- **Realistic Metrics**: Accounts for missing data as downtime
- **Coherent Panels**: Left (%) and right (time units) use same calculation base

### 3. Sophisticated Device Logic
- **Dual Service Requirement**: Device available only when BOTH services active
- **Status Classification**: 
  - `active` = Available ✅
  - `stuck`, `inactive`, `stopped`, `NULL` = Unavailable ❌
- **Missing Data Handling**: Counts as downtime (device not reporting)

### 4. Debug Capabilities
- **Host Debug**: Shows host machine health and uptime
- **Device Debug**: Shows device service status and availability calculations
- **Coherent Metrics**: Debug tables use same formulas as panels
- **Troubleshooting**: Compare received vs expected vs available pings

### 5. Panel Layout (8 Core Availability Panels)
```
┌─────────────────┬─────────────────────────┐
│ Daily Availability │   Daily Uptime/Downtime │
│    (% 0-100)       │     (Hours 0-24)        │
├─────────────────┼─────────────────────────┤
│ Weekly Availability│  Weekly Uptime/Downtime │
│    (% 0-100)       │      (Days 0-7)         │
├─────────────────┼─────────────────────────┤
│Monthly Availability│ Monthly Uptime/Downtime │
│    (% 0-100)       │     (Days 0-30)         │
├─────────────────┼─────────────────────────┤
│Yearly Availability │ Yearly Uptime/Downtime │
│    (% 0-100)       │     (Days 0-365)        │
└─────────────────┴─────────────────────────┘
```

## Database Schema

### `system_metrics` (Host & Server Data)
- **Server Data**: `host_name = 'server'` (backend server metrics)
- **Host Data**: `host_name != 'server'` (host machine metrics)
- **Fields**: `cpu_percent`, `memory_percent`, `disk_percent`, `uptime_seconds`
- **Frequency**: 1 record per minute per host/server

### `system_device_metrics` (Device-Level Data)
- **Device Data**: Per-device service status and metrics
- **Key Fields**: 
  - `device_name`: Device identifier
  - `host_name`: Which host runs this device
  - `ffmpeg_status`: FFmpeg service status (`active`, `stuck`, `inactive`)
  - `monitor_status`: Monitor service status (`active`, `stuck`, `inactive`)
- **Frequency**: 1 record per minute per device

### `system_incident` (Incident Management)
- **Incident Tracking**: Formal incident lifecycle management
- **Status Flow**: `open` → `in_progress` → `resolved` → `closed`
- **Integration**: Used in server dashboard for incident metrics

## Configuration Notes

### Panel Types
- **Stat Panels**: Single value displays (CPU, Memory, Disk, Uptime)
- **Bar Charts**: Availability percentages and uptime/downtime comparisons
- **Time Series**: Resource usage trends over time
- **Tables**: Debug data and detailed metrics

### Thresholds
- **Availability**: Red (0-90%), Yellow (90-95%), Green (95-100%)
- **Resource Usage**: Green (0-70%), Yellow (70-90%), Red (90-100%)
- **Uptime**: Red (0-1h), Yellow (1h-24h), Green (24h+)

### Refresh Rate
- **Both Dashboards**: 30-second auto-refresh
- **Time Range**: Last 24 hours default
- **Real-Time**: Near real-time monitoring with 1-minute data granularity