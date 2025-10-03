"""
AI Prompt Validation and Disambiguation

Pre-processes prompts, validates AI plans, finds suggestions for invalid nodes.
Integrates with learned disambiguation database.

This module consolidates all validation logic in one place:
- Pre-processing: Apply learned mappings before AI generation
- Post-processing: Validate AI plans after generation
- Fuzzy matching: Find similar nodes for suggestions
"""

import re
from difflib import get_close_matches
from typing import Dict, List, Optional, Tuple

from shared.src.lib.supabase.ai_prompt_disambiguation_db import (
    get_learned_mapping,
    get_learned_mappings_batch,
    save_disambiguation
)


# =============================================================================
# STOPWORDS & FILTERS
# =============================================================================

# Common English words that should NOT be treated as navigation nodes
# These are filtered out to prevent false positive ambiguities
STOPWORDS = {
    # Articles & prepositions
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that',
    'the', 'was', 'will', 'with', 'she', 'they', 'we', 'you',
    
    # Navigation/action verbs (not node names)
    'go', 'to', 'navigate', 'open', 'close', 'press', 'click', 'tap',
    'select', 'exit', 'move', 'change', 'switch', 'set', 'get',
    
    # Temporal/sequential words
    'then', 'now', 'next', 'after', 'before', 'first', 'last', 'again',
    'back', 'forward', 'up', 'down',
    
    # Common actions
    'do', 'make', 'take', 'show', 'see', 'look', 'find', 'use',
}


def is_valid_potential_node(phrase: str) -> bool:
    """
    Check if a phrase could potentially be a navigation node reference.
    
    Rules:
    1. Must be at least 3 characters total (filters: "go", "to", "in", "up")
    2. Must not be a stopword
    3. Individual words in phrase must be >= 3 chars (unless contains digits/special chars)
    
    Args:
        phrase: Potential node name or phrase
    
    Returns:
        True if phrase could be a valid node reference
    
    Examples:
        >>> is_valid_potential_node("live_fullscreen")
        True
        >>> is_valid_potential_node("home")
        True
        >>> is_valid_potential_node("to")
        False
        >>> is_valid_potential_node("go")
        False
        >>> is_valid_potential_node("to_live")  # "to" is < 3 chars
        False
        >>> is_valid_potential_node("ch+")  # Has special char, might be valid
        True
    """
    phrase = phrase.strip().lower()
    
    # Must be at least 3 characters total
    if len(phrase) < 3:
        return False
    
    # Check if entire phrase is a stopword
    if phrase in STOPWORDS:
        return False
    
    # For multi-word or underscore-separated phrases, check each part
    # Split on spaces and underscores
    parts = re.split(r'[\s_]+', phrase)
    
    for part in parts:
        # Allow parts with digits or special characters (e.g., "ch+", "5", "360")
        if any(c.isdigit() or not c.isalnum() for c in part):
            continue
        
        # Alphabetic parts must be >= 3 chars OR be exceptions
        if len(part) < 3 and part in STOPWORDS:
            return False
    
    return True


# =============================================================================
# FUZZY MATCHING UTILITIES
# =============================================================================

def find_fuzzy_matches(target: str, available_nodes: List[str], 
                      max_results: int = 2, cutoff: float = 0.6) -> List[str]:
    """
    Find fuzzy string matches using difflib.
    
    IMPROVED: Returns max 2 results with higher cutoff (0.6) for better quality suggestions.
    
    Args:
        target: The string to match
        available_nodes: List of valid node names
        max_results: Maximum number of matches to return (default: 2 for UI)
        cutoff: Similarity threshold (0.0-1.0, default: 0.6 for quality)
    
    Returns:
        List of matching nodes, best matches first (max 2)
    
    Examples:
        >>> find_fuzzy_matches("live fullscreen", ["live_fullscreen", "live", "fullscreen"])
        ["live_fullscreen", "live"]  # Max 2, best matches
    """
    # Try exact match first (case-insensitive)
    for node in available_nodes:
        if node.lower() == target.lower():
            return [node]
    
    # Fuzzy match with higher cutoff for quality
    target_lower = target.lower()
    nodes_lower = [n.lower() for n in available_nodes]
    
    matches = get_close_matches(target_lower, nodes_lower, n=max_results, cutoff=cutoff)
    
    # Return original-cased nodes (max 2)
    return [n for n in available_nodes if n.lower() in matches][:max_results]


