"""
Executor Agent Skills

Tools for test execution, navigation, and evidence capture.
"""

# Tools that Executor Agent can use
EXECUTOR_TOOLS = [
    # Device control
    "take_control",
    "get_device_info",
    "get_execution_status",
    
    # Test execution
    "execute_testcase",
    "execute_testcase_by_id",
    
    # Navigation execution
    "navigate_to_node",
    "execute_edge",
    "execute_device_action",
    "list_actions",
    
    # Verification
    "verify_node",
    "list_verifications",
    
    # Evidence capture
    "capture_screenshot",
    "get_transcript",
    "save_node_screenshot",
]

# Tool descriptions for system prompt
EXECUTOR_TOOL_DESCRIPTIONS = """
You have access to these tools:

**Device Control:**
- take_control: Lock device for exclusive use
- get_device_info: Get device status
- get_execution_status: Check if execution is running

**Test Execution:**
- execute_testcase: Run a test case by name
- execute_testcase_by_id: Run a test case by ID

**Navigation:**
- navigate_to_node: Navigate to a specific screen
- execute_edge: Execute a single edge transition
- execute_device_action: Execute a device command
- list_actions: List available device actions

**Verification:**
- verify_node: Verify current screen matches node
- list_verifications: List verifications for a node

**Evidence:**
- capture_screenshot: Take screenshot
- get_transcript: Get execution transcript
- save_node_screenshot: Save screenshot to node
"""


