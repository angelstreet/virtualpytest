#!/usr/bin/env python3
"""
Test the LLM directly with the correct prompt to verify it works
"""

import json
import subprocess

def test_llm_direct():
    """Test the LLM with the corrected prompt"""
    
    print("🤖 Testing LLM Direct with Corrected Prompt")
    print("=" * 50)
    
    # The corrected prompt with nodes
    prompt_content = """You are controlling a TV application on a device (STB/mobile/PC).
Your task is to navigate through the app using available commands provided.

Task: "go to home_replay"
Device: android_mobile
Nodes: ['home', 'home_tvguide', 'live_fullscreen', 'live', 'home_movies', 'home_replay', 'home_saved', 'tvguide_livetv']

Commands: ['execute_navigation', 'click_element', 'press_key', 'wait']

Rules:
- "go to node X" → execute_navigation, target_node="X"
- "click X" → click_element, element_id="X"
- "press X" → press_key, key="X"

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{"analysis": "Task requires navigating to live content. Since 'live' node is available, I'll navigate there directly.", "feasible": true, "plan": [{"step": 1, "command": "execute_navigation", "params": {"target_node": "live"}, "description": "Navigate to live content"}]}

If task is not possible:
{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED:"""

    # Create the curl command
    curl_data = {
        "model": "qwen/qwen-2.5-vl-7b-instruct",
        "messages": [
            {
                "role": "user",
                "content": prompt_content
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.0
    }
    
    curl_command = [
        "curl", "-X", "POST", "https://api.openrouter.ai/api/v1/chat/completions",
        "-H", "Authorization: Bearer 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",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(curl_data)
    ]
    
    print("📤 Sending request to LLM...")
    print(f"📝 Prompt includes 'home_replay': {'home_replay' in prompt_content}")
    print(f"📝 Prompt includes 'Nodes:': {'Nodes:' in prompt_content}")
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            
            if 'choices' in response and len(response['choices']) > 0:
                ai_response = response['choices'][0]['message']['content']
                print("\n🤖 AI Response:")
                print("=" * 40)
                print(ai_response)
                print("=" * 40)
                
                # Try to parse the AI response as JSON
                try:
                    ai_json = json.loads(ai_response)
                    print("\n✅ AI Response Analysis:")
                    print(f"   • Has analysis field: {'analysis' in ai_json}")
                    print(f"   • Task feasible: {ai_json.get('feasible', 'unknown')}")
                    print(f"   • Plan steps: {len(ai_json.get('plan', []))}")
                    
                    if 'analysis' in ai_json:
                        print(f"   • Analysis: {ai_json['analysis']}")
                    
                    if ai_json.get('feasible') and ai_json.get('plan'):
                        first_step = ai_json['plan'][0]
                        print(f"   • First step: {first_step.get('command')} -> {first_step.get('params', {}).get('target_node')}")
                        
                        if first_step.get('params', {}).get('target_node') == 'home_replay':
                            print("\n🎉 SUCCESS: AI correctly identified home_replay as available!")
                        else:
                            print("\n⚠️  AI didn't use home_replay directly (but that might be valid)")
                    
                except json.JSONDecodeError:
                    print("\n❌ AI response is not valid JSON")
                    
            else:
                print("\n❌ No choices in response")
                print(f"Response: {response}")
        else:
            print(f"\n❌ Curl failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("\n⏰ Request timed out")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_llm_direct()
