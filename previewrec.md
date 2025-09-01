# RecHostPreview - Adaptive Video Streaming

## Overview
Smart video preview system that matches ffmpeg generation timing for optimal performance and eliminates 404 errors.

## Frame Generation Reality
- **ffmpeg**: Creates 1 frame every 200ms sequentially (0→1→2→3→4, then new timestamp)
- **Frontend**: Single 200ms loop matching ffmpeg timing
- **Result**: No more batch 404s, smooth continuous playback

## Architecture
### Single Loop System
- **One 200ms Loop**: Matches ffmpeg's natural generation rhythm
- **Frame Tracking**: Intelligent counter tracks next expected frame (0-4, cycles per timestamp)
- **Queue Management**: Rolling window of 3-5 frames ahead

### Frame Processing
- Try to preload next expected frame (just 1 image per cycle)
- If successful, add to queue (max 5 frames)
- If queue has images, display next one with smooth fading
- If frame not ready, skip silently (no 404 errors)

## Key Features
- ✅ Matches ffmpeg generation timing (200ms)
- ✅ Eliminates batch 404 errors
- ✅ Video-like continuous playback
- ✅ No loading states (keeps current image)
- ✅ Existing 2-image fading system preserved
- ✅ Intelligent frame counter with timestamp detection

## Implementation
- `RecHostPreview.tsx`: Single-loop system with frame tracking
- **Removed**: Batch thinking, dual loops, parallel fetching
- **Added**: Sequential frame generation matching ffmpeg timing
- **1.5s Initial Delay**: Only for first frame to ensure generation starts