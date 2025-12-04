"""
Analyst Agent Skills

Tools for result analysis, bug detection, coverage tracking, and Jira integration.
"""

# Tools that Analyst Agent can use
ANALYST_TOOLS = [
    # Coverage analysis
    "get_requirement_coverage",
    "get_coverage_summary",
    "get_uncovered_requirements",
    "get_testcase_requirements",
    
    # Result inspection
    "list_testcases",
    "load_testcase",
    "get_execution_status",
    
    # Verification analysis
    "list_verifications",
    "verify_node",
    
    # Evidence review
    "capture_screenshot",
    "get_transcript",
    
    # Navigation context (to understand what was tested)
    "list_navigation_nodes",
    "get_node",
    "get_edge",
    "list_nodes",
    "list_edges",
    
    # Requirements context
    "list_requirements",
    "get_requirement",
]

# Future: Jira integration tools (to be added)
JIRA_TOOLS = [
    # "jira_search_issues",      # Search for existing tickets
    # "jira_create_issue",       # Create new bug ticket
    # "jira_add_comment",        # Add comment to existing ticket
    # "jira_get_issue",          # Get ticket details
]

# Tool descriptions for system prompt
ANALYST_TOOL_DESCRIPTIONS = """
You have access to these tools:

**Coverage Analysis:**
- get_requirement_coverage: Get test coverage for a requirement
- get_coverage_summary: Get overall coverage metrics
- get_uncovered_requirements: Find requirements without tests
- get_testcase_requirements: Get requirements linked to a test case

**Result Inspection:**
- list_testcases: List all test cases (with status if available)
- load_testcase: Load test case details and last result
- get_execution_status: Check execution status

**Verification:**
- list_verifications: List node verifications
- verify_node: Check if screen matches expected state

**Evidence:**
- capture_screenshot: Take current screenshot
- get_transcript: Get execution logs

**Navigation Context:**
- list_navigation_nodes: Get all nodes in tree
- get_node: Get node details
- get_edge: Get edge details
- list_nodes/list_edges: Query tree structure

**Requirements:**
- list_requirements: List all requirements
- get_requirement: Get requirement details

**Coming Soon - Jira Integration:**
- Search for existing bug tickets
- Create new tickets for real bugs
- Link test failures to Jira issues
"""

