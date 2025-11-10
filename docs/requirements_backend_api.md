# Requirements Management Backend API

## Overview

Backend API endpoints for managing requirements and their linkage to testcases and scripts. Follows the same patterns as `server_testcase_routes.py` for consistency.

**Base URL**: `/server/requirements`

**Authentication**: All routes require `team_id` (passed as query param or in request body)

---

## Requirements CRUD Operations

### 1. Create Requirement

**Endpoint**: `POST /server/requirements/create`

**Description**: Create a new requirement definition.

**Request Body**:
```json
{
  "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
  "requirement_code": "REQ_PLAYBACK_001",
  "requirement_name": "Basic Video Playback",
  "category": "playback",
  "priority": "P1",
  "description": "User should be able to play video content",
  "acceptance_criteria": [
    "Video starts within 2 seconds",
    "Audio is synchronized",
    "Playback controls are responsive"
  ],
  "app_type": "streaming",
  "device_model": "all",
  "status": "active",
  "source_document": "https://confluence.example.com/req-001",
  "created_by": "test_engineer"
}
```

**Response Success** (200):
```json
{
  "success": true,
  "requirement_id": "abc-123-def-456"
}
```

**Response Duplicate** (409):
```json
{
  "success": false,
  "error": "Requirement code already exists: REQ_PLAYBACK_001"
}
```

---

### 2. List Requirements

**Endpoint**: `GET /server/requirements/list`

**Description**: List all requirements for a team with optional filters.

**Query Parameters**:
- `team_id` (required): Team ID
- `category` (optional): Filter by category
- `priority` (optional): Filter by priority (P1, P2, P3)
- `app_type` (optional): Filter by app type
- `device_model` (optional): Filter by device model
- `status` (optional): Filter by status (default: "active")

**Example**:
```bash
curl "http://localhost:5109/server/requirements/list?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce&category=playback&priority=P1"
```

**Response** (200):
```json
{
  "success": true,
  "requirements": [
    {
      "requirement_id": "abc-123",
      "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
      "requirement_code": "REQ_PLAYBACK_001",
      "requirement_name": "Basic Video Playback",
      "category": "playback",
      "priority": "P1",
      "description": "...",
      "acceptance_criteria": ["..."],
      "app_type": "streaming",
      "device_model": "all",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

### 3. Get Requirement by ID

**Endpoint**: `GET /server/requirements/<requirement_id>`

**Query Parameters**:
- `team_id` (required): Team ID

**Example**:
```bash
curl "http://localhost:5109/server/requirements/abc-123?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

**Response** (200):
```json
{
  "success": true,
  "requirement": {
    "requirement_id": "abc-123",
    "requirement_code": "REQ_PLAYBACK_001",
    "requirement_name": "Basic Video Playback",
    "..."
  }
}
```

**Response Not Found** (404):
```json
{
  "success": false,
  "error": "Requirement not found"
}
```

---

### 4. Get Requirement by Code

**Endpoint**: `GET /server/requirements/by-code/<requirement_code>`

**Query Parameters**:
- `team_id` (required): Team ID

