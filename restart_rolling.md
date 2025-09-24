# Restart Rolling Buffer Implementation Plan

## Overview
Add a simple "Rewind" button alongside the existing "Restart" button. Clean implementation with minimal code changes - no legacy code, no backward compatibility, no fallbacks.

## Current State Analysis

### Existing Components
- **useRestart.ts**: Handles video generation, analysis, dubbing, and timing
- **FFmpeg Script**: `run_ffmpeg_and_rename_local.sh` - captures live streams  
- **Rec.tsx**: Has "Restart" button that calls `restartStreams()`

### Current Flow
1. User clicks "Restart" → generates 10-second video from current moment
2. Video analysis (audio, subtitles, descriptions)
3. Translation and dubbing capabilities

## New Architecture: Simple Dual Button System

### 1. Button Layout
```
Current: [Restart]
New:     [Rewind] [Restart]
```

- **Restart**: Existing functionality (unchanged)
- **Rewind**: New - generate video from 24h rolling buffer

### 2. Simple Implementation

#### A. FFmpeg Change (1 line)
```bash
# Change hls_list_size from 600 to 86400 (24h retention)
-hls_list_size 86400
```

#### B. New Backend Endpoint
```python
@router.post("/rewind/generate")
async def generate_rewind_video(request: RewindRequest):
    """Generate 10s video from X hours ago"""
```

#### C. New Frontend Button
```tsx
<Button onClick={handleRewind}>Rewind</Button>
```

## Simple Implementation Plan

### Step 1: FFmpeg Rolling Buffer (5 minutes)
**File**: `backend_host/scripts/run_ffmpeg_and_rename_local.sh`

```bash
# Line 111: Change from 600 to 86400
-hls_list_size 86400

# Line 147: Change from 150 to 21600  
-hls_list_size 21600
```

### Step 2: Backend Rewind Endpoint (30 minutes)
**File**: `backend_server/src/routes/restart_routes.py`

```python
@router.post("/rewind/generate")
async def generate_rewind_video(request: dict):
    """Generate 10s video from X hours ago"""
    hours_ago = request.get("hours_ago", 1)
    host_name = request.get("host_name")
    device_id = request.get("device_id")
    
    # Find segments from X hours ago
    # Concatenate 10 seconds worth
    # Return video URL
    
    return {"success": True, "video_url": "..."}
```

### Step 3: Add Rewind Button (15 minutes)
**File**: `frontend/src/pages/Rec.tsx`

```tsx
// Add next to existing Restart button (line 257)
<Button
  variant="outlined" 
  size="small"
  startIcon={<ReplayIcon />}
  onClick={handleRewind}
  sx={{ height: 32, minWidth: 120 }}
>
  Rewind
</Button>

const handleRewind = () => {
  // Simple: generate video from 1 hour ago
  // Later: add time picker
};
```

## File Changes Summary

### 3 Files to Modify
```
✏️  backend_host/scripts/run_ffmpeg_and_rename_local.sh  (2 lines)
✏️  backend_server/src/routes/restart_routes.py  (1 new endpoint)  
✏️  frontend/src/pages/Rec.tsx  (1 new button)
```

### Zero Changes Required
- useRestart.ts hook (unchanged)
- Video processing pipeline (unchanged)
- Analysis, dubbing, translation (unchanged)
- Database schemas (unchanged)

## Storage Requirements
- **Per Device**: ~40GB (24h rolling buffer)
- **Auto-cleanup**: FFmpeg handles segment deletion automatically

## Implementation Time
- **Total**: 50 minutes
- **Step 1**: 5 minutes (FFmpeg config)
- **Step 2**: 30 minutes (Backend endpoint)
- **Step 3**: 15 minutes (Frontend button)

## How It Works
1. **FFmpeg**: Keeps 24h of segments instead of 10 minutes
2. **Rewind Button**: Calls new endpoint with "hours_ago" parameter
3. **Backend**: Finds segments from X hours ago, concatenates 10 seconds
4. **Result**: Same video player shows historical footage

## Benefits
- **Simple**: Just 2 buttons side by side
- **Clean**: No mode switching, no complex UI
- **Fast**: Reuses existing video processing pipeline
- **Minimal**: Only 3 files changed, ~50 lines total
