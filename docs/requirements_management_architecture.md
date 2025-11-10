# Requirements Management System - Architecture Summary

## 🎯 Overview

Requirements management system for VirtualPyTest that links requirements to testcases and scripts for complete coverage tracking and reporting.

**Status:** ✅ **IMPLEMENTED** (2025-11-10)

---

## 📊 Database Schema

### **Tables Created:**

#### 1. `requirements`
Stores requirement definitions with metadata.

**Key Fields:**
- `requirement_id` (UUID, PK)
- `team_id` (UUID, FK → teams)
- `requirement_code` (VARCHAR) - e.g., "REQ_PLAYBACK_001"
- `requirement_name` (TEXT) - e.g., "Basic Video Playback"
- `category` (VARCHAR) - e.g., "playback", "auth", "navigation"
- `priority` (VARCHAR) - "P1", "P2", "P3"
- `description` (TEXT)
- `acceptance_criteria` (JSONB) - Array of criteria
- `app_type` (VARCHAR) - "streaming", "social", "all"
- `device_model` (VARCHAR) - "android_mobile", "android_tv", "all"
- `status` (VARCHAR) - "active", "deprecated", "draft"
- `source_document` (VARCHAR) - Link to spec

#### 2. `testcase_requirements`
Junction table linking testcases to requirements.

**Key Fields:**
- `testcase_id` (UUID, FK → testcase_definitions)
- `requirement_id` (UUID, FK → requirements)
- `coverage_type` (VARCHAR) - "full", "partial", "negative"
- `coverage_notes` (TEXT)

#### 3. `script_requirements`
Junction table linking scripts to requirements.

**Key Fields:**
- `script_name` (VARCHAR) - Script filename (e.g., "device_get_info.py")
- `requirement_id` (UUID, FK → requirements)
- `coverage_type` (VARCHAR) - "full", "partial", "negative"
- `coverage_notes` (TEXT)

### **Views Created:**

#### 1. `requirements_coverage_summary`
Shows coverage counts for all requirements.

**Returns:**
```sql
requirement_code, requirement_name, category, priority, status,
testcase_count, script_count, total_coverage_count
```

#### 2. `uncovered_requirements`
Shows active requirements with no coverage.

**Returns:**
All requirement fields where `total_coverage_count = 0`

---

## 🔗 How Everything Links

### **Architecture Diagram:**

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

### **Linking Flow:**

1. **Create Requirement:**
   ```python
   from shared.src.lib.database.requirements_db import create_requirement
   
   req_id = create_requirement(
       team_id="...",
       requirement_code="REQ_PLAYBACK_001",
       requirement_name="Basic Video Playback",
       category="playback",
       priority="P1",
       app_type="streaming",
       device_model="all"
   )
   ```

2. **Link Testcase to Requirement:**
   ```python
   from shared.src.lib.database.requirements_db import link_testcase_to_requirement
   
   link_testcase_to_requirement(
       testcase_id="abc-123",
       requirement_id=req_id,
       coverage_type="full",
       coverage_notes="Tests happy path only"
   )
   ```

3. **Link Script to Requirement:**
   ```python
   from shared.src.lib.database.requirements_db import link_script_to_requirement
   
   link_script_to_requirement(
       script_name="device_get_info.py",
       requirement_id=req_id,
       coverage_type="full"
   )
   ```

4. **Track Execution:**
   - Existing `script_results` table already tracks executions
   - Links via `script_name` (for both testcases and scripts)
   - No changes needed to execution tracking!

5. **Query Coverage:**
   ```python
   from shared.src.lib.database.requirements_db import get_requirement_coverage
   
   coverage = get_requirement_coverage(
       team_id="...",
       requirement_id=req_id
   )
   # Returns: {requirement, testcases, scripts, execution_stats}
   ```

---

## 📈 Coverage Tracking

### **How Coverage is Tracked:**

```sql
-- Per requirement coverage
SELECT 
    r.requirement_code,
    r.requirement_name,
    COUNT(DISTINCT tr.testcase_id) AS testcase_count,
    COUNT(DISTINCT sr.script_name) AS script_count
FROM requirements r
LEFT JOIN testcase_requirements tr ON r.requirement_id = tr.requirement_id
LEFT JOIN script_requirements sr ON r.requirement_id = sr.requirement_id
GROUP BY r.requirement_id;
```

