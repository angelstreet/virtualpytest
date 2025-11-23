# KPI Measurement System (Post-Processed)

## Overview

The KPI (Key Performance Indicator) Measurement System measures **actual perceived time** from navigation action execution to visual confirmation appearing on screen. This provides accurate performance metrics for navigation flows.

**Key Characteristics:**
- ⚡ **Post-processed**: Runs asynchronously after navigation (non-blocking)
- 📸 **Image-based**: Scans 5 FPS FFmpeg captures for visual confirmation
- 🎯 **Accurate**: Measures real user-perceived latency
- 🔄 **Automatic**: Triggered by navigation executor when configured
- 🛑 **Early exit**: Stops scanning at first match (efficient)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Navigation Execution                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │ Execute      │──▶│ Main Actions │──▶│ Success?     │       │
│  │ Navigation   │   │ Succeed?     │   │              │       │
│  └──────────────┘   └──────────────┘   └──────┬───────┘       │
│                                                │                 │
│                                         ✅ YES (main actions)   │
└────────────────────────────────────────────────┼────────────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────┐
                                    │ Queue KPI Measurement  │
                                    │ (if node has KPI refs) │
                                    └────────┬───────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              KPI Executor Service (Background)                  │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │ Python      │───▶│ Process      │───▶│ Scan Captures   │  │
│  │ Queue       │    │ Request      │    │ (5 FPS)         │  │
│  │ (FIFO)      │    │              │    │                 │  │
│  └─────────────┘    └──────────────┘    └────┬────────────┘  │
│                                               │                 │
│                                               ▼                 │
│                                    ┌──────────────────────┐    │
│                                    │ Match Found?         │    │
│                                    │ (image/text verify)  │    │
│                                    └─────┬────────────────┘    │
│                                          │                      │
│                                    YES ──┼── NO (continue)     │
│                                          │                      │
│                                          ▼                      │
│                                    ┌──────────────────────┐    │
│                                    │ Calculate KPI Time   │    │
│                                    │ Update Database      │    │
│                                    └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. **Configuration** (Node Level)

Each navigation node can have `kpi_references` configured - these are verifications that indicate the target state is reached.

**Example Node Configuration:**
```json
{
  "node_id": "home_screen",
  "label": "Home Screen",
  "kpi_references": [
    {
      "verification_type": "image",
      "reference_image": "home_logo.png",
      "threshold": 0.8,
      "timeout": 5000
    }
  ]
}
```

### 2. **Navigation Execution** (Trigger)

When navigation executor completes a step successfully:

```python
# navigation_executor.py (line 473)
if result.get('success', False) and result.get('main_actions_succeeded', False):
    # Only queue KPI if MAIN actions succeeded (not retry/failure)
    self._queue_kpi_measurement(
        step=step,
        action_timestamp=action_completion_timestamp,
        team_id=team_id
    )
```

**Critical Rules:**
- ✅ **Queue KPI**: Main actions succeeded without retry/failure
- ❌ **Skip KPI**: Retry actions were executed
- ❌ **Skip KPI**: Failure actions were executed
- ❌ **Skip KPI**: Node has no `kpi_references` configured

### 3. **Queueing Process**

```python
# navigation_executor.py (_queue_kpi_measurement)

# 1. Get node's KPI references from database
node_data = get_node_by_id(target_tree_id, target_node_id, team_id)
kpi_references = node_data['node'].get('kpi_references', [])

if not kpi_references:
    return  # Skip - no KPI configured

# 2. Get capture directory for this device
capture_dir = self._get_device_capture_dir()  # e.g., /var/www/html/stream/capture1/captures

# 3. Create execution result record (for storing KPI later)
execution_result_id = record_edge_execution(
    team_id=team_id,
    tree_id=target_tree_id,
    edge_id=edge_id,
    host_name=self.host_name,
    device_model=self.device_model,
    success=True,
    execution_time_ms=0,  # Will be updated by KPI
    message="KPI measurement queued"
)

# 4. Create request object
request = KPIMeasurementRequest(
    execution_result_id=execution_result_id,
    team_id=team_id,
    capture_dir=capture_dir,
    action_timestamp=action_timestamp,  # When action completed
    kpi_references=kpi_references,
    timeout_ms=timeout_ms
)

# 5. Send to queue
kpi_executor = get_kpi_executor()
kpi_executor.enqueue_measurement(request)
```

