"""
AI Graph Builder - Complete AI-driven test case graph generation

Single-file implementation of the full AI pipeline:
1. Preprocessing: Cache check, exact matches, disambiguation
2. Generation: AI API call, JSON parsing
3. Post-processing: Validation, label enforcement, transition pre-fetching
4. Caching: Store successful graphs

NO legacy code, NO backward compatibility
Clean architecture following backend_host conventions
"""

import time
import re
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from difflib import get_close_matches, SequenceMatcher

# Imports
from shared.src.lib.utils.ai_utils import call_text_ai
from shared.src.lib.config.constants import AI_CONFIG
from shared.src.lib.database.ai_graph_cache_db import (
    store_graph,
    get_graph_by_fingerprint,
    _generate_fingerprint
)
from backend_host.src.services.ai.ai_preprocessing import (
    preprocess_prompt,
    check_exact_match
)


class AIGraphBuilder:
    """
    AI Graph Builder - Orchestrates complete AI graph generation pipeline
    
    Architecture:
    - Preprocessing: Smart prompt analysis before AI
    - Generation: AI API call with optimized context
    - Post-processing: Graph validation and enhancement
    - Caching: Intelligent caching for performance
    """
    
    def __init__(self, device):
        """
        Initialize AIGraphBuilder for a device
        
        Args:
            device: Device instance with navigation_executor, testcase_executor
        """
        self.device = device
        self._context_cache = {}
        self._cache_ttl = 86400  # 24 hours
        
        print(f"[@ai_builder] Initialized for device: {device.device_id}")
    
    # ========================================
    # PUBLIC API
    # ========================================
    
    def generate_graph(self,
                      prompt: str,
                      userinterface_name: str,
                      team_id: str,
                      current_node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate test case graph from natural language prompt
        
        Complete pipeline:
        1. Load context (available nodes/actions/verifications)
        2. Check cache
        3. Preprocess prompt (exact match, disambiguation)
        4. Call AI if needed
        5. Parse & validate response
        6. Enforce label conventions
        7. Pre-fetch navigation transitions
        8. Return graph + stats
        
        Args:
            prompt: Natural language test case description
            userinterface_name: Interface context (e.g., "horizon_android_mobile")
            team_id: Team ID for database operations
            current_node_id: Optional current navigation position
            
        Returns:
            {
                'success': bool,
                'graph': {'nodes': [...], 'edges': [...]},
                'analysis': str,
                'execution_time': float,
                'generation_stats': {
                    'prompt_tokens': int,
                    'completion_tokens': int,
                    'block_counts': {...}
                }
            }
        """
        start_time = time.time()
        
        try:
            print(f"[@ai_builder] 🎨 Starting graph generation")
            print(f"[@ai_builder]   Prompt: {prompt[:100]}...")
            print(f"[@ai_builder]   Interface: {userinterface_name}")
            
            # Step 1: Load context
            context = self._load_context(userinterface_name, current_node_id, team_id)
            
            # Step 2: Check cache (MANDATORY - skip AI if cache hit)
            fingerprint = _generate_fingerprint(prompt, context)
            cached = get_graph_by_fingerprint(fingerprint, team_id)
            
            if cached:
                print(f"[@ai_builder] ✅ CACHE HIT - returning immediately (no AI call)")
                return {
                    'success': True,
                    'graph': cached['graph'],
                    'analysis': cached['analysis'],
                    'execution_time': time.time() - start_time,
                    'message': 'Graph loaded from cache',
                    'cached': True
                }
            
            print(f"[@ai_builder] Cache MISS - generating with AI")
            
            # Step 3: Preprocess (exact match, learned mappings, disambiguation)
            # Extract node list for preprocessing
            node_list = [node.get('node_label', node.get('node_id')) 
                        for node in context.get('nodes', [])]
            
            # Check for exact match (skip AI entirely)
            exact_node = check_exact_match(prompt, node_list)
            if exact_node:
                print(f"[@ai_builder] 🎯 Exact match - generating simple graph (no AI)")
                graph = self._create_simple_navigation_graph(exact_node)
                analysis = f"Goal: Navigate to {exact_node}\nThinking: Exact match found, created direct navigation path."
                
                # Store in cache
                store_graph(
                    fingerprint=fingerprint,
                    original_prompt=prompt,
                    device_model=self.device.device_model,
                    userinterface_name=userinterface_name,
                    available_nodes=node_list,
                    graph=graph,
                    analysis=analysis,
                    team_id=team_id
                )
                
                return {
                    'success': True,
                    'graph': graph,
                    'analysis': analysis,
                    'execution_time': time.time() - start_time,
                    'message': 'Simple navigation generated (exact match)',
                    'cached': False,
                    'exact_match': True
                }
            
            # Apply learned mappings and check for ambiguities
            preprocessed = preprocess_prompt(prompt, node_list, team_id, userinterface_name)
            
            if preprocessed['status'] == 'needs_disambiguation':
                # Return disambiguation request to frontend
                return {
                    'success': False,
                    'needs_disambiguation': True,
                    'ambiguities': preprocessed['ambiguities'],
                    'auto_corrections': preprocessed.get('auto_corrections', []),
                    'original_prompt': prompt,
                    'execution_time': time.time() - start_time
                }
            
            # Use corrected prompt if available
            final_prompt = preprocessed.get('corrected_prompt', prompt)
            if preprocessed['status'] == 'auto_corrected':
                print(f"[@ai_builder] ✅ Applied {len(preprocessed['corrections'])} auto-corrections")
            
            # Step 4: Generate with AI
            ai_response = self._generate_with_ai(final_prompt, context, current_node_id)
            
            # Step 5: Check feasibility
            if not ai_response.get('feasible', True):
                return {
                    'success': False,
                    'error': 'Task not feasible',
                    'analysis': ai_response.get('analysis', ''),
                    'execution_time': time.time() - start_time
                }
            
            # Step 6: Extract graph
            graph = ai_response.get('graph', {})
            if not graph or not graph.get('nodes'):
                return {
                    'success': False,
                    'error': 'AI returned empty graph',
                    'execution_time': time.time() - start_time
                }
            
            # Step 7: Post-process graph
            graph = self._postprocess_graph(graph, context)
            
            # Step 8: Calculate stats
            stats = self._calculate_stats(graph, ai_response.get('_usage', {}))
            
            # Step 9: Store in cache for future use
            store_graph(
                fingerprint=fingerprint,
                original_prompt=prompt,
                device_model=context['device_model'],
                userinterface_name=userinterface_name,
                available_nodes=list(context.get('available_nodes', [])),
                graph=graph,
                analysis=ai_response.get('analysis', ''),
                team_id=team_id
            )
            
            print(f"[@ai_builder] ✅ Graph generated successfully")
            print(f"[@ai_builder]   Nodes: {len(graph.get('nodes', []))}, Edges: {len(graph.get('edges', []))}")
            
            return {
                'success': True,
                'graph': graph,
                'analysis': ai_response.get('analysis', ''),
                'plan_id': ai_response.get('id'),
                'execution_time': time.time() - start_time,
                'message': 'Graph generated successfully',
                'generation_stats': stats
            }
            
        except Exception as e:
            print(f"[@ai_builder] ❌ Graph generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Graph generation error: {str(e)}',
                'execution_time': time.time() - start_time
            }
    
    # ========================================
    # CONTEXT LOADING
    # ========================================
    
    def _load_context(self, userinterface_name: str, current_node_id: Optional[str], team_id: str) -> Dict[str, Any]:
        """
        Load execution context: available nodes, actions, verifications
        
        Uses caching to avoid repeated database queries
        """
        # Check cache
        cache_key = f"{self.device.device_id}_{userinterface_name}_{team_id}"
        cached_data, cache_time = self._context_cache.get(cache_key, (None, None))
        
        if cached_data and cache_time:
            current_time = time.time()
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_builder:context] ✅ Cache HIT (age: {current_time - cache_time:.1f}s)")
                cached_data['current_node_id'] = current_node_id
                return cached_data
        
        print(f"[@ai_builder:context] Loading fresh context...")
        
        # Load from device services
        context = {
            'device_model': self.device.device_model,
            'userinterface_name': userinterface_name,
            'team_id': team_id,
            'current_node_id': current_node_id,
        }
        
        # Get navigation nodes
        nav_nodes = self.device.navigation_executor.get_available_nodes(userinterface_name, team_id)
        context['available_nodes'] = self._format_navigation_context(nav_nodes)
        
        # Get actions
        actions = self.device.testcase_executor.get_available_actions()
        context['available_actions'] = self._format_action_context(actions)
        
        # Get verifications
        verifications = self.device.testcase_executor.get_available_verifications()
        context['available_verifications'] = self._format_verification_context(verifications)
        
        # Cache it
        self._context_cache[cache_key] = (context, time.time())
        
        print(f"[@ai_builder:context] Loaded: {len(nav_nodes)} nodes, {len(actions)} actions, {len(verifications)} verifications")
        
        return context
    
    def _format_navigation_context(self, nodes: List[Dict]) -> str:
        """Format navigation nodes for AI prompt"""
        if not nodes:
            return "Available Navigation Nodes: []"
        
        node_list = [f"- {node.get('node_label', node.get('node_id'))}" for node in nodes[:50]]  # Limit to 50
        return f"Available Navigation Nodes:\n" + "\n".join(node_list)
    
    def _format_action_context(self, actions: List[Dict]) -> str:
        """Format actions for AI prompt"""
        if not actions:
            return "Available Actions: []"
        
        action_list = []
        for action in actions[:20]:  # Limit to 20
            name = action.get('name', action.get('command'))
            desc = action.get('description', '')
            action_list.append(f"- {name}: {desc}" if desc else f"- {name}")
        
        return f"Available Actions:\n" + "\n".join(action_list)
    
    def _format_verification_context(self, verifications: List[Dict]) -> str:
        """Format verifications for AI prompt"""
        if not verifications:
            return "Available Verifications: []"
        
        verify_list = []
        for verify in verifications[:20]:  # Limit to 20
            name = verify.get('name', verify.get('type'))
            desc = verify.get('description', '')
            verify_list.append(f"- {name}: {desc}" if desc else f"- {name}")
        
        return f"Available Verifications:\n" + "\n".join(verify_list)
    
    # ========================================
    # AI GENERATION
    # ========================================
    
    def _generate_with_ai(self, prompt: str, context: Dict, current_node_id: Optional[str]) -> Dict:
        """
        Generate graph using AI
        
        Builds optimized prompt, calls API, parses response
        """
        # Build AI prompt
        ai_prompt = self._build_ai_prompt(prompt, context)
        
        # Call AI
        print(f"[@ai_builder:ai] Calling AI (prompt length: {len(ai_prompt)} chars)...")
        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=2000,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )
        
        if not result.get('success'):
            raise Exception(f"AI call failed: {result.get('error')}")
        
        print(f"[@ai_builder:ai] ✅ AI response received ({len(result.get('content', ''))} chars)")
        
        # Parse JSON
        parsed = self._parse_ai_response(result['content'])
        
        # Attach usage stats
        if 'usage' in result:
            parsed['_usage'] = result['usage']
        
        return parsed
    
    def _build_ai_prompt(self, prompt: str, context: Dict) -> str:
        """
        Build optimized AI prompt with context
        
        Includes:
        - Task description
        - Available navigation nodes
        - Available actions
        - Available verifications
        - Output format with examples
        - Label naming rules
        """
        current_node_label = context.get('current_node_label', 'ENTRY')
        
        ai_prompt = f"""You are controlling a TV application on a device ({context['device_model']}).
Your task is to navigate through the app using available commands provided.

Task: "{prompt}"
Device: {context['device_model']}
Current Position: {current_node_label}

OUTPUT FORMAT: Generate a React Flow graph with nodes and edges.

Node Types:
- start: Entry point (always first, id="start")
- navigation: Navigate to UI node
- action: Execute device action  
- verification: Check UI state
- success: Test passed (terminal)
- failure: Test failed (terminal)

{context['available_nodes']}

{context['available_actions']}

{context['available_verifications']}

Rules:
- If already at target node, respond with feasible=true, graph with just start→success
- If exact node exists → navigate directly
- If NO similar node → set feasible=false
- NEVER use node names not in the navigation list
- PRIORITIZE navigation over manual actions
- ALWAYS include label field in node data following these formats:
  * start: label="START"
  * success: label="SUCCESS"
  * failure: label="FAILURE"
  * navigation: label="navigation_N:target_node" (e.g., "navigation_1:home")
  * action: label="action_N:command" (e.g., "action_1:click_element")
  * verification: label="verification_N:type" (e.g., "verification_1:check_audio")

CRITICAL: Include "analysis" field with Goal and Thinking.

Analysis format:
- Goal: [What needs to be achieved]
- Thinking: [Brief explanation of approach/reasoning]

Example Response:
{{
  "analysis": "Goal: Navigate to home\\nThinking: 'home' node exists in navigation list → direct navigation in one step",
  "feasible": true,
  "graph": {{
    "nodes": [
      {{"id": "start", "type": "start", "position": {{"x": 100, "y": 100}}, "data": {{"label": "START"}}}},
      {{"id": "nav1", "type": "navigation", "position": {{"x": 100, "y": 200}}, "data": {{"label": "navigation_1:home", "target_node": "home", "target_node_id": "home", "action_type": "navigation"}}}},
      {{"id": "success", "type": "success", "position": {{"x": 100, "y": 300}}, "data": {{"label": "SUCCESS"}}}}
    ],
    "edges": [
      {{"id": "e1", "source": "start", "target": "nav1", "sourceHandle": "success", "type": "success"}},
      {{"id": "e2", "source": "nav1", "target": "success", "sourceHandle": "success", "type": "success"}}
    ]
  }}
}}

If task is not possible:
{{"analysis": "Goal: [state goal]\\nThinking: Task not feasible → no relevant navigation nodes exist", "feasible": false, "graph": {{"nodes": [], "edges": []}}}}

RESPOND WITH JSON ONLY. Keep analysis concise with Goal and Thinking structure."""

        return ai_prompt
    
    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """
        Parse AI JSON response with robust error handling
        
        Handles:
        - Markdown code blocks
        - Trailing content after JSON
        - Control characters in strings
        """
        try:
            cleaned_content = content.strip()
            
            # Handle markdown code blocks
            json_match = re.search(r'```json\s*\n(.*?)```', cleaned_content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1).strip()
            elif '```' in cleaned_content:
                json_match = re.search(r'```\s*\n(.*?)```', cleaned_content, re.DOTALL)
                if json_match:
                    cleaned_content = json_match.group(1).strip()
            elif cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
            
            # Sanitize control characters
            cleaned_content = self._sanitize_json_string(cleaned_content)
            
            # Parse JSON (handle trailing data)
            from json import JSONDecoder
            decoder = JSONDecoder()
            parsed_json, idx = decoder.raw_decode(cleaned_content)
            
            # Warn about trailing content
            remaining = cleaned_content[idx:].strip()
            if remaining:
                print(f"[@ai_builder:parse] ⚠️ AI returned extra content after JSON (ignored)")
            
            # Validate required fields
            if 'analysis' not in parsed_json:
                raise Exception("AI response missing 'analysis' field")
            if 'feasible' not in parsed_json:
                parsed_json['feasible'] = True
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[@ai_builder:parse] ❌ JSON parsing error: {e}")
            print(f"[@ai_builder:parse] Content preview: {content[:200]}")
            raise Exception(f"AI returned invalid JSON: {str(e)}")
    
    def _sanitize_json_string(self, json_str: str) -> str:
        """Remove/escape control characters that break JSON parsing"""
        # Replace literal newlines in strings with \n
        sanitized = re.sub(r'(?<!\\)\n(?=[^{}\[\]:,]*["\'])', r'\\n', json_str)
        # Replace tabs
        sanitized = re.sub(r'(?<!\\)\t', r'\\t', sanitized)
        # Remove other control characters
        sanitized = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', sanitized)
        return sanitized
    
    # ========================================
    # POST-PROCESSING
    # ========================================
    
    def _postprocess_graph(self, graph: Dict, context: Dict) -> Dict:
        """
        Post-process graph after AI generation
        
        Steps:
        1. Validate structure
        2. Enforce label conventions
        3. Pre-fetch navigation transitions
        4. Validate nodes exist
        """
        print(f"[@ai_builder:postprocess] Processing graph...")
        
        # Enforce labels
        graph = self._enforce_labels(graph)
        
        # Pre-fetch navigation transitions
        self._prefetch_navigation_transitions(graph, context)
        
        print(f"[@ai_builder:postprocess] ✅ Post-processing complete")
        
        return graph
    
    def _enforce_labels(self, graph: Dict) -> Dict:
        """
        Enforce label naming conventions
        
        - navigation: navigation_N:target_node
        - action: action_N:command
        - verification: verification_N:type
        - start/success/failure: uppercase
        """
        nodes = graph.get('nodes', [])
        
        nav_counter = 0
        action_counter = 0
        verify_counter = 0
        
        for node in nodes:
            node_type = node.get('type')
            data = node.get('data', {})
            
            if node_type == 'start':
                data['label'] = 'START'
            elif node_type == 'success':
                data['label'] = 'SUCCESS'
            elif node_type == 'failure':
                data['label'] = 'FAILURE'
            elif node_type == 'navigation':
                nav_counter += 1
                target = data.get('target_node') or data.get('target_node_id') or 'unknown'
                data['label'] = f"navigation_{nav_counter}:{target}"
            elif node_type == 'action':
                action_counter += 1
                command = data.get('command') or data.get('action_type') or 'action'
                data['label'] = f"action_{action_counter}:{command}"
            elif node_type == 'verification':
                verify_counter += 1
                verify_type = data.get('verification_type') or data.get('type') or 'verify'
                data['label'] = f"verification_{verify_counter}:{verify_type}"
        
        print(f"[@ai_builder:labels] Enforced labels: {nav_counter} nav, {action_counter} action, {verify_counter} verify")
        
        return graph
    
    def _prefetch_navigation_transitions(self, graph: Dict, context: Dict) -> None:
        """
        Pre-fetch navigation transitions for all navigation nodes
        
        Resolves target nodes and embeds transition data in graph
        """
        nodes = graph.get('nodes', [])
        nav_nodes = [n for n in nodes if n.get('type') == 'navigation']
        
        if not nav_nodes:
            return
        
        print(f"[@ai_builder:prefetch] Pre-fetching transitions for {len(nav_nodes)} navigation nodes...")
        
        for node in nav_nodes:
            data = node.get('data', {})
            target_node = data.get('target_node') or data.get('target_node_id')
            
            if not target_node:
                continue
            
            try:
                # Use device's navigation executor to get path
                path_result = self.device.navigation_executor.get_navigation_path(
                    target_node_id=target_node,
                    userinterface_name=context['userinterface_name'],
                    team_id=context['team_id']
                )
                
                if path_result.get('success'):
                    data['transitions'] = path_result.get('transitions', [])
                    print(f"[@ai_builder:prefetch] ✅ Pre-fetched path to: {target_node}")
                else:
                    print(f"[@ai_builder:prefetch] ⚠️ Could not resolve: {target_node}")
                    data['transitions'] = []
                    
            except Exception as e:
                print(f"[@ai_builder:prefetch] ❌ Error pre-fetching {target_node}: {e}")
                data['transitions'] = []
    
    # ========================================
    # STATS CALCULATION
    # ========================================
    
    def _calculate_stats(self, graph: Dict, usage: Dict) -> Dict:
        """Calculate generation statistics"""
        nodes = graph.get('nodes', [])
        
        block_counts = {
            'navigation': len([n for n in nodes if n.get('type') == 'navigation']),
            'action': len([n for n in nodes if n.get('type') == 'action']),
            'verification': len([n for n in nodes if n.get('type') == 'verification']),
            'other': len([n for n in nodes if n.get('type') not in ['start', 'success', 'failure', 'navigation', 'action', 'verification']]),
            'total': len(nodes),
        }
        
        blocks_generated = [
            {
                'type': node.get('type'),
                'label': node.get('data', {}).get('label') or node.get('type'),
                'id': node.get('id'),
            }
            for node in nodes
        ]
        
        return {
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
            'block_counts': block_counts,
            'blocks_generated': blocks_generated,
        }
    
    # ========================================
    # CACHE MANAGEMENT
    # ========================================
    
    def clear_context_cache(self):
        """Clear context cache"""
        self._context_cache.clear()
        print(f"[@ai_builder] Context cache cleared")
    
    # ========================================
    # SIMPLE GRAPH GENERATION (No AI)
    # ========================================
    
    def _create_simple_navigation_graph(self, target_node: str) -> Dict:
        """
        Create a simple START → navigation → SUCCESS graph without AI
        
        Used for exact match preprocessing
        
        Args:
            target_node: Node to navigate to
            
        Returns:
            Graph dict with nodes and edges
        """
        return {
            'nodes': [
                {
                    'id': 'start',
                    'type': 'start',
                    'position': {'x': 100, 'y': 100},
                    'data': {'label': 'START'}
                },
                {
                    'id': 'nav1',
                    'type': 'navigation',
                    'position': {'x': 100, 'y': 200},
                    'data': {
                        'label': f'navigation_1:{target_node}',
                        'target_node': target_node,
                        'target_node_id': target_node,
                        'action_type': 'navigation'
                    }
                },
                {
                    'id': 'success',
                    'type': 'success',
                    'position': {'x': 100, 'y': 300},
                    'data': {'label': 'SUCCESS'}
                }
            ],
            'edges': [
                {
                    'id': 'e_start_nav1',
                    'source': 'start',
                    'target': 'nav1',
                    'sourceHandle': 'success',
                    'type': 'success'
                },
                {
                    'id': 'e_nav1_success',
                    'source': 'nav1',
                    'target': 'success',
                    'sourceHandle': 'success',
                    'type': 'success'
                }
            ]
        }