### **Execution History per Requirement:**

```sql
-- Get executions for all testcases/scripts covering a requirement
SELECT 
    sr.script_name,
    sr.started_at,
    sr.completed_at,
    sr.success,
    sr.execution_time_ms
FROM script_results sr
WHERE sr.script_name IN (
    -- Testcases covering this requirement
    SELECT td.testcase_name 
    FROM testcase_requirements tr
    JOIN testcase_definitions td ON tr.testcase_id = td.testcase_id
    WHERE tr.requirement_id = '<requirement_id>'
    
    UNION
    
    -- Scripts covering this requirement
    SELECT script_name
    FROM script_requirements
    WHERE requirement_id = '<requirement_id>'
)
ORDER BY sr.started_at DESC;
```

---

## 📊 Reporting Queries

### **1. Coverage by Category:**

```python
from shared.src.lib.database.requirements_db import get_coverage_summary

summary = get_coverage_summary(team_id="...", category="playback")
# Returns:
# {
#   'by_category': {
#     'playback': {
#       'total': 10,
#       'covered': 7,
#       'coverage_percentage': 70.0,
#       'testcase_count': 12,
#       'script_count': 3
#     }
#   },
#   'total_requirements': 10,
#   'total_covered': 7,
#   'coverage_percentage': 70.0
# }
```

### **2. Uncovered Requirements:**

```python
from shared.src.lib.database.requirements_db import get_uncovered_requirements

uncovered = get_uncovered_requirements(team_id="...")
# Returns list of requirements with no testcase or script coverage
```

### **3. Requirement Detail with Executions:**

```python
from shared.src.lib.database.requirements_db import get_requirement_coverage

coverage = get_requirement_coverage(team_id="...", requirement_id="...")
# Returns:
# {
#   'requirement': {...},
#   'testcases': [
#     {
#       'testcase_name': 'TC_001',
#       'coverage_type': 'full',
#       'execution_count': 15,
#       'pass_count': 14,
#       'last_execution': {...}
#     }
#   ],
#   'scripts': [
#     {
#       'script_name': 'device_get_info.py',
#       'coverage_type': 'full',
#       'execution_count': 10,
#       'pass_count': 10,
#       'last_execution': {...}
#     }
#   ]
# }
```

---

## 🎯 Integration Points

### **1. TestCase Builder (Frontend):**

Add requirement selector to testcase save dialog:

```typescript
// When saving testcase
const requirementIds = selectedRequirements.map(r => r.requirement_id);

// Link after save
requirementIds.forEach(reqId => {
  linkTestcaseToRequirement(testcaseId, reqId);
});
```

### **2. Script Execution (Backend):**

Scripts can declare requirements in docstring:

```python
"""
Script: device_get_info.py

Requirements:
  - REQ_DEVICE_001: Extract Device Info (full coverage)
"""

# Auto-link on first execution via script analyzer
```

### **3. UserInterface Creation:**

When creating standard testcase library:

```python
# Create requirement
req_id = create_requirement(
    team_id=team_id,
    requirement_code="REQ_PLAYBACK_001",
    requirement_name="Basic Video Playback",
    category="playback",
    priority="P1",
    app_type="streaming"
)

# Create testcase
testcase_id = create_testcase(
    team_id=team_id,
    testcase_name="TC_030_Play_Video",
    graph_json={...},
    tags=["P1", "playback", "streaming"]
)

# Link them
link_testcase_to_requirement(testcase_id, req_id)
```

### **4. Coverage Dashboard:**

```typescript
// Frontend dashboard component
const CoverageDashboard = () => {
  const summary = useCoverageSummary();
  
  return (
    <Grid>
      <CategoryCard category="playback" 
        total={summary.playback.total}
        covered={summary.playback.covered}
        percentage={summary.playback.coverage_percentage} />
      <UncoveredList requirements={summary.uncovered} />
      <ExecutionHistory requirements={summary.recent_executions} />
    </Grid>
  );
};
```

---

## 📝 Sample Data

### **10 Requirements Created:**