**Example**:
```bash
curl "http://localhost:5109/server/requirements/by-code/REQ_PLAYBACK_001?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

**Response**: Same as Get by ID

---

### 5. Update Requirement

**Endpoint**: `PUT /server/requirements/<requirement_id>`

**Request Body**:
```json
{
  "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
  "requirement_name": "Updated Name",
  "description": "Updated description",
  "priority": "P2",
  "status": "active",
  "acceptance_criteria": ["Updated criteria"]
}
```

**Response** (200):
```json
{
  "success": true
}
```

---

## TestCase-Requirement Linkage

### 6. Link TestCase to Requirement

**Endpoint**: `POST /server/requirements/link-testcase`

**Description**: Link a testcase to a requirement for coverage tracking.

**Request Body**:
```json
{
  "testcase_id": "testcase-uuid-123",
  "requirement_id": "requirement-uuid-456",
  "coverage_type": "full",
  "coverage_notes": "Covers all acceptance criteria",
  "created_by": "test_engineer"
}
```

**Coverage Types**:
- `full`: Complete coverage of the requirement
- `partial`: Partial coverage
- `negative`: Negative test case
- `regression`: Regression test

**Response** (200):
```json
{
  "success": true
}
```

---

### 7. Unlink TestCase from Requirement

**Endpoint**: `POST /server/requirements/unlink-testcase`

**Request Body**:
```json
{
  "testcase_id": "testcase-uuid-123",
  "requirement_id": "requirement-uuid-456"
}
```

**Response** (200):
```json
{
  "success": true
}
```

---

### 8. Get TestCase Requirements

**Endpoint**: `GET /server/requirements/testcase/<testcase_id>/requirements`

**Description**: Get all requirements linked to a testcase.

**Example**:
```bash
curl "http://localhost:5109/server/requirements/testcase/testcase-uuid-123/requirements"
```

**Response** (200):
```json
{
  "success": true,
  "requirements": [
    {
      "requirement_id": "abc-123",
      "requirement_code": "REQ_PLAYBACK_001",
      "requirement_name": "Basic Video Playback",
      "coverage_type": "full",
      "coverage_notes": "Covers all acceptance criteria",
      "..."
    }
  ],
  "count": 1
}
```

---

## Script-Requirement Linkage

### 9. Link Script to Requirement

**Endpoint**: `POST /server/requirements/link-script`

**Description**: Link a script to a requirement for coverage tracking.

**Request Body**:
```json
{
  "script_name": "device_get_info.py",
  "requirement_id": "requirement-uuid-456",
  "coverage_type": "full",
  "coverage_notes": "Validates device info retrieval",
  "created_by": "test_engineer"
}
```

**Response** (200):
```json
{
  "success": true
}
```

---

### 10. Unlink Script from Requirement

**Endpoint**: `POST /server/requirements/unlink-script`

**Request Body**:
```json
{
  "script_name": "device_get_info.py",
  "requirement_id": "requirement-uuid-456"
}
```

**Response** (200):
```json
{
  "success": true
}
```

---

### 11. Get Script Requirements

**Endpoint**: `GET /server/requirements/script/<script_name>/requirements`

**Description**: Get all requirements linked to a script.

**Example**:
```bash
curl "http://localhost:5109/server/requirements/script/device_get_info.py/requirements"
```

**Response**: Same structure as TestCase Requirements

---

## Coverage Reporting

### 12. Get Requirement Coverage

**Endpoint**: `GET /server/requirements/<requirement_id>/coverage`

**Description**: Get detailed coverage for a specific requirement, including linked testcases, scripts, and execution statistics.

**Query Parameters**:
- `team_id` (required): Team ID

**Example**:
```bash
curl "http://localhost:5109/server/requirements/abc-123/coverage?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

**Response** (200):
```json
{
  "success": true,
  "coverage": {
    "requirement": {
      "requirement_id": "abc-123",
      "requirement_code": "REQ_PLAYBACK_001",
      "requirement_name": "Basic Video Playback",
      "..."
    },
    "testcases": [
      {
        "testcase_id": "tc-123",
        "testcase_name": "TC_030_Play_Video",
        "description": "Test video playback",
        "coverage_type": "full",
        "execution_count": 15,
        "pass_count": 14,
        "last_execution": {
          "success": true,
          "started_at": "2024-01-01T12:00:00Z"
        }
      }
    ],
    "scripts": [
      {
        "script_name": "device_get_info.py",
        "coverage_type": "full",
        "execution_count": 50,
        "pass_count": 50,
        "last_execution": {
          "success": true,
          "started_at": "2024-01-01T13:00:00Z"
        }
      }
    ],
    "total_testcases": 1,
    "total_scripts": 1,
    "total_coverage": 2
  }
}
```

---

### 13. Get Coverage Summary

**Endpoint**: `GET /server/requirements/coverage/summary`

**Description**: Get coverage summary across all requirements, grouped by category.

**Query Parameters**:
- `team_id` (required): Team ID
- `category` (optional): Filter by category
- `priority` (optional): Filter by priority

