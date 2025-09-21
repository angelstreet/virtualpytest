# Host AV Routes Refactoring Migration Plan

## Overview

This document outlines the comprehensive plan to refactor the large `host_av_routes.py` file (1534 lines) by splitting monitoring and restart functionality into separate, focused route modules. This refactoring will improve maintainability, separation of concerns, and code organization without breaking existing functionality.

## Current State Analysis

### File Structure
```
backend_host/src/routes/host_av_routes.py (1534 lines)
├── Core AV functionality (12 endpoints)
├── Restart video system (8 endpoints) 
└── Monitoring system (2 endpoints)
```

### Identified Issues
- **Monolithic file**: Single file handling multiple distinct domains
- **Mixed concerns**: AV control, restart analysis, and monitoring in one module
- **Maintenance burden**: Large file difficult to navigate and modify
- **Code duplication**: Request deduplication logic specific to restart endpoints

### Dependencies Analysis
- **Common imports**: `Flask`, `request`, `jsonify`, `current_app`, `send_file`
- **Host utilities**: `get_controller`, `get_device_by_id` from `utils.host_utils`
- **Shared libraries**: Various utilities from `shared.lib.utils.*`
- **Request deduplication**: Threading-based logic for AI analysis endpoints

## Target Architecture

### New File Structure
```
backend_host/src/routes/
├── host_av_routes.py (reduced - core AV functionality)
├── host_restart_routes.py (new - restart video system)
└── host_monitoring_routes.py (new - monitoring system)
```

### Blueprint Organization
- **host_av_bp**: `/host/av/*` - Core AV operations
- **host_restart_bp**: `/host/restart/*` - Restart video analysis
- **host_monitoring_bp**: `/host/monitoring/*` - Monitoring operations

## Detailed Migration Plan

### Phase 1: Endpoint Analysis & Mapping

#### Core AV Endpoints (Remain in host_av_routes.py)
| Current Endpoint | Keep | Description |
|------------------|------|-------------|
| `/connect` | ✅ | AV controller connection |
| `/disconnect` | ✅ | AV controller disconnection |
| `/status` | ✅ | AV controller status |
| `/restartStream` | ✅ | Stream service restart |
| `/takeControl` | ✅ | AV system control |
| `/getStreamUrl` | ✅ | Stream URL retrieval |
| `/takeScreenshot` | ✅ | Temporary screenshot |
| `/saveScreenshot` | ✅ | Screenshot upload to R2 |
| `/startCapture` | ✅ | Video capture start |
| `/stopCapture` | ✅ | Video capture stop |
| `/images/screenshot/<filename>` | ✅ | Screenshot serving |
| `/images` | ✅ | Image/JSON file serving |

#### Restart Endpoints (Move to host_restart_routes.py)
| Current Endpoint | New Endpoint | Description |
|------------------|--------------|-------------|
| `/generateRestartVideo` | `/host/restart/generateVideo` | Generate video (4-call arch) |
| `/generateRestartVideoOnly` | `/host/restart/generateVideoOnly` | Generate video only |
| `/analyzeRestartAudio` | `/host/restart/analyzeAudio` | Audio transcript analysis |
| `/analyzeRestartSubtitles` | `/host/restart/analyzeSubtitles` | Subtitle analysis |
| `/analyzeRestartSummary` | `/host/restart/analyzeSummary` | Video summary analysis |
| `/analyzeRestartComplete` | `/host/restart/analyzeComplete` | Combined analysis |
| `/generateRestartReport` | `/host/restart/generateReport` | Report generation |
| `/analyzeRestartVideo` | `/host/restart/analyzeVideo` | Async AI analysis |

#### Monitoring Endpoints (Move to host_monitoring_routes.py)
| Current Endpoint | New Endpoint | Description |
|------------------|--------------|-------------|
| `/listCaptures` | `/host/monitoring/listCaptures` | List captured frames |
| `/monitoring/latest-json` | `/host/monitoring/latest-json` | Latest JSON analysis |

### Phase 2: Frontend Impact Analysis

#### Frontend Files Using Restart Endpoints
- **Primary**: `frontend/src/hooks/pages/useRestart.ts`
  - Uses: `generateRestartVideo`, `analyzeRestartAudio`, `analyzeRestartComplete`, `generateRestartReport`
  - **Impact**: None (server proxies maintain same URLs)

