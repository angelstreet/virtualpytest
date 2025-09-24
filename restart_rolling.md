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

## Enhanced HLS Player Implementation

### Step 1: FFmpeg Rolling Buffer ✅
**File**: `backend_host/scripts/run_ffmpeg_and_rename_local.sh`
- Already configured for 24h retention (86,400 segments)

### Step 2: Enhanced HLS Player Component ✅
**File**: `frontend/src/components/video/EnhancedHLSPlayer.tsx`

```tsx
<EnhancedHLSPlayer 
  deviceId="device1"
  hostName="host1"
  width="100%"
  height={400}
/>
```

**Features:**
- **Live/24h Toggle**: Switch between live stream and 24h archive
- **Timeline Scrubber**: Navigate through 24h history (only in archive mode)
- **Custom Controls**: Play/pause, volume, fullscreen
- **Mode Indicators**: Clear visual feedback for current mode

### Step 3: Integration
Replace existing video players with `EnhancedHLSPlayer` component:

```tsx
// Instead of basic <video> or HLS player
<EnhancedHLSPlayer 
  deviceId={device.device_id}
  hostName={device.host_name}
/>
```

## File Changes Summary

### New Files Created
```
➕  frontend/src/components/video/EnhancedHLSPlayer.tsx  (new component)
```

### Files Modified
```
✅  backend_host/scripts/run_ffmpeg_and_rename_local.sh  (already configured)
✏️  frontend/src/pages/Rec.tsx  (removed separate rewind button)
```

### Zero Changes Required
- Backend endpoints (no new APIs needed)
- useRestart.ts hook (unchanged)
- Video processing pipeline (unchanged)
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
1. **FFmpeg**: Keeps 24h of segments (86,400 for hardware, 21,600 for VNC)
2. **Enhanced Player**: Every HLS player has Live/24h toggle at the top
3. **Live Mode**: Shows current stream with minimal delay
4. **24h Mode**: Shows full timeline scrubber for navigation
5. **Timeline**: User can scrub through entire 24-hour history

## Benefits
- **Better UX**: Toggle on every player, no separate buttons needed
- **Intuitive**: Clear Live vs Archive modes with visual indicators
- **Powerful**: Full timeline navigation in archive mode
- **Clean**: Single component handles both live and historical viewing
- **Minimal**: Only 1 new component, reuses existing HLS infrastructure