1. `REQ_PLAYBACK_001` - Basic Video Playback (P1)
2. `REQ_PLAYBACK_002` - Pause and Resume (P1)
3. `REQ_PLAYBACK_003` - Skip Forward/Backward (P2)
4. `REQ_AUTH_001` - User Login (P1)
5. `REQ_AUTH_002` - User Logout (P1)
6. `REQ_NAV_001` - Navigate to Home (P1)
7. `REQ_NAV_002` - Navigate to Search (P1)
8. `REQ_SETTINGS_001` - Change Video Quality (P2)
9. `REQ_SETTINGS_002` - Enable Subtitles (P2)
10. `REQ_DEVICE_001` - Extract Device Info (P2) ✅ **COVERED** by `device_get_info.py`

---

## 🚀 Next Steps

### **Phase 1: Backend Integration (Immediate)**

1. ✅ Database tables created
2. ✅ Python module (`requirements_db.py`) created
3. ✅ Sample requirements populated
4. ✅ Test linkage verified (`device_get_info.py` → `REQ_DEVICE_001`)
5. ⏳ Update `testcase_db.py` to accept `requirement_codes` parameter
6. ⏳ Add requirements parameter to MCP `create_testcase` and `save_testcase` tools

### **Phase 2: Frontend Integration (Week 1-2)**

1. Create Requirements Management page
2. Add requirement selector to TestCase Builder
3. Add requirement selector to Script metadata
4. Build Coverage Dashboard

### **Phase 3: Reporting (Week 3-4)**

1. Coverage reports by category
2. Coverage reports by priority
3. Coverage reports by app type
4. Trend analysis (coverage over time)
5. Export to CSV/PDF

### **Phase 4: Standard Library (Month 2)**

1. Create standard requirements for streaming apps
2. Create standard requirements for social apps
3. Create standard requirements for news apps
4. Auto-link standard testcases to requirements

---

## 🔍 Example: Complete Flow

### **Scenario: Netflix Mobile Testing**

1. **Create Requirements:**
   ```sql
   INSERT INTO requirements (...)
   VALUES ('REQ_PLAYBACK_001', 'Basic Video Playback', ...)
   ```

2. **Create UserInterface:**
   ```python
   create_userinterface(
       name="netflix_mobile",
       device_model="android_mobile"
   )
   ```

3. **Create TestCase:**
   ```python
   testcase_id = create_testcase(
       testcase_name="TC_030_Play_Video_Netflix",
       graph_json={...},
       requirement_codes=["REQ_PLAYBACK_001"]  # NEW!
   )
   ```

4. **Execute TestCase:**
   ```python
   execute_testcase(testcase_name="TC_030_Play_Video_Netflix")
   # → Creates entry in script_results
   ```

5. **Query Coverage:**
   ```python
   coverage = get_requirement_coverage(
       team_id="...",
       requirement_code="REQ_PLAYBACK_001"
   )
   # Shows: TC_030_Play_Video_Netflix with execution history
   ```

6. **Generate Report:**
   ```python
   summary = get_coverage_summary(team_id="...")
   # Shows: 1/3 playback requirements covered (33%)
   ```

---

## 🎓 Key Concepts

### **Coverage Types:**

- **`full`**: Complete requirement coverage (default)
- **`partial`**: Incomplete coverage (e.g., only happy path)
- **`negative`**: Tests failure scenarios only

### **Requirement Status:**

- **`active`**: Current requirement (default)
- **`deprecated`**: Obsolete requirement
- **`draft`**: Pending approval

### **App Type:**

- **`streaming`**: Netflix, YouTube, Disney+
- **`social`**: Facebook, Twitter, Instagram
- **`news`**: CNN, BBC, Reuters
- **`all`**: Cross-app requirements

### **Device Model:**

- **`android_mobile`**: Android phones
- **`android_tv`**: Android TV / STB
- **`web`**: Web browsers
- **`all`**: Cross-platform requirements

---

## 📚 Python API Reference

See `shared/src/lib/database/requirements_db.py` for complete API.

**Key Functions:**
- `create_requirement()` - Create new requirement
- `list_requirements()` - List with filters
- `link_testcase_to_requirement()` - Link testcase
- `link_script_to_requirement()` - Link script
- `get_requirement_coverage()` - Get detailed coverage
- `get_coverage_summary()` - Get summary statistics
- `get_uncovered_requirements()` - Find gaps

---

**Version**: 1.0.0  
**Created**: 2025-11-10  
**Database**: virtualpytest (Supabase)  
**Migration**: `017_requirements_management.sql`

