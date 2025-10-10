# Automatic Zapping Detection Architecture

## ✅ Overview

Automatic zapping detection identifies channel changes by detecting blackscreen events followed by channel banners. It differentiates between:
- **Automatic zapping**: Triggered by our system actions (e.g., `live_chup`)
- **Manual zapping**: User pressed physical IR remote

## 📊 Database Layer - Uses Existing `zap_results` Table

### Schema (Updated)
```sql
CREATE TABLE zap_results (
    id uuid PRIMARY KEY,
    script_result_id uuid REFERENCES script_results(id), -- ✅ NOW NULLABLE
    team_id uuid NOT NULL,
    host_name text NOT NULL,
    device_name text NOT NULL,
    device_model text,
    execution_date timestamp with time zone NOT NULL,
    iteration_index integer NOT NULL,
    action_command text NOT NULL,
    duration_seconds numeric NOT NULL,
    
    -- Detection flags
    motion_detected boolean DEFAULT false,
    subtitles_detected boolean DEFAULT false,
    audio_speech_detected boolean DEFAULT false,
    blackscreen_freeze_detected boolean DEFAULT false,
    
    -- Channel info (from AI banner detection)
    channel_name text,
    channel_number text,
    program_name text,
    program_start_time text,
    program_end_time text,
    
    -- Metadata
    detection_method text,  -- 'automatic' or 'manual'
    blackscreen_freeze_duration_seconds numeric,
    ...
);
```

### Key Changes
- **`script_result_id` is now nullable** (migration: `18_zap_results_allow_null_script.sql`)
- When `script_result_id` is NULL → automatic zapping during monitoring
- When `script_result_id` is UUID → zapping from script execution

### Database Functions (Reused)
- `record_zap_iteration()` - Stores zapping events (now accepts `script_result_id: Optional[str]`)
- `get_zap_results()` - Retrieves zapping history
- `get_zap_summary_for_script()` - Gets script-specific zapping data

## 🔧 Backend Implementation

### 1. Shared Detection Utility
**File**: `shared/src/lib/utils/zapping_detector_utils.py`

**Key Function**: `detect_and_record_zapping()`
- ✅ **Reuses existing code** - no duplication!
- Uses device's `verification_video` controller
- Calls `analyze_channel_banner_ai()` from existing AI helpers
- Updates frame JSON with zapping metadata
- Writes to `live_events.json` for real-time display
- Stores in `zap_results` table using `record_zap_iteration()`

### 2. Capture Monitor Integration
**File**: `backend_host/scripts/capture_monitor.py`

**Trigger**: When blackscreen **ends** and duration < 2 seconds
- Reads action info from frame JSON (10-second correlation window)
- Calls `detect_and_record_zapping()`
- Logs result (automatic vs manual)

### 3. API Endpoints
**Server Route**: `/server/monitoring/live-events`
- Proxies request to host

**Host Route**: `/host/monitoring/live-events`
- Reads `live_events.json` from device metadata directory
- Filters expired events (> 10 seconds old)
- Returns active zapping events

## 🎨 Frontend Implementation

### 1. Type Definitions
**File**: `frontend/src/types/pages/Monitoring_Types.ts`

- `LiveMonitoringEvent` interface for real-time zapping events
- `MonitoringAnalysis` extended with zapping metadata

### 2. useMonitoring Hook
**File**: `frontend/src/hooks/monitoring/useMonitoring.ts`

- Polls `/server/monitoring/live-events` every 1 second
- Returns `liveEvents` array
- Auto-clears in archive mode

### 3. ActionHistory Component
**File**: `frontend/src/components/monitoring/ActionHistory.tsx`

**Visual Display**:
- 🟢 **Green badge**: "ZAP → BBC One (1)" - Automatic zapping
- 🟠 **Orange badge**: "MANUAL ZAP → ITV (2)" - Manual zapping
- 🔵 **Blue badge**: Regular actions

**Features**:
- Merges live events with regular actions
- Shows channel name, number, program
- Auto-removes after 10 seconds

## 🔄 Data Flow

```
1. Blackscreen event ends (< 2s) in capture_monitor.py
   ↓
2. Check frame JSON for recent action (< 10s)
   ↓
3. Analyze next frame for channel banner (AI)
   ↓
4. Update frame JSON with zapping metadata
   ↓
5. Write to live_events.json (expires in 10s)
   ↓
6. Store in zap_results table (script_result_id = NULL)
   ↓
7. Frontend polls live_events API (1s interval)
   ↓
8. ActionHistory displays with colored badges
```

## 🎯 Key Design Decisions

### ✅ Reuse Existing Code
- Uses `analyze_channel_banner_ai()` from device controllers
- Uses `record_zap_iteration()` from `zap_results_db`
- Single banner region configuration (same as `zap_executor`)