### 4. **Background Processing**

The KPI Executor service runs as a systemd service and continuously processes the queue:

```python
# kpi_executor.py (_worker_loop)

while self.running:
    # Wait for measurement request (1 second timeout)
    request = self.queue.get(timeout=1.0)
    
    # Process the measurement
    self._process_measurement(request)
    
    # Mark as done
    self.queue.task_done()
```

### 5. **Capture Scanning**

For each measurement request:

```python
# kpi_executor.py (_scan_until_match)

# 1. Calculate time window
end_timestamp = action_timestamp + (timeout_ms / 1000.0)

# 2. Find all captures in time window
pattern = os.path.join(capture_dir, "capture_*.jpg")
all_captures = []

for path in glob.glob(pattern):
    ts = os.path.getmtime(path)
    if action_timestamp <= ts <= end_timestamp:
        all_captures.append({'path': path, 'timestamp': ts})

# 3. Sort chronologically (oldest first)
all_captures.sort(key=lambda x: x['timestamp'])

# 4. Scan captures sequentially
for i, capture in enumerate(all_captures):
    all_refs_match = True
    
    # Run ALL verifications on this capture
    for kpi_ref in kpi_references:
        if verification_type == 'image':
            result = image_ctrl.execute_verification(kpi_ref, image_source_url=capture['path'])
        elif verification_type == 'text':
            result = text_ctrl.execute_verification(kpi_ref, image_source_url=capture['path'])
        
        if not result.get('success'):
            all_refs_match = False
            break
    
    # MATCH FOUND - stop immediately
    if all_refs_match:
        kpi_ms = int((capture['timestamp'] - action_timestamp) * 1000)
        return {'success': True, 'kpi_ms': kpi_ms}
```

### 6. **Database Update**

```python
# kpi_executor.py (_update_result)

update_data = {
    'kpi_measurement_success': True,
    'kpi_measurement_ms': 1234,  # Actual measured time
    'kpi_measurement_error': None
}

supabase.table('execution_results').update(update_data).eq(
    'id', execution_result_id
).eq('team_id', team_id).execute()
```

---

## Database Schema

### `execution_results` Table

Stores KPI measurements for each navigation edge execution:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `team_id` | UUID | Team identifier |
| `tree_id` | UUID | Navigation tree |
| `edge_id` | UUID | Navigation edge |
| `host_name` | TEXT | Device host |
| `device_model` | TEXT | Device model |
| `success` | BOOLEAN | Edge execution success |
| `execution_time_ms` | INTEGER | Edge execution time |
| `message` | TEXT | Result message |
| `kpi_measurement_success` | BOOLEAN | **KPI measurement success** |
| `kpi_measurement_ms` | INTEGER | **KPI measurement time (ms)** |
| `kpi_measurement_error` | TEXT | **KPI measurement error** |
| `created_at` | TIMESTAMP | Record creation time |

### `navigation_nodes` Table (KPI Configuration)

Each node can have `kpi_references` configured:

| Column | Type | Description |
|--------|------|-------------|
| `node_id` | UUID | Node identifier |
| `label` | TEXT | Node label |
| `verifications` | JSONB | Node verifications (manual checks) |
| `kpi_references` | JSONB | **KPI references (post-processed)** |

**Example `kpi_references`:**
```json
[
  {
    "verification_type": "image",
    "reference_image": "home_logo.png",
    "threshold": 0.85,
    "timeout": 5000,
    "region": {"x": 100, "y": 200, "width": 300, "height": 100}
  },
  {
    "verification_type": "text",
    "expected_text": "Welcome",
    "timeout": 3000
  }
]
```

---

## Service Deployment

