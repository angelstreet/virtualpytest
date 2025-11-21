"""
Screen Analysis Tools - Unified selector analysis for actions and verifications

Provides LLMs with direct access to the same selector scoring logic used by exploration.
No more guessing - get analyzed selectors ready for create_edge or verify_node.
"""

import json
from typing import Dict, Any, List
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG

# Import unified selector scoring
from shared.src.selector_scoring import (
    find_best_selector,
    get_selector_value,
    PLATFORM_PRIORITY_ORDER,
    SelectorPriority
)


class ScreenAnalysisTools:
    """Screen analysis tools for finding best selectors"""
    
    def __init__(self):
        self.formatter = MCPFormatter()
    
    def analyze_screen_for_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze screen elements to find best selector for clicking/interacting.
        Returns ready-to-use action parameters.
        
        Args:
            params: {
                'elements': list - Elements from dump_ui_elements
                'intent': str - What to click (e.g., "search field", "login button")
                'platform': str - 'mobile' or 'web'
                'team_id': str (optional)
            }
        
        Returns:
            {
                'selector_type': 'id',
                'selector_value': 'search-field',
                'command': 'click_element_by_id',
                'action_params': {'element_id': 'search-field', 'wait_time': 1000},
                'score': 1200,
                'unique': true,
                'confidence': 'high'
            }
        """
        elements = params.get('elements', [])
        intent = params.get('intent', '')
        platform = params.get('platform', 'web')
        
        # Validate
        if not elements:
            return self.formatter.error("No elements provided. Call dump_ui_elements first.")
        
        if platform not in ['mobile', 'web']:
            return self.formatter.error(f"Invalid platform: {platform}. Use 'mobile' or 'web'.")
        
        # Find best selector using unified scoring
        try:
            result = find_best_selector(
                elements=elements,
                platform=platform,
                context_label=intent,
                require_unique=True  # Always require uniqueness
            )
            
            if not result:
                return self.formatter.error(
                    f"No unique selector found for '{intent}'.\n"
                    f"This usually means:\n"
                    f"1. Element doesn't exist on screen\n"
                    f"2. All selectors are ambiguous (multiple matches)\n"
                    f"Try: dump_ui_elements to see what's available"
                )
            
            # Build action command based on platform and selector type
            selector_type = result['selector_type']
            selector_value = result['selector_value']
            
            if selector_type == 'id':
                command = 'click_element_by_id'
                action_params = {
                    'element_id': selector_value,
                    'wait_time': 1000
                }
            elif selector_type == 'xpath':
                command = 'click_element'
                action_params = {
                    'xpath': selector_value,
                    'wait_time': 1000
                }
            else:  # text or content_desc
                command = 'click_element'
                action_params = {
                    'text': selector_value,
                    'wait_time': 1000
                }
            
            # Determine confidence
            score = result['score']
            if score >= 1000:
                confidence = 'high'
            elif score >= 500:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # Format response
            response_text = f"✅ Best selector for '{intent}':\n\n"
            response_text += f"**Selector:** {selector_type} = `{selector_value}`\n"
            response_text += f"**Score:** {score} ({confidence} confidence)\n"
            response_text += f"**Unique:** {'Yes ✓' if result['details'].get('unique') else 'No ✗'}\n\n"
            
            response_text += f"**Ready-to-use action:**\n"
            response_text += f"```json\n"
            response_text += json.dumps({
                'command': command,
                'params': action_params
            }, indent=2)
            response_text += f"\n```\n\n"
            
            # Show priority order used
            response_text += f"**Priority order used:** {' > '.join(PLATFORM_PRIORITY_ORDER[platform])}\n"
            
            return {"content": [{"type": "text", "text": response_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Analysis failed: {str(e)}")
    
    def analyze_screen_for_verification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze screen elements to find best verification for node detection.
        Returns ready-to-use verification parameters.
        
        Args:
            params: {
                'elements': list - Elements from dump_ui_elements
                'node_label': str - Node name (e.g., "home", "login", "search_results")
                'platform': str - 'mobile' or 'web'
                'team_id': str (optional)
            }
        
        Returns:
            {
                'primary_verification': {
                    'command': 'waitForElementToAppear',
                    'params': {'search_term': '#home-tab-selected'},
                    'score': 1500
                },
                'confidence': 'high'
            }
        """
        elements = params.get('elements', [])
        node_label = params.get('node_label', '')
        platform = params.get('platform', 'web')
        
        # Validate
        if not elements:
            return self.formatter.error("No elements provided. Call dump_ui_elements first.")
        
        if not node_label:
            return self.formatter.error("node_label is required (e.g., 'home', 'login')")
        
        if platform not in ['mobile', 'web']:
            return self.formatter.error(f"Invalid platform: {platform}. Use 'mobile' or 'web'.")
        
        # Find best selector
        try:
            result = find_best_selector(
                elements=elements,
                platform=platform,
                context_label=node_label,
                require_unique=True
            )
            
            if not result:
                return self.formatter.error(
                    f"No unique verification found for node '{node_label}'.\n"
                    f"Try: Navigate to the screen first, then dump_ui_elements"
                )
            
            # Build verification command based on platform
            selector_type = result['selector_type']
            selector_value = result['selector_value']
            
            # Verification command name varies by platform
            if platform == 'mobile':
                verification_command = 'waitForElementToAppear'
                param_name = 'search_term'
            else:  # web
                verification_command = 'waitForElementToAppear'
                param_name = 'text'
            
            verification_params = {param_name: selector_value}
            
            # Determine confidence
            score = result['score']
            if score >= 1000:
                confidence = 'high'
            elif score >= 500:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # Format response
            response_text = f"✅ Best verification for node '{node_label}':\n\n"
            response_text += f"**Selector:** {selector_type} = `{selector_value}`\n"
            response_text += f"**Score:** {score} ({confidence} confidence)\n"
            response_text += f"**Unique:** {'Yes ✓' if result['details'].get('unique') else 'No ✗'}\n\n"
            
            response_text += f"**Ready-to-use verification:**\n"
            response_text += f"```json\n"
            response_text += json.dumps({
                'command': verification_command,
                'verification_type': 'adb' if platform == 'mobile' else 'web',
                'params': verification_params
            }, indent=2)
            response_text += f"\n```\n\n"
            
            response_text += f"**Usage in create_node:**\n"
            response_text += f"Add this to node's `data.verifications` array\n\n"
            
            response_text += f"**Priority order used:** {' > '.join(PLATFORM_PRIORITY_ORDER[platform])}\n"
            
            return {"content": [{"type": "text", "text": response_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.error(f"Analysis failed: {str(e)}")