### ✅ Separate Live Events Channel
- Solves race condition (AI processing time vs frontend polling)
- `live_events.json` updated immediately after detection
- Events auto-expire (no cleanup needed)

### ✅ 10-Second Correlation Window
- Correlates blackscreen with recent action
- If action within 10s → "automatic"
- If no action → "manual"

### ✅ Database Integration
- `script_result_id = NULL` for monitoring-based detections
- `script_result_id = UUID` for script-based zapping
- All zapping data in ONE table
- Easy querying and analytics

## 📁 Files Modified/Created

### Backend
- ✅ `shared/src/lib/utils/zapping_detector_utils.py` (NEW - shared detection logic)
- ✅ `backend_host/scripts/capture_monitor.py` (MODIFIED - triggers detection)
- ✅ `shared/src/lib/supabase/zap_results_db.py` (MODIFIED - nullable script_result_id)
- ✅ `backend_server/src/routes/server_monitoring_routes.py` (MODIFIED - new endpoint)
- ✅ `backend_host/src/routes/host_monitoring_routes.py` (MODIFIED - new endpoint)
- ✅ `shared/src/lib/utils/storage_path_utils.py` (MODIFIED - reverse lookup function)
- ✅ `setup/db/18_zap_results_allow_null_script.sql` (NEW - schema migration)

### Frontend
- ✅ `frontend/src/types/pages/Monitoring_Types.ts` (MODIFIED - new interfaces)
- ✅ `frontend/src/hooks/monitoring/useMonitoring.ts` (MODIFIED - live events polling)
- ✅ `frontend/src/components/monitoring/ActionHistory.tsx` (MODIFIED - zapping display)
- ✅ `frontend/src/components/monitoring/MonitoringOverlay.tsx` (MODIFIED - pass live events)

## 🚀 Usage

### Automatic Detection (No Script)
```python
# In capture_monitor.py
if blackscreen_ended and duration_ms < 2000:
    action_info = self._read_action_from_frame_json(capture_folder, filename)
    result = detect_and_record_zapping(
        device_id=device_id,
        device_model=device_model,
        capture_folder=capture_folder,
        frame_filename=filename,
        blackscreen_duration_ms=duration_ms,
        action_info=action_info  # None if no recent action
    )
```

### Query Automatic Zapping
```python
# Get all automatic zapping (not part of scripts)
from shared.src.lib.supabase.zap_results_db import get_zap_results

results = get_zap_results(
    team_id='...',
    # Filter for monitoring-based zaps (no script_result_id)
)

auto_zaps = [r for r in results['zap_results'] if r['script_result_id'] is None]
```

## 🔍 Monitoring

### Live Events JSON Structure
```json
{
  "events": [
    {
      "event_id": "uuid",
      "event_type": "zapping",
      "timestamp": "2025-10-10T14:30:00Z",
      "frame_filename": "frame_001.jpg",
      "detection_type": "automatic",
      "blackscreen_duration_ms": 450,
      "channel_name": "BBC One",
      "channel_number": "1",
      "program_name": "News at Six",
      "confidence": 0.95,
      "expires_at": 1728569410,
      "action_command": "live_chup",
      "action_timestamp": 1728569399.5
    }
  ],
  "updated_at": "2025-10-10T14:30:00Z"
}
```

### Frame JSON Metadata
```json
{
  "timestamp": "2025-10-10T14:30:00Z",
  "last_action_executed": "live_chup",
  "last_action_timestamp": 1728569399.5,
  "blackscreen_detected": true,
  "zapping_detected": true,
  "zapping_channel_name": "BBC One",
  "zapping_channel_number": "1",
  "zapping_program_name": "News at Six",
  "zapping_confidence": 0.95,
  "zapping_blackscreen_duration_ms": 450,
  "zapping_detection_type": "automatic",
  "zapping_detected_at": "2025-10-10T14:30:01Z"
}
```

## 📊 Analytics Queries

### Zapping Speed (Time from Action to Channel Banner)
```sql
SELECT 
    action_command,
    AVG(blackscreen_freeze_duration_seconds) as avg_zap_time_seconds,
    COUNT(*) as total_zaps
FROM zap_results
WHERE 
    detection_method = 'automatic'
    AND script_result_id IS NULL  -- Only monitoring-based zaps
GROUP BY action_command;
```

### Manual vs Automatic Zapping Ratio
```sql
SELECT 
    detection_method,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM zap_results
WHERE script_result_id IS NULL
GROUP BY detection_method;
```

### Most Viewed Channels (from automatic zapping)
```sql
SELECT 
    channel_name,
    channel_number,
    COUNT(*) as zap_count
FROM zap_results
WHERE 
    script_result_id IS NULL
    AND channel_name IS NOT NULL
GROUP BY channel_name, channel_number
ORDER BY zap_count DESC
LIMIT 10;
```