#### Frontend Files Using Monitoring Endpoints  
- **Primary**: `frontend/src/hooks/monitoring/useMonitoring.ts`
  - Uses: `monitoring/latest-json`
  - **Impact**: None (server proxies maintain same URLs)

#### Server Proxy Updates Required
**File**: `backend_server/src/routes/server_av_routes.py`

| Server Endpoint | Current Proxy Target | New Proxy Target |
|----------------|---------------------|------------------|
| `/server/av/generateRestartVideo` | `/host/av/generateRestartVideo` | `/host/restart/generateVideo` |
| `/server/av/analyzeRestartAudio` | `/host/av/analyzeRestartAudio` | `/host/restart/analyzeAudio` |
| `/server/av/analyzeRestartComplete` | `/host/av/analyzeRestartComplete` | `/host/restart/analyzeComplete` |
| `/server/av/generateRestartReport` | `/host/av/generateRestartReport` | `/host/restart/generateReport` |
| `/server/av/listCaptures` | `/host/av/listCaptures` | `/host/monitoring/listCaptures` |
| `/server/av/monitoring/latest-json` | `/host/av/monitoring/latest-json` | `/host/monitoring/latest-json` |

### Phase 3: Implementation Steps

#### Step 1: Create host_restart_routes.py
**File**: `backend_host/src/routes/host_restart_routes.py`

```python
"""
Host Restart Video Routes

This module contains restart video system endpoints for:
- Video generation and analysis
- AI-powered audio/subtitle analysis  
- Report generation
- Request deduplication for AI operations
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from src.lib.utils.host_utils import get_controller, get_device_by_id
import os
import threading
import time
import signal
from contextlib import contextmanager
from typing import Dict

# Create blueprint
host_restart_bp = Blueprint('host_restart', __name__, url_prefix='/host/restart')

# Request deduplication tracking (prevents duplicate AI analysis calls)
_active_requests: Dict[str, float] = {}  # request_key -> start_time
_request_lock = threading.Lock()

# Utility functions for request deduplication
def _get_request_key(endpoint: str, device_id: str, video_id: str) -> str:
    """Generate unique key for request deduplication"""
    return f"{endpoint}:{device_id}:{video_id}"

def _is_request_active(request_key: str) -> bool:
    """Check if request is already being processed"""
    # Implementation...

def _mark_request_active(request_key: str):
    """Mark request as active"""
    # Implementation...

def _mark_request_complete(request_key: str):
    """Mark request as complete"""
    # Implementation...

@contextmanager
def timeout(duration):
    """Timeout context manager for AI operations"""
    # Implementation...

# Restart endpoints (8 total)
@host_restart_bp.route('/generateVideo', methods=['POST'])
def generate_restart_video():
    """Generate video only - fast response (new 4-call architecture)"""
    # Move from host_av_routes.py

@host_restart_bp.route('/generateVideoOnly', methods=['POST']) 
def generate_restart_video_only():
    """Generate video only - fast response"""
    # Move from host_av_routes.py

@host_restart_bp.route('/analyzeAudio', methods=['POST'])
def analyze_restart_audio():
    """Analyze audio transcript"""
    # Move from host_av_routes.py with deduplication

@host_restart_bp.route('/analyzeSubtitles', methods=['POST'])
def analyze_restart_subtitles():
    """Analyze subtitles"""
    # Move from host_av_routes.py with deduplication

@host_restart_bp.route('/analyzeSummary', methods=['POST'])
def analyze_restart_summary():
    """Analyze video summary"""
    # Move from host_av_routes.py with deduplication

@host_restart_bp.route('/analyzeComplete', methods=['POST'])
def analyze_restart_complete():
    """Combined restart analysis: subtitles + summary in single call"""
    # Move from host_av_routes.py with deduplication

@host_restart_bp.route('/generateReport', methods=['POST'])
def generate_restart_report():
    """Generate report with all analysis data collected from frontend"""
    # Move from host_av_routes.py

@host_restart_bp.route('/analyzeVideo', methods=['POST'])
def analyze_restart_video():
    """Async AI analysis for restart video - subtitle detection + video descriptions"""
    # Move from host_av_routes.py
```

#### Step 2: Create host_monitoring_routes.py
**File**: `backend_host/src/routes/host_monitoring_routes.py`

