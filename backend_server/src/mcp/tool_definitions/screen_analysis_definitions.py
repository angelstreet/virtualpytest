"""Screen Analysis tool definitions - Unified selector analysis"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get screen analysis tool definitions"""
    return [
        {
            "name": "analyze_screen_for_action",
            "description": """Analyze screen elements to find BEST selector for clicking/interacting.

✅ Uses same selector scoring logic as AI exploration system (shared/src/selector_scoring.py)

**CRITICAL - Use this BEFORE creating edges:**
1. Call dump_ui_elements() to get elements
2. Call analyze_screen_for_action(elements, intent, platform)
3. Get ready-to-use action with guaranteed unique selector
4. Use in create_edge()

**Platform-Specific Priority:**
- Mobile: ID (resource_id) > CONTENT_DESC > XPATH > TEXT
- Web: ID (#id) > XPATH > TEXT

**Why use this:**
- ❌ OLD WAY: LLM guesses from raw dump → picks ambiguous "Search" text → edge fails
- ✅ NEW WAY: LLM calls this tool → gets analyzed "#search-field" ID → edge works

**Returns:**
Ready-to-use action parameters with:
- selector_type: 'id', 'xpath', or 'text'
- selector_value: The actual selector string
- command: The correct command ('click_element_by_id', etc.)
- action_params: Ready to use in create_edge
- score: Confidence score (>1000 = high, >500 = medium)
- unique: Boolean - is this selector unique on page?

Example:
  # Step 1: Get elements
  elements = dump_ui_elements(device_id='device1')
  
  # Step 2: Analyze what to click
  action = analyze_screen_for_action(
    elements=elements['elements'],
    intent='search field',
    platform='web'
  )
  # Returns: {command: 'click_element_by_id', params: {element_id: 'search-field'}, score: 1200, unique: true}
  
  # Step 3: Use in edge
  create_edge(
    actions=[{
      'command': action['command'],
      'params': action['action_params']
    }]
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "elements": {
                        "type": "array",
                        "description": "Elements from dump_ui_elements (REQUIRED)"
                    },
                    "intent": {
                        "type": "string",
                        "description": "What to click (e.g., 'search field', 'login button')"
                    },
                    "platform": {
                        "type": "string",
                        "description": "'mobile' or 'web' (REQUIRED)",
                        "enum": ["mobile", "web"]
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional - uses default if omitted)"
                    }
                },
                "required": ["elements", "platform"]
            }
        },
        {
            "name": "analyze_screen_for_verification",
            "description": """Analyze screen elements to find BEST verification for node detection.

✅ Uses same selector scoring logic as AI exploration system (shared/src/selector_scoring.py)

**CRITICAL - Use this BEFORE creating nodes:**
1. Navigate to the screen
2. Call dump_ui_elements() to get elements
3. Call analyze_screen_for_verification(elements, node_label, platform)
4. Get ready-to-use verification parameters
5. Use in create_node(data={verifications: [...]})

**Platform-Specific Priority:**
- Mobile: ID (resource_id) > CONTENT_DESC > XPATH > TEXT
- Web: ID (#id) > XPATH > TEXT

**Why use this:**
- ❌ OLD WAY: LLM guesses verification → uses ambiguous text → node detection fails
- ✅ NEW WAY: LLM calls this tool → gets unique selector → node detection works

**Returns:**
Ready-to-use verification with:
- command: 'waitForElementToAppear'
- verification_type: 'adb' or 'web'
- params: {search_term: ...} or {text: ...}
- score: Confidence score
- unique: Is this selector unique?

Example:
  # Step 1: Navigate to screen
  navigate_to_node(target_node_label='home')
  
  # Step 2: Get elements
  elements = dump_ui_elements(device_id='device1')
  
  # Step 3: Analyze verification
  verification = analyze_screen_for_verification(
    elements=elements['elements'],
    node_label='home',
    platform='web'
  )
  # Returns: {command: 'waitForElementToAppear', params: {text: '#home-tab-selected'}, score: 1500, unique: true}
  
  # Step 4: Use in node
  create_node(
    label='home',
    data={
      'verifications': [{
        'command': verification['command'],
        'verification_type': verification['verification_type'],
        'params': verification['params']
      }]
    }
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "elements": {
                        "type": "array",
                        "description": "Elements from dump_ui_elements (REQUIRED)"
                    },
                    "node_label": {
                        "type": "string",
                        "description": "Node name (e.g., 'home', 'login', 'search_results') (REQUIRED)"
                    },
                    "platform": {
                        "type": "string",
                        "description": "'mobile' or 'web' (REQUIRED)",
                        "enum": ["mobile", "web"]
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional - uses default if omitted)"
                    }
                },
                "required": ["elements", "node_label", "platform"]
            }
        }
    ]

