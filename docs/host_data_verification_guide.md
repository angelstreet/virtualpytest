# Host Data Verification Guide

## Overview
This guide provides systematic SQL queries and procedures to quickly diagnose host availability issues, data collection gaps, and service status problems in the monitoring system.

## Quick Availability Check

### 1. Daily Availability Summary
```sql
WITH device_availability AS (
    SELECT 
        device_name,
        host_name,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings,
        COUNT(*) as total_pings
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY device_name, host_name
)
SELECT 
    device_name as "Device",
    host_name as "Host",
    total_pings as "Total Pings",
    available_pings as "Available Pings",
    ROUND((available_pings * 100.0 / 1440), 1) as "Availability %",
    ROUND((total_pings * 100.0 / 1440), 1) as "Data Coverage %",
    CASE 
        WHEN total_pings < 1200 THEN '🔴 Data Collection Issue'
        WHEN available_pings < (total_pings * 0.95) THEN '🟡 Service Issue'
        ELSE '✅ Healthy'
    END as "Status"
FROM device_availability
ORDER BY "Availability %" ASC;
```

**Expected Results:**
- **Total Pings**: ~1440 (24h × 60min)
- **Data Coverage %**: Should be >95%
- **Availability %**: Should be >95% when data coverage is good

## Data Gap Analysis

### 2. Identify Data Collection Gaps
```sql
-- Find periods with missing data (gaps > 5 minutes)
WITH minute_series AS (
    SELECT generate_series(
        DATE_TRUNC('minute', NOW() - INTERVAL '24 hours'),
        DATE_TRUNC('minute', NOW()),
        INTERVAL '1 minute'
    ) as expected_minute
),
actual_data AS (
    SELECT DISTINCT DATE_TRUNC('minute', timestamp) as actual_minute
    FROM system_device_metrics 
    WHERE host_name = 'YOUR_HOST_NAME'  -- Replace with actual host
      AND device_name = 'YOUR_DEVICE_NAME'  -- Replace with actual device
      AND timestamp >= NOW() - INTERVAL '24 hours'
),
gaps AS (
    SELECT 
        ms.expected_minute,
        CASE WHEN ad.actual_minute IS NULL THEN 1 ELSE 0 END as is_missing
    FROM minute_series ms
    LEFT JOIN actual_data ad ON ms.expected_minute = ad.actual_minute
),
gap_groups AS (
    SELECT 
        expected_minute,
        is_missing,
        SUM(is_missing) OVER (ORDER BY expected_minute) - 
        ROW_NUMBER() OVER (PARTITION BY is_missing ORDER BY expected_minute) as gap_group
    FROM gaps
    WHERE is_missing = 1
),
gap_summary AS (
    SELECT 
        gap_group,
        MIN(expected_minute) as gap_start,
        MAX(expected_minute) as gap_end,
        COUNT(*) as gap_duration_minutes
    FROM gap_groups
    GROUP BY gap_group
    HAVING COUNT(*) >= 5  -- Only show gaps of 5+ minutes
)
SELECT 
    TO_CHAR(gap_start, 'YYYY-MM-DD HH24:MI') as "Gap Start",
    TO_CHAR(gap_end, 'YYYY-MM-DD HH24:MI') as "Gap End",
    gap_duration_minutes as "Duration (minutes)",
    CASE 
        WHEN gap_duration_minutes >= 60 THEN '🔴 Major Gap'
        WHEN gap_duration_minutes >= 30 THEN '🟡 Significant Gap'
        ELSE '⚠️ Minor Gap'
    END as "Severity"
FROM gap_summary
ORDER BY gap_start;
```