```python
"""
Host Monitoring Routes

This module contains monitoring system endpoints for:
- Capture frame listing and management
- JSON analysis file retrieval
- Monitoring data access
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from src.lib.utils.host_utils import get_controller, get_device_by_id
import os
import re

# Create blueprint
host_monitoring_bp = Blueprint('host_monitoring', __name__, url_prefix='/host/monitoring')

@host_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """List captured frames for monitoring with URLs built like screenshots"""
    # Move from host_av_routes.py

@host_monitoring_bp.route('/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file for monitoring"""
    # Move from host_av_routes.py
```

#### Step 3: Update Route Registrations
**File**: `backend_host/src/app.py`

```python
# Add imports (line 69-88)
from routes import (
    host_control_routes, 
    host_web_routes,
    host_aiagent_routes,
    host_ai_generation_routes,
    host_aitestcase_routes,
    host_verification_routes,
    host_power_routes,
    host_av_routes,
    host_restart_routes,        # NEW
    host_monitoring_routes,     # NEW
    host_remote_routes,
    # ... existing imports
)

# Add blueprint registrations (line 92-112)
blueprints = [
    (host_control_routes.host_control_bp, 'Device control'),
    (host_web_routes.host_web_bp, 'Web automation'),
    (host_aiagent_routes.host_aiagent_bp, 'AI agent execution'),
    (host_ai_generation_routes.host_ai_generation_bp, 'AI interface generation'),
    (host_aitestcase_routes.host_aitestcase_bp, 'AI test case execution'),
    (host_verification_routes.host_verification_bp, 'Verification services'),
    (host_power_routes.host_power_bp, 'Power control'),
    (host_av_routes.host_av_bp, 'Audio/Video operations'),
    (host_restart_routes.host_restart_bp, 'Restart video system'),      # NEW
    (host_monitoring_routes.host_monitoring_bp, 'Monitoring system'),   # NEW
    (host_remote_routes.host_remote_bp, 'Remote device control'),
    # ... existing blueprints
]
```

**File**: `backend_host/src/routes/__init__.py`

```python
# Import all host route modules
from . import (
    host_control_routes,
    host_web_routes,
    host_aiagent_routes,
    host_aitestcase_routes,
    host_verification_routes,
    host_power_routes,
    host_av_routes,
    host_restart_routes,        # NEW
    host_monitoring_routes,     # NEW
    host_remote_routes,
    host_desktop_bash_routes,
    host_desktop_pyautogui_routes,
    host_script_routes,
    host_heatmap_routes,
    host_verification_appium_routes,
    host_verification_text_routes,
    host_verification_audio_routes,
    host_verification_adb_routes,
    host_verification_image_routes,
    host_verification_video_routes  # ADD MISSING
)
```

#### Step 4: Update Server Proxy Routes
**File**: `backend_server/src/routes/server_av_routes.py`

Update proxy targets for restart endpoints:
```python
# Line ~548: generateRestartVideo
response_data, status_code = proxy_to_host_with_params(
    '/host/restart/generateVideo',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~570: analyzeRestartAudio  
response_data, status_code = proxy_to_host_with_params(
    '/host/restart/analyzeAudio',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~592: generateRestartReport
response_data, status_code = proxy_to_host_with_params(
    '/host/restart/generateReport',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~614: analyzeRestartComplete
response_data, status_code = proxy_to_host_with_params(
    '/host/restart/analyzeComplete',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~650: analyzeRestartVideo
response_data, status_code = proxy_to_host_with_params(
    '/host/restart/analyzeVideo',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~867: listCaptures
response_data, status_code = proxy_to_host_with_params(
    '/host/monitoring/listCaptures',  # CHANGED
    'POST',
    request_data,
    query_params
)

# Line ~903: monitoring/latest-json
response_data, status_code = proxy_to_host_with_params(
    '/host/monitoring/latest-json',  # UNCHANGED (already correct)
    'POST',
    request_data,
    query_params
)
```

#### Step 5: Clean host_av_routes.py
Remove moved endpoints and dependencies:

```python
"""
Host Audio/Video Routes

This module contains the host-specific audio/video API endpoints for:
- AV controller connection management
- Video capture control  
- Screenshot capture

These endpoints run on the host and use the host's own stored device object.
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from src.lib.utils.host_utils import get_controller, get_device_by_id
import os
import time

# Create blueprint
host_av_bp = Blueprint('host_av', __name__, url_prefix='/host/av')

# REMOVE: Request deduplication tracking (moved to restart routes)
# REMOVE: All restart-related endpoints (8 endpoints)
# REMOVE: All monitoring-related endpoints (2 endpoints)

# KEEP: Core AV endpoints (12 endpoints)
@host_av_bp.route('/connect', methods=['POST'])
def connect():
    # Keep existing implementation

@host_av_bp.route('/disconnect', methods=['POST']) 
def disconnect():
    # Keep existing implementation

# ... keep all other core AV endpoints
```

