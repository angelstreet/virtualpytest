# System Monitoring Grafana Queries

SQL queries for system monitoring dashboard panels in Grafana.

## Panel 1: System Health Overview (Stat Panels)

### CPU Usage (Current)
```sql
SELECT 
  ROUND(AVG(cpu_percent), 1) as "CPU %"
FROM system_metrics 
WHERE $__timeFilter(timestamp)
  AND timestamp >= NOW() - INTERVAL '5 minutes'
```

### Memory Usage (Current)  
```sql
SELECT 
  ROUND(AVG(memory_percent), 1) as "Memory %"
FROM system_metrics 
WHERE $__timeFilter(timestamp)
  AND timestamp >= NOW() - INTERVAL '5 minutes'
```

### Disk Usage (Current)
```sql
SELECT 
  ROUND(AVG(disk_percent), 1) as "Disk %"
FROM system_metrics 
WHERE $__timeFilter(timestamp)
  AND timestamp >= NOW() - INTERVAL '5 minutes'
```

### System Uptime (Current)
```sql
SELECT 
  MAX(uptime_seconds) as "Uptime Seconds"
FROM system_metrics 
WHERE $__timeFilter(timestamp)
  AND timestamp >= NOW() - INTERVAL '5 minutes'
```

## Panel 2: System Metrics Over Time (Time Series)

### CPU, Memory, Disk Usage Trends
```sql
SELECT 
  $__timeGroup(timestamp, '1m') as time,
  AVG(cpu_percent) as "CPU %",
  AVG(memory_percent) as "Memory %", 
  AVG(disk_percent) as "Disk %"
FROM system_metrics
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

## Panel 3: Host Status Table

### Hosts and Server with Latest Metrics
```sql
WITH latest_metrics AS (
  SELECT DISTINCT ON (host_name)
    host_name,
    timestamp,
    cpu_percent,
    memory_percent,
    disk_percent,
    uptime_seconds,
    platform,
    ffmpeg_status,
    monitor_status
  FROM system_metrics
  WHERE $__timeFilter(timestamp)
  ORDER BY host_name, timestamp DESC
)
SELECT 
  CASE 
    WHEN host_name = 'server' THEN '🖥️ Server'
    ELSE '📱 ' || host_name
  END as "Host",
  platform as "Platform",
  ROUND(cpu_percent, 1) as "CPU %",
  ROUND(memory_percent, 1) as "Memory %",
  ROUND(disk_percent, 1) as "Disk %",
  CASE 
    WHEN host_name = 'server' THEN 'N/A'
    WHEN uptime_seconds < 3600 THEN ROUND(uptime_seconds/60) || 'm'
    WHEN uptime_seconds < 86400 THEN ROUND(uptime_seconds/3600) || 'h'
    ELSE ROUND(uptime_seconds/86400) || 'd'
  END as "Uptime",
  CASE 
    WHEN host_name = 'server' THEN 'N/A'
    ELSE (ffmpeg_status->>'status')
  END as "FFmpeg",
  CASE 
    WHEN host_name = 'server' THEN 'N/A'
    ELSE (monitor_status->>'status')
  END as "Monitor",
  TO_CHAR(timestamp, 'HH24:MI:SS') as "Last Seen"
FROM latest_metrics
ORDER BY 
  CASE WHEN host_name = 'server' THEN 0 ELSE 1 END,  -- Server first
  host_name
```

## Panel 4: FFmpeg Process Status (Table)

### FFmpeg Status by Host (Hosts Only)
```sql
WITH latest_metrics AS (
  SELECT DISTINCT ON (host_name)
    host_name,
    timestamp,
    ffmpeg_status
  FROM system_metrics
  WHERE $__timeFilter(timestamp)
    AND host_name != 'server'  -- Exclude server
  ORDER BY host_name, timestamp DESC
)
SELECT 
  host_name as "Host",
  (ffmpeg_status->>'status') as "Status",
  (ffmpeg_status->>'processes_running')::int as "Processes",
  CASE 
    WHEN (ffmpeg_status->>'status') = 'active' THEN '🟢 Active'
    WHEN (ffmpeg_status->>'status') = 'stuck' THEN '🟡 Stuck'
    WHEN (ffmpeg_status->>'status') = 'stopped' THEN '🔴 Stopped'
    ELSE '⚪ Unknown'
  END as "Health",
  TO_CHAR(timestamp, 'HH24:MI:SS') as "Last Check"
FROM latest_metrics
WHERE ffmpeg_status IS NOT NULL
ORDER BY host_name
```

## Panel 5: Monitor Process Status (Table)

### Capture Monitor Status by Host (Hosts Only)
```sql
WITH latest_metrics AS (
  SELECT DISTINCT ON (host_name)
    host_name,
    timestamp,
    monitor_status
  FROM system_metrics
  WHERE $__timeFilter(timestamp)
    AND host_name != 'server'  -- Exclude server
  ORDER BY host_name, timestamp DESC
)
SELECT 
  host_name as "Host",
  (monitor_status->>'status') as "Status",
  CASE WHEN (monitor_status->>'process_running')::boolean THEN 'Yes' ELSE 'No' END as "Process Running",
  CASE 
    WHEN (monitor_status->>'status') = 'active' THEN '🟢 Active'
    WHEN (monitor_status->>'status') = 'stuck' THEN '🟡 Stuck'  
    WHEN (monitor_status->>'status') = 'stopped' THEN '🔴 Stopped'
    ELSE '⚪ Unknown'
  END as "Health",
  TO_CHAR(timestamp, 'HH24:MI:SS') as "Last Check"