### 3. Hourly Data Coverage Analysis
```sql
-- Analyze data collection by hour to identify patterns
WITH hourly_coverage AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour_bucket,
        COUNT(*) as pings_in_hour,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings_in_hour,
        MIN(timestamp) as first_ping_in_hour,
        MAX(timestamp) as last_ping_in_hour
    FROM system_device_metrics 
    WHERE host_name = 'YOUR_HOST_NAME'  -- Replace with actual host
      AND device_name = 'YOUR_DEVICE_NAME'  -- Replace with actual device
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY DATE_TRUNC('hour', timestamp)
    ORDER BY hour_bucket
),
expected_hours AS (
    SELECT generate_series(
        DATE_TRUNC('hour', NOW() - INTERVAL '24 hours'),
        DATE_TRUNC('hour', NOW()),
        INTERVAL '1 hour'
    ) as expected_hour
)
SELECT 
    TO_CHAR(eh.expected_hour, 'YYYY-MM-DD HH24:00') as "Hour",
    COALESCE(hc.pings_in_hour, 0) as "Pings Received",
    COALESCE(hc.available_pings_in_hour, 0) as "Available Pings",
    CASE 
        WHEN hc.pings_in_hour IS NULL THEN '❌ No Data'
        WHEN hc.pings_in_hour < 50 THEN '⚠️ Low Data'
        WHEN hc.available_pings_in_hour = 0 THEN '🔴 All Unavailable'
        WHEN hc.available_pings_in_hour < hc.pings_in_hour THEN '🟡 Partial Available'
        ELSE '✅ Fully Available'
    END as "Status",
    TO_CHAR(hc.first_ping_in_hour, 'HH24:MI:SS') as "First Ping",
    TO_CHAR(hc.last_ping_in_hour, 'HH24:MI:SS') as "Last Ping"
FROM expected_hours eh
LEFT JOIN hourly_coverage hc ON eh.expected_hour = hc.hour_bucket
ORDER BY eh.expected_hour;
```

## Service Status Analysis

### 4. Service Status Breakdown
```sql
-- Analyze FFmpeg and Monitor service status
SELECT 
    host_name as "Host",
    device_name as "Device",
    COUNT(*) as "Total Records",
    
    -- Service status breakdown
    COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as "Both Active",
    COUNT(CASE WHEN ffmpeg_status = 'inactive' THEN 1 END) as "FFmpeg Inactive",
    COUNT(CASE WHEN monitor_status = 'inactive' THEN 1 END) as "Monitor Inactive",
    COUNT(CASE WHEN ffmpeg_status = 'inactive' AND monitor_status = 'inactive' THEN 1 END) as "Both Inactive",
    
    -- Percentages
    ROUND(COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) * 100.0 / COUNT(*), 1) as "Service Availability %",
    
    -- Time range
    MIN(timestamp) as "First Record",
    MAX(timestamp) as "Last Record"
    
FROM system_device_metrics 
WHERE host_name != 'server'
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY host_name, device_name
ORDER BY "Service Availability %" ASC;
```

### 5. Recent Status Changes
```sql
-- Find recent status changes that might indicate issues
SELECT 
    host_name as "Host",
    device_name as "Device",
    timestamp as "Timestamp",
    ffmpeg_status as "FFmpeg",
    monitor_status as "Monitor",
    LAG(ffmpeg_status) OVER (PARTITION BY host_name, device_name ORDER BY timestamp) as "Prev FFmpeg",
    LAG(monitor_status) OVER (PARTITION BY host_name, device_name ORDER BY timestamp) as "Prev Monitor",
    CASE 
        WHEN ffmpeg_status != LAG(ffmpeg_status) OVER (PARTITION BY host_name, device_name ORDER BY timestamp) 
             OR monitor_status != LAG(monitor_status) OVER (PARTITION BY host_name, device_name ORDER BY timestamp)
        THEN '🔄 Status Change'
        ELSE '➡️ No Change'
    END as "Change"
FROM system_device_metrics 
WHERE host_name != 'server'
  AND timestamp >= NOW() - INTERVAL '2 hours'
ORDER BY timestamp DESC
LIMIT 50;
```

## Host Health Overview

### 6. All Hosts Summary
```sql
-- Quick overview of all hosts
WITH latest_host_metrics AS (
    SELECT DISTINCT ON (host_name) 
        host_name, 
        timestamp, 
        cpu_percent, 
        memory_percent, 
        disk_percent, 
        uptime_seconds 
    FROM system_device_metrics 
    WHERE host_name != 'server'
    ORDER BY host_name, timestamp DESC
),
host_availability AS (
    SELECT 
        host_name,
        COUNT(CASE WHEN ffmpeg_status = 'active' AND monitor_status = 'active' THEN 1 END) as available_pings,
        COUNT(*) as total_pings
    FROM system_device_metrics 
    WHERE host_name != 'server'
      AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY host_name
)
SELECT 
    lhm.host_name as "Host", 
    ROUND(lhm.cpu_percent::numeric, 1) as "CPU %", 
    ROUND(lhm.memory_percent::numeric, 1) as "Memory %", 
    ROUND(lhm.disk_percent::numeric, 1) as "Disk %", 
    CASE 
        WHEN lhm.uptime_seconds < 3600 THEN ROUND(lhm.uptime_seconds/60) || 'm' 
        WHEN lhm.uptime_seconds < 86400 THEN ROUND(lhm.uptime_seconds/3600) || 'h' 
        ELSE ROUND(lhm.uptime_seconds/86400) || 'd' 
    END as "Uptime", 
    TO_CHAR(lhm.timestamp, 'HH24:MI:SS') as "Last Update",
    ha.total_pings as "24h Pings",
    ROUND((ha.available_pings * 100.0 / 1440), 1) as "Availability %",
    CASE 
        WHEN ha.total_pings < 1200 THEN '🔴 Data Issue'
        WHEN ha.available_pings < (ha.total_pings * 0.95) THEN '🟡 Service Issue'
        ELSE '✅ Healthy'
    END as "Status"
FROM latest_host_metrics lhm
LEFT JOIN host_availability ha ON lhm.host_name = ha.host_name
ORDER BY lhm.host_name;
```