**Example**:
```bash
curl "http://localhost:5109/server/requirements/coverage/summary?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

**Response** (200):
```json
{
  "success": true,
  "summary": {
    "by_category": {
      "playback": {
        "total": 5,
        "covered": 4,
        "testcase_count": 8,
        "script_count": 3,
        "coverage_percentage": 80.0
      },
      "auth": {
        "total": 3,
        "covered": 3,
        "testcase_count": 5,
        "script_count": 2,
        "coverage_percentage": 100.0
      }
    },
    "total_requirements": 8,
    "total_covered": 7,
    "coverage_percentage": 87.5
  }
}
```

---

### 14. Get Uncovered Requirements

**Endpoint**: `GET /server/requirements/uncovered`

**Description**: Get all active requirements that have no linked testcases or scripts.

**Query Parameters**:
- `team_id` (required): Team ID

**Example**:
```bash
curl "http://localhost:5109/server/requirements/uncovered?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

**Response** (200):
```json
{
  "success": true,
  "requirements": [
    {
      "requirement_id": "xyz-789",
      "requirement_code": "REQ_AUTH_003",
      "requirement_name": "OAuth Integration",
      "category": "auth",
      "priority": "P2",
      "app_type": "all",
      "device_model": "all"
    }
  ],
  "count": 1
}
```

---

## Integration Examples

### Example 1: Create Requirement and Link TestCase

```bash
# Step 1: Create requirement
curl -X POST http://localhost:5109/server/requirements/create \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    "requirement_code": "REQ_PLAYBACK_001",
    "requirement_name": "Basic Video Playback",
    "category": "playback",
    "priority": "P1"
  }'

# Response: {"success": true, "requirement_id": "abc-123"}

# Step 2: Link existing testcase
curl -X POST http://localhost:5109/server/requirements/link-testcase \
  -H "Content-Type: application/json" \
  -d '{
    "testcase_id": "testcase-uuid-123",
    "requirement_id": "abc-123",
    "coverage_type": "full"
  }'
```

### Example 2: Check Coverage for Requirement

```bash
# Get detailed coverage
curl "http://localhost:5109/server/requirements/abc-123/coverage?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"

# Check overall coverage summary
curl "http://localhost:5109/server/requirements/coverage/summary?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"

# Find gaps - uncovered requirements
curl "http://localhost:5109/server/requirements/uncovered?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce"
```

---

## Error Handling

All endpoints follow standard error response format:

**400 Bad Request**:
```json
{
  "success": false,
  "error": "team_id is required"
}
```

**404 Not Found**:
```json
{
  "success": false,
  "error": "Requirement not found"
}
```

**409 Conflict**:
```json
{
  "success": false,
  "error": "Requirement code already exists: REQ_PLAYBACK_001"
}
```

**500 Internal Server Error**:
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

---

## Database Schema Reference

### Requirements Table
- `requirement_id` (UUID, PK)
- `team_id` (UUID, FK to teams)
- `requirement_code` (VARCHAR, unique per team)
- `requirement_name` (TEXT)
- `category` (VARCHAR)
- `priority` (VARCHAR: P1, P2, P3)
- `description` (TEXT)
- `acceptance_criteria` (JSONB array)
- `app_type` (VARCHAR: streaming, social, news, all)
- `device_model` (VARCHAR: android_mobile, android_tv, web, all)
- `status` (VARCHAR: active, deprecated, draft)
- `source_document` (VARCHAR)
- `created_at`, `updated_at`, `created_by`

### Junction Tables
- `testcase_requirements`: Links testcases to requirements
- `script_requirements`: Links scripts to requirements

### Views
- `requirements_coverage_summary`: Aggregated coverage stats
- `uncovered_requirements`: Requirements with no coverage

---

## Next Steps (Frontend Integration)

1. **TestCase Builder UI**:
   - Add requirements selector when saving testcase
   - Display linked requirements in testcase list
   - Show coverage badges

2. **Coverage Dashboard**:
   - Implement `/coverage` page using summary endpoint
   - Display by category/priority charts
   - Show uncovered requirements alerts

3. **Requirements Manager UI**:
   - Create `/requirements` page for CRUD operations
   - Bulk import from spreadsheet/CSV
   - Visual coverage tracking

---

## Files Created/Modified

### New Files:
- `/backend_server/src/routes/server_requirements_routes.py` - All 14 endpoints

### Modified Files:
- `/backend_server/src/app.py` - Registered blueprint

### Existing (No changes needed):
- `/shared/src/lib/database/requirements_db.py` - Already has all functions
- `/setup/db/schema/017_requirements_management.sql` - Already applied

