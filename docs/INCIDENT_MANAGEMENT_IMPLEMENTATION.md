# Incident Management System Implementation

## Overview

This document outlines the implementation of a proper incident management system to complement our existing device monitoring. Currently, we have excellent **detection capabilities** but lack proper **incident lifecycle management**.

## Current State Analysis

### What We Have ✅
- **Advanced Detection**: Sophisticated status transitions (`active` → `stuck` → `stopped`)
- **Granular Monitoring**: Per-device, per-process tracking (FFmpeg/Monitor)
- **Historical Analysis**: 24-hour incident timeline with forensics
- **Data Quality**: Minute-boundary synchronized metrics

### What We're Missing ❌
- **Active Incident Tracking**: No way to see "what's broken RIGHT NOW"
- **Incident Lifecycle**: No tracking from detection → resolution → closure
- **Availability Metrics**: No uptime percentages (99.9%, 99.0%, etc.)
- **SLA Compliance**: No availability reporting against targets
- **Automated Alerting**: No proactive notifications when incidents occur

## Required Implementation

### 1. New Database Table: `system_incident`

```sql
CREATE TABLE system_incident (
    -- Primary identification
    incident_id SERIAL PRIMARY KEY,
    incident_uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- Device/Process identification
    host_name VARCHAR(50) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    capture_folder VARCHAR(50) NOT NULL,
    video_device VARCHAR(50),
    
    -- Incident classification
    incident_type VARCHAR(50) NOT NULL, -- 'ffmpeg_failure', 'monitor_failure', 'system_failure'
    severity VARCHAR(20) NOT NULL,      -- 'critical', 'high', 'medium', 'low'
    component VARCHAR(50) NOT NULL,     -- 'ffmpeg', 'monitor', 'system'
    
    -- Status and lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- 'open', 'in_progress', 'resolved', 'closed'
    
    -- Timing
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- Duration calculations (in minutes)
    detection_to_ack_minutes INTEGER,
    ack_to_resolution_minutes INTEGER,
    total_duration_minutes INTEGER,
    
    -- Details
    description TEXT,
    root_cause TEXT,
    resolution_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_incident_status (status),
    INDEX idx_incident_device (device_name, capture_folder),
    INDEX idx_incident_detected (detected_at),
    INDEX idx_incident_type_severity (incident_type, severity)
);
```

### 2. Incident Detection Logic Enhancement

#### Current Detection (Keep)
Your existing transition detection in `system_monitoring_grafana_queries.md` is excellent for **forensic analysis**.

#### New Detection (Add)
We need **real-time incident creation** that:
1. **Creates incidents** when problems are detected
2. **Resolves incidents** when problems are fixed
3. **Prevents duplicates** for ongoing issues

#### Detection Rules

```sql
-- Rule 1: FFmpeg Failure Detection
INSERT INTO system_incident (
    host_name, device_id, device_name, capture_folder, video_device,
    incident_type, severity, component, status, detected_at, description
)
SELECT DISTINCT
    host_name, device_id, device_name, capture_folder, video_device,
    'ffmpeg_failure',
    CASE 
        WHEN ffmpeg_status = 'stopped' THEN 'critical'
        WHEN ffmpeg_status = 'stuck' THEN 'high'
    END,
    'ffmpeg',
    'open',
    timestamp,
    CASE 
        WHEN ffmpeg_status = 'stopped' THEN 'FFmpeg process has stopped completely'
        WHEN ffmpeg_status = 'stuck' THEN 'FFmpeg process is running but not creating files'
    END
FROM system_device_metrics sdm
WHERE ffmpeg_status IN ('stuck', 'stopped')
  AND timestamp >= NOW() - INTERVAL '5 minutes'
  AND NOT EXISTS (
    SELECT 1 FROM system_incident si 
    WHERE si.device_name = sdm.device_name 
      AND si.capture_folder = sdm.capture_folder
      AND si.component = 'ffmpeg'
      AND si.status IN ('open', 'in_progress')
  );

-- Rule 2: Monitor Failure Detection  
INSERT INTO system_incident (
    host_name, device_id, device_name, capture_folder, video_device,
    incident_type, severity, component, status, detected_at, description
)
SELECT DISTINCT
    host_name, device_id, device_name, capture_folder, video_device,
    'monitor_failure',
    CASE 
        WHEN monitor_status = 'stopped' THEN 'critical'
        WHEN monitor_status = 'stuck' THEN 'high'
    END,
    'monitor',
    'open',
    timestamp,
    CASE 
        WHEN monitor_status = 'stopped' THEN 'Monitor process has stopped completely'
        WHEN monitor_status = 'stuck' THEN 'Monitor process is running but not creating JSON files'
    END
FROM system_device_metrics sdm
WHERE monitor_status IN ('stuck', 'stopped')
  AND timestamp >= NOW() - INTERVAL '5 minutes'
  AND NOT EXISTS (
    SELECT 1 FROM system_incident si 
    WHERE si.device_name = sdm.device_name 
      AND si.capture_folder = sdm.capture_folder
      AND si.component = 'monitor'
      AND si.status IN ('open', 'in_progress')
  );
```

