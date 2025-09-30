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
# FUZZY MATCHING UTILITIES
# =============================================================================

def find_fuzzy_matches(target: str, available_nodes: List[str], 
                      max_results: int = 3, cutoff: float = 0.4) -> List[str]:
    """
    Find fuzzy string matches using difflib.
    
    Args:
        target: The string to match
        available_nodes: List of valid node names
        max_results: Maximum number of matches to return
        cutoff: Similarity threshold (0.0-1.0)
    
    Returns:
        List of matching nodes, best matches first
    """
    # Try exact match first (case-insensitive)
    for node in available_nodes:
        if node.lower() == target.lower():
            return [node]
    
    # Fuzzy match
    target_lower = target.lower()
    nodes_lower = [n.lower() for n in available_nodes]
    
    matches = get_close_matches(target_lower, nodes_lower, n=max_results, cutoff=cutoff)
    
    # Return original-cased nodes
    return [n for n in available_nodes if n.lower() in matches]


def extract_potential_node_phrases(prompt: str) -> List[str]:
    """
    Extract phrases from prompt that could be node references.
    
    Patterns:
    - Quoted strings: "live fullscreen"
    - After navigation keywords: "navigate to live"
    - Individual words
    
    Args:
        prompt: User's natural language prompt
    
    Returns:
        List of potential node phrases
    """
    phrases = []
    
    # Pattern 1: Quoted strings
    quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
    phrases.extend(quoted)
    
    # Pattern 2: Words/phrases after navigation keywords
    # Matches: "to X", "navigate to X", "go to X", "open X"
    navigation_pattern = r'(?:to|navigate to|go to|open)\s+([a-zA-Z0-9_\s]+?)(?:\s+and|\s+then|$|,|\.|;)'
    nav_matches = re.findall(navigation_pattern, prompt.lower())
    phrases.extend([m.strip() for m in nav_matches])
    
    # Pattern 3: Individual words (might be node names)
    words = re.findall(r'\b[a-zA-Z0-9_]+\b', prompt.lower())
    phrases.extend(words)
    
    # Also try multi-word combinations (2-word phrases)
    words_list = prompt.lower().split()
    for i in range(len(words_list) - 1):
        two_word = f"{words_list[i]} {words_list[i+1]}"
        phrases.append(two_word)
        # Also try with underscore
        two_word_underscore = f"{words_list[i]}_{words_list[i+1]}"
        phrases.append(two_word_underscore)
    
    # Deduplicate while preserving order
    seen = set()
    unique_phrases = []
    for phrase in phrases:
        phrase = phrase.strip()
        if phrase and phrase not in seen and len(phrase) > 1:  # Skip single chars
            seen.add(phrase)
            unique_phrases.append(phrase)
    
    return unique_phrases


# =============================================================================
# PRE-PROCESSING (Before AI Generation)
# =============================================================================

def preprocess_prompt(prompt: str, available_nodes: List[str], 
                     team_id: str, userinterface_name: str) -> Dict:
    """
    Pre-process prompt: apply learned mappings and check for ambiguities.
    
    This runs BEFORE AI plan generation to:
    1. Apply learned mappings automatically
    2. Detect ambiguous phrases that need user input
    3. Auto-correct high-confidence single matches
    
    Args:
        prompt: User's natural language prompt
        available_nodes: List of valid navigation nodes
        team_id: Team ID for database lookup
        userinterface_name: UI context (e.g., "horizon_android_mobile")
    
    Returns:
        {
            'status': 'clear' | 'auto_corrected' | 'needs_disambiguation',
            'corrected_prompt': str (if auto_corrected),
            'corrections': [...] (if auto_corrected),
            'ambiguities': [...] (if needs_disambiguation)
        }
    """
    # Extract potential node phrases from prompt
    phrases = extract_potential_node_phrases(prompt)
    
    # Get learned mappings from database (batch query for efficiency)
    learned = get_learned_mappings_batch(team_id, userinterface_name, phrases)
    
    # Track what we corrected vs what needs user input
    auto_corrections = []
    needs_disambiguation = []
    
    for phrase in phrases:
        # Skip if exact match exists
        if phrase in available_nodes:
            continue
        
        # Check learned mapping (HIGHEST PRIORITY)
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
        
        # Find fuzzy matches
        matches = find_fuzzy_matches(phrase, available_nodes, max_results=3, cutoff=0.4)
        
        if len(matches) == 1:
            # Single high-confidence match → auto-correct
            auto_corrections.append({
                'from': phrase,
                'to': matches[0],
                'source': 'fuzzy'
            })
            print(f"[@ai_prompt_validation:preprocess] Fuzzy auto-correct: '{phrase}' → '{matches[0]}'")
        elif len(matches) > 1:
            # Multiple matches → needs user disambiguation
            needs_disambiguation.append({
                'original': phrase,
                'suggestions': matches
            })
            print(f"[@ai_prompt_validation:preprocess] Ambiguous: '{phrase}' → {matches}")
    
    # Determine status and return appropriate response
    if not auto_corrections and not needs_disambiguation:
        return {'status': 'clear', 'prompt': prompt}
    
    if needs_disambiguation:
        return {
            'status': 'needs_disambiguation',
            'original_prompt': prompt,
            'ambiguities': needs_disambiguation,
            'auto_corrections': auto_corrections  # Show what was auto-corrected
        }
    
    # Auto-corrected only (apply corrections to prompt)
    corrected_prompt = prompt
    for correction in auto_corrections:
        # Use word boundaries to avoid partial replacements
        corrected_prompt = re.sub(
            r'\b' + re.escape(correction['from']) + r'\b',
            correction['to'],
            corrected_prompt,
            flags=re.IGNORECASE
        )
    
    return {
        'status': 'auto_corrected',
        'original_prompt': prompt,
        'corrected_prompt': corrected_prompt,
        'corrections': auto_corrections
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
        
        # Find fuzzy suggestions
        suggestions = find_fuzzy_matches(target, available_nodes, max_results=3, cutoff=0.4)
        
        if len(suggestions) == 1:
            # Single match → auto-fix
            step['params']['target_node'] = suggestions[0]
            if 'description' in step:
                step['description'] = suggestions[0]
            modified = True
            print(f"[@ai_prompt_validation:validate] Auto-fixed (fuzzy): '{target}' → '{suggestions[0]}'")
        else:
            # Multiple or no matches → needs user input
            invalid_nodes.append({
                'original': target,
                'suggestions': suggestions,
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
