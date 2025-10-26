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
import traceback
import threading
from typing import Dict, List, Optional, Any, Tuple
from difflib import get_close_matches, SequenceMatcher
from dataclasses import dataclass, asdict
from datetime import datetime

# Imports
from shared.src.lib.utils.ai_utils import call_text_ai
from shared.src.lib.config.constants import AI_CONFIG, CACHE_CONFIG
from shared.src.lib.database.ai_graph_cache_db import (
    store_graph,
    get_graph_by_fingerprint,
    _generate_fingerprint
)
from backend_host.src.services.ai.ai_preprocessing import (
    preprocess_prompt,
    check_exact_match,
    smart_preprocess  # NEW: Smart preprocessing with filtering
)


# =====================================================
# PROMPT TEMPLATES & VERSIONING
# =====================================================

PROMPT_TEMPLATES = {
    'v1': {
        'version': '1.0.0',
        'description': 'Original prompt template',
        'template': '''Task: {task}

{available_nodes}

{available_actions}

{available_verifications}

Generate a test case graph in JSON format with nodes and edges.'''
    },
    'v2': {
        'version': '2.0.0',
        'description': 'Improved with explicit label requirements and examples',
        'template': '''Task: {task}

Context:
{available_nodes}
{available_actions}
{available_verifications}

CRITICAL LABEL REQUIREMENTS:
- Navigation nodes: MUST use format "navigation_N:target_node" (e.g., "navigation_1:home")
- Action nodes: MUST use format "action_N:command" (e.g., "action_1:click")
- Verification nodes: MUST use format "verification_N:type" (e.g., "verification_1:check_audio")
- Terminal nodes: Use "START", "SUCCESS", "FAILURE"

Generate a test case graph in JSON format following these requirements.'''
    }
}

DEFAULT_PROMPT_VERSION = 'v2'  # Current production version


# =====================================================
# METRICS & OBSERVABILITY
# =====================================================

