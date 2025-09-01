# RecHostPreview - Adaptive Video Streaming

## Overview
Smart video preview system that adapts frame rates based on device count for optimal performance.

## Adaptive Frame Rates
- **1-5 devices**: 5 FPS (200ms intervals)
- **6-10 devices**: 1 FPS (1000ms intervals)  
- **11-20 devices**: 0.5 FPS (2000ms intervals)
- **21+ devices**: 0.3 FPS (3333ms intervals)

## Architecture
### Two-Loop System
- **Display Loop**: Fixed 200ms for smooth UI transitions
- **Queue Refill Loop**: Adaptive timing based on device count

### Queue Management
- Max 10 images per device
- Automatic cleanup of old frames
- Graceful handling of missing images

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
