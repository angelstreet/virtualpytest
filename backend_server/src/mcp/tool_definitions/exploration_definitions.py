"""AI Exploration tool definitions - Automated tree building"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get AI exploration tool definitions"""
    return [
        {
            "name": "start_ai_exploration",
            "description": """Start AI-powered exploration of a userinterface (RECOMMENDED for new apps).

🤖 **Automated Tree Building** - AI analyzes screen and proposes navigation structure.

**What it does:**
1. Captures screenshot of home screen
2. Analyzes UI elements (buttons, tabs, menus)
3. Detects strategy (click for mobile/web, D-pad for TV)
4. Proposes nodes and edges structure
5. Returns plan for your approval

**Returns:**
- exploration_id: For polling status
- exploration_plan: Proposed items to create
- strategy: 'click' (mobile/web) or 'dpad' (TV)
- screenshot: Visual of analyzed screen

**Next step:** Call `approve_exploration_plan()` to create structure

Example:
  # Step 1: Start exploration
  result = start_ai_exploration(
    userinterface_name='sauce-demo',
    original_prompt='Build navigation for e-commerce site'
  )
  
  # Step 2: Review plan
  print(result['exploration_plan']['items'])  # ['login', 'signup', 'search', ...]
  
  # Step 3: Approve (see approve_exploration_plan)

**Prerequisites:**
- Userinterface must exist (create_userinterface)
- Device must be on home screen
- get_compatible_hosts() recommended first

**Time saved:** 
- Manual: 10+ steps per edge (create, test, fix)
- AI: 3 steps total (start, approve, validate)""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {
                        "type": "string",
                        "description": "User interface name (e.g., 'sauce-demo', 'netflix_mobile')"
                    },
                    "tree_id": {
                        "type": "string",
                        "description": "Navigation tree ID (optional - auto-detected from userinterface)"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional - uses default)"
                    },
                    "original_prompt": {
                        "type": "string",
                        "description": "Your goal/intent (optional - helps AI context)"
                    }
                },
                "required": ["userinterface_name"]
            }
        },
        {
            "name": "get_exploration_status",
            "description": """Poll AI exploration progress.

Returns current status and plan details.

**Statuses:**
- 'exploring': AI analyzing screen
- 'awaiting_approval': Plan ready for review
- 'structure_created': Nodes/edges created
- 'validating': Testing edges
- 'validation_complete': Ready for finalization
- 'failed': Error occurred

Example:
  status = get_exploration_status(
    exploration_id='uuid-from-start',
    host_name='sunri-pi1'
  )
  
  if status['status'] == 'awaiting_approval':
    # Review plan and approve
    print(status['exploration_plan']['items'])""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID from start_ai_exploration"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name (from start_ai_exploration response)"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    }
                },
                "required": ["exploration_id", "host_name"]
            }
        },
        {
            "name": "approve_exploration_plan",
            "description": """Approve AI plan and create navigation structure (nodes + edges).

Creates all nodes and edges in batch with proper selectors from AI analysis.

**Parameters:**
- selected_items: Which items to create (defaults to all if not specified)
- selected_screen_items: TV only - which screen nodes to create (defaults to all)

**TV Dual-Layer (automatic):**
- Creates focus nodes (menu positions): home_tvguide, home_apps
- Creates screen nodes (actual screens): tvguide, apps
- Bidirectional edges with RIGHT/LEFT, OK/BACK

**Mobile/Web (automatic):**
- Creates screen nodes: login, signup, search
- Bidirectional edges with click_element + BACK

**Returns:**
- nodes_created: Count of nodes
- edges_created: Count of edges
- node_ids: List of created node IDs
- edge_ids: List of created edge IDs

Example:
  # Approve all items
  result = approve_exploration_plan(
    exploration_id='uuid',
    host_name='sunri-pi1',
    userinterface_name='sauce-demo'
  )
  
  # Or select specific items
  result = approve_exploration_plan(
    exploration_id='uuid',
    host_name='sunri-pi1',
    userinterface_name='sauce-demo',
    selected_items=['login', 'signup', 'search']
  )
  
  # TV: Also select which screens
  result = approve_exploration_plan(
    exploration_id='uuid',
    host_name='sunri-pi1', 
    userinterface_name='netflix_tv',
    selected_items=['tv guide', 'apps'],
    selected_screen_items=['tv guide']  # Only create screen for tv guide
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "userinterface_name": {
                        "type": "string",
                        "description": "User interface name"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    },
                    "selected_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Items to create (optional - defaults to all)"
                    },
                    "selected_screen_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "TV only: Screen nodes to create (optional - defaults to all)"
                    }
                },
                "required": ["exploration_id", "host_name", "userinterface_name"]
            }
        },
        {
            "name": "validate_exploration_edges",
            "description": """Auto-validate all created edges by testing them sequentially.

Tests each edge by:
1. Executing forward action (click or D-pad)
2. Capturing screenshot (visual proof)
3. Executing reverse action (BACK or LEFT)
4. Verifying return to origin

**Returns progress updates:**
- Shows which edge is being tested
- Reports success/failure per edge
- Provides screenshots of reached screens
- Suggests fixes for failed edges

**TV Dual-Layer (depth-first):**
Tests complete cycles:
- home → home_tvguide: RIGHT
- home_tvguide ↓ tvguide: OK (screenshot)
- tvguide ↑ home_tvguide: BACK
- Continue to next item

**Mobile/Web:**
Tests each edge:
- home → login: click
- login → home: BACK

Example:
  # Start validation
  result = validate_exploration_edges(
    exploration_id='uuid',
    host_name='sunri-pi1',
    userinterface_name='sauce-demo'
  )
  
  # Poll for progress
  while result['has_more_items']:
    result = validate_exploration_edges(...)
    print(f"Tested: {result['item']} - {result['click_result']}")
  
  # When done: result['has_more_items'] == False""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "userinterface_name": {
                        "type": "string",
                        "description": "User interface name"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    }
                },
                "required": ["exploration_id", "host_name", "userinterface_name"]
            }
        },
        {
            "name": "get_node_verification_suggestions",
            "description": """Get AI-suggested verifications for created nodes.

Analyzes UI dumps captured during validation to find unique elements per node.

**Returns:**
- Suggested verifications for each node
- Confidence scores
- Uniqueness validation

Example:
  suggestions = get_node_verification_suggestions(
    exploration_id='uuid',
    host_name='sunri-pi1'
  )
  
  # Review suggestions
  for suggestion in suggestions['suggestions']:
    print(f"Node: {suggestion['node_id']}")
    print(f"Verification: {suggestion['verification']}")""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    }
                },
                "required": ["exploration_id", "host_name"]
            }
        },
        {
            "name": "approve_node_verifications",
            "description": """Apply AI-suggested verifications to nodes.

Adds verifications + screenshots to nodes for reliable detection.

Example:
  result = approve_node_verifications(
    exploration_id='uuid',
    host_name='sunri-pi1',
    approved_verifications=suggestions['suggestions']
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "userinterface_name": {
                        "type": "string",
                        "description": "User interface name"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    },
                    "approved_verifications": {
                        "type": "array",
                        "description": "Verifications to apply (from get_node_verification_suggestions)"
                    }
                },
                "required": ["exploration_id", "host_name", "userinterface_name", "approved_verifications"]
            }
        },
        {
            "name": "finalize_exploration",
            "description": """Finalize exploration by removing _temp suffixes.

Makes all nodes and edges permanent.

**This is the final step** after validation is complete.

Example:
  result = finalize_exploration(
    exploration_id='uuid',
    host_name='sunri-pi1',
    tree_id='tree-uuid'
  )
  
  print(f"Finalized: {result['nodes_renamed']} nodes, {result['edges_renamed']} edges")""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "exploration_id": {
                        "type": "string",
                        "description": "Exploration ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "tree_id": {
                        "type": "string",
                        "description": "Tree ID"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    }
                },
                "required": ["exploration_id", "host_name", "tree_id"]
            }
        }
    ]