## Troubleshooting Workflow

### Step 1: Quick Health Check
1. Run query #6 (All Hosts Summary) to get overview
2. Identify hosts with low availability or data issues

### Step 2: Detailed Analysis for Problem Hosts
1. Run query #1 (Daily Availability Summary) for specific host/device
2. If "Data Coverage %" is low, run query #2 (Data Gap Analysis)
3. If "Service Availability %" is low, run query #4 (Service Status Breakdown)

### Step 3: Pattern Analysis
1. Run query #3 (Hourly Coverage) to identify time-based patterns
2. Run query #5 (Recent Status Changes) to see recent issues

### Step 4: Root Cause Identification

#### Data Collection Issues (Low Data Coverage)
- **Symptoms**: Total pings < 1200, large gaps in data
- **Possible Causes**:
  - Network connectivity issues
  - Monitoring agent crashed/stopped
  - Host system issues (high CPU, memory, disk)
  - Power outages or reboots

#### Service Issues (Low Service Availability)
- **Symptoms**: Good data coverage but low service availability
- **Possible Causes**:
  - FFmpeg process issues
  - Monitor service problems
  - Application-level failures
  - Resource constraints

## Interpretation Guide

### Availability Metrics
- **>95%**: Excellent
- **90-95%**: Good, minor issues
- **80-90%**: Fair, investigate
- **<80%**: Poor, immediate attention needed

### Data Coverage Metrics
- **>95%**: Normal operation
- **85-95%**: Some collection issues
- **<85%**: Significant monitoring problems

### Common Patterns
- **Overnight gaps**: Scheduled maintenance or power saving
- **Regular hourly gaps**: Cron job conflicts or resource constraints
- **Random gaps**: Network instability or hardware issues
- **Service flapping**: Application restart loops or resource issues

## Quick Reference Commands

### Replace Placeholders
Before running queries, replace:
- `YOUR_HOST_NAME` with actual host name (e.g., 'sunri-pi3')
- `YOUR_DEVICE_NAME` with actual device name (e.g., 'Tizen7')

### Time Ranges
- Change `INTERVAL '24 hours'` to adjust analysis period
- Use `INTERVAL '7 days'` for weekly analysis
- Use `INTERVAL '1 hour'` for recent issues

### Grafana Integration
These queries can be used directly in Grafana panels by:
1. Setting datasource to your PostgreSQL connection
2. Using "Table" visualization for most queries
3. Setting appropriate refresh intervals (30s-5m)

## Emergency Quick Checks

### Is the host completely down?
```sql
SELECT host_name, MAX(timestamp) as last_seen
FROM system_device_metrics 
WHERE host_name != 'server'
  AND timestamp >= NOW() - INTERVAL '10 minutes'
GROUP BY host_name
ORDER BY last_seen DESC;
```

### Which devices are currently unavailable?
```sql
SELECT DISTINCT ON (device_name, host_name)
    device_name, host_name, timestamp, ffmpeg_status, monitor_status
FROM system_device_metrics 
WHERE host_name != 'server'
  AND timestamp >= NOW() - INTERVAL '5 minutes'
  AND (ffmpeg_status != 'active' OR monitor_status != 'active')
ORDER BY device_name, host_name, timestamp DESC;
```

---

**Note**: This guide assumes the standard monitoring setup with 1-minute ping intervals. Adjust expectations and thresholds based on your actual monitoring configuration.
