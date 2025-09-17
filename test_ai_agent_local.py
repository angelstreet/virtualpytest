#!/usr/bin/env python3
"""
Test the actual AI agent code locally to debug the node extraction issue
"""

import sys
import os

# Add the project paths
sys.path.append('/Users/cpeengineering/virtualpytest')
sys.path.append('/Users/cpeengineering/virtualpytest/backend_core/src')
sys.path.append('/Users/cpeengineering/virtualpytest/shared')

def test_ai_agent_locally():
    """Test the actual AI agent code with mock data"""
    
    print("🧪 Testing AI Agent Code Locally")
    print("=" * 50)
    
    # Mock navigation tree data (same structure as logs show)
    mock_navigation_tree = {
        'nodes': [
            {'node_id': 'node-1', 'label': 'home'},
            {'node_id': 'node-1748723779677', 'label': 'home_tvguide'},
            {'node_id': 'node-1750663753038', 'label': 'live_fullscreen'},
            {'node_id': 'node-1749036265480', 'label': 'live'},
            {'node_id': 'node-1749014425463', 'label': 'home_movies'},
            {'node_id': 'node-1749014380799', 'label': 'home_replay'},
            {'node_id': 'node-1749014440260', 'label': 'home_saved'},
            {'node_id': 'node-1748862182738', 'label': 'tvguide_livetv'},
        ]
    }
    
    # Test the exact code from ai_agent.py
    print("\n📝 Testing Node Extraction (from ai_agent.py):")
    
    # Extract available navigation nodes from the loaded tree
    available_nodes = []
    if mock_navigation_tree and 'nodes' in mock_navigation_tree:
        # Extract only labels for AI (short and token-efficient)
        available_nodes = [node.get('label') for node in mock_navigation_tree['nodes'] 
                         if node.get('label')]
        print(f"AI[device1]: Extracted {len(available_nodes)} navigation nodes: {available_nodes}")
    
    # Build navigation context with ALL nodes
    navigation_context = ""
    if available_nodes:
        navigation_context = f"Nodes: {available_nodes}"
    
    print(f"\n📋 Navigation Context: '{navigation_context}'")
    
    # Test prompt construction
    task_description = "go to home_replay"
    device_model = "android_mobile"
    navigation_commands = ['execute_navigation', 'click_element', 'press_key', 'wait']
    
    prompt = f"""You are controlling a TV application on a device (STB/mobile/PC).
Your task is to navigate through the app using available commands provided.

Task: "{task_description}"
Device: {device_model}
{navigation_context}

Commands: {navigation_commands}

Rules:
- "go to node X" → execute_navigation, target_node="X"
- "click X" → click_element, element_id="X"
- "press X" → press_key, key="X"

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{{"analysis": "Task requires navigating to live content. Since 'live' node is available, I'll navigate there directly.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "live"}}, "description": "Navigate to live content"}}]}}

If task is not possible:
{{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED:"""

    print("\n🎯 GENERATED PROMPT:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    
    # Check if the issue is resolved
    has_nodes_line = "Nodes:" in prompt
    has_home_replay = "home_replay" in prompt
    
    print(f"\n🔍 DIAGNOSIS:")
    print(f"✅ Prompt contains 'Nodes:' line: {has_nodes_line}")
    print(f"✅ Prompt contains 'home_replay': {has_home_replay}")
    print(f"✅ Available nodes count: {len(available_nodes)}")
    
    if has_nodes_line and has_home_replay:
        print("\n🎉 SUCCESS: The fix works! The server needs to be restarted.")
    else:
        print("\n❌ ISSUE: Something is still wrong with the code.")
    
    return available_nodes, navigation_context, prompt

if __name__ == "__main__":
    nodes, context, prompt = test_ai_agent_locally()
    
    print(f"\n📊 SUMMARY:")
    print(f"   • Nodes extracted: {len(nodes)}")
    print(f"   • Context: {context[:50]}...")
    print(f"   • Prompt length: {len(prompt)} characters")
