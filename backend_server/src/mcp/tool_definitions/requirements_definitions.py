"""Requirements tool definitions for requirements management and coverage tracking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get requirements-related tool definitions"""
    return [
        {
            "name": "create_requirement",
            "description": """Create a new requirement for requirements management
                
Creates a requirement with code, title, description, priority, and category.
Used for tracking test coverage and linking testcases to requirements.

Example:
  create_requirement(
    requirement_code='REQ_PLAYBACK_001',
    requirement_name='User can play video content',
    description='Users must be able to select and play video content from the catalog',
    priority='P1',
    category='playback'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "requirement_code": {"type": "string", "description": "Requirement code (e.g., 'REQ_PLAYBACK_001')"},
                    "requirement_name": {"type": "string", "description": "Requirement title"},
                    "description": {"type": "string", "description": "Detailed description (optional)"},
                    "priority": {"type": "string", "description": "Priority: P1, P2, P3 (optional - default: P2)"},
                    "category": {"type": "string", "description": "Category (e.g., 'playback', 'navigation', 'search')"},
                    "acceptance_criteria": {"type": "string", "description": "Acceptance criteria (optional)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["requirement_code", "requirement_name"]
            }
        },
        {
            "name": "list_requirements",
            "description": """List all requirements with optional filters

Returns list of requirements with optional filtering by category, priority, or status.

Common Next Steps:
- To link requirements to test cases → Call list_testcases() FIRST to see what test cases exist
- To check coverage → Call get_coverage_summary()
- To find gaps → Call get_uncovered_requirements()

Don't assume test cases exist just because requirements exist!

Example:
  list_requirements(
    category='playback',
    priority='P1'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                    "priority": {"type": "string", "description": "Filter by priority: P1, P2, P3 (optional)"},
                    "status": {"type": "string", "description": "Filter by status (optional - default: 'active')"}
                },
                "required": []
            }
        },
        {
            "name": "get_requirement",
            "description": """Get requirement details by ID

Returns full details for a specific requirement.

Example:
  get_requirement(
    requirement_id='abc-123-def'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string", "description": "Requirement ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["requirement_id"]
            }
        },
        {
            "name": "update_requirement",
            "description": """Update an existing requirement

Modify requirement fields including app_type and device_model for reusability.

Example:
  update_requirement(
    requirement_id='abc-123-def',
    app_type='streaming',
    device_model='all',
    description='Updated description'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string", "description": "Requirement ID (REQUIRED)"},
                    "requirement_name": {"type": "string", "description": "Requirement name (optional)"},
                    "requirement_code": {"type": "string", "description": "Requirement code (optional)"},
                    "description": {"type": "string", "description": "Description (optional)"},
                    "priority": {"type": "string", "description": "Priority: P1, P2, P3 (optional)"},
                    "category": {"type": "string", "description": "Category (optional)"},
                    "app_type": {"type": "string", "description": "App type: 'streaming', 'social', 'all' (optional)"},
                    "device_model": {"type": "string", "description": "Device model: 'android_mobile', 'android_tv', 'web', 'all' (optional)"},
                    "status": {"type": "string", "description": "Status: 'active', 'deprecated' (optional)"},
                    "acceptance_criteria": {"type": "string", "description": "Acceptance criteria (optional)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["requirement_id"]
            }
        },
        {
            "name": "link_testcase_to_requirement",
            "description": """Link testcase to requirement for coverage tracking

Creates a link between a testcase and requirement to track test coverage.

CRITICAL PREREQUISITE - ALWAYS CHECK FIRST:
1. Call list_testcases() to see what test cases exist
2. Call list_requirements() to see what requirements exist  
3. Verify both IDs exist before linking
4. DO NOT assume test cases exist just because requirements exist

WRONG Workflow (causes errors):
  list_requirements() → ✓ Found requirements
  [SKIP list_testcases] ← ERROR: Assumption
  link_testcase_to_requirement() → FAILS: testcase_id doesn't exist

CORRECT Workflow:
  list_requirements() → ✓ Found requirements
  list_testcases() → ✓ Found 1 test case for sauce-demo
  link_testcase_to_requirement(
    testcase_id='<actual ID from list_testcases>',
    requirement_id='<actual ID from list_requirements>'
  )

Example:
  # Step 1: Check what exists
  requirements = list_requirements(category='navigation')
  testcases = list_testcases()  # ← MANDATORY
  
  # Step 2: Link with actual IDs
  link_testcase_to_requirement(
    testcase_id='tc-abc-123',  # From list_testcases output
    requirement_id='req-def-456',  # From list_requirements output
    coverage_type='full'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Testcase ID"},
                    "requirement_id": {"type": "string", "description": "Requirement ID"},
                    "coverage_type": {"type": "string", "description": "Coverage type: 'full' or 'partial' (optional - default: 'full')"},
                    "coverage_notes": {"type": "string", "description": "Coverage notes (optional)"}
                },
                "required": ["testcase_id", "requirement_id"]
            }
        },
        {
            "name": "unlink_testcase_from_requirement",
            "description": """Unlink testcase from requirement

Removes the link between a testcase and requirement.

Example:
  unlink_testcase_from_requirement(
    testcase_id='tc-abc-123',
    requirement_id='req-def-456'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Testcase ID"},
                    "requirement_id": {"type": "string", "description": "Requirement ID"}
                },
                "required": ["testcase_id", "requirement_id"]
            }
        },
        {
            "name": "get_testcase_requirements",
            "description": """Get all requirements linked to a testcase

Returns list of requirements that are covered by a specific testcase.

Example:
  get_testcase_requirements(
    testcase_id='tc-abc-123'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Testcase ID"}
                },
                "required": ["testcase_id"]
            }
        },
        {
            "name": "get_requirement_coverage",
            "description": """Get detailed coverage for a requirement

Returns coverage details including linked testcases, scripts, and execution history.

Example:
  get_requirement_coverage(
    requirement_id='req-abc-123'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string", "description": "Requirement ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["requirement_id"]
            }
        },
        {
            "name": "get_coverage_summary",
            "description": """Get coverage summary across all requirements

Returns overall coverage metrics including total requirements, covered/uncovered counts,
coverage percentage, and breakdowns by priority and category.

Example:
  get_coverage_summary()
  
  # With filters
  get_coverage_summary(
    category='playback',
    priority='P1'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                    "priority": {"type": "string", "description": "Filter by priority (optional)"}
                },
                "required": []
            }
        },
        {
            "name": "get_uncovered_requirements",
            "description": """Get all requirements without test coverage

Returns list of requirements that have no linked testcases or scripts.
Useful for identifying gaps in test coverage.

Example:
  get_uncovered_requirements()""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": []
            }
        }
    ]