def extract_potential_node_phrases(prompt: str) -> List[str]:
    """
    Extract phrases from prompt that could be node references.
    
    IMPROVED with stopword and length filtering to reduce false positives.
    
    Patterns:
    - Quoted strings: "live fullscreen"
    - After navigation keywords: "navigate to live" → extracts "live"
    - Individual words (filtered by stopwords and length)
    - Multi-word combinations (2-3 words)
    
    Args:
        prompt: User's natural language prompt
    
    Returns:
        List of potential node phrases (filtered)
    
    Examples:
        >>> extract_potential_node_phrases("go to live fullscreen")
        ['live fullscreen', 'live', 'fullscreen']
        # Filtered: "go", "to" (stopwords < 3 chars)
    """
    phrases = []
    prompt_lower = prompt.lower()
    
    # Pattern 1: Quoted strings (high priority - user explicitly marked)
    quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
    for q in quoted:
        if is_valid_potential_node(q):
            phrases.append(q.lower())
    
    # Pattern 2: After navigation keywords
    # Extract content after "go to", "navigate to", "open", etc.
    navigation_pattern = r'(?:go\s+to|navigate\s+to|open|goto)\s+([a-zA-Z0-9_\s]+?)(?:\s+and|\s+then|$|,|\.|;)'
    nav_matches = re.findall(navigation_pattern, prompt_lower)
    for match in nav_matches:
        clean_match = match.strip()
        if is_valid_potential_node(clean_match):
            phrases.append(clean_match)
    
    # Pattern 3: Extract all words, then filter
    words = re.findall(r'\b[a-zA-Z0-9_]+\b', prompt_lower)
    for word in words:
        if is_valid_potential_node(word):
            phrases.append(word)
    
    # Deduplicate while preserving order
    seen = set()
    unique_phrases = []
    for phrase in phrases:
        phrase = phrase.strip()
        if phrase and phrase not in seen:
            seen.add(phrase)
            unique_phrases.append(phrase)
    
    return unique_phrases


# =============================================================================
# PRE-PROCESSING (Before AI Generation)
# =============================================================================

