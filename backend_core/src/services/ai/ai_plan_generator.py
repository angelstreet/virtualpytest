"""
AI Plan Generator

Stateless AI planner with all original sophistication preserved.
"""

import time
import json
from typing import Dict, Any

from shared.lib.utils.ai_utils import call_text_ai, AI_CONFIG


class AIPlanGenerator:
    """Stateless AI planner with ALL original sophistication preserved"""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        # PRESERVE: All original caching logic
        self._context_cache = {}
        self._action_cache = {}
        self._verification_cache = {}
        self._navigation_cache = {}
        self._cache_ttl = 300  # 5 minutes

    def generate_plan(self, prompt: str, context: Dict, current_node_id: str = None) -> Dict:
        """Generate plan dict directly - no object conversion"""
        # Add current node to context
        context = context.copy()
        context['current_node_id'] = current_node_id
        
        # Use cached context if available
        cached_context = self._get_cached_context(context)
        ai_response = self._call_ai(prompt, cached_context)
        
        # Transform plan structure for frontend compatibility
        if 'plan' in ai_response:
            ai_response['steps'] = ai_response.pop('plan')  # Rename 'plan' to 'steps'
        
        # Add metadata to AI response and return dict directly
        import uuid
        ai_response['id'] = str(uuid.uuid4())
        ai_response['prompt'] = prompt
        return ai_response
    
    def _get_cached_context(self, context: Dict) -> Dict:
        """Apply caching logic to context"""
        userinterface_name = context['userinterface_name']
        device_model = context['device_model']
        current_time = time.time()
        
        # Check main context cache
        cache_key = f"{userinterface_name}:{device_model}"
        if cache_key in self._context_cache:
            cached_data, cache_time = self._context_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_planner] Using cached context for {cache_key}")
                # Merge with current context (preserve current_node_id)
                cached_data = cached_data.copy()
                cached_data['current_node_id'] = context.get('current_node_id')
                return cached_data
        
        # Cache the context
        self._context_cache[cache_key] = (context, current_time)
        print(f"[@ai_planner] Cached context for {cache_key}")
        return context
    
    def _call_ai(self, prompt: str, context: Dict) -> Dict:
        """PRESERVE: All original sophisticated AI prompt logic"""
        available_nodes = context['available_nodes']
        available_actions = context['available_actions']
        available_verifications = context['available_verifications']
        device_model = context['device_model']
        current_node_id = context.get('current_node_id')
        current_node_label = context.get('current_node_label')
        
        print(f"[@ai_planner] _call_ai context: nodes={len(available_nodes)}, actions={len(available_actions)}, verifications={len(available_verifications)}, device_model={device_model}")
        
        # Use context as-is from services
        navigation_context = available_nodes
        action_context = available_actions
        verification_context = available_verifications
        
        # PRESERVE: All original sophisticated AI prompt
        ai_prompt = f"""You are controlling a TV application on a device ({device_model}).
Your task is to navigate through the app using available commands provided.

Task: "{prompt}"
Device: {device_model}
Current Position: {current_node_label}

Navigation System: Each node in the navigation list is a DIRECT destination you can navigate to in ONE STEP.
- Node names like "home_replay", "home_movies", "live" are COMPLETE node identifiers, not hierarchical paths
- To go to "home_replay" → execute_navigation with target_node="home_replay" (NOT "home" then "replay")
- Each node represents a specific screen/section that can be reached directly through the navigation tree
- Only use action commands (click/press) if the exact node doesn't exist in the available navigation nodes

{navigation_context}

{action_context}

{verification_context}

Rules:
- If already at target node, respond with feasible=true, plan=[]
- "go to node X" → execute_navigation, target_node="X" (use EXACT node name from navigation list)
- "click X" → click_element, element_id="X"  
- "press X" → press_key, key="X"
- NEVER break down node names (e.g., "home_replay" is ONE node, not "home" + "replay")
- PRIORITIZE navigation over manual actions
- ALWAYS specify action_type in params

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{{"analysis": "Task requires navigating to home_replay. Since 'home_replay' node is available in the navigation list, I'll navigate there directly in one step.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home_replay", "action_type": "navigation"}}, "description": "Navigate directly to home_replay"}}]}}

If task is not possible:
{{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED"""

        # Log the full prompt for debugging
        print(f"[@ai_planner] AI Prompt (length: {len(ai_prompt)} chars):")
        print("=" * 80)
        print(repr(ai_prompt))
        print("=" * 80)

        # PRESERVE: All original AI call logic
        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=2000,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )

        print(f"[@ai_planner] AI Response received, content length: {len(result.get('content', '')) if result else 0} characters")

        if not result.get('success'):
            raise Exception(f"AI call failed: {result.get('error')}")

        return self._extract_json_from_ai_response(result['content'])
    
    def _extract_json_from_ai_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from AI response using existing codebase pattern"""
        try:
            # Use existing codebase pattern (same as ai_utils.py, video_ai_helpers.py, ai_analyzer.py)
            cleaned_content = content.strip()
            
            # Handle markdown code blocks
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
            
            print(f"[@ai_planner] Cleaned content: {repr(cleaned_content)}")
            
            # Parse JSON
            parsed_json = json.loads(cleaned_content)
            print(f"[@ai_planner] Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[@ai_planner] JSON parsing error: {e}")
            print(f"[@ai_planner] Raw content: {repr(content)}")
            raise Exception(f"AI returned invalid JSON: {e}")
        except Exception as e:
            print(f"[@ai_planner] JSON extraction error: {e}")
            raise Exception(f"Failed to extract JSON from AI response: {e}")
    
    def clear_context_cache(self, device_model: str = None, userinterface_name: str = None):
        """PRESERVE: All original cache clearing logic"""
        if device_model and userinterface_name:
            # Clear specific caches
            action_key = f"action:{device_model}:{userinterface_name}"
            verification_key = f"verification:{device_model}:{userinterface_name}"
            navigation_key = f"navigation:{device_model}:{userinterface_name}"
            context_key = f"{userinterface_name}:{device_model}"
            
            self._action_cache.pop(action_key, None)
            self._verification_cache.pop(verification_key, None)
            self._navigation_cache.pop(navigation_key, None)
            self._context_cache.pop(context_key, None)
            
            print(f"[@ai_planner] Cleared context caches for model: {device_model}, interface: {userinterface_name}")
        else:
            # Clear all caches
            self._action_cache.clear()
            self._verification_cache.clear()
            self._navigation_cache.clear()
            self._context_cache.clear()
            print(f"[@ai_planner] Cleared all context caches")
