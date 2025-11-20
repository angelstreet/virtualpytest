"""
Dump Analyzer - Find unique elements across multiple UI dumps
"""

from typing import List, Dict, Optional, Set, Tuple
import json
import re


def _dump_to_string(dump: Dict) -> str:
    """
    Convert dump data to readable string format for frontend display
    
    Args:
        dump: Dump dictionary with 'elements' array
        
    Returns:
        Formatted string representation
    """
    if not dump or not isinstance(dump, dict):
        return "<empty dump>"
    
    elements = dump.get('elements', [])
    
    if not elements:
        return "<no elements found>"
    
    # Build formatted string
    lines = []
    lines.append(f"Total Elements: {len(elements)}\n")
    lines.append("=" * 80)
    
    for i, elem in enumerate(elements, 1):
        lines.append(f"\n[{i}] Element:")
        
        # Handle both object attributes and dict keys
        if hasattr(elem, '__dict__'):
            # Object (AndroidElement, AppiumElement)
            elem_dict = elem.__dict__
        elif isinstance(elem, dict):
            # Dict (Web elements)
            elem_dict = elem
        else:
            lines.append(f"  <unknown format: {type(elem)}>")
            continue
        
        # Display key attributes
        for key in ['text', 'content_desc', 'class', 'resource_id', 'xpath', 'bounds']:
            value = elem_dict.get(key)
            if value:
                lines.append(f"  {key}: {value}")
    
    return "\n".join(lines)


def analyze_unique_elements(node_verification_data: List[Dict]) -> List[Dict]:
    """
    Analyze dumps to find unique element per node
    
    Args:
        node_verification_data: List of {node_id, node_label, dump, screenshot_url}
        
    Returns:
        List of {node_id, node_label, screenshot_url, dump, suggested_verification}
    """
    print(f"\n{'='*100}")
    print(f"[@dump_analyzer] 🔍 STARTING ANALYSIS: {len(node_verification_data)} nodes to analyze")
    print(f"{'='*100}")
    
    results = []
    
    # Extract all dumps
    all_dumps = {item['node_id']: item['dump'] for item in node_verification_data}
    
    for item in node_verification_data:
        node_id = item['node_id']
        node_label = item['node_label']
        screenshot_url = item['screenshot_url']
        current_dump = item['dump']
        
        # Convert dump to string for frontend display
        dump_string = _dump_to_string(current_dump)
        
        print(f"\n{'='*100}")
        print(f"[@dump_analyzer] 🎯 ANALYZING NODE: '{node_label}' ({node_id})")
        print(f"{'='*100}")
        
        # Try text first (using smart scoring)
        unique_text = _find_unique_text_for_node(node_id, node_label, current_dump, all_dumps)
        if unique_text:
            print(f"[@dump_analyzer] ✅ SUCCESS: Found unique text: '{unique_text}'")
            results.append({
                'node_id': node_id,
                'node_label': node_label,
                'screenshot_url': screenshot_url,
                'dump': dump_string,
                'suggested_verification': {
                    'method': 'checkElement',
                    'params': {'text': unique_text},
                    'found': True,
                    'type': 'text'
                }
            })
            continue
        
        print(f"[@dump_analyzer] ⚠️  No unique text found, trying xpath...")
        
        # Fallback to xpath
        unique_xpath = _find_unique_xpath_for_node(node_id, current_dump, all_dumps)
        if unique_xpath:
            print(f"[@dump_analyzer] ✅ SUCCESS: Found unique xpath: '{unique_xpath}'")
            results.append({
                'node_id': node_id,
                'node_label': node_label,
                'screenshot_url': screenshot_url,
                'dump': dump_string,
                'suggested_verification': {
                    'method': 'checkElement',
                    'params': {'xpath': unique_xpath},
                    'found': True,
                    'type': 'xpath'
                }
            })
            continue
        
        # No unique element found
        print(f"[@dump_analyzer] ❌ FAILURE: No unique element found for '{node_label}'")
        print(f"[@dump_analyzer]    → This node has no text or xpath that's unique to it")
        results.append({
            'node_id': node_id,
            'node_label': node_label,
            'screenshot_url': screenshot_url,
            'dump': dump_string,
            'suggested_verification': {
                'method': 'checkElement',
                'params': {},
                'found': False,
                'type': None
            }
        })
    
    return results


