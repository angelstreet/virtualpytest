# Requirements Management System

## 🎯 Overview

Complete requirements management system for VirtualPyTest that links requirements to testcases and scripts for comprehensive coverage tracking and reporting.

**Status:** ✅ **FULLY IMPLEMENTED** (2025-11-10)

---

## 📐 Naming Convention

### **Requirements Format:**
```
<CATEGORY>_<PRIORITY><NUMBER> - <Action Statement>

Components:
- CATEGORY: 3-4 char uppercase code (APP, AUTH, NAV, LIVE, EPG, VOD, PLAY, etc.)
- PRIORITY: P1, P2, P3 (single letter+digit)
- NUMBER: 2-digit (01-99) within category+priority
- Name: Action-oriented, 3-8 words max

Examples:
✅ APP_P101 - User can launch app successfully
✅ AUTH_P101 - User can login with credentials
✅ PLAY_P101 - User can play video content
✅ SRCH_P101 - User can search for content
```

### **Testcases Format:**
```
TC_<CATEGORY>_<NUMBER>_<CamelCase>

Components:
- TC: Fixed prefix
- CATEGORY: Same 3-4 char code as requirements
- NUMBER: 2-digit (01-99) within category
- Description: CamelCase, 2-4 words max

Examples:
✅ TC_APP_01_LaunchApp
✅ TC_AUTH_01_LoginLogout
✅ TC_PLAY_01_BasicPlayback
✅ TC_SRCH_01_ContentSearch

Description field:
- Full sentence describing test flow
- "Navigate to X, perform Y, verify Z"
```

### **Scripts Format:**
```
script_<category>_<action>.py

For AI-generated:
ai_<category>_<action>_<YYYYMMDD_HHMMSS>.py

Examples:
✅ script_validation_login.py
✅ script_device_setup.py
✅ ai_validation_login_20251110_143022.py
```

---

## 📊 Category Taxonomy

### **Streaming Apps Categories** (Netflix, YouTube, Sunrise TV)

| Category | Code | Description | Priority Examples |
|----------|------|-------------|-------------------|
| **App Lifecycle** | APP | Launch, resume, crash recovery | P1: Launch, P2: Device info |
| **Authentication** | AUTH | Login, logout, sessions | P1: Login/Logout, P2: Auto-login |
| **Navigation** | NAV | Menu navigation, deep linking | P1: Main navigation, P2: Breadcrumbs |
| **Live TV** | LIVE | Channel tuning, zapping, timeshift | P1: Channel switch, P2: Favorites |
| **EPG** | EPG | Program guide, reminders | P1: EPG display, P2: Reminders |
| **VOD** | VOD | On-demand catalog, recommendations | P1: Catalog browse, P2: Continue watching |
| **Player** | PLAY | Playback + controls + subtitles + audio | P1: Play/Pause, P2: Subtitles |
| **Recording** | REC | DVR functionality (Sunrise, Horizon) | P1: Record program, P2: Series recording |
| **Search** | SRCH | Content search, filters | P1: Basic search, P2: Voice search |
| **Content Detail** | CONT | Content info, cast, related | P1: Detail display, P2: Related content |
| **Settings** | SETT | App configuration | P2: Video quality, P3: Language |
| **Downloads** | DOWN | Offline content (mobile) | P2: Download, P3: Auto-delete |
| **Profile** | PROF | User profiles, preferences | P2: Profile access, P3: Avatar |
| **Performance** | PERF | Speed, responsiveness, metrics | P2: Launch time, P3: Memory |
| **Network** | NET | Connectivity, reconnection | P2: Network switch, P3: Offline mode |
| **Error Handling** | ERR | Error states, recovery | P2: Playback errors, P3: Error messages |
| **Accessibility** | A11Y | Screen reader, captions | P3: Screen reader, P3: High contrast |

### **Priority Guidelines:**
- **P1 (Critical):** Core functionality, app breaking if missing
- **P2 (Important):** Major features, significant UX impact  
- **P3 (Nice-to-have):** Enhancement features, minor UX improvements

---

## 🗄️ Database Schema

### **Tables**

#### 1. `requirements`
Stores requirement definitions with metadata.

```sql
CREATE TABLE requirements (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(team_id),
    requirement_code VARCHAR(50) NOT NULL,
    requirement_name TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    app_type VARCHAR(50) DEFAULT 'all',
    device_model VARCHAR(50) DEFAULT 'all',
    status VARCHAR(20) DEFAULT 'active',
    source_document VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    UNIQUE(team_id, requirement_code)
);
```

