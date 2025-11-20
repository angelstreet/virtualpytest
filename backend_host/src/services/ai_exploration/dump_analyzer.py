"""
Dump Analyzer - Find unique elements across multiple UI dumps
"""

from typing import List, Dict, Optional, Set, Tuple
import json
import re


def _get_verification_command(device_model: str) -> str:
    """
    Get the correct verification command based on device model.
    
    Returns:
        - 'waitForElementToAppear' for ADB/Appium (android_mobile, android_tv)
        - 'waitForElementToAppear' for Web (horizon_web, etc.)
        - 'waitForImageToAppear' for image-based (default fallback)
    """
    if not device_model:
        return 'waitForImageToAppear'
    
    model_lower = device_model.lower()
    
    # ADB/Appium: android_mobile, android_tv
    if 'android' in model_lower or 'mobile' in model_lower or 'appium' in model_lower:
        return 'waitForElementToAppear'
    
    # Web: horizon_web, playwright, etc.
    if 'web' in model_lower or 'playwright' in model_lower:
        return 'waitForElementToAppear'
    
    # Default: Image verification
    return 'waitForImageToAppear'


# ============================================================================
# WEAK WORDS: Can be used as secondary verification only (not strong enough alone)
# ============================================================================
WEAK_VERIFICATION_WORDS = {
    # Navigation/Actions (too common alone, but OK as secondary)
    'back', 'next', 'previous', 'prev', 'forward', 'close', 'exit',
    'cancel', 'ok', 'confirm', 'yes', 'no', 'done', 'finish',
    
    # Search/Filter (appear everywhere)
    'search', 'filter', 'sort', 'order', 'show all', 'view all',
    
    # Media controls
    'play', 'pause', 'stop', 'watch', 'listen',
    
    # Generic content words
    'more', 'less', 'info', 'details', 'description',
    'title', 'name', 'delete', 'remove', 'add', 'edit',
    
    # Time/Date (dynamic but can be used as secondary)
    'today', 'yesterday', 'tomorrow', 'now',
    
    # Generic UI elements
    'menu', 'options', 'settings',  # Settings as standalone word
    'button', 'tab', 'icon', 'image',
    
    # Content-specific weak words
    'popular', 'trending', 'new', 'featured', 'recommended',
    'movies', 'shows', 'series', 'videos', 'channels'
}


def _is_weak_word(text: str) -> bool:
    """
    Check if text is a weak verification candidate.
    Weak = Can be used as secondary/complementary verification only.
    Returns True if the text should not be used as primary verification.
    """
    text_lower = text.lower().strip()
    
    # Check if text is ONLY a weak word (single word)
    words = text_lower.split()
    if len(words) == 1 and words[0] in WEAK_VERIFICATION_WORDS:
        return True
    
    # Also check if it's a simple 2-word phrase with weak words
    # e.g., "Popular Movies" = weak + weak
    if len(words) == 2 and all(w in WEAK_VERIFICATION_WORDS for w in words):
        return True
    
    return False


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


def analyze_unique_elements(node_verification_data: List[Dict], device_model: str = None) -> List[Dict]:
    """
    Analyze dumps to find unique element per node
    
    Args:
        node_verification_data: List of {node_id, node_label, dump, screenshot_url}
        device_model: Device model name to determine verification command (e.g., 'android_mobile', 'horizon_web')
    
    Returns:
        List of {node_id, node_label, screenshot_url, dump, suggested_verification}
    """
    print(f"\n{'='*100}")
    print(f"[@dump_analyzer] 🔍 STARTING ANALYSIS: {len(node_verification_data)} nodes to analyze")
    print(f"[@dump_analyzer] 🎮 Device model: {device_model}")
    print(f"{'='*100}")
    
    # Determine verification command based on device type
    verification_command = _get_verification_command(device_model)
    print(f"[@dump_analyzer] ✅ Using verification command: {verification_command}")
    
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
        
        # Try text first (using smart scoring with primary/secondary support)
        unique_text_result = _find_unique_text_for_node(node_id, node_label, current_dump, all_dumps)
        if unique_text_result:
            primary = unique_text_result['primary']
            secondary = unique_text_result.get('secondary')
            
            if secondary:
                print(f"[@dump_analyzer] ✅ SUCCESS: Primary='{primary}', Secondary='{secondary}'")
            else:
                print(f"[@dump_analyzer] ✅ SUCCESS: Primary='{primary}' (no secondary needed)")
            
            # Store verifications
            verifications = []
            verifications.append({'text': primary})
            if secondary:
                verifications.append({'text': secondary})
            
            results.append({
                'node_id': node_id,
                'node_label': node_label,
                'screenshot_url': screenshot_url,
                'dump': dump_string,
                'suggested_verification': {
                    'method': verification_command,
                    'params': verifications[0],  # Frontend expects single params for now
                    'params_all': verifications,  # Store all for future use
                    'found': True,
                    'type': 'text',
                    'has_secondary': len(verifications) > 1
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
                    'method': verification_command,
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
                'method': verification_command,
                'params': {},
                'found': False,
                'type': None
            }
        })
    
    return results