### 1. **Service File**

Location: `backend_host/config/services/kpi-executor.service`

```ini
[Unit]
Description=VirtualPyTest KPI Measurement Executor Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=%USER%
Group=%USER%
WorkingDirectory=%PROJECT_ROOT%
Environment=PYTHONPATH=%PROJECT_ROOT%/shared/lib:%PROJECT_ROOT%/backend_host/src
Environment=PATH=%PROJECT_ROOT%/venv/bin:/usr/bin:/usr/local/bin
ExecStart=%PROJECT_ROOT%/venv/bin/python backend_host/scripts/kpi_executor.py
Restart=always
RestartSec=10
StandardOutput=append:/tmp/kpi_executor_service.log
StandardError=append:/tmp/kpi_executor_service.log

# Security
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### 2. **Installation**

The service is installed by `setup/local/install_host_services.sh`:

```bash
# Install KPI executor service
sudo cp backend_host/config/services/kpi-executor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kpi-executor.service
sudo systemctl start kpi-executor.service
```

### 3. **Service Management**

```bash
# Start service
sudo systemctl start kpi-executor.service

# Stop service
sudo systemctl stop kpi-executor.service

# Restart service
sudo systemctl restart kpi-executor.service

# Check status
sudo systemctl status kpi-executor.service

# View logs
tail -f /tmp/kpi_executor_service.log

# View systemd journal
journalctl -u kpi-executor.service -f
```

---

## Configuration Guide

### Node KPI References

Configure KPI references in the Navigation Editor for each node:

#### **Image Verification KPI**

Checks if a specific image appears on screen:

```json
{
  "verification_type": "image",
  "reference_image": "login_success_icon.png",
  "threshold": 0.85,
  "timeout": 5000,
  "region": {
    "x": 100,
    "y": 200,
    "width": 300,
    "height": 100
  }
}
```

**Parameters:**
- `reference_image`: Image file stored in database (base64) or S3
- `threshold`: Match confidence (0.0 - 1.0)
- `timeout`: Maximum time to wait (ms)
- `region`: Optional - limit search to specific screen area

#### **Text Verification KPI**

Checks if specific text appears on screen (OCR):

```json
{
  "verification_type": "text",
  "expected_text": "Home",
  "case_sensitive": false,
  "timeout": 3000,
  "region": {
    "x": 0,
    "y": 0,
    "width": 1080,
    "height": 200
  }
}
```

**Parameters:**
- `expected_text`: Text to find via OCR
- `case_sensitive`: Whether to match case exactly
- `timeout`: Maximum time to wait (ms)
- `region`: Optional - limit OCR to specific area

### Multiple KPI References

You can configure **multiple** KPI references - **ALL must match** for success:

```json
{
  "node_id": "dashboard",
  "kpi_references": [
    {
      "verification_type": "image",
      "reference_image": "dashboard_logo.png",
      "threshold": 0.9,
      "timeout": 5000
    },
    {
      "verification_type": "text",
      "expected_text": "Dashboard",
      "timeout": 5000
    }
  ]
}
```

**Behavior:**
- Scans each capture for **both** logo AND text
- Only succeeds when **both** are found in same capture
- Provides higher confidence that target state is reached

---

## Monitoring and Troubleshooting

### Service Logs

**Main service log:**
```bash
tail -f /tmp/kpi_executor_service.log
```

**Example output:**
```
2025-10-01 14:32:15 [INFO] 🚀 [KPIExecutor Service] Starting KPI Executor Service
2025-10-01 14:32:15 [INFO] 🔧 [KPIExecutor] Initialized (queue capacity: 1000)
2025-10-01 14:32:15 [INFO] ✅ [KPIExecutor] Worker thread started
2025-10-01 14:32:15 [INFO] ✅ [KPIExecutor Service] Service running, waiting for KPI measurement requests...
2025-10-01 14:35:42 [INFO] 📋 [KPIExecutor] Queued KPI measurement (queue size: 1)
2025-10-01 14:35:42 [INFO] 🔍 [KPIExecutor] Processing KPI measurement
2025-10-01 14:35:42 [INFO]    • Execution result: a1b2c3d4
2025-10-01 14:35:42 [INFO]    • Action timestamp: 14:35:40
2025-10-01 14:35:42 [INFO]    • Timeout: 5000ms
2025-10-01 14:35:42 [INFO]    • KPI references: 1
2025-10-01 14:35:42 [INFO] 📸 [KPIExecutor] Found 12 captures in time window
2025-10-01 14:35:43 [INFO] ✅ [KPIExecutor] KPI match found!
2025-10-01 14:35:43 [INFO]    • KPI duration: 1234ms
2025-10-01 14:35:43 [INFO]    • Captures scanned: 7
2025-10-01 14:35:43 [INFO] 💾 [KPIExecutor] Stored KPI result: 1234ms (success: True)
2025-10-01 14:35:43 [INFO] ⏱️ [KPIExecutor] Processing completed in 856ms
```

### Common Issues

#### **Issue: No captures found in time window**

```
❌ [KPIExecutor] KPI measurement failed: No captures found in time window
   • Captures scanned: 0