def preprocess_prompt(prompt: str, available_nodes: List[str], 
                     team_id: str, userinterface_name: str) -> Dict:
    """
    Pre-process prompt: try to solve WITHOUT AI, or prepare for AI generation.
    
    This runs BEFORE AI plan generation to:
    1. Find exact matches → return direct navigation plan (SKIP AI)
    2. Apply learned mappings automatically
    3. Detect ambiguous phrases that need user input
    4. Auto-correct high-confidence single matches
    
    Args:
        prompt: User's natural language prompt
        available_nodes: List of valid navigation nodes
        team_id: Team ID for database lookup
        userinterface_name: UI context (e.g., "horizon_android_mobile")
    
    Returns:
        {
            'status': 'exact_match' | 'clear' | 'auto_corrected' | 'needs_disambiguation',
            'target_node': str (if exact_match),
            'corrected_prompt': str (if auto_corrected),
            'corrections': [...] (if auto_corrected),
            'ambiguities': [...] (if needs_disambiguation)
        }
    """
    print(f"[@ai_prompt_validation:preprocess] Starting preprocessing: '{prompt}'")
    print(f"[@ai_prompt_validation:preprocess] Available nodes: {len(available_nodes)} nodes")
    
    # Extract potential node phrases from prompt
    phrases = extract_potential_node_phrases(prompt)
    print(f"[@ai_prompt_validation:preprocess] Extracted phrases: {phrases}")
    
    # Get learned mappings from database (batch query for efficiency)
    learned = get_learned_mappings_batch(team_id, userinterface_name, phrases)
    if learned:
        print(f"[@ai_prompt_validation:preprocess] Found {len(learned)} learned mappings")
    
    # Track what we found
    exact_matches = []
    auto_corrections = []
    needs_disambiguation = []
    
    for phrase in phrases:
        # Check for exact match first (HIGHEST PRIORITY - skip AI entirely)
        if phrase in available_nodes:
            exact_matches.append(phrase)
            print(f"[@ai_prompt_validation:preprocess] ✅ Exact match: '{phrase}'")
            continue
        
        # Check learned mapping (SECOND PRIORITY)
        if phrase in learned:
            learned_node = learned[phrase]
            # Validate learned mapping is still valid (node might have been deleted)
            if learned_node in available_nodes:
                auto_corrections.append({
                    'from': phrase,
                    'to': learned_node,
                    'source': 'learned'
                })
                print(f"[@ai_prompt_validation:preprocess] Learned mapping: '{phrase}' → '{learned_node}'")
                continue
        
        # Find fuzzy matches (THIRD PRIORITY)
        matches = find_fuzzy_matches(phrase, available_nodes, max_results=2, cutoff=0.6)
        
        if len(matches) == 1:
            # Single high-confidence match → auto-correct
            auto_corrections.append({
                'from': phrase,
                'to': matches[0],
                'source': 'fuzzy'
            })
            print(f"[@ai_prompt_validation:preprocess] Fuzzy auto-correct: '{phrase}' → '{matches[0]}'")
        elif len(matches) > 1:
            # Multiple matches (max 2) → needs user disambiguation
            needs_disambiguation.append({
                'original': phrase,
                'suggestions': matches  # Max 2 suggestions
            })
            print(f"[@ai_prompt_validation:preprocess] ⚠️ Ambiguous: '{phrase}' → {matches}")
        else:
            print(f"[@ai_prompt_validation:preprocess] ⚠️ No match found: '{phrase}'")
    
    # CASE 1: Single exact match found → Direct navigation (SKIP AI)
    if len(exact_matches) == 1 and not auto_corrections and not needs_disambiguation:
        print(f"[@ai_prompt_validation:preprocess] ✅ Result: EXACT_MATCH → '{exact_matches[0]}' (AI not needed)")
        return {
            'status': 'exact_match',
            'target_node': exact_matches[0],
            'original_prompt': prompt
        }
    
    # CASE 2: Multiple exact matches → needs clarification
    if len(exact_matches) > 1:
        print(f"[@ai_prompt_validation:preprocess] ⚠️ Result: AMBIGUOUS (multiple exact matches: {exact_matches})")
        needs_disambiguation.append({
            'original': 'multiple_nodes',
            'suggestions': exact_matches[:2]  # Max 2 for UI
        })
    
    # CASE 3: Needs user disambiguation
    if needs_disambiguation:
        print(f"[@ai_prompt_validation:preprocess] ⚠️ Result: NEEDS_DISAMBIGUATION ({len(needs_disambiguation)} ambiguities)")
        return {
            'status': 'needs_disambiguation',
            'original_prompt': prompt,
            'ambiguities': needs_disambiguation,
            'auto_corrections': auto_corrections,
            'exact_matches': exact_matches
        }
    
    # CASE 4: Auto-corrected (apply corrections to prompt)
    if auto_corrections:
        corrected_prompt = prompt
        for correction in auto_corrections:
            # Use word boundaries to avoid partial replacements
            corrected_prompt = re.sub(
                r'\b' + re.escape(correction['from']) + r'\b',
                correction['to'],
                corrected_prompt,
                flags=re.IGNORECASE
            )
        print(f"[@ai_prompt_validation:preprocess] ✅ Result: AUTO_CORRECTED → '{corrected_prompt}'")
        return {
            'status': 'auto_corrected',
            'original_prompt': prompt,
            'corrected_prompt': corrected_prompt,
            'corrections': auto_corrections,
            'exact_matches': exact_matches
        }
    
    # CASE 5: Clear (no changes needed, but AI required)
    print(f"[@ai_prompt_validation:preprocess] ✅ Result: CLEAR (AI generation needed)")
    return {
        'status': 'clear',
        'prompt': prompt,
        'exact_matches': exact_matches
    }