def _score_text_candidate(text: str, node_label: str) -> Tuple[int, bool]:
    """
    Score a text candidate for how good it is as a verification point.
    
    Returns:
        (score, is_weak): 
            - score: Higher = better candidate
            - is_weak: True if this should only be used as secondary verification
    """
    score = 0
    text_lower = text.lower()
    label_lower = node_label.lower()
    
    # 0. CHECK IF WEAK (can only be secondary verification)
    is_weak = _is_weak_word(text)
    
    # 1. EXACT MATCH to Node Label (Highest Priority)
    # If node is "Settings" and text is "Settings", this is the gold standard
    if text_lower == label_lower:
        return (1000, False)  # Always strong if exact match
    
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
    
    # Boost "Selected/Active" state (Strongest indicator of current screen)
    if 'selected' in text_lower or 'focused' in text_lower or 'current' in text_lower:
        score += 500

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
        
    return (score, is_weak)


def _find_unique_text_for_node(target_node_id: str, target_node_label: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[Dict]:
    """
    Find text that appears only in target node, using scoring.
    
    Returns:
        Dict with 'primary' and optionally 'secondary' verification, or None
        {
            'primary': 'Home Tab currently selected',
            'secondary': 'Popular Movies'  # Optional
        }
    """
    
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
    
    # Score all candidates and separate strong vs weak
    strong_candidates = []  # Can be used as primary
    weak_candidates = []    # Can only be used as secondary
    
    print(f"[@dump_analyzer]   📊 Scoring {len(unique_texts)} unique candidates for '{target_node_label}':")
    
    for text in unique_texts:
        score, is_weak = _score_text_candidate(text, target_node_label)
        
        if is_weak:
            weak_candidates.append((score, text))
            if score > 0:  # Only log relevant weak candidates
                print(f"      • '{text}' = {score} (weak)")
        else:
            strong_candidates.append((score, text))
            if score > 0:  # Only log positive/relevant scores
                print(f"      • '{text}' = {score}")
    
    # Sort both lists by score
    strong_candidates.sort(key=lambda x: x[0], reverse=True)
    weak_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Strategy: Use best strong candidate as primary, best weak as secondary (if available)
    primary_verification = None
    secondary_verification = None
    
    if strong_candidates and strong_candidates[0][0] > -20:
        # We have a good strong candidate
        primary_verification = strong_candidates[0][1]
        print(f"[@dump_analyzer]   ✅ Primary: '{primary_verification}' (score: {strong_candidates[0][0]})")
        
        # Try to add a secondary (another strong OR a weak)
        if len(strong_candidates) > 1 and strong_candidates[1][0] > 0:
            secondary_verification = strong_candidates[1][1]
            print(f"[@dump_analyzer]   ➕ Secondary: '{secondary_verification}' (score: {strong_candidates[1][0]})")
        elif weak_candidates and weak_candidates[0][0] > 0:
            secondary_verification = weak_candidates[0][1]
            print(f"[@dump_analyzer]   ➕ Secondary: '{secondary_verification}' (score: {weak_candidates[0][0]}, weak)")
    
    elif weak_candidates and weak_candidates[0][0] > -20:
        # No strong candidates, but we have a decent weak one
        # In this case, we MUST have a secondary to make it reliable
        if len(weak_candidates) >= 2 and weak_candidates[1][0] > 0:
            primary_verification = weak_candidates[0][1]
            secondary_verification = weak_candidates[1][1]
            print(f"[@dump_analyzer]   ⚠️  Only weak candidates available:")
            print(f"[@dump_analyzer]      Primary (weak): '{primary_verification}' (score: {weak_candidates[0][0]})")
            print(f"[@dump_analyzer]      Secondary (weak): '{secondary_verification}' (score: {weak_candidates[1][0]})")
        else:
            print(f"[@dump_analyzer]   ❌ Only one weak candidate, not reliable enough without secondary")
            return None
    else:
        print(f"[@dump_analyzer]   ❌ All candidates had low scores")
        return None
    
    # Return result
    if primary_verification:
        result = {'primary': primary_verification}
        if secondary_verification:
            result['secondary'] = secondary_verification
        return result
    
    return None


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
        if hasattr(elem, 'text') or hasattr(elem, 'content_desc'):
            text = getattr(elem, 'text', '')
            content_desc = getattr(elem, 'content_desc', '')
            
            # Clean up placeholder values often found in Android dumps
            if str(text) == '<no text>': text = ''
            if str(content_desc) == '<no content-desc>': content_desc = ''
            
            # Use text if available, otherwise content_desc
            # This allows us to find "en" which is often in content_desc only
            val = str(text).strip() or str(content_desc).strip()
            
            if val:
                texts.add(val)
        
        # Web dump (dict)
        elif isinstance(elem, dict):
            text = elem.get('text', '') or elem.get('content_desc', '')
            if text and str(text).strip():
                texts.add(str(text).strip())
    
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