**Fields:**
- `app_type`: "streaming", "social", "news", "all"
- `device_model`: "android_mobile", "android_tv", "web", "all"
- `status`: "active", "deprecated", "draft"

#### 2. `testcase_requirements`
Junction table linking testcases to requirements.

```sql
CREATE TABLE testcase_requirements (
    testcase_id UUID REFERENCES testcase_definitions(testcase_id) ON DELETE CASCADE,
    requirement_id UUID REFERENCES requirements(requirement_id) ON DELETE CASCADE,
    coverage_type VARCHAR(20) DEFAULT 'full',
    coverage_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (testcase_id, requirement_id)
);
```

**Coverage Types:**
- `full`: Complete requirement coverage (default)
- `partial`: Incomplete coverage (e.g., only happy path)
- `negative`: Tests failure scenarios only

#### 3. `script_requirements`
Junction table linking scripts to requirements.

```sql
CREATE TABLE script_requirements (
    script_name VARCHAR(200) NOT NULL,
    requirement_id UUID REFERENCES requirements(requirement_id) ON DELETE CASCADE,
    coverage_type VARCHAR(20) DEFAULT 'full',
    coverage_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (script_name, requirement_id)
);
```

### **Views**

#### 1. `requirements_coverage_summary`
Aggregated coverage statistics.

```sql
CREATE VIEW requirements_coverage_summary AS
SELECT 
    r.requirement_id,
    r.requirement_code,
    r.requirement_name,
    r.category,
    r.priority,
    r.status,
    COUNT(DISTINCT tr.testcase_id) AS testcase_count,
    COUNT(DISTINCT sr.script_name) AS script_count,
    (COUNT(DISTINCT tr.testcase_id) + COUNT(DISTINCT sr.script_name)) AS total_coverage_count
FROM requirements r
LEFT JOIN testcase_requirements tr ON r.requirement_id = tr.requirement_id
LEFT JOIN script_requirements sr ON r.requirement_id = sr.requirement_id
GROUP BY r.requirement_id;
```

#### 2. `uncovered_requirements`
Active requirements with no coverage.

```sql
CREATE VIEW uncovered_requirements AS
SELECT * FROM requirements_coverage_summary
WHERE total_coverage_count = 0 AND status = 'active';
```

---

## 🏗️ Architecture

### **System Flow**

```
UserInterface (Netflix, YouTube, etc.)
    ↓
Navigation Tree (nodes + edges)
    ↓
TestCases OR Scripts
    ↓ (via testcase_requirements OR script_requirements)
Requirements
    ↓
Execution Tracking (script_results)
    ↓
Coverage Reports
```