def _score_text_candidate(text: str, node_label: str) -> int:
    """
    Score a text candidate for how good it is as a verification point.
    Higher score = better candidate.
    """
    score = 0
    text_lower = text.lower()
    label_lower = node_label.lower()
    
    # 1. EXACT MATCH to Node Label (Highest Priority)
    # If node is "Settings" and text is "Settings", this is the gold standard
    if text_lower == label_lower:
        return 1000
    
    # 2. Partial Match to Node Label
    if label_lower in text_lower:
        score += 100
    
    # 3. Length Heuristics
    length = len(text)
    if length < 3:
        score -= 50  # Too short (e.g., "ok", "en")
    elif 4 <= length <= 25:
        score += 20  # Sweet spot for titles/labels
    elif length > 40:
        score -= 20  # Likely a description/paragraph
        
    # 4. Content Analysis
    
    # Penalize potential dynamic content (digits, time, prices)
    if re.search(r'\d', text): 
        score -= 30  # Contains numbers (risk of dynamic ID/Time)
    if re.search(r'\d{1,2}:\d{2}', text):
        score -= 100 # Looks like time
    if re.search(r'[\$\€\£]', text):
        score -= 100 # Looks like price
        
    # Penalize common low-value words
    bad_words = {'ok', 'cancel', 'back', 'next', 'done', 'yes', 'no', 'on', 'off'}
    if text_lower in bad_words:
        score -= 50
        
    # Boost Title Case (likely a proper UI label)
    if text[0].isupper() and ' ' in text:
        score += 10
        
    return score


def _find_unique_text_for_node(target_node_id: str, target_node_label: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[str]:
    """Find text that appears only in target node, using scoring"""
    
    # Extract text elements from target dump
    target_texts = _extract_texts_from_dump(target_dump)
    
    if not target_texts:
        return None
    
    # Extract texts from all OTHER nodes
    other_texts = set()
    for node_id, dump in all_dumps.items():
        if node_id != target_node_id:
            node_texts = _extract_texts_from_dump(dump)
            other_texts.update(node_texts)
    
    # Find texts unique to target
    unique_texts = target_texts - other_texts
    
    if not unique_texts:
        return None
    
    # Score all candidates
    scored_candidates = []
    print(f"[@dump_analyzer]   📊 Scoring {len(unique_texts)} unique candidates for '{target_node_label}':")
    
    for text in unique_texts:
        score = _score_text_candidate(text, target_node_label)
        scored_candidates.append((score, text))
        if score > 0: # Only log positive/relevant scores to avoid noise
            print(f"      • '{text}' = {score}")
            
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    best_score, best_text = scored_candidates[0]
    
    # If the best candidate has a terrible score (e.g. it's just "12:34"), reject it
    if best_score < -20:
        print(f"[@dump_analyzer]   ❌ All unique texts had low scores (best was '{best_text}' with {best_score}). Ignoring.")
        return None
        
    print(f"[@dump_analyzer]   ✅ Selected best candidate: '{best_text}' (score: {best_score})")
    return best_text


def _find_unique_xpath_for_node(target_node_id: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[str]:
    """Find xpath that appears only in target node"""
    
    # Extract xpaths from target dump
    target_xpaths = _extract_xpaths_from_dump(target_dump)
    
    if not target_xpaths:
        return None
    
    # Extract xpaths from all OTHER nodes
    other_xpaths = set()
    for node_id, dump in all_dumps.items():
        if node_id != target_node_id:
            node_xpaths = _extract_xpaths_from_dump(dump)
            other_xpaths.update(node_xpaths)
    
    # Find xpaths unique to target
    unique_xpaths = target_xpaths - other_xpaths
    
    if not unique_xpaths:
        return None
    
    # Pick shortest unique xpath (usually most specific)
    shortest = min(unique_xpaths, key=len)
    return shortest


def _extract_texts_from_dump(dump: Dict) -> set:
    """Extract all text values from dump (mobile or web)"""
    texts = set()
    
    if not dump or not isinstance(dump, dict):
        return texts
    
    elements = dump.get('elements', [])
    
    for elem in elements:
        # Mobile dump (AndroidElement)
        if hasattr(elem, 'text'):
            text = elem.text
            if text and text.strip() and text != '<no text>':
                texts.add(text.strip())
        
        # Web dump (dict)
        elif isinstance(elem, dict):
            text = elem.get('text', '') or elem.get('content_desc', '')
            if text and text.strip():
                texts.add(text.strip())
    
    return texts


def _extract_xpaths_from_dump(dump: Dict) -> set:
    """Extract all xpath values from dump (mobile or web)"""
    xpaths = set()
    
    if not dump or not isinstance(dump, dict):
        return xpaths
    
    elements = dump.get('elements', [])
    
    for elem in elements:
        # Mobile dump (AndroidElement)
        if hasattr(elem, 'xpath'):
            xpath = elem.xpath
            if xpath and xpath.strip():
                xpaths.add(xpath.strip())
        
        # Web dump (dict)
        elif isinstance(elem, dict):
            xpath = elem.get('xpath', '') or elem.get('selector', '')
            if xpath and xpath.strip():
                xpaths.add(xpath.strip())
    
    return xpaths
