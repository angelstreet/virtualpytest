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

## Implementation Plan

### Phase 1: Rolling Buffer Infrastructure (Week 1)

#### 1.1 FFmpeg Configuration Update
**File**: `backend_host/scripts/run_ffmpeg_and_rename_local.sh`

**Changes** (Minimal):
```bash
# Add dual playlist generation
# Current: -hls_list_size 600
# New:     -hls_list_size 86400 (for archive)
#          Generate live.m3u8 via post-processing
```

**Implementation**:
- Modify existing FFmpeg command to use 24h retention
- Add post-processing script to create live playlist
- No changes to core capture logic

#### 1.2 Nginx Dynamic Playlist Generator
**File**: `backend_server/config/nginx/sites-available/rolling-hls`

```nginx
# Generate live playlist (last 30 segments)
location ~ ^/stream/([^/]+)/live\.m3u8$ {
    content_by_lua_block {
        -- Dynamic generation of live playlist
        -- Returns last 30 segments for low latency
    }
}

# Serve archive playlist (full 24h)
location ~ ^/stream/([^/]+)/archive\.m3u8$ {
    alias /var/www/html/stream/$1/output.m3u8;
}
```

#### 1.3 Rolling Buffer Service
**File**: `backend_server/src/services/rolling_buffer_processor.py`

```python
class RollingBufferProcessor:
    """Manages 24h rolling buffer and metadata"""
    
    def __init__(self):
        self.buffer_duration = 24 * 3600  # 24 hours
        self.segment_duration = 1  # 1 second per segment
        
    async def get_timestamp_mapping(self, device_id: str) -> Dict:
        """Map segment numbers to actual timestamps"""
        
    async def find_segments_for_timerange(self, device_id: str, 
                                        start_time: datetime, 
                                        duration: int) -> List[str]:
        """Find segments for specific time range"""
        
    async def cleanup_old_segments(self, device_id: str):
        """Remove segments older than 24h"""
```

### Phase 2: Rewind Video Generator (Week 2)

#### 2.1 Rewind Generator Service
**File**: `backend_server/src/services/rewind_generator.py`

```python
class RewindGenerator:
    """Generate videos from rolling buffer segments"""
    
    async def generate_rewind_video(self, 
                                  device_id: str,
                                  timestamp: datetime,
                                  duration: int = 10) -> str:
        """
        Generate video from specific timestamp
        
        Args:
            device_id: Target device
            timestamp: Start time for video
            duration: Video length in seconds
            
        Returns:
            URL to generated video
        """
        
    async def get_available_timerange(self, device_id: str) -> Dict:
        """Get available time range for rewind"""
```

#### 2.2 Backend API Endpoints
**File**: `backend_server/src/routes/restart_routes.py`

```python
# New endpoints
@router.post("/rewind/generate")
async def generate_rewind_video(request: RewindRequest):
    """Generate video from rolling buffer"""
    
@router.get("/rewind/available-range/{device_id}")
async def get_available_range(device_id: str):
    """Get available time range for device"""
    
@router.get("/rewind/timeline/{device_id}")
async def get_timeline_data(device_id: str):
    """Get timeline metadata for UI"""
```

### Phase 3: Frontend Integration (Week 3)

#### 3.1 Hook Extension
**File**: `frontend/src/hooks/pages/useRestart.ts`

**Minimal Changes**:
```typescript
interface UseRestartReturn {
  // Existing properties...
  
  // New rewind properties
  isRewindMode: boolean;
  availableTimeRange: { start: Date; end: Date } | null;
  selectedTimestamp: Date | null;
  
  // New functions
  switchToRewindMode: () => void;
  switchToRestartMode: () => void;
  generateRewindVideo: (timestamp: Date, duration?: number) => Promise<void>;
  getAvailableTimeRange: () => Promise<void>;
}

export const useRestart = ({ host, device, includeAudioAnalysis }: UseRestartParams): UseRestartReturn => {
  // Existing state...
  
  // New rewind state
  const [isRewindMode, setIsRewindMode] = useState(false);
  const [availableTimeRange, setAvailableTimeRange] = useState<{ start: Date; end: Date } | null>(null);
  const [selectedTimestamp, setSelectedTimestamp] = useState<Date | null>(null);
  
  // New functions
  const switchToRewindMode = useCallback(async () => {
    setIsRewindMode(true);
    await getAvailableTimeRange();
  }, []);
  
  const switchToRestartMode = useCallback(() => {
    setIsRewindMode(false);
    setSelectedTimestamp(null);
  }, []);
  
  const generateRewindVideo = useCallback(async (timestamp: Date, duration = 10) => {
    // Call rewind API
    // Use existing video processing pipeline
  }, []);
  
  // Return extended API
  return {
    // Existing returns...
    isRewindMode,
    availableTimeRange,
    selectedTimestamp,
    switchToRewindMode,
    switchToRestartMode,
    generateRewindVideo,
    getAvailableTimeRange,
  };
};
```

#### 3.2 UI Component Updates
**File**: `frontend/src/components/RestartButton.tsx` → `frontend/src/components/VideoControls.tsx`

```tsx
interface VideoControlsProps {
  onRestart: () => void;
  onRewind: () => void;
  isRewindMode: boolean;
  isGenerating: boolean;
}

export const VideoControls: React.FC<VideoControlsProps> = ({
  onRestart,
  onRewind,
  isRewindMode,
  isGenerating
}) => {
  return (
    <div className="flex gap-2">
      <button
        onClick={onRewind}
        disabled={isGenerating}
        className={`px-4 py-2 rounded ${isRewindMode ? 'bg-blue-600' : 'bg-gray-600'}`}
      >
        📼 Rewind
      </button>
      <button
        onClick={onRestart}
        disabled={isGenerating}
        className={`px-4 py-2 rounded ${!isRewindMode ? 'bg-green-600' : 'bg-gray-600'}`}
      >
        🔄 Restart
      </button>
    </div>
  );
};
```

