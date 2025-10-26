"""
AI Prompt Preprocessing

Pre-processes prompts before AI generation:
- Apply learned mappings from database
- Detect ambiguous phrases
- Auto-correct high-confidence matches
- Extract exact node matches

Adapted from old shared/src/lib/executors/ai_prompt_validation.py
Now lives in backend_host/src/services/ai/ (host-specific, not shared)
"""

import re
from difflib import get_close_matches
from typing import Dict, List, Optional

from shared.src.lib.database.ai_prompt_disambiguation_db import (
    get_learned_mapping,
    get_learned_mappings_batch,
    save_disambiguation
)


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


def preprocess_prompt(prompt: str, available_nodes: List[str], 
                     team_id: str, userinterface_name: str) -> Dict:
    """
    Pre-process prompt: apply learned mappings and check for ambiguities.
    
    This runs BEFORE AI generation to:
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
                print(f"[@ai_preprocessing] ✅ Learned mapping: '{phrase}' → '{learned_node}'")
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
            print(f"[@ai_preprocessing] ✅ Fuzzy auto-correct: '{phrase}' → '{matches[0]}'")
        elif len(matches) > 1:
            # Multiple matches → needs user disambiguation
            needs_disambiguation.append({
                'original': phrase,
                'suggestions': matches
            })
            print(f"[@ai_preprocessing] ⚠️  Ambiguous: '{phrase}' → {matches}")
    
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


def check_exact_match(prompt: str, available_nodes: List[str]) -> Optional[str]:
    """
    Check if prompt is a simple exact node match (skip AI entirely).
    
    Examples that should match:
    - "home" → node "home"
    - "navigate to live" → node "live"
    - "go to settings" → node "settings"
    
    Args:
        prompt: User prompt
        available_nodes: List of available nodes
        
    Returns:
        Node name if exact match found, None otherwise
    """
    prompt_lower = prompt.lower().strip()
    
    # Direct match
    if prompt_lower in [n.lower() for n in available_nodes]:
        for node in available_nodes:
            if node.lower() == prompt_lower:
                print(f"[@ai_preprocessing] 🎯 Exact match (direct): '{prompt}' → '{node}'")
                return node
    
    # Extract after navigation keywords
    patterns = [
        r'(?:navigate to|go to|open)\s+([a-zA-Z0-9_\s]+)$',
        r'to\s+([a-zA-Z0-9_\s]+)$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            extracted = match.group(1).strip()
            if extracted in [n.lower() for n in available_nodes]:
                for node in available_nodes:
                    if node.lower() == extracted:
                        print(f"[@ai_preprocessing] 🎯 Exact match (extracted): '{prompt}' → '{node}'")
                        return node
    
    return None