### Phase 4: Testing & Validation

#### Pre-Migration Testing
1. **Endpoint inventory**: Document all current endpoints and their functionality
2. **Integration tests**: Verify current restart and monitoring flows work
3. **Frontend validation**: Confirm useRestart and useMonitoring hooks function correctly

#### Post-Migration Testing  
1. **Route registration**: Verify new blueprints register successfully
2. **Endpoint accessibility**: Test all endpoints respond correctly
3. **Frontend compatibility**: Confirm no breaking changes to frontend
4. **Server proxy validation**: Verify proxy routes forward to correct new endpoints
5. **Deduplication testing**: Confirm request deduplication works in new restart routes

#### Rollback Plan
1. **Git branch**: Perform migration in feature branch
2. **Backup strategy**: Keep original host_av_routes.py until validation complete
3. **Quick revert**: Ability to restore original file if issues arise

### Phase 5: Documentation & Cleanup

#### Documentation Updates
1. **API documentation**: Update endpoint documentation with new URLs
2. **Architecture docs**: Update system architecture diagrams
3. **Developer guides**: Update development setup instructions

#### Code Cleanup
1. **Remove obsolete code**: Delete moved endpoints from host_av_routes.py
2. **Import optimization**: Clean up unused imports
3. **Comment updates**: Update file headers and comments

## Risk Assessment & Mitigation

### High Risk Items
1. **Blueprint registration failures**: Mitigate with comprehensive testing
2. **Import path issues**: Validate all imports before deployment
3. **Proxy URL mismatches**: Double-check all server proxy updates

### Medium Risk Items  
1. **Request deduplication logic**: Thoroughly test moved threading code
2. **Timeout handling**: Verify signal handling works in new context
3. **Error handling**: Ensure error responses maintain same format

### Low Risk Items
1. **Performance impact**: Minimal - same code, different organization
2. **Memory usage**: No significant change expected
3. **Logging consistency**: Maintain existing logging patterns

## Success Criteria

### Functional Requirements
- ✅ All existing endpoints remain accessible
- ✅ Frontend applications continue to work without changes
- ✅ Server proxy routes correctly forward requests
- ✅ Request deduplication continues to prevent duplicate AI calls
- ✅ Error handling and timeouts work as before

### Non-Functional Requirements  
- ✅ Improved code maintainability and readability
- ✅ Clear separation of concerns between AV, restart, and monitoring
- ✅ Reduced file size and complexity
- ✅ Better organization for future development
- ✅ No performance degradation

### Validation Checklist
- [ ] All 22 endpoints respond correctly
- [ ] Frontend restart flow works end-to-end
- [ ] Frontend monitoring displays frames correctly  
- [ ] Server logs show correct proxy forwarding
- [ ] No 404 errors in browser network tab
- [ ] Request deduplication prevents duplicate AI analysis
- [ ] All blueprints register successfully on startup
- [ ] Error responses maintain consistent format

## Timeline & Dependencies

### Prerequisites
- [ ] Code review and approval of migration plan
- [ ] Test environment setup for validation
- [ ] Backup of current working system

### Implementation Schedule
1. **Day 1**: Create new route files (Steps 1-2)
2. **Day 2**: Update registrations and test locally (Step 3)  
3. **Day 3**: Update server proxies and integration test (Step 4)
4. **Day 4**: Clean original file and comprehensive testing (Step 5)
5. **Day 5**: Documentation and deployment preparation

### Dependencies
- No external API changes required
- No database schema changes required  
- No frontend code changes required
- Compatible with existing deployment pipeline

## Conclusion

This migration plan provides a comprehensive, low-risk approach to refactoring the monolithic `host_av_routes.py` file into focused, maintainable modules. The phased approach ensures system stability while achieving the architectural improvements needed for long-term maintainability.

The key benefits include:
- **Better organization**: Clear separation between AV control, restart system, and monitoring
- **Improved maintainability**: Smaller, focused files are easier to understand and modify
- **Zero downtime**: Frontend continues to work unchanged during migration
- **Future-proof**: Modular structure supports independent evolution of each system

By following this plan, we can achieve a cleaner codebase architecture without disrupting existing functionality or requiring extensive testing of dependent systems.