@dataclass
class GenerationMetrics:
    """Structured metrics for graph generation tracking"""
    fingerprint: str
    device_id: str
    team_id: str
    userinterface_name: str
    
    # Performance
    cached: bool
    preprocessing_method: str  # 'exact'|'learned'|'fuzzy'|'ai'|'none'
    duration_ms: int
    
    # AI usage (if applicable)
    ai_called: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    ai_cost_estimate: float  # Rough estimate in USD
    
    # Graph stats
    node_count: int
    edge_count: int
    
    # Preprocessing confidence (if applicable)
    preprocessing_confidence: Optional[float]
    auto_corrections_count: int
    
    # Timestamp
    timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dict for logging"""
        return asdict(self)


class AIGraphBuilder:
    """
    AI Graph Builder - Orchestrates complete AI graph generation pipeline
    
    Architecture:
    - Preprocessing: Smart prompt analysis before AI
    - Generation: AI API call with optimized context
    - Post-processing: Graph validation and enhancement
    - Caching: Intelligent caching for performance
    """
    
    def __init__(self, device, prompt_version: str = DEFAULT_PROMPT_VERSION):
        """
        Initialize AIGraphBuilder for a device
        
        Args:
            device: Device instance with navigation_executor, testcase_executor
            prompt_version: AI prompt template version ('v1', 'v2', etc.)
        """
        self.device = device
        self._context_cache = {}
        # Use MEDIUM_TTL (5 minutes) - navigation changes frequently
        self._cache_ttl = CACHE_CONFIG['MEDIUM_TTL']
        
        # Prompt versioning
        if prompt_version not in PROMPT_TEMPLATES:
            print(f"[@ai_builder] ⚠️  Unknown prompt version '{prompt_version}', using '{DEFAULT_PROMPT_VERSION}'")
            prompt_version = DEFAULT_PROMPT_VERSION
        self.prompt_version = prompt_version
        template_info = PROMPT_TEMPLATES[prompt_version]
        print(f"[@ai_builder] Using prompt template: {template_info['version']} - {template_info['description']}")
        
        # Metrics collection
        self._metrics_buffer = []  # Store recent metrics
        self._metrics_max_buffer = 100  # Keep last 100 generations
        
        # Race condition prevention (cache locking)
        self._generation_locks = {}  # fingerprint → Lock
        self._lock_manager = threading.Lock()  # Protects _generation_locks dict
        
        print(f"[@ai_builder] Initialized for device: {device.device_id}")
        print(f"[@ai_builder] Context cache TTL: {self._cache_ttl}s ({self._cache_ttl/60:.1f} minutes)")
    
    def _record_metric(self, metric: GenerationMetrics):
        """
        Record generation metrics for observability
        
        Args:
            metric: GenerationMetrics instance
        """
        # Add to buffer
        self._metrics_buffer.append(metric)
        
        # Keep buffer size limited
        if len(self._metrics_buffer) > self._metrics_max_buffer:
            self._metrics_buffer.pop(0)
        
        # Log structured metrics
        print(f"[@ai_builder:metrics] {metric.preprocessing_method.upper()} generation")
        print(f"[@ai_builder:metrics]   Duration: {metric.duration_ms}ms")
        print(f"[@ai_builder:metrics]   Cached: {metric.cached}")
        if metric.ai_called:
            print(f"[@ai_builder:metrics]   AI tokens: {metric.total_tokens} (~${metric.ai_cost_estimate:.4f})")
        print(f"[@ai_builder:metrics]   Graph: {metric.node_count} nodes, {metric.edge_count} edges")
    
    def get_metrics_summary(self) -> Dict:
        """
        Get metrics summary for monitoring
        
        Returns:
            Dict with aggregated metrics
        """
        if not self._metrics_buffer:
            return {'total_generations': 0}
        
        total = len(self._metrics_buffer)
        cached = sum(1 for m in self._metrics_buffer if m.cached)
        ai_called = sum(1 for m in self._metrics_buffer if m.ai_called)
        total_tokens = sum(m.total_tokens for m in self._metrics_buffer)
        total_cost = sum(m.ai_cost_estimate for m in self._metrics_buffer)
        avg_duration = sum(m.duration_ms for m in self._metrics_buffer) / total
        
        # Count preprocessing methods
        methods = {}
        for m in self._metrics_buffer:
            methods[m.preprocessing_method] = methods.get(m.preprocessing_method, 0) + 1
        
        return {
            'total_generations': total,
            'cache_hit_rate': cached / total if total > 0 else 0,
            'ai_call_rate': ai_called / total if total > 0 else 0,
            'total_tokens_used': total_tokens,
            'total_cost_estimate': total_cost,
            'avg_duration_ms': avg_duration,
            'preprocessing_methods': methods,
            'device_id': self.device.device_id
        }
    
    def _create_metric(self, fingerprint: str, team_id: str, userinterface_name: str,
                      graph: Dict, cached: bool, preprocessing_method: str, 
                      duration_ms: int, ai_usage: Optional[Dict] = None,
                      preprocessing_confidence: Optional[float] = None,
                      auto_corrections_count: int = 0) -> GenerationMetrics:
        """
        Create a GenerationMetrics instance
        
        Args:
            fingerprint: Graph fingerprint
            team_id: Team ID
            userinterface_name: Interface name
            graph: Generated graph
            cached: Whether loaded from cache
            preprocessing_method: 'exact'|'learned'|'fuzzy'|'ai'|'none'
            duration_ms: Generation duration in milliseconds
            ai_usage: AI token usage dict (if AI was called)
            preprocessing_confidence: Confidence score for preprocessing
            auto_corrections_count: Number of auto-corrections applied
            
        Returns:
            GenerationMetrics instance
        """
        ai_called = ai_usage is not None
        prompt_tokens = ai_usage.get('prompt_tokens', 0) if ai_usage else 0
        completion_tokens = ai_usage.get('completion_tokens', 0) if ai_usage else 0
        total_tokens = ai_usage.get('total_tokens', 0) if ai_usage else 0
        
        # Rough cost estimate (OpenRouter pricing varies, using ~$0.01 per 1K tokens as average)
        ai_cost_estimate = (total_tokens / 1000) * 0.01 if ai_called else 0.0
        
        return GenerationMetrics(
            fingerprint=fingerprint,
            device_id=self.device.device_id,
            team_id=team_id,
            userinterface_name=userinterface_name,
            cached=cached,
            preprocessing_method=preprocessing_method,
            duration_ms=duration_ms,
            ai_called=ai_called,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            ai_cost_estimate=ai_cost_estimate,
            node_count=len(graph.get('nodes', [])),
            edge_count=len(graph.get('edges', [])),
            preprocessing_confidence=preprocessing_confidence,
            auto_corrections_count=auto_corrections_count,
            timestamp=datetime.now().isoformat()
        )
    
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
            
            # Step 2: Generate fingerprint for this request
            fingerprint = _generate_fingerprint(prompt, context)
            
            # Step 3: Get or create lock for this fingerprint (prevent duplicate AI calls)
            with self._lock_manager:
                if fingerprint not in self._generation_locks:
                    self._generation_locks[fingerprint] = threading.Lock()
                generation_lock = self._generation_locks[fingerprint]
            
            # Step 4: Acquire lock (only ONE request per fingerprint generates)
            with generation_lock:
                # Check cache AGAIN (another request might have just completed)
                cached = get_graph_by_fingerprint(fingerprint, team_id)
                
                if cached:
                    print(f"[@ai_builder] ✅ CACHE HIT (after lock) - returning immediately")
                    return {
                        'success': True,
                        'graph': cached['graph'],
                        'analysis': cached['analysis'],
                        'execution_time': time.time() - start_time,
                        'message': 'Graph loaded from cache',
                        'cached': True
                    }
                
                print(f"[@ai_builder] Cache MISS - this request will generate")
                
                # Step 5: SMART PREPROCESSING with context filtering
                # Extract raw lists for smart_preprocess
                node_list = [node.get('node_label', node.get('node_id')) 
                            for node in context.get('nodes_raw', [])]
                action_list = [action.get('command', action.get('action_type', '')) 
                              for action in context.get('actions_raw', [])]
                verification_list = [v.get('command', v.get('verification_type', ''))
                                    for v in context.get('verifications_raw', [])]
                
                # Run smart preprocessing (intent extraction + context filtering)
                preprocessed = smart_preprocess(
                    prompt=prompt,
                    all_nodes=node_list,
                    all_actions=action_list,
                    all_verifications=verification_list,
                    team_id=team_id,
                    userinterface_name=userinterface_name
                )
                
                # Handle different preprocessing outcomes
                if preprocessed['status'] == 'exact_match':
                    # Simple prompt with exact match - skip AI entirely
                    exact_node = preprocessed['node']
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
                
                elif preprocessed['status'] == 'needs_disambiguation':
                    # Return disambiguation request to frontend
                    return {
                        'success': False,
                        'needs_disambiguation': True,
                        'ambiguities': preprocessed['ambiguities'],
                        'auto_corrections': preprocessed.get('auto_corrections', []),
                        'original_prompt': prompt,
                        'execution_time': time.time() - start_time
                    }
                
                elif preprocessed['status'] == 'impossible':
                    # Task cannot be completed (missing required context)
                    return {
                        'success': False,
                        'error': preprocessed['reason'],
                        'execution_time': time.time() - start_time
                    }
                
                elif preprocessed['status'] == 'ready':
                    # Ready for AI generation with filtered context
                    final_prompt = preprocessed['corrected_prompt']
                    filtered_context = preprocessed['filtered_context']
                    structure_hints = preprocessed['structure_hints']
                    formatted_context = preprocessed['formatted_context']
                    
                    print(f"[@ai_builder] ✅ Preprocessing complete")
                    print(f"[@ai_builder]   Context reduction: {preprocessed['stats']['reduction_percent']}")
                    
                    # Update context with filtered data for AI
                    # Replace full catalog with filtered items
                    context['available_nodes'] = formatted_context
                    context['structure_hints'] = structure_hints
                    context['intent'] = preprocessed['intent']
                else:
                    # Unknown status
                    return {
                        'success': False,
                        'error': f"Unknown preprocessing status: {preprocessed['status']}",
                        'execution_time': time.time() - start_time
                    }
                
                # Step 6: Generate with AI (inside lock to prevent duplicate calls)
                ai_response = self._generate_with_ai(final_prompt, context, current_node_id)
                
                # Step 7: Check feasibility
                if not ai_response.get('feasible', True):
                    return {
                        'success': False,
                        'error': 'Task not feasible',
                        'analysis': ai_response.get('analysis', ''),
                        'execution_time': time.time() - start_time
                    }
                
                # Step 8: Extract graph
                graph = ai_response.get('graph', {})
                if not graph or not graph.get('nodes'):
                    return {
                        'success': False,
                        'error': 'AI returned empty graph',
                        'execution_time': time.time() - start_time
                    }
                
                # Step 9: Post-process graph
                graph = self._postprocess_graph(graph, context)
                
                # Step 10: Calculate stats
                stats = self._calculate_stats(graph, ai_response.get('_usage', {}))
                
                # Step 11: Store in cache for future use (still inside lock)
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
            # Lock released here - subsequent requests can now use cached result
            
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
        # Store RAW data for preprocessing (lists of dicts)
        context['nodes_raw'] = nav_nodes
        # Store FORMATTED strings for AI prompt
        context['available_nodes'] = self._format_navigation_context(nav_nodes)
        
        # Get actions
        actions = self.device.testcase_executor.get_available_actions()
        context['actions_raw'] = actions
        context['available_actions'] = self._format_action_context(actions)
        
        # Get verifications
        verifications = self.device.testcase_executor.get_available_verifications()
        context['verifications_raw'] = verifications
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
        Build AI prompt using versioned template
        
        Uses self.prompt_version to select template, allowing A/B testing
        and gradual rollout of prompt improvements.
        
        Context-aware: Includes current device state and structure hints
        """
        template_config = PROMPT_TEMPLATES[self.prompt_version]
        template = template_config['template']
        
        # Get current node context (context-aware generation)
        current_node_id = context.get('current_node_id')
        current_context = ""
        if current_node_id and current_node_id != 'unknown':
            current_context = f"\n\nCURRENT DEVICE STATE:\n- Currently at node: {current_node_id}\n- If already at target node, skip navigation\n- Optimize path from current position"
        
        # Get structure hints from smart preprocessing
        structure_hints = context.get('structure_hints', '')
        if structure_hints:
            current_context += f"\n\n{structure_hints}"
        
        # Format template with context
        ai_prompt = template.format(
            task=prompt,
            available_nodes=context.get('available_nodes', ''),
            available_actions=context.get('available_actions', ''),
            available_verifications=context.get('available_verifications', '')
        ) + current_context
        
        print(f"[@ai_builder:prompt] Using template {self.prompt_version} ({template_config['version']})")
        if current_node_id:
            print(f"[@ai_builder:prompt] Context-aware: current node = {current_node_id}")
        if structure_hints:
            print(f"[@ai_builder:prompt] Structure hints included")
        
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
        """Clear context cache (manual)"""
        self._context_cache.clear()
        print(f"[@ai_builder] Context cache cleared manually")
    
    def invalidate_context_cache(self, reason: str = "Navigation tree updated"):
        """
        Invalidate context cache when navigation graph changes
        
        This should be called when:
        - Navigation nodes are added/removed
        - Node properties are updated
        - User interface structure changes
        
        Args:
            reason: Why cache is being invalidated (for logging)
        """
        self._context_cache.clear()
        print(f"[@ai_builder] 🔄 Context cache invalidated: {reason}")
        print(f"[@ai_builder]    Reason: Ensure fresh data for AI generation")
    
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