# =============================================================================
# POST-PROCESSING (After AI Generation)
# =============================================================================

def validate_plan(plan: Dict, available_nodes: List[str], 
                 team_id: str, userinterface_name: str) -> Dict:
    """
    Validate AI-generated plan: check nodes exist, apply learned mappings, find suggestions.
    
    This runs AFTER AI generates a plan to:
    1. Validate all navigation nodes exist
    2. Apply learned mappings to fix invalid nodes
    3. Auto-fix single-match fuzzy matches
    4. Return suggestions for ambiguous nodes
    
    Args:
        plan: AI-generated plan dict
        available_nodes: List of valid navigation nodes
        team_id: Team ID for database lookup
        userinterface_name: UI context
    
    Returns:
        {
            'valid': bool,
            'plan': modified_plan (with auto-fixes applied),
            'invalid_nodes': [{'original': str, 'suggestions': [str], 'step_index': int}],
            'modified': bool (whether auto-fixes were applied)
        }
    """
    if not plan.get('steps'):
        return {'valid': True, 'plan': plan, 'invalid_nodes': [], 'modified': False}
    
    invalid_nodes = []
    modified = False
    
    for step_index, step in enumerate(plan['steps']):
        if step.get('command') != 'execute_navigation':
            continue
        
        target = step.get('params', {}).get('target_node')
        if not target:
            continue
        
        # Check if valid
        if target in available_nodes:
            continue
        
        # Try learned mapping from database
        learned_node = get_learned_mapping(team_id, userinterface_name, target)
        if learned_node and learned_node in available_nodes:
            # Auto-fix with learned mapping
            step['params']['target_node'] = learned_node
            if 'description' in step:
                step['description'] = learned_node
            modified = True
            print(f"[@ai_prompt_validation:validate] Auto-fixed (learned): '{target}' → '{learned_node}'")
            continue
        
        # Find fuzzy suggestions (max 2 with higher quality threshold)
        suggestions = find_fuzzy_matches(target, available_nodes, max_results=2, cutoff=0.6)
        
        if len(suggestions) == 1:
            # Single match → auto-fix
            step['params']['target_node'] = suggestions[0]
            if 'description' in step:
                step['description'] = suggestions[0]
            modified = True
            print(f"[@ai_prompt_validation:validate] Auto-fixed (fuzzy): '{target}' → '{suggestions[0]}'")
        else:
            # Multiple (max 2) or no matches → needs user input
            invalid_nodes.append({
                'original': target,
                'suggestions': suggestions,  # Max 2 suggestions
                'step_index': step_index
            })
            print(f"[@ai_prompt_validation:validate] Invalid node: '{target}' (suggestions: {suggestions})")
    
    return {
        'valid': len(invalid_nodes) == 0,
        'plan': plan,
        'invalid_nodes': invalid_nodes,
        'modified': modified
    }


# =============================================================================
# HELPER: Apply User Selections
# =============================================================================

def apply_user_selections(plan: Dict, selections: Dict[str, str], 
                         team_id: str, userinterface_name: str, 
                         save_to_db: bool = True) -> Dict:
    """
    Apply user disambiguation selections to plan and optionally save to database for learning.
    
    Args:
        plan: AI plan with invalid nodes
        selections: {"original_phrase": "selected_node"}
        team_id: Team ID
        userinterface_name: UI context
        save_to_db: Whether to save selections for future learning
    
    Returns:
        Modified plan with selections applied
    """
    for step in plan.get('steps', []):
        if step.get('command') != 'execute_navigation':
            continue
        
        target = step.get('params', {}).get('target_node')
        if target in selections:
            new_node = selections[target]
            step['params']['target_node'] = new_node
            if 'description' in step:
                step['description'] = new_node
            
            # Save to DB for learning
            if save_to_db:
                save_disambiguation(team_id, userinterface_name, target, new_node)
                print(f"[@ai_prompt_validation:apply_selections] Saved learning: '{target}' → '{new_node}'")
    
    return plan
