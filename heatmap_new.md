# 24h Circular Heatmap System

## Overview

The new heatmap system provides **continuous 24-hour monitoring** with **zero-latency access** to device analysis data. It replaces the on-demand generation system with a **circular buffer** approach that pre-processes data every minute.

## Architecture

### **Circular Buffer Design**
- **1440 fixed files** in R2 storage (24h × 60min)
- **Time-based naming**: `HHMM.jpg` + `HHMM.json` (e.g., `1425.jpg`, `1425.json`)
- **Automatic overwrite**: Files replace themselves every 24 hours
- **No cleanup needed**: Storage size never grows beyond 1440 files

### **Data Flow**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Every Minute  │    │    Frontend      │    │   User Action   │
│                 │    │                  │    │                 │
│ 1. Get host data│    │ 1. Calculate     │    │ 1. Click device │
│ 2. Create mosaic│───▶│    timeline      │    │   with freeze   │
│ 3. Save HHMM.jpg│    │ 2. Load images   │    │ 2. Open modal   │
│ 4. Save HHMM.json    │ 3. Show analysis │    │ 3. View frames  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Implementation

### **Backend Service**

#### **HeatmapProcessor** (`backend_server/src/services/heatmap_processor.py`)
- **Continuous processing**: Runs every minute at :00 seconds
- **Host data collection**: Queries all registered hosts for analysis
- **Mosaic generation**: Creates grid layout from device screenshots
- **R2 upload**: Uses existing CloudflareUtils to save both image and JSON with time-only naming

```python
# Example file naming
now = datetime.now()
time_key = f"{now.hour:02d}{now.minute:02d}"  # "1425" for 2:25 PM

# Upload files
upload_to_r2(f"heatmaps/{time_key}.jpg", mosaic_image)
upload_to_r2(f"heatmaps/{time_key}.json", analysis_data)
```

#### **JSON Structure** (`HHMM.json`)
```json
{
  "time_key": "1425",
  "timestamp": "2024-09-24T14:25:00.000Z",
  "devices": [
    {
      "host_name": "pi-1",
      "device_id": "device1",
      "image_url": "http://pi-1/stream/capture1/captures/frame_001.jpg",
      "analysis_json": {
        "audio": true,
        "blackscreen": false,
        "freeze": false,
        "volume_percentage": 45,
        "mean_volume_db": -20,
        "freeze_diffs": [0.1, 0.2, 0.05],
        "last_3_filenames": ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"]
      }
    }
  ],
  "incidents_count": 0,
  "hosts_count": 3
}
```

### **Frontend Components**

#### **useHeatmapTimeline Hook** (`frontend/src/hooks/useHeatmapTimeline.ts`)
- **Timeline generation**: Creates 1440 timeline items automatically
- **Predictable URLs**: Calculates R2 URLs without API calls
- **Auto-refresh**: Updates timeline every minute
- **Analysis loading**: Fetches JSON data for current timeline position

```typescript
// Generate timeline items
const timeline = [];
for (let i = 0; i < 1440; i++) {
  const time = new Date(now.getTime() - (i * 60000));
  const timeKey = `${time.getHours().toString().padStart(2,'0')}${time.getMinutes().toString().padStart(2,'0')}`;
  
  timeline.push({
    timeKey,                                           // "1425"
    displayTime: time,                                 // Full Date object
    mosaicUrl: `${R2_URL}/heatmaps/${timeKey}.jpg`,   // Direct R2 access
    analysisUrl: `${R2_URL}/heatmaps/${timeKey}.json` // Direct R2 access
  });
}
```

#### **MosaicPlayer Component** (`frontend/src/components/MosaicPlayer.tsx`)
- **Image display**: Shows mosaic with error handling
- **Timeline scrubber**: 1440-position slider for navigation
- **Playback controls**: Auto-play through timeline
- **Status indicators**: Shows incidents and loading states

#### **Simplified Heatmap Page** (`frontend/src/pages/Heatmap.tsx`)
- **No generation UI**: Removed all on-demand generation controls
- **Always-ready data**: Timeline loads immediately on page open
- **Real-time updates**: New minute data appears automatically
- **Preserved features**: Freeze modal, analysis table, history

## Key Benefits

### **Performance**
- ⚡ **Instant loading**: No waiting for generation
- 🔄 **Always current**: Data updates every minute
- 📱 **Zero API calls**: Frontend calculates all URLs
- 💾 **Fixed storage**: Never exceeds 1440 files

### **User Experience**
- 🕐 **24h visibility**: Complete day view always available
- 🎯 **Precise navigation**: Jump to any minute instantly
- 🚨 **Real-time alerts**: Incidents appear as they happen
- 📊 **Continuous monitoring**: No gaps in coverage

### **Maintenance**
- 🔧 **Zero cleanup**: Circular buffer self-manages
- 📈 **Predictable load**: Consistent processing every minute
- 🛡️ **Fault tolerant**: Missing minutes show graceful errors
- 🔄 **Self-healing**: Errors resolve automatically next minute