```

**Causes:**
- FFmpeg capture service not running
- Capture directory path incorrect
- Timeout too short (action timestamp + timeout before first capture)

**Solution:**
```bash
# Check FFmpeg service
sudo systemctl status ffmpeg-capture@device1.service

# Check capture directory
ls -lh /var/www/html/stream/capture1/captures/

# Increase timeout in KPI reference configuration
```

#### **Issue: No match found (timeout)**

```
❌ [KPIExecutor] KPI measurement failed: No match found in 25 captures (timeout 5000ms)
   • Captures scanned: 25
```

**Causes:**
- KPI reference image/text doesn't match actual screen
- Threshold too strict (image matching)
- Wrong region configured
- Visual element appears after timeout

**Solution:**
- Review reference image/text configuration
- Lower threshold (e.g., 0.85 → 0.75)
- Increase timeout
- Verify actual screen state in captures

#### **Issue: Queue full**

```
❌ [KPIExecutor] Queue full! Dropping KPI measurement request
```

**Causes:**
- Too many navigation operations (queue capacity: 1000)
- KPI executor service stopped/crashed
- Slow processing (verification taking too long)

**Solution:**
```bash
# Check service status
sudo systemctl status kpi-executor.service

# Restart service
sudo systemctl restart kpi-executor.service

# Check processing time in logs
grep "Processing completed" /tmp/kpi_executor_service.log
```

---

## Performance Metrics

### Queue Performance

- **Capacity**: 1000 requests
- **Processing time**: ~200-1000ms per request (depends on captures scanned)
- **Concurrency**: Single worker thread (sequential processing)

### Capture Scanning

- **FPS**: 5 captures per second (FFmpeg default)
- **Scan strategy**: Forward chronological (oldest → newest)
- **Early exit**: Stops at first match
- **Average scans**: 5-15 captures per measurement

### Database Impact

- **Writes**: 1 UPDATE per measurement
- **Table**: `execution_results`
- **Fields updated**: 3 (success, ms, error)

---

## API Access

### Query KPI Results

```python
from shared.src.lib.database.client import get_supabase

supabase = get_supabase()

# Get KPI results for specific edge
result = supabase.table('execution_results') \
    .select('*') \
    .eq('edge_id', edge_id) \
    .eq('team_id', team_id) \
    .order('created_at', desc=True) \
    .limit(10) \
    .execute()

for record in result.data:
    print(f"Edge: {record['edge_id']}")
    print(f"KPI Success: {record['kpi_measurement_success']}")
    print(f"KPI Time: {record['kpi_measurement_ms']}ms")
    print(f"Error: {record['kpi_measurement_error']}")
