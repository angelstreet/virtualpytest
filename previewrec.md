# RecHostPreview - Adaptive Video Streaming

## Overview
Smart video preview system that adapts frame rates based on device count for optimal performance.

## Adaptive Frame Rates
- **1-5 devices**: 3 FPS (~1667ms refill for 5 frames, preloading base, _2, _4)
- **6-10 devices**: 1 FPS (5000ms refill)  
- **11-20 devices**: 0.5 FPS (10000ms refill)
- **21+ devices**: 0.3 FPS (~16667ms refill)

## Architecture
### Two-Loop System
- **Display Loop**: Fixed 200ms for smooth UI transitions (consumes 1 frame per cycle)
- **Queue Refill Loop**: Adaptive timing matched to batch size and FPS (fetches 5 frames per refill)

### Queue Management
- Max 10 images per device
- Automatic cleanup of old frames
- Graceful handling of missing images
- Timestamp-aware batch replacement to prevent mixing old/new frames
- Parallel preloading of frames with post-sorting to maintain order

## Key Features
- ✅ Video-like continuous playback
- ✅ No loading states (keeps current image)
- ✅ Existing 2-image fading system preserved
- ✅ Scales from 1 to 32+ devices efficiently
- ✅ Backend-friendly staggered requests

## Implementation
- `useRec.ts`: Adaptive interval calculation
- `RecHostPreview.tsx`: Queue-based display system
- Removed: 30s polling, 1.5s delays
- Added: Continuous loops with smart queuing