#### Auto-Resolution Logic

```sql
-- Auto-resolve FFmpeg incidents when service recovers
UPDATE system_incident 
SET 
    status = 'resolved',
    resolved_at = NOW(),
    total_duration_minutes = EXTRACT(EPOCH FROM (NOW() - detected_at))/60,
    resolution_notes = 'Auto-resolved: FFmpeg service recovered'
WHERE status IN ('open', 'in_progress')
  AND component = 'ffmpeg'
  AND (device_name, capture_folder) IN (
    SELECT device_name, capture_folder 
    FROM system_device_metrics 
    WHERE ffmpeg_status = 'active' 
      AND timestamp >= NOW() - INTERVAL '2 minutes'
  );

-- Auto-resolve Monitor incidents when service recovers  
UPDATE system_incident 
SET 
    status = 'resolved',
    resolved_at = NOW(),
    total_duration_minutes = EXTRACT(EPOCH FROM (NOW() - detected_at))/60,
    resolution_notes = 'Auto-resolved: Monitor service recovered'
WHERE status IN ('open', 'in_progress')
  AND component = 'monitor'
  AND (device_name, capture_folder) IN (
    SELECT device_name, capture_folder 
    FROM system_device_metrics 
    WHERE monitor_status = 'active' 
      AND timestamp >= NOW() - INTERVAL '2 minutes'
  );
```

### 3. New Grafana Dashboard Panels

#### Panel A: Current Active Incidents (Critical)
```sql
-- Shows incidents happening RIGHT NOW
SELECT 
    incident_id as "ID",
    device_name as "Device",
    capture_folder as "Folder",
    component as "Component",
    severity as "Severity",
    incident_type as "Type",
    EXTRACT(EPOCH FROM (NOW() - detected_at))/60 as "Duration (min)",
    TO_CHAR(detected_at, 'HH24:MI:SS') as "Started",
    description as "Description"
FROM system_incident 
WHERE status IN ('open', 'in_progress')
ORDER BY severity DESC, detected_at ASC;
```

#### Panel B: Device Availability (Last 24h)
```sql
-- Calculate availability percentage per device
WITH device_availability AS (
    SELECT 
        device_name,
        capture_folder,
        COUNT(*) as total_minutes,
        COUNT(CASE 
            WHEN ffmpeg_status = 'active' AND monitor_status = 'active' 
            THEN 1 
        END) as healthy_minutes
    FROM system_device_metrics 
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY device_name, capture_folder
),
incident_downtime AS (
    SELECT 
        device_name,
        capture_folder,
        COALESCE(SUM(total_duration_minutes), 0) as downtime_minutes
    FROM system_incident 
    WHERE detected_at >= NOW() - INTERVAL '24 hours'
      AND status IN ('resolved', 'closed')
    GROUP BY device_name, capture_folder
)
SELECT 
    da.device_name as "Device",
    da.capture_folder as "Folder",
    ROUND((da.healthy_minutes * 100.0 / da.total_minutes), 2) as "Availability %",
    COALESCE(id.downtime_minutes, 0) as "Downtime (min)",
    1440 - COALESCE(id.downtime_minutes, 0) as "Uptime (min)",
    CASE 
        WHEN (da.healthy_minutes * 100.0 / da.total_minutes) >= 99.9 THEN '🟢 Excellent'
        WHEN (da.healthy_minutes * 100.0 / da.total_minutes) >= 99.0 THEN '🟡 Good'
        WHEN (da.healthy_minutes * 100.0 / da.total_minutes) >= 95.0 THEN '🟠 Fair'
        ELSE '🔴 Poor'
    END as "SLA Status"
FROM device_availability da
LEFT JOIN incident_downtime id ON da.device_name = id.device_name 
    AND da.capture_folder = id.capture_folder
ORDER BY "Availability %" DESC;
```