### **Component Integration**

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
├─────────────────────────────────────────────────────────────┤
│  Navigation Bar                                               │
│  ├── Test > Test Plan > Requirements                         │
│  └── Test > Test Plan > Coverage                             │
│                                                               │
│  Pages                                                        │
│  ├── Requirements.tsx (CRUD UI)                              │
│  └── Coverage.tsx (Dashboard UI)                             │
│                                                               │
│  Hooks                                                        │
│  ├── useRequirements.ts (API client)                         │
│  └── useCoverage.ts (API client)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (Flask)                         │
├─────────────────────────────────────────────────────────────┤
│  Routes: /server/requirements/*                              │
│  Files:                                                       │
│  - server_requirements_routes.py (14 endpoints)              │
│  - requirements_db.py (database layer)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓ SQL
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE (Supabase)                       │
├─────────────────────────────────────────────────────────────┤
│  Tables: requirements, testcase_requirements,                │
│          script_requirements                                  │
│  Views: requirements_coverage_summary,                       │
│         uncovered_requirements                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 Backend API

**Base URL**: `/server/requirements`  
**Authentication**: All routes require `team_id` query parameter

### **CRUD Operations**

#### 1. Create Requirement
```
POST /server/requirements/create
```

**Request:**
```json
{
  "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
  "requirement_code": "PLAY_P101",
  "requirement_name": "User can play video content",
  "category": "play",
  "priority": "P1",
  "description": "User can play video content from catalog",
  "app_type": "streaming",
  "device_model": "all"
}
```

**Response:**
```json
{
  "success": true,
  "requirement_id": "abc-123-def-456"
}
```

#### 2. List Requirements
```
GET /server/requirements/list?team_id=xxx&category=play&priority=P1
```

**Response:**
```json
{
  "success": true,
  "requirements": [...],
  "count": 10
}
```

#### 3. Get Requirement
```
GET /server/requirements/<id>?team_id=xxx
GET /server/requirements/by-code/<code>?team_id=xxx
```

#### 4. Update Requirement
```
PUT /server/requirements/<id>
```

**Request:**
```json
{
  "team_id": "xxx",
  "requirement_name": "Updated name",
  "priority": "P2",
  "status": "deprecated"
}
```

### **Linkage Operations**

#### 5. Link TestCase to Requirement
```
POST /server/requirements/link-testcase
```

**Request:**
```json
{
  "testcase_id": "tc-uuid-123",
  "requirement_id": "req-uuid-456",
  "coverage_type": "full",
  "coverage_notes": "Covers all acceptance criteria"
}
```

#### 6. Unlink TestCase from Requirement
```
POST /server/requirements/unlink-testcase
```

#### 7. Get TestCase Requirements
```
GET /server/requirements/testcase/<testcase_id>/requirements
```

#### 8. Link/Unlink/Get Script Requirements
```
POST /server/requirements/link-script
POST /server/requirements/unlink-script
GET /server/requirements/script/<script_name>/requirements
```

### **Coverage Reporting**

#### 9. Get Requirement Coverage
```
GET /server/requirements/<id>/coverage?team_id=xxx
```

**Response:**
```json
{
  "success": true,
  "coverage": {
    "requirement": {...},
    "testcases": [
      {
        "testcase_name": "TC_PLAY_01_BasicPlayback",
        "coverage_type": "full",
        "execution_count": 15,
        "pass_count": 14
      }
    ],
    "scripts": [...]
  }
}
```

#### 10. Get Coverage Summary
```
GET /server/requirements/coverage/summary?team_id=xxx&category=play
```

**Response:**
```json
{
  "success": true,
  "summary": {
    "by_category": {
      "play": {
        "total": 5,
        "covered": 4,
        "coverage_percentage": 80.0
      }
    },
    "total_requirements": 20,
    "total_covered": 18,
    "coverage_percentage": 90.0
  }
}
```

#### 11. Get Uncovered Requirements
```
GET /server/requirements/uncovered?team_id=xxx
```

---

## 🎨 Frontend Implementation

### **Pages**

#### 1. Requirements Page (`/test-plan/requirements`)

**Features:**
- ✅ Requirements table with search and filters
- ✅ Create/Edit requirement dialogs
- ✅ Color-coded priority chips (P1=red, P2=orange, P3=blue)
- ✅ Status badges (active=green, deprecated=gray)
- ✅ Filter by category, priority, app type, device model

**Hook:**
```typescript
const {
  requirements,
  isLoading,
  createRequirement,
  updateRequirement,
  linkTestcase,
  linkScript,
} = useRequirements();
```

#### 2. Coverage Page (`/test-plan/coverage`)

**Features:**
- ✅ Overall coverage summary cards
- ✅ Coverage by category table with progress bars
- ✅ Uncovered requirements alert
- ✅ Color-coded indicators (green ≥80%, yellow ≥50%, red <50%)

**Hook:**
```typescript
const {
  coverageSummary,
  uncoveredRequirements,
  loadCoverageSummary,
  loadRequirementCoverage,
} = useCoverage();
```

### **Navigation**

```
Test > Test Plan
├── Test Cases
├── Campaigns
├── Requirements ✅
└── Coverage ✅
```

---

## 💻 Usage Examples

### **Example 1: Create Requirement and Link TestCase**

**Python (Database Layer):**
```python
from shared.src.lib.database.requirements_db import (
    create_requirement,
    link_testcase_to_requirement
)

# Create requirement
req_id = create_requirement(
    team_id="7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    requirement_code="PLAY_P101",
    requirement_name="User can play video content",
    category="play",
    priority="P1",
    app_type="streaming",
    device_model="all"
)

# Link testcase
link_testcase_to_requirement(
    testcase_id="tc-uuid-123",
    requirement_id=req_id,
    coverage_type="full"
)
```

**TypeScript (Frontend):**
```typescript
const { createRequirement, linkTestcase } = useRequirements();

// Create requirement
const reqId = await createRequirement({
  requirement_code: "PLAY_P101",
  requirement_name: "User can play video content",
  category: "play",
  priority: "P1",
  app_type: "streaming",
  device_model: "all"
});

// Link testcase
await linkTestcase(
  "tc-uuid-123",
  reqId,
  "full"
);
```

**cURL (API):**
```bash
# Create requirement
curl -X POST http://localhost:5109/server/requirements/create \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    "requirement_code": "PLAY_P101",
    "requirement_name": "User can play video content",
    "category": "play",
    "priority": "P1"
  }'

# Link testcase
curl -X POST http://localhost:5109/server/requirements/link-testcase \
  -H "Content-Type: application/json" \
  -d '{
    "testcase_id": "tc-uuid-123",
    "requirement_id": "abc-123",
    "coverage_type": "full"
  }'
```

### **Example 2: Query Coverage**

**Python:**
```python
from shared.src.lib.database.requirements_db import (
    get_coverage_summary,
    get_uncovered_requirements
)

# Get summary
summary = get_coverage_summary(
    team_id="7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    category="play"
)
# Returns: {'by_category': {'play': {'total': 5, 'covered': 4, ...}}}

# Find gaps
uncovered = get_uncovered_requirements(
    team_id="7fdeb4bb-3639-4ec3-959f-b54769a219ce"
)
# Returns: List of requirements with no coverage
```

**TypeScript:**
```typescript
const { loadCoverageSummary, loadUncoveredRequirements } = useCoverage();

// Load summary
await loadCoverageSummary({ category: "play" });

// Load uncovered
await loadUncoveredRequirements();
```

---

## 🔄 MCP Integration

### **MCP Tools Available**

All requirements operations are exposed through MCP server for AI agents:

```python
# Available MCP tools (52 total, requirements = tools 43-52)
43. create_requirement - Create new requirement
44. list_requirements - List all requirements  
45. get_requirement - Get requirement by ID
46. update_requirement - Update requirement
47. link_testcase_to_requirement - Link testcase for coverage
48. unlink_testcase_from_requirement - Unlink testcase
49. get_testcase_requirements - Get testcase requirements
50. get_requirement_coverage - Get requirement coverage details
51. get_coverage_summary - Get overall coverage metrics
52. get_uncovered_requirements - Get requirements without coverage
```

**Example Usage:**
```python
# AI can create requirements via MCP
mcp_virtualpytest_create_requirement(
    requirement_code="PLAY_P101",
    requirement_name="User can play video content",
    category="play",
    priority="P1"
)

# AI can check coverage
mcp_virtualpytest_get_coverage_summary(
    category="play"
)
```

---

## 📝 Sample Data

### **Current Requirements (20 active):**

**P1 (Critical - 12):**
- APP_P101 - User can launch app successfully
- AUTH_P101 - User can login with credentials
- AUTH_P102 - User can logout from app
- NAV_P101 - User can navigate to home screen
- NAV_P102 - User can navigate to search screen
- NAV_P103 - User can navigate back using back button
- PLAY_P101 - User can play video content
- PLAY_P102 - User can pause and resume video
- PLAY_P103 - User can exit video player
- PLAY_P104 - User can seek video timeline
- PLAY_P105 - User can select and play content from catalog
- SRCH_P101 - User can search for content

**P2 (Important - 8):**
- APP_P201 - System can extract device information
- CONT_P201 - Content detail page displays complete information
- DOWN_P201 - User can view downloaded content
- PLAY_P201 - User can skip forward and backward in video
- PLAY_P202 - User can enable and disable subtitles
- PROF_P201 - User can access profile settings
- SETT_P201 - User can change video quality
- VOD_P201 - Home screen displays content recommendations

### **Current Testcases (13 active):**

- TC_APP_01_GetDeviceInfo
- TC_CONT_02_DetailAccess
- TC_DOWN_01_AccessDownloads
- TC_NAV_01_MainTabs
- TC_NAV_02_ScreenTransitions
- TC_NAV_03_BackButton
- TC_NAV_04_DeepNavigation
- TC_PLAY_01_BasicPlayback
- TC_PLAY_02_ExitPlayer
- TC_PROF_01_AccessProfile
- TC_SRCH_01_ContentSearch
- TC_SRCH_02_SearchToDetail
- TC_VOD_01_HomeContent

---

## 🚀 Complete Workflow

### **Scenario: Netflix Mobile Testing**

1. **Create Requirements**
```python
# Create playback requirements
req_ids = []
for req in [
    ("PLAY_P101", "User can play video content"),
    ("PLAY_P102", "User can pause and resume video"),
    ("PLAY_P103", "User can exit video player"),
]:
    req_id = create_requirement(
        team_id="...",
        requirement_code=req[0],
        requirement_name=req[1],
        category="play",
        priority="P1",
        app_type="streaming"
    )
    req_ids.append(req_id)
```

2. **Create TestCases**
```python
# Create testcase with naming convention
testcase_id = create_testcase(
    team_id="...",
    testcase_name="TC_PLAY_01_BasicPlayback",
    graph_json={...},
    description="Navigate from home to player and verify video starts",
    userinterface_name="netflix_mobile"
)
```

3. **Link Testcase to Requirements**
```python
# Link testcase to multiple requirements
for req_id in req_ids:
    link_testcase_to_requirement(
        testcase_id=testcase_id,
        requirement_id=req_id,
        coverage_type="full"
    )
```

4. **Execute and Track**
```python
# Execute testcase (automatically tracked in script_results)
execute_testcase(testcase_name="TC_PLAY_01_BasicPlayback")
```

5. **Generate Coverage Report**
```python
# Get coverage summary
summary = get_coverage_summary(team_id="...")
print(f"Coverage: {summary['coverage_percentage']}%")

# Find gaps
uncovered = get_uncovered_requirements(team_id="...")
print(f"Uncovered: {len(uncovered)} requirements")
```

---

## 📚 Python API Reference

**Module:** `shared/src/lib/database/requirements_db.py`

**Key Functions:**

| Function | Description |
|----------|-------------|
| `create_requirement()` | Create new requirement |
| `list_requirements()` | List with filters (category, priority, app_type, device_model) |
| `get_requirement()` | Get by ID |
| `get_requirement_by_code()` | Get by code |
| `update_requirement()` | Update fields (NEW: app_type, device_model) |
| `link_testcase_to_requirement()` | Link testcase |
| `unlink_testcase_from_requirement()` | Unlink testcase |
| `get_testcase_requirements()` | Get requirements for testcase |
| `link_script_to_requirement()` | Link script |
| `unlink_script_from_requirement()` | Unlink script |
| `get_script_requirements()` | Get requirements for script |
| `get_requirement_coverage()` | Get detailed coverage + execution stats |
| `get_coverage_summary()` | Get summary by category/priority |
| `get_uncovered_requirements()` | Find coverage gaps |

---

## 🎓 Best Practices

### **1. Requirement Creation**
- ✅ Use consistent naming convention (CATEGORY_PRIORITY_NUMBER)
- ✅ Set app_type and device_model for reusability
- ✅ Write clear, action-oriented names
- ✅ Document acceptance criteria
- ✅ Link to source documents

### **2. TestCase Naming**
- ✅ Follow TC_CATEGORY_NUMBER_CamelCase format
- ✅ Match category with requirements
- ✅ Use sequential numbering within category
- ✅ Write descriptive camelCase suffixes

### **3. Coverage Tracking**
- ✅ Link testcases immediately after creation
- ✅ Use appropriate coverage_type (full/partial/negative)
- ✅ Add coverage notes for clarity
- ✅ Monitor uncovered requirements regularly
- ✅ Aim for 80%+ coverage on P1 requirements

### **4. Maintenance**
- ✅ Mark obsolete requirements as deprecated
- ✅ Update requirements when specs change
- ✅ Review coverage quarterly
- ✅ Clean up unused requirements

---

## 📁 Files Reference

### **Backend:**
- `backend_server/src/routes/server_requirements_routes.py` - 14 API endpoints
- `shared/src/lib/database/requirements_db.py` - Database operations
- `backend_server/src/mcp/tools/requirements_tools.py` - MCP tools

### **Frontend:**
- `frontend/src/pages/Requirements.tsx` - Requirements CRUD UI
- `frontend/src/pages/Coverage.tsx` - Coverage dashboard
- `frontend/src/hooks/pages/useRequirements.ts` - Requirements hook
- `frontend/src/hooks/pages/useCoverage.ts` - Coverage hook
- `frontend/src/components/common/Navigation_Bar.tsx` - Navigation

### **Database:**
- `setup/db/schema/017_requirements_management.sql` - Schema migration

---

**Version**: 2.0.0  
**Updated**: 2025-11-10  
**Status**: Production Ready  
**Database**: virtualpytest (Supabase)

