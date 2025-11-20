"""
Dump Analyzer - Find unique elements across multiple UI dumps
"""

from typing import List, Dict, Optional
import json


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
    print(f"\n[@dump_analyzer] Analyzing {len(node_verification_data)} dumps for unique elements")
    
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
        
        print(f"\n  Analyzing node: {node_label}")
        
        # Try text first
        unique_text = _find_unique_text_for_node(node_id, current_dump, all_dumps)
        if unique_text:
            print(f"    ✅ Found unique text: '{unique_text}'")
            results.append({
                'node_id': node_id,
                'node_label': node_label,
                'screenshot_url': screenshot_url,
                'dump': dump_string,  # ✅ Include formatted dump string for frontend display
                'suggested_verification': {
                    'method': 'checkElement',
                    'params': {'text': unique_text},
                    'found': True,
                    'type': 'text'
                }
            })
            continue
        
        # Fallback to xpath
        unique_xpath = _find_unique_xpath_for_node(node_id, current_dump, all_dumps)
        if unique_xpath:
            print(f"    ✅ Found unique xpath: '{unique_xpath}'")
            results.append({
                'node_id': node_id,
                'node_label': node_label,
                'screenshot_url': screenshot_url,
                'dump': dump_string,  # ✅ Include formatted dump string for frontend display
                'suggested_verification': {
                    'method': 'checkElement',
                    'params': {'xpath': unique_xpath},
                    'found': True,
                    'type': 'xpath'
                }
            })
            continue
        
        # No unique element found
        print(f"    ❌ No unique element found")
        results.append({
            'node_id': node_id,
            'node_label': node_label,
            'screenshot_url': screenshot_url,
            'dump': dump_string,  # ✅ Include formatted dump string for frontend display
            'suggested_verification': {
                'method': 'checkElement',
                'params': {},
                'found': False,
                'type': None
            }
        })
    
    return results


def _find_unique_text_for_node(target_node_id: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[str]:
    """Find text that appears only in target node"""
    
    # Extract text elements from target dump
    target_texts = _extract_texts_from_dump(target_dump)
    
    if not target_texts:
        return None
    
    # Extract texts from all OTHER nodes
    other_texts = set()
    for node_id, dump in all_dumps.items():
        if node_id != target_node_id:
            other_texts.update(_extract_texts_from_dump(dump))
    
    # Find texts unique to target
    unique_texts = target_texts - other_texts
    
    if not unique_texts:
        return None
    
    # Pick shortest unique text (usually most specific)
    return min(unique_texts, key=len)


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
            other_xpaths.update(_extract_xpaths_from_dump(dump))
    
    # Find xpaths unique to target
    unique_xpaths = target_xpaths - other_xpaths
    
    if not unique_xpaths:
        return None
    
    # Pick shortest unique xpath (usually most specific)
    return min(unique_xpaths, key=len)


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