#### Panel C: Incident Summary Stats
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
FROM system_incident;
```

#### Panel D: Recent Incident History (Last 20)
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
        WHEN status IN ('resolved', 'closed') THEN total_duration_minutes || 'm'
        ELSE EXTRACT(EPOCH FROM (NOW() - detected_at))/60 || 'm (ongoing)'
    END as "Duration",
    COALESCE(resolution_notes, description) as "Notes"
FROM system_incident 
ORDER BY detected_at DESC 
LIMIT 20;
```

### 4. Implementation Steps

#### Step 1: Database Setup
1. **Create the `system_incident` table** using the SQL schema above
2. **Add indexes** for performance optimization
3. **Test table creation** with sample data

#### Step 2: Detection Integration
1. **Create stored procedure** or scheduled job to run incident detection every 2-5 minutes
2. **Implement auto-resolution logic** to close incidents when services recover
3. **Test detection** by manually stopping/starting services

#### Step 3: Dashboard Updates
1. **Add new panels** to existing Grafana dashboard
2. **Configure refresh intervals** (30 seconds for active incidents, 1 minute for others)
3. **Set up color coding** for severity levels and SLA status

#### Step 4: Alerting Setup (Future)
1. **Configure Grafana alerts** for new incidents
2. **Set up notification channels** (email, Slack, etc.)
3. **Define escalation rules** based on severity and duration

### 5. Benefits After Implementation

#### Immediate Visibility
- **"What's broken right now?"** - Active incidents panel
- **"How reliable are my devices?"** - Availability percentages  
- **"Are we meeting SLA?"** - Color-coded compliance status

#### Operational Metrics
- **MTTR (Mean Time To Recovery)**: Average resolution time
- **MTBF (Mean Time Between Failures)**: Device reliability trends
- **Availability Tracking**: 99.9%, 99.0% compliance reporting

#### Incident Management
- **Lifecycle Tracking**: From detection → resolution → closure
- **Root Cause Analysis**: Structured incident documentation
- **Trend Analysis**: Identify recurring problems and patterns

## Implementation Strategy

### ⚠️ **NO LEGACY CODE OR BACKWARD COMPATIBILITY**

This implementation follows a **clean replacement approach**:

- **DELETE existing incident detection queries** from `system_monitoring_grafana_queries.md`
- **REPLACE with new incident management system** - no fallback mechanisms
- **NO parallel running** of old and new systems
- **COMPLETE migration** to new `system_incident` table approach

### Single-Phase Implementation
1. **Create `system_incident` table** (new clean schema)
2. **Delete old incident history panel** from Grafana dashboard  
3. **Replace with new incident management panels** (no backward compatibility)
4. **Implement detection/resolution logic** (clean new approach)
5. **Remove obsolete incident queries** from documentation

## Success Metrics

After implementation, you should be able to answer:

1. **"What devices are currently having problems?"** ✅
2. **"What was our uptime last week?"** ✅  
3. **"How quickly do we resolve incidents?"** ✅
4. **"Are we meeting our 99% availability target?"** ✅
5. **"Which devices are most/least reliable?"** ✅

This transforms your monitoring from **reactive forensics** to **proactive incident management**.
