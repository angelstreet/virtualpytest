"""
Builder Agent Skills

Tools for creating test cases, requirements, and manual tree construction.
"""

# Tools that Builder Agent can use
BUILDER_TOOLS = [
    # Requirements management
    "create_requirement",
    "list_requirements",
    "get_requirement",
    "update_requirement",
    
    # Test case management
    "save_testcase",
    "generate_and_save_testcase",
    "list_testcases",
    "load_testcase",
    "rename_testcase",
    
    # Requirement-testcase linking
    "link_testcase_to_requirement",
    "unlink_testcase_from_requirement",
    "get_testcase_requirements",
    
    # Manual tree construction (when AI exploration not suitable)
    "create_node",
    "create_edge",
    "create_subtree",
    
    # Coverage tracking
    "get_requirement_coverage",
    "get_coverage_summary",
    "get_uncovered_requirements",
]

# Tool descriptions for system prompt
BUILDER_TOOL_DESCRIPTIONS = """
You have access to these tools:

**Requirements:**
- create_requirement: Create a new requirement with acceptance criteria
- list_requirements: List all requirements for a userinterface
- get_requirement: Get requirement details
- update_requirement: Update requirement

**Test Cases:**
- save_testcase: Save a manually created test case
- generate_and_save_testcase: AI-generate and save test case
- list_testcases: List all test cases
- load_testcase: Load test case details
- rename_testcase: Rename a test case

**Linking:**
- link_testcase_to_requirement: Link test case to requirement
- unlink_testcase_from_requirement: Unlink test case
- get_testcase_requirements: Get requirements for a test case

**Manual Tree Construction:**
- create_node: Create a navigation node
- create_edge: Create an edge between nodes
- create_subtree: Create multiple nodes/edges at once

**Coverage:**
- get_requirement_coverage: Get coverage for a requirement
- get_coverage_summary: Get overall coverage summary
- get_uncovered_requirements: Find requirements without tests
"""