#### 3.3 Timeline Component
**File**: `frontend/src/components/RewindTimeline.tsx`

```tsx
interface RewindTimelineProps {
  availableRange: { start: Date; end: Date };
  selectedTimestamp: Date | null;
  onTimestampSelect: (timestamp: Date) => void;
  onGenerateVideo: () => void;
}

export const RewindTimeline: React.FC<RewindTimelineProps> = ({
  availableRange,
  selectedTimestamp,
  onTimestampSelect,
  onGenerateVideo
}) => {
  // Interactive timeline with 24h range
  // Click to select timestamp
  // Generate button
};
```

### Phase 4: Integration & Testing (Week 4)

#### 4.1 Service Integration
- Configure systemd services for rolling buffer
- Set up Nginx for dynamic playlists
- Test 24h retention and cleanup

#### 4.2 Frontend Integration
- Update existing components to use new VideoControls
- Add RewindTimeline to video pages
- Test mode switching and video generation

#### 4.3 Performance Optimization
- Monitor storage usage (35-40GB per device)
- Optimize segment cleanup
- Cache timeline metadata

## File Modifications Summary

### Minimal Changes Required

#### Backend Files
```
✏️  backend_host/scripts/run_ffmpeg_and_rename_local.sh  (2 lines changed)
➕  backend_server/src/services/rolling_buffer_processor.py  (new)
➕  backend_server/src/services/rewind_generator.py  (new)
✏️  backend_server/src/routes/restart_routes.py  (3 new endpoints)
➕  backend_server/config/nginx/sites-available/rolling-hls  (new)
```

#### Frontend Files
```
✏️  frontend/src/hooks/pages/useRestart.ts  (~50 lines added)
🔄  frontend/src/components/RestartButton.tsx → VideoControls.tsx  (rename + extend)
➕  frontend/src/components/RewindTimeline.tsx  (new)
✏️  frontend/src/pages/[...pages using restart]  (component name updates)
```

### Zero Changes Required
- Existing video processing pipeline
- Analysis, dubbing, translation systems
- Database schemas
- Authentication/authorization

## Storage Requirements

### Per Device (24h Rolling)
- **Hardware Device**: ~25GB continuous
- **VNC Device**: ~15GB continuous
- **Total for 2 devices**: ~40GB

### Cleanup Strategy
- Automatic cleanup of segments >24h old
- Rewind videos cached for 7 days
- Timeline metadata: ~1MB per device

## Deployment Strategy

### Phase 1: Infrastructure (No User Impact)
1. Deploy rolling buffer service
2. Update FFmpeg configuration
3. Configure Nginx dynamic playlists
4. Test 24h retention

### Phase 2: Backend API (No User Impact)
1. Deploy rewind generator service
2. Add new API endpoints
3. Test video generation from buffer

### Phase 3: Frontend (User-Visible Changes)
1. Deploy new VideoControls component
2. Add RewindTimeline component
3. Update existing pages
4. Feature announcement

### Phase 4: Monitoring & Optimization
1. Monitor storage usage
2. Optimize performance
3. User feedback integration

## Benefits

### User Experience
- **Instant Access**: 24h of historical video available
- **Familiar Interface**: Existing restart functionality unchanged
- **Progressive Enhancement**: New rewind feature adds value without disruption

### Technical Benefits
- **Minimal Code Changes**: Leverages existing infrastructure
- **Backward Compatible**: All existing features work unchanged
- **Scalable**: Easy to add more devices
- **Efficient**: Single stream, dual access patterns

### Operational Benefits
- **No Downtime**: Rolling deployment possible
- **Easy Rollback**: Can disable rewind feature without affecting restart
- **Monitoring**: Existing monitoring covers new components

## Risk Mitigation

### Storage Risks
- **Monitoring**: Disk usage alerts at 80% capacity
- **Cleanup**: Aggressive cleanup if storage critical
- **Fallback**: Reduce retention to 12h if needed

### Performance Risks
- **Load Testing**: Test with multiple concurrent rewind requests
- **Caching**: Cache timeline metadata and common video segments
- **Rate Limiting**: Limit rewind generation requests per user

### Integration Risks
- **Feature Flags**: Enable/disable rewind per device
- **Gradual Rollout**: Enable for subset of users first
- **Monitoring**: Track error rates and performance metrics

## Success Metrics

### Technical Metrics
- Storage usage within 40GB per device
- Rewind video generation <5 seconds
- 99.9% uptime for rolling buffer service
- <2 second timeline loading

### User Metrics
- Rewind feature adoption rate
- User satisfaction with historical access
- Reduced support tickets for "missed events"
- Increased session duration on video pages

## Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Infrastructure | Rolling buffer service, FFmpeg updates |
| 2 | Backend API | Rewind generator, API endpoints |
| 3 | Frontend | UI components, hook extensions |
| 4 | Integration | Testing, optimization, deployment |

## Conclusion

This plan provides a comprehensive approach to implementing 24-hour rolling buffer functionality with minimal disruption to existing systems. The dual-mode approach (Restart/Rewind) maintains familiar user experience while adding powerful new capabilities.

The implementation leverages existing infrastructure and follows established patterns, ensuring reliable delivery and easy maintenance.