## File Structure

### **New Files Created**
```
backend_server/src/services/
├── __init__.py                    # Service initialization
└── heatmap_processor.py          # Background processor

frontend/src/hooks/
└── useHeatmapTimeline.ts         # Timeline management hook

frontend/src/components/
└── MosaicPlayer.tsx              # Mosaic display component
```

### **Modified Files**
```
frontend/src/pages/Heatmap.tsx                           # Simplified page
frontend/src/components/heatmap/HeatMapAnalysisSection.tsx # Updated types
```

### **Deleted Files**
```
frontend/src/hooks/pages/useHeatmap.ts                   # Old generation hook
backend_server/src/routes/server_heatmap_routes.py       # Old API endpoints  
backend_server/src/lib/utils/heatmap_utils.py           # Old generation utils
```

## Deployment

### **1. Install and Start Service**
```bash
# Automatic installation (recommended)
./setup/local/install_server.sh

# Manual installation
sudo cp backend_server/config/services/heatmap_processor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable heatmap_processor
sudo systemctl start heatmap_processor

# Check status
sudo systemctl status heatmap_processor
sudo journalctl -u heatmap_processor -f
```

### **2. Environment Variables**
```bash
# Add to frontend .env
REACT_APP_CLOUDFLARE_R2_PUBLIC_URL=https://pub-your-bucket.r2.dev
```

### **3. Wait for Data Population**
- **First hour**: Partial timeline (only recent minutes)
- **After 24 hours**: Complete 24h timeline available
- **Graceful degradation**: Missing files show error messages

### **4. Verify Operation**
```bash
# Check R2 bucket for files
# Should see: 0000.jpg, 0000.json, 0001.jpg, 0001.json, etc.

# Check frontend timeline
# Should show 1440 timeline positions with current data
```

## Monitoring

### **Health Checks**
- **Processor logs**: Check for minute-by-minute processing
- **R2 file count**: Should remain at ~2880 files (1440 × 2)
- **Frontend errors**: Missing files indicate processor issues
- **Timeline gaps**: Show when processor was down

### **Performance Metrics**
- **Processing time**: Each minute should complete in <30 seconds
- **File sizes**: Mosaics ~100KB, JSON ~5KB per minute
- **Storage usage**: ~150MB total (fixed size)
- **Frontend load time**: <1 second (no API calls)

## Migration from Old System

### **Comparison**

| Aspect | Old System | New System |
|--------|------------|------------|
| **Data Access** | On-demand generation | Always available |
| **Wait Time** | 30-60 seconds | Instant |
| **Storage** | Growing database | Fixed 1440 files |
| **API Calls** | Multiple endpoints | Zero for viewing |
| **Maintenance** | Manual cleanup | Self-managing |
| **Code Size** | ~2000 lines | ~500 lines |

### **Migration Steps**
1. ✅ Deploy new processor service
2. ✅ Wait 24h for data population  
3. ✅ Switch frontend to new components
4. ✅ Remove old generation code
5. ✅ Clean up old database records (optional)

## Troubleshooting

### **Service Commands**
```bash
# Check service status
sudo systemctl status heatmap_processor

# View logs
sudo journalctl -u heatmap_processor -f

# Restart service
sudo systemctl restart heatmap_processor
```

### **Common Issues**

**Import/Module Errors**
- Ensure PYTHONPATH includes all required paths
- Service file sets: `PYTHONPATH=/home/sunri-pi1/virtualpytest:/home/sunri-pi1/virtualpytest/shared:/home/sunri-pi1/virtualpytest/backend_server`
- Uses `python -m src.services` which loads `__main__.py`

**No mosaic images showing**
- Check processor service is running
- Verify R2 credentials in `backend_server/src/.env`
- Required vars: `CLOUDFLARE_R2_ENDPOINT`, `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_R2_PUBLIC_URL`
- Check host connectivity for data collection

**Timeline shows errors**
- Normal for first 24h (partial data)
- Check processor logs for specific minute failures
- Verify host analysis endpoints are responding

**Analysis data missing**
- JSON files may be missing or corrupted
- Check host analysis data format
- Processor will retry next minute automatically

**Performance issues**
- Reduce mosaic image quality in processor
- Check R2 bandwidth limits
- Optimize host query timeouts

## Future Enhancements

### **Possible Improvements**
- **Incident timeline**: Color-code timeline ticks by incident type
- **Zoom levels**: Hour/day/week views with aggregated data
- **Real-time updates**: WebSocket for instant new minute notifications
- **Compression**: Optimize file sizes for longer retention
- **Alerting**: Push notifications for critical incidents

### **Scalability**
- **Multiple teams**: Separate R2 prefixes per team
- **Geographic distribution**: Regional R2 buckets
- **Load balancing**: Multiple processor instances
- **Caching**: CDN for frequently accessed files

---

**The new system transforms heatmap from reactive to proactive, providing instant access to 24h monitoring data with minimal code and zero maintenance overhead.**