```

### Average KPI by Edge

```sql
SELECT 
    edge_id,
    COUNT(*) as measurements,
    AVG(kpi_measurement_ms) as avg_kpi_ms,
    MIN(kpi_measurement_ms) as min_kpi_ms,
    MAX(kpi_measurement_ms) as max_kpi_ms,
    SUM(CASE WHEN kpi_measurement_success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate
FROM execution_results
WHERE team_id = '...'
    AND kpi_measurement_ms IS NOT NULL
GROUP BY edge_id
ORDER BY avg_kpi_ms DESC;
```

---

## Best Practices

### 1. **KPI Reference Configuration**

✅ **DO:**
- Use simple, clear visual indicators (logos, icons, headers)
- Set reasonable timeouts (3000-5000ms typical)
- Use multiple references for critical navigation
- Test KPI references in NavigationEditor before deploying

❌ **DON'T:**
- Use complex images that change frequently
- Set very short timeouts (< 1000ms)
- Rely on text OCR alone (less reliable)
- Configure KPI for every single node (only key checkpoints)

### 2. **Performance Optimization**

✅ **DO:**
- Configure KPI only for important navigation milestones
- Use image matching over OCR when possible (faster)
- Specify regions to limit search area (faster matching)
- Monitor queue size in logs

❌ **DON'T:**
- Configure KPI for intermediate steps
- Use very large timeout values (> 10000ms)
- Leave service disabled (measurements won't happen)

### 3. **Monitoring**

✅ **DO:**
- Regularly check service logs for errors
- Monitor average KPI times for regressions
- Alert on high failure rates
- Review captures when KPI measurements fail

❌ **DON'T:**
- Ignore failed measurements
- Assume service is running (check status)
- Delete captures before KPI processing completes

---

## Integration with Other Services

### FFmpeg Capture Service

**Dependency**: KPI executor requires 5 FPS captures from FFmpeg

```bash
# FFmpeg capture service must be running
sudo systemctl status ffmpeg-capture@device1.service
```

**Capture format:**
- Location: `/var/www/html/stream/capture{N}/captures/`
- Format: `capture_YYYYMMDD_HHMMSS_mmm.jpg`
- FPS: 5 frames per second
- Retention: 24 hours (managed by cleanup service)

### Navigation Executor

**Integration**: Automatic queueing after successful navigation

```python
# navigation_executor.py automatically queues KPI when:
# 1. Navigation step succeeds
# 2. Main actions succeeded (no retry/failure)
# 3. Target node has kpi_references configured
```

### Execution Results Database

**Storage**: KPI results stored in same table as edge executions

```python
# Single record per navigation edge execution
# Updated with KPI measurements asynchronously
```

---

## Future Enhancements

### Planned Features

1. **Video Analysis KPI**
   - Detect motion/animation completion
   - Measure loading spinners disappearing
   - Analyze video transitions

2. **Multi-Device KPI Comparison**
   - Compare KPI across device models
   - Identify device-specific performance issues
   - Generate comparative reports

3. **Grafana Dashboard Integration**
   - Real-time KPI monitoring
   - Performance trend charts
   - Alert on KPI degradation

4. **Smart Timeout Adjustment**
   - Auto-adjust timeouts based on historical data
   - Reduce false negatives
   - Optimize scanning efficiency

---

## Summary

The KPI Measurement System provides **accurate, post-processed performance metrics** for navigation flows by:

1. ⚡ **Non-blocking**: Queues measurements asynchronously
2. 📸 **Visual confirmation**: Scans actual screen captures
3. 🎯 **Selective**: Only measures when main actions succeed
4. 🔧 **Configurable**: Per-node KPI references
5. 📊 **Trackable**: Stores results in database for analysis

**Key Benefits:**
- Measure real user-perceived latency
- Identify performance regressions
- Compare navigation flows
- Validate optimization efforts

---

## Related Documentation

- [SERVICE_EXECUTORS_GUIDE.md](../SERVICE_EXECUTORS_GUIDE.md) - Navigation/Action/Verification executors
- [CAPTURE_CONFIG.md](../backend_host/scripts/CAPTURE_CONFIG.md) - FFmpeg capture configuration
- [README.md](../backend_host/scripts/README.md) - Background services overview