FROM latest_metrics
WHERE monitor_status IS NOT NULL
ORDER BY host_name
```

## Panel 6: Resource Usage Histogram (Bar Chart)

### Average Resource Usage by Host
```sql
SELECT 
  host_name as "Host",
  ROUND(AVG(cpu_percent), 1) as "CPU %",
  ROUND(AVG(memory_percent), 1) as "Memory %",
  ROUND(AVG(disk_percent), 1) as "Disk %"
FROM system_metrics
WHERE $__timeFilter(timestamp)
GROUP BY host_name
ORDER BY host_name
```

## Panel 7: System Alerts (Table)

### Hosts with High Resource Usage
```sql
WITH latest_metrics AS (
  SELECT DISTINCT ON (host_name)
    host_name,
    timestamp,
    cpu_percent,
    memory_percent,
    disk_percent,
    ffmpeg_status,
    monitor_status
  FROM system_metrics
  WHERE $__timeFilter(timestamp)
  ORDER BY host_name, timestamp DESC
),
alerts AS (
  SELECT 
    host_name,
    CASE 
      WHEN cpu_percent > 80 THEN 'High CPU: ' || ROUND(cpu_percent, 1) || '%'
      WHEN memory_percent > 85 THEN 'High Memory: ' || ROUND(memory_percent, 1) || '%'
      WHEN disk_percent > 90 THEN 'High Disk: ' || ROUND(disk_percent, 1) || '%'
      WHEN (ffmpeg_status->>'status') = 'stuck' THEN 'FFmpeg Stuck'
      WHEN (ffmpeg_status->>'status') = 'stopped' THEN 'FFmpeg Stopped'
      WHEN (monitor_status->>'status') = 'stuck' THEN 'Monitor Stuck'
      WHEN (monitor_status->>'status') = 'stopped' THEN 'Monitor Stopped'
      ELSE NULL
    END as alert_message,
    CASE 
      WHEN cpu_percent > 90 OR memory_percent > 95 OR disk_percent > 95 THEN 'Critical'
      WHEN cpu_percent > 80 OR memory_percent > 85 OR disk_percent > 90 THEN 'Warning'
      WHEN (ffmpeg_status->>'status') IN ('stuck', 'stopped') THEN 'Warning'
      WHEN (monitor_status->>'status') IN ('stuck', 'stopped') THEN 'Warning'
      ELSE 'Info'
    END as severity,
    timestamp
  FROM latest_metrics
)
SELECT 
  host_name as "Host",
  alert_message as "Alert",
  severity as "Severity",
  TO_CHAR(timestamp, 'HH24:MI:SS') as "Time"
FROM alerts
WHERE alert_message IS NOT NULL
ORDER BY 
  CASE severity 
    WHEN 'Critical' THEN 1 
    WHEN 'Warning' THEN 2 
    ELSE 3 
  END,
  host_name
```

## Panel Configuration Notes

### Stat Panels (Panels 1)
- **Visualization**: Stat
- **Unit**: Percent (0-100) for CPU/Memory/Disk, Seconds for Uptime
- **Thresholds**: 
  - Green: 0-70% (CPU/Memory), 0-80% (Disk)
  - Yellow: 70-85% (CPU/Memory), 80-90% (Disk)  
  - Red: 85%+ (CPU/Memory), 90%+ (Disk)

### Time Series (Panel 2)
- **Visualization**: Time Series
- **Y-Axis**: Percent (0-100)
- **Legend**: Show
- **Fill opacity**: 0.3

### Tables (Panels 3, 4, 5, 7)
- **Visualization**: Table
- **Field Overrides**: Color coding for Health/Severity columns
- **Cell display mode**: Color background for status columns

### Bar Chart (Panel 6)
- **Visualization**: Bar Chart
- **X-axis**: Host names
- **Y-axis**: Percentage values
- **Multiple series**: CPU, Memory, Disk

## Dashboard Layout

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   CPU %     │  Memory %   │   Disk %    │   Uptime    │
│   (Stat)    │   (Stat)    │   (Stat)    │   (Stat)    │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────────────────────────────────┐
│           System Metrics Over Time (Time Series)       │
└─────────────────────────────────────────────────────────┘
┌──────────────────────────┬──────────────────────────────┐
│    FFmpeg Status         │    Monitor Status            │
│      (Table)             │      (Table)                 │
└──────────────────────────┴──────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              Host Status Overview (Table)              │
└─────────────────────────────────────────────────────────┘
┌──────────────────────────┬──────────────────────────────┐
│  Resource Usage by Host  │    System Alerts             │
│     (Bar Chart)          │      (Table)                 │
└──────────────────────────┴──────────────────────────────┘
```
