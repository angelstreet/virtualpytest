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
    print(f"\n{'='*100}")
    print(f"[@dump_analyzer] 🔍 STARTING ANALYSIS: {len(node_verification_data)} nodes to analyze")
    print(f"{'='*100}")
    
    results = []
    
    # Extract all dumps
    all_dumps = {item['node_id']: item['dump'] for item in node_verification_data}
    
    print(f"\n[@dump_analyzer] 📊 Overview of all nodes:")
    for node_id, dump in all_dumps.items():
        node_label = next(item['node_label'] for item in node_verification_data if item['node_id'] == node_id)
        elements_count = len(dump.get('elements', [])) if isinstance(dump, dict) else 0
        print(f"  • {node_label} ({node_id}): {elements_count} elements")
    
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
        
        # Try text first
        unique_text = _find_unique_text_for_node(node_id, current_dump, all_dumps)
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
        print(f"[@dump_analyzer]    → User will need to manually add verification")
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
    
    print(f"\n{'='*100}")
    print(f"[@dump_analyzer] 📋 SUMMARY:")
    print(f"  • Total nodes analyzed: {len(node_verification_data)}")
    print(f"  • Unique elements found: {len([r for r in results if r['suggested_verification']['found']])}")
    print(f"  • No unique element: {len([r for r in results if not r['suggested_verification']['found']])}")
    print(f"{'='*100}\n")
    
    return results


def _find_unique_text_for_node(target_node_id: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[str]:
    """Find text that appears only in target node"""
    
    print(f"[@dump_analyzer:_find_unique_text_for_node] 🔍 Searching for unique text...")
    
    # Extract text elements from target dump
    target_texts = _extract_texts_from_dump(target_dump)
    
    print(f"[@dump_analyzer:_find_unique_text_for_node]   → Target node has {len(target_texts)} text elements")
    if target_texts:
        print(f"[@dump_analyzer:_find_unique_text_for_node]   → Sample texts: {list(target_texts)[:5]}")
    
    if not target_texts:
        print(f"[@dump_analyzer:_find_unique_text_for_node]   ❌ No text elements found in target dump")
        return None
    
    # Extract texts from all OTHER nodes
    other_texts = set()
    for node_id, dump in all_dumps.items():
        if node_id != target_node_id:
            node_texts = _extract_texts_from_dump(dump)
            other_texts.update(node_texts)
    
    print(f"[@dump_analyzer:_find_unique_text_for_node]   → Other nodes have {len(other_texts)} total text elements")
    
    # Find texts unique to target
    unique_texts = target_texts - other_texts
    
    print(f"[@dump_analyzer:_find_unique_text_for_node]   → Found {len(unique_texts)} unique texts")
    if unique_texts:
        print(f"[@dump_analyzer:_find_unique_text_for_node]   → Unique texts: {list(unique_texts)[:10]}")
    
    if not unique_texts:
        print(f"[@dump_analyzer:_find_unique_text_for_node]   ❌ All texts also appear in other nodes")
        return None
    
    # Pick shortest unique text (usually most specific)
    shortest = min(unique_texts, key=len)
    print(f"[@dump_analyzer:_find_unique_text_for_node]   ✅ Selected shortest: '{shortest}' (length: {len(shortest)})")
    return shortest


def _find_unique_xpath_for_node(target_node_id: str, target_dump: Dict, all_dumps: Dict[str, Dict]) -> Optional[str]:
    """Find xpath that appears only in target node"""
    
    print(f"[@dump_analyzer:_find_unique_xpath_for_node] 🔍 Searching for unique xpath...")
    
    # Extract xpaths from target dump
    target_xpaths = _extract_xpaths_from_dump(target_dump)
    
    print(f"[@dump_analyzer:_find_unique_xpath_for_node]   → Target node has {len(target_xpaths)} xpath elements")
    if target_xpaths:
        print(f"[@dump_analyzer:_find_unique_xpath_for_node]   → Sample xpaths: {list(target_xpaths)[:3]}")
    
    if not target_xpaths:
        print(f"[@dump_analyzer:_find_unique_xpath_for_node]   ❌ No xpath elements found in target dump")
        return None
    
    # Extract xpaths from all OTHER nodes
    other_xpaths = set()
    for node_id, dump in all_dumps.items():
        if node_id != target_node_id:
            node_xpaths = _extract_xpaths_from_dump(dump)
            other_xpaths.update(node_xpaths)
    
    print(f"[@dump_analyzer:_find_unique_xpath_for_node]   → Other nodes have {len(other_xpaths)} total xpath elements")
    
    # Find xpaths unique to target
    unique_xpaths = target_xpaths - other_xpaths
    
    print(f"[@dump_analyzer:_find_unique_xpath_for_node]   → Found {len(unique_xpaths)} unique xpaths")
    if unique_xpaths:
        print(f"[@dump_analyzer:_find_unique_xpath_for_node]   → Sample unique xpaths: {list(unique_xpaths)[:3]}")
    
    if not unique_xpaths:
        print(f"[@dump_analyzer:_find_unique_xpath_for_node]   ❌ All xpaths also appear in other nodes")
        return None
    
    # Pick shortest unique xpath (usually most specific)
    shortest = min(unique_xpaths, key=len)
    print(f"[@dump_analyzer:_find_unique_xpath_for_node]   ✅ Selected shortest: '{shortest[:100]}...' (length: {len(shortest)})")
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

