"""
Screen Analyzer - AI vision analysis using VideoAIHelpers
Analyzes screenshots to understand menu structure and detect screen changes
"""

from typing import Dict, Optional
import json


class ScreenAnalyzer:
    """AI vision analysis using existing VideoAIHelpers"""
    
    def __init__(self, device, controller=None, ai_model: str = 'qwen'):
        """
        Initialize with device context
        
        Args:
            device: Device instance (from ExplorationEngine)
            controller: Remote controller instance (for android_mobile native screenshots)
            ai_model: 'qwen' (default), later: user-selectable
        """
        self.device = device
        self.device_id = device.device_id
        self.host_name = device.host_name
        self.device_model_name = device.device_model
        self.controller = controller
        self.ai_model = ai_model
        
    def anticipate_tree(self, screenshot_path: str = None) -> Dict:
        """
        Phase 1: Analyze first screenshot and identify all interactive elements
        
        For mobile/web: Use UI dump to extract interactive elements (screenshot optional)
        For TV/STB: Use AI vision to identify menu items (screenshot required)
        
        Args:
            screenshot_path: Path to screenshot image (optional for mobile/web)
            
        Returns:
            {
                'menu_type': 'horizontal',
                'items': ['home', 'settings', 'profile'],
                'lines': [['home', 'settings'], ['profile']],
                'predicted_depth': 2,
                'strategy': 'click_elements' or 'test_dpad_directions'
            }
        """
        # Determine if device uses click (mobile/web) or DPAD (TV/STB)
        # ✅ FIX: Include 'host' in detection (host = web browser)
        is_mobile_or_web = self.device_model_name and (
            'mobile' in self.device_model_name.lower() or 
            'web' in self.device_model_name.lower() or 
            'host' in self.device_model_name.lower()
        )
        
        print(f"\n{'='*80}")
        print(f"[@screen_analyzer:anticipate_tree] PHASE 1 ANALYSIS")
        print(f"{'='*80}")
        print(f"📸 Screenshot Path: {screenshot_path or 'None (not required for dump-based analysis)'}")
        print(f"🎮 Device Type: {'MOBILE/WEB (dump-based)' if is_mobile_or_web else 'TV/STB (AI vision-based)'}")
        print(f"📱 Device Model: {self.device_model_name}")
        
        if is_mobile_or_web:
            # Use UI dump for mobile/web (screenshot not needed)
            try:
                return self._analyze_from_dump(screenshot_path)
            except Exception as e:
                print(f"❌ [@screen_analyzer:anticipate_tree] DUMP ANALYSIS FAILED")
                print(f"   Device: {self.device_model_name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
                # ❌ DO NOT SILENTLY FALL BACK - re-raise the error
                raise Exception(f"UI dump analysis failed for {self.device_model_name}: {e}")
        else:
            # Use AI vision for TV/STB (screenshot required)
            if not screenshot_path:
                # Fallback for TV/STB without screenshot
                print(f"  ⚠️ No screenshot available for TV/STB device - using basic fallback")
                return {
                    'menu_type': 'horizontal',
                    'items': ['search', 'home', 'settings', 'profile'],  # Generic fallback
                    'lines': [['search', 'home', 'settings', 'profile']],
                    'predicted_depth': 1,
                    'strategy': 'test_dpad_directions',
                    'item_selectors': {}
                }
            try:
                return self._analyze_from_ai_vision(screenshot_path)
            except Exception as e:
                print(f"❌ [@screen_analyzer:anticipate_tree] AI VISION ANALYSIS FAILED")
                print(f"   Device: {self.device_model_name}")
                print(f"   Screenshot: {screenshot_path}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
                raise Exception(f"AI vision analysis failed for {self.device_model_name}: {e}")
    
    def _analyze_from_dump(self, screenshot_path: str) -> Dict:
        """
        Extract interactive elements from UI dump (mobile/web only)
        Fails fast if dump is not available - no fallback
        """
        print(f"\n📱 USING UI DUMP ANALYSIS")
        print(f"{'-'*80}")
        
        # Both mobile and web now use unified dump_elements()
        print(f"[@screen_analyzer] Using unified dump_elements() method")
        print(f"[@screen_analyzer] Device model: {self.device_model_name}")
        print(f"[@screen_analyzer] Controller type: {type(self.controller).__name__}")
        
        # Try calling dump_elements - signature varies by controller type
        # ✅ Handle both sync (mobile) and async (web) controllers
        try:
            result = self.controller.dump_elements()
            print(f"[@screen_analyzer] dump_elements() returned type: {type(result)}")
            
            # ✅ Check if result is a coroutine (async method)
            import inspect
            if inspect.iscoroutine(result):
                print(f"[@screen_analyzer] Detected async method - using existing event loop")
                import asyncio
                try:
                    # Try to get the running loop (Playwright's controller loop)
                    loop = asyncio.get_running_loop()
                    print(f"[@screen_analyzer] Using running loop: {loop}")
                    # We're already in an async context - this shouldn't happen
                    # But if it does, we need to schedule it differently
                    raise RuntimeError("Cannot use asyncio.run() from within async context")
                except RuntimeError:
                    # Not in async context OR need to use existing loop
                    # Get the controller's loop and submit the coroutine
                    if hasattr(self.controller, '_submit_to_controller_loop'):
                        print(f"[@screen_analyzer] Submitting to controller loop")
                        future = self.controller._submit_to_controller_loop(result)
                        result = future.result()  # Block until complete
                        print(f"[@screen_analyzer] Controller loop result type: {type(result)}")
                    else:
                        # Fallback to asyncio.run (may cause issues but better than crashing)
                        print(f"[@screen_analyzer] Fallback to asyncio.run()")
                        result = asyncio.run(result)
                        print(f"[@screen_analyzer] Async result type: {type(result)}")
            
        except Exception as e:
            print(f"❌ [@screen_analyzer:_analyze_from_dump] dump_elements() FAILED")
            print(f"   Controller: {type(self.controller).__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"dump_elements() call failed: {e}")
        
        # Handle different return types
        if isinstance(result, dict):
            # Web returns dict: {success: bool, elements: list, ...}
            print(f"[@screen_analyzer] Web format detected - keys: {result.keys()}")
            
            if not result.get('success'):
                error = result.get('error', 'Unknown error')
                print(f"❌ [@screen_analyzer:_analyze_from_dump] UI dump indicated failure")
                print(f"   Success: {result.get('success')}")
                print(f"   Error: {error}")
                print(f"   Full result: {result}")
                raise Exception(f"Failed to get UI dump - cannot proceed: {error}")
            
            elements = result.get('elements', [])
            print(f"[@screen_analyzer] Elements retrieved: {len(elements)}")
            
            # Debug: Log full raw dump for exploration debugging
            print(f"\n{'='*80}")
            print(f"[@screen_analyzer:DEBUG] FULL RAW DUMP ({len(elements)} elements)")
            print(f"{'='*80}")
            for i, elem in enumerate(elements, 1):
                print(f"\n[Element {i}/{len(elements)}]")
                print(f"  tagName: {elem.get('tagName')}")
                print(f"  id: {elem.get('id')}")
                print(f"  selector: {elem.get('selector')}")
                print(f"  textContent: {elem.get('textContent', '')[:100]}")  # First 100 chars
                print(f"  className: {elem.get('className', '')[:50]}")  # First 50 chars
                print(f"  attributes: {elem.get('attributes', {})}")
                print(f"  position: {elem.get('position')}")
                print(f"  isVisible: {elem.get('isVisible')}")
            print(f"{'='*80}\n")
            
            if not elements:
                print(f"❌ [@screen_analyzer:_analyze_from_dump] No elements in dump")
                print(f"   Result: {result}")
                raise Exception("No elements found in UI dump")
            
            # Parse web elements (dict format)
            print(f"[@screen_analyzer] Parsing web elements...")
            interactive_elements = self._extract_interactive_elements_web(elements)
        else:
            # Mobile returns tuple: (success, elements, error)
            print(f"[@screen_analyzer] Mobile format detected - tuple with {len(result)} items")
            success, elements, error = result
            print(f"[@screen_analyzer] Success: {success}, Elements: {len(elements) if elements else 0}, Error: {error}")
            
            if not success:
                print(f"❌ [@screen_analyzer:_analyze_from_dump] Mobile dump failed")
                print(f"   Success: {success}")
                print(f"   Error: {error}")
                print(f"   Elements: {elements}")
                raise Exception(f"Failed to get UI dump - cannot proceed: {error}")
            
            # Parse mobile elements (AndroidElement objects)
            print(f"[@screen_analyzer] Parsing mobile elements...")
            interactive_elements = self._extract_interactive_elements_mobile(elements)
        
        if not interactive_elements:
            print(f"⚠️  [@screen_analyzer:_analyze_from_dump] No interactive elements after parsing")
            print(f"   Raw element count: {len(elements)}")
            print(f"   This may indicate:")
            print(f"   - Flutter app without activated semantics")
            print(f"   - Page still loading")
            print(f"   - Dynamic content not yet rendered")
            
            # Return empty result instead of raising exception
            # Let the caller (exploration engine) handle this gracefully
            return {
                'menu_type': 'click_based',
                'items': [],
                'lines': [],
                'predicted_depth': 0,
                'strategy': 'click_elements',
                'error': 'No interactive elements found in UI dump',
                'suggestion': 'Check if page is fully loaded or if Flutter semantics need manual activation'
            }
        
        print(f"✅ EXTRACTED FROM DUMP:")
        print(f"{'-'*80}")
        print(f"Items ({len(interactive_elements)}):")
        print(f"Elements: {', '.join(interactive_elements)}")
        print(f"{'-'*80}\n")
        
        return {
            'menu_type': 'click_based',  # Mobile/web = click-based, no line structure
            'items': interactive_elements,
            'lines': [],  # No lines for click-based navigation
            'predicted_depth': 2,
            'strategy': 'click_elements'
        }
    
    def _extract_interactive_elements_mobile(self, elements: list) -> list:
        """
        Parse mobile UI dump elements (AndroidElement objects)
        Extract both static navigation + dynamic content
        
        Args:
            elements: List of AndroidElement objects from dump_elements()
        
        Returns:
            List of element names (strings)
        """
        interactive_elements = []
        
        # Filter out common non-interactive text
        ignore_keywords = ['image', 'icon', 'loading', 'placeholder', '...', 'content', 'decoration', 'logo', 'home', 'accueil']
        
        # UI accessibility hints to strip (before dynamic content detection)
        # ONLY strip instructions/state, NOT element types (Tab, Button, etc.)
        accessibility_patterns = [
            ', Double-tap to Open',
            ', Double-tap to activate',
            ', Double-tap to select',
            ' currently selected',
        ]
        
        # Dynamic content indicators (program titles, prices, descriptions)
        dynamic_indicators = [
            'available for replay', 'watch now', 'continue watching',
            'chf', 'usd', 'eur', 'gbp', '$', '€', '£',  # Price indicators
            ' - ',  # Time ranges like "21:10 - 23:10"
            ' from ', ' to ',  # Alternate time/price ranges
            'season ', 'episode ', 's0', 'e0',  # TV series
            'podcast ',  # Podcast titles
            ','  # Titles often have commas (e.g., "Show Name, Description")
        ]
        
        # Navigation keywords that should NOT be filtered (even if they match above)
        # These are common navigation tab names that we MUST keep
        navigation_whitelist = ['replay', 'radio', 'guide', 'tv', 'home', 'search', 'settings', 'accueil']
        
        # UI element type keywords (multilingual) - elements containing these get more lenient filtering
        # These indicate proper UI elements, not dynamic content
        ui_element_keywords = [
            'button', 'btn', 'bouton',  # Button (EN, abbrev, FR)
            'tab', 'onglet',  # Tab (EN, FR)
            'selected', 'sélectionné', 'seleccionado',  # Selected (EN, FR, ES)
            'menu', 'menü',  # Menu (EN, DE)
            'switch', 'toggle',  # Toggle switches
            'checkbox', 'radio',  # Form controls
        ]
        
        for elem in elements:
            # ✅ FIX: Don't require clickable=true
            # TextViews in navigation bars (bottom tabs, top tabs) are NOT marked clickable
            # but they ARE navigation elements. We'll filter by content instead.
            # Only skip if it's a container or decoration (checked via keywords)
            
            # Get the best label for this element
            label = None
            
            # Priority 1: text
            if elem.text and elem.text != '<no text>' and elem.text.strip():
                label = elem.text.strip()
            # Priority 2: content_desc
            elif elem.content_desc and elem.content_desc != '<no content-desc>' and elem.content_desc.strip():
                label = elem.content_desc.strip()
            # Priority 3: resource_id (extract last part after /)
            elif elem.resource_id and elem.resource_id != '<no resource-id>' and elem.resource_id.strip():
                # Extract meaningful part from resource ID like "com.example:id/button_name"
                resource_id = elem.resource_id.strip()
                if '/' in resource_id:
                    label = resource_id.split('/')[-1]
                else:
                    label = resource_id
            
            # Skip if no useful label
            if not label:
                continue
            
            # Filter out simple single digits (1, 2, 3, etc.)
            if label.isdigit() and len(label) <= 2:
                continue
            
            # Filter out non-interactive keywords
            if any(keyword in label.lower() for keyword in ignore_keywords):
                continue
            
            # ✅ CLEAN: Strip accessibility hints BEFORE dynamic content detection
            original_label = label
            for pattern in accessibility_patterns:
                if pattern.lower() in label.lower():
                    # Case-insensitive removal
                    import re
                    label = re.sub(re.escape(pattern), '', label, flags=re.IGNORECASE).strip()
            
            # Clean up extra commas/spaces after stripping
            label = label.rstrip(',').strip()
            
            # Skip if label became empty after cleaning
            if not label:
                continue
            
            # ✅ Detect and SKIP dynamic content (AFTER cleaning accessibility text)
            # 1. Very long labels (> 30 chars) = likely program description
            # 2. Contains time patterns or content indicators
            # BUT: Don't skip common navigation keywords even if they match
            
            # Check if it's a navigation keyword (whitelist)
            is_navigation = any(nav.lower() == label.lower() for nav in navigation_whitelist)
            
            # Check if label contains UI element type keywords (more lenient filtering)
            contains_ui_keyword = any(keyword in label.lower() for keyword in ui_element_keywords)
            
            # Determine length threshold based on whether it's a UI element
            if contains_ui_keyword:
                length_threshold = 40  # More lenient for UI elements with metadata
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🏷️  UI element detected: '{label}' | using threshold={length_threshold}")
            else:
                length_threshold = 30  # Standard threshold for other elements
            
            if not is_navigation:
                # Not a whitelisted navigation keyword, apply dynamic content filter
                if len(label) > length_threshold or any(indicator in label.lower() for indicator in dynamic_indicators):
                    print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🚫 FILTERED: Dynamic content | label='{label}' | len={len(label)} | threshold={length_threshold} | elem.id={elem.id}")
                    continue  # Skip dynamic content
            
            # Add to list (avoid duplicates)
            if label not in interactive_elements:
                interactive_elements.append(label)
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] ✅ KEPT: '{label}' | elem.id={elem.id} | clickable={elem.clickable}")
            else:
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🔁 DUPLICATE: '{label}' | elem.id={elem.id}")
        
        return interactive_elements[:20]  # Limit to top 20 elements
    
    def _extract_interactive_elements_web(self, elements: list) -> list:
        """
        Parse web UI dump elements (dict objects from Playwright)
        Extract NAVIGATION targets only - filter out layout, external links, and grouped components
        
        Args:
            elements: List of dict objects from dump_elements()
                     Each dict has: text, tag, selector, visible, clickable, etc.
        
        Returns:
            List of element names (strings) - navigation targets only
        """
        interactive_elements = []
        seen_selectors = set()  # Track duplicates
        
        # ═══════════════════════════════════════════════════════════════
        # FILTER PATTERNS
        # ═══════════════════════════════════════════════════════════════
        
        # Layout containers (structural, not clickable destinations)
        layout_keywords = [
            'container', 'wrapper', 'columns', 'row', 'grid', 'sidebar',
            'header', 'footer', 'upper', 'lower', 'table-cell', 'layout',
            'section', 'main', 'content', 'aside', 'nav'  # nav is container, not link
        ]
        
        # Non-interactive decorations
        decoration_keywords = [
            'image', 'icon', 'loading', 'placeholder', 'decoration', 
            'logo', 'banner', 'badge', 'divider', 'spacer', 'tagline',
            'slogan', 'motto', 'caption'
        ]
        
        # External/social links (navigate AWAY from app)
        external_keywords = [
            'social', 'facebook', 'twitter', 'instagram', 'youtube',
            'linkedin', 'pinterest', 'tiktok', 'share', 'external',
            'rss', 'feed', 'subscribe', 'newsletter'
        ]
        
        # Search components (should be grouped as one)
        search_group = {
            'ids': set(),
            'found': False,
            'label': 'search'
        }
        
        # Cart components (should be grouped as one)
        cart_group = {
            'ids': set(),
            'found': False,
            'label': 'cart'
        }
        
        # ═══════════════════════════════════════════════════════════════
        # PASS 1: Identify groups and collect elements
        # ═══════════════════════════════════════════════════════════════
        
        for elem in elements:
            selector = elem.get('selector', '') or elem.get('id', '')
            if not selector:
                continue
            
            selector_lower = selector.lower()
            
            # Group search components
            if any(word in selector_lower for word in ['search', 'product-search']):
                search_group['ids'].add(selector)
                search_group['found'] = True
                continue
            
            # Group cart components
            if any(word in selector_lower for word in ['cart', 'minicart']):
                cart_group['ids'].add(selector)
                cart_group['found'] = True
                continue
        
        # ═══════════════════════════════════════════════════════════════
        # PASS 2: Extract navigation targets with filtering
        # ═══════════════════════════════════════════════════════════════
        
        for elem in elements:
            selector = elem.get('selector', '') or elem.get('id', '')
            if not selector:
                continue
            
            # Skip if already processed in a group
            if selector in search_group['ids'] or selector in cart_group['ids']:
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # SMART DUPLICATE CHECK
            # ═══════════════════════════════════════════════════════════════
            # Generic selectors (a, div, button) are not unique.
            # Use text+href as the uniqueness key for generic selectors.
            # For specific selectors (#id, .class), the selector itself is unique enough.
            
            text_content = elem.get('textContent', '').strip()
            attributes = elem.get('attributes', {})
            href = attributes.get('href', '')
            
            # Generic selectors (single tag name without #id or .class)
            is_generic = not ('#' in selector or '.' in selector or ':' in selector)
            
            if is_generic:
                # Use text+href as uniqueness key for generic selectors
                unique_key = f"{selector}|{text_content}|{href}"
            else:
                # Use selector for specific ones
                unique_key = selector
            
            # Skip duplicates
            if unique_key in seen_selectors:
                continue
            
            seen_selectors.add(unique_key)
            
            # ═══════════════════════════════════════════════════════════════
            # PRIORITY FILTER: Navigation elements need (ID OR text) AND href
            # ═══════════════════════════════════════════════════════════════
            
            tag = elem.get('tagName', '').lower()
            element_id = elem.get('id', '') or ''  # Handle None
            
            # Detect Flutter semantic elements
            is_flutter = tag == 'flt-semantics' or (element_id and element_id.startswith('flt-semantic-node'))
            
            # For Flutter elements, REQUIRE text (IDs are dynamic and unstable)
            if is_flutter:
                if not text_content or len(text_content) < 2:
                    print(f"[@screen_analyzer:_extract_web] Filtered FLUTTER NO TEXT: {selector}")
                    continue
                # Check for tappable attribute
                is_tappable = 'flt-tappable' in str(attributes) or elem.get('flt-tappable') is not None
                if not is_tappable:
                    print(f"[@screen_analyzer:_extract_web] Filtered FLUTTER NOT TAPPABLE: {text_content[:30]}")
                    continue
                
                # CRITICAL: Replace unstable ID selector with text-based selector
                # Flutter IDs change on refresh (flt-semantic-node-6 → flt-semantic-node-7)
                selector = text_content  # Use text as selector
                print(f"[@screen_analyzer:_extract_web] Flutter element: using text selector '{text_content}' instead of dynamic ID")
            
            # Check identifiers (skip ID check for Flutter)
            has_id = '#' in selector and not is_flutter
            has_text = len(text_content) > 2
            
            # Check if clickable/navigable
            # For <a> tags: MUST have href (otherwise it's not a link)
            # For other tags: href not required (buttons, inputs, Flutter elements, etc.)
            if tag == 'a':
                # Links without href are not navigation targets
                if not href or href.startswith('#'):
                    print(f"[@screen_analyzer:_extract_web] Filtered NO HREF: {selector} (text: {text_content[:20]})")
                    continue
            
            # Filter elements with NO identifiers (no ID, no text)
            # BUT: If we have a valid href (and it's a link), we should keep it even without text
            # (The href itself describes the destination)
            if not has_id and not has_text:
                if tag == 'a' and href and len(href) > 2:
                    # Use href as fallback label
                    print(f"[@screen_analyzer:_extract_web] Weak identifier but valid href: {href} -> Keeping")
                else:
                    print(f"[@screen_analyzer:_extract_web] Filtered WEAK IDENTIFIER: {selector} (tag: {tag}, text: '{text_content}')")
                    continue
            
            # Get label for this element
            label = None
            
            # Priority 1: For Flutter, ALWAYS use text (IDs are dynamic)
            if is_flutter and text_content:
                label = text_content
            # Priority 2: Text content (More human-readable than ID for web)
            elif text_content:
                label = text_content
            # Priority 3: ID from selector (Reliable fallback if text is missing)
            elif has_id:
                label = selector.split('#')[-1].strip()
            # Priority 4: aria-label
            elif attributes.get('aria-label'):
                label = attributes['aria-label'].strip()
            # Priority 5: Derive from href (Fallback for links with empty text)
            elif tag == 'a' and href:
                # /collections/all -> collections/all
                clean_href = href.strip('/').split('/')[-1]
                if clean_href:
                    label = clean_href.replace('-', ' ').replace('_', ' ').title()
            # Priority 6: class name (last resort)
            elif '.' in selector:
                label = selector.split('.')[-1].strip()
            
            if not label:
                continue
            
            label_lower = label.lower()
            
            # ═══════════════════════════════════════════════════════════════
            # FILTERS: Exclude non-navigation elements
            # ═══════════════════════════════════════════════════════════════
            
            # Filter 1: Layout containers
            if any(kw in label_lower for kw in layout_keywords):
                print(f"[@screen_analyzer:_extract_web] Filtered LAYOUT: {label}")
                continue
            
            # Filter 2: Decorations
            if any(kw in label_lower for kw in decoration_keywords):
                print(f"[@screen_analyzer:_extract_web] Filtered DECORATION: {label}")
                continue
            
            # Filter 3: External/social links
            if any(kw in label_lower for kw in external_keywords):
                print(f"[@screen_analyzer:_extract_web] Filtered EXTERNAL: {label}")
                continue
            
            # Filter 4: Very short (< 2 chars) or very long (> 40 chars)
            if len(label) < 2 or len(label) > 40:
                print(f"[@screen_analyzer:_extract_web] Filtered LENGTH: {label} ({len(label)} chars)")
                continue
            
            # Filter 5: URL quality checks
            # External URL check (for <a> tags)
            if tag == 'a' and href:
                # Skip external URLs
                if any(ext in href for ext in ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'mailto:']):
                    print(f"[@screen_analyzer:_extract_web] Filtered EXTERNAL URL: {label} ({href})")
                    continue
                
                # Skip anchors (#)
                if href.startswith('#') and len(href) < 3:
                    print(f"[@screen_analyzer:_extract_web] Filtered ANCHOR: {label} ({href})")
                    continue
            
            # Filter 6: Dynamic content patterns
            dynamic_indicators = ['$', '€', '£', 'chf', 'usd', 'eur', 'season ', 'episode ']
            if any(ind in label_lower for ind in dynamic_indicators):
                print(f"[@screen_analyzer:_extract_web] Filtered DYNAMIC: {label}")
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # PASSED ALL FILTERS - Add to results
            # ═══════════════════════════════════════════════════════════════
            
            clean_label = label.replace('_', ' ').replace('-', ' ').title()
            
            if clean_label not in interactive_elements:
                interactive_elements.append(clean_label)
                seen_selectors.add(selector)
                print(f"[@screen_analyzer:_extract_web] ✅ INCLUDED: {clean_label} (selector: {selector})")
        
        # ═══════════════════════════════════════════════════════════════
        # Add grouped components
        # ═══════════════════════════════════════════════════════════════
        
        if search_group['found']:
            interactive_elements.insert(0, 'Search')  # Add at beginning (high priority)
            print(f"[@screen_analyzer:_extract_web] ✅ GROUPED: Search (from {len(search_group['ids'])} elements)")
        
        if cart_group['found']:
            interactive_elements.append('Cart')
            print(f"[@screen_analyzer:_extract_web] ✅ GROUPED: Cart (from {len(cart_group['ids'])} elements)")
        
        print(f"[@screen_analyzer:_extract_web] Final count: {len(interactive_elements)} navigation targets")
        
        return interactive_elements[:20]  # Limit to top 20 elements
    
    def _analyze_from_ai_vision(self, screenshot_path: str) -> Dict:
        """
        Use AI vision to analyze screenshot (TV/STB only)
        """
        # Unified prompt for TV/STB
        prompt = """You are a UI-automation engineer.

From the screenshot of a streaming/TV app (Netflix, YouTube, Android TV, Apple TV, set-top-box, etc.), list every visible item or clickable elements (tabs). Avoid none interactive content: asset, program card, program name, duration or time. Provide the list in the order left to right on same line.

Example output:

profile, sunrise, cast, airplay, search
popular_on_tv, show all
home, tvguide, replay, movies_and_series, saved, debug

Return ONLY the lines of comma-separated items, nothing else."""

        print(f"\n📝 AI VISION ANALYSIS")
        print(f"{'-'*80}")
        print(f"PROMPT SENT TO AI:")
        print(f"{'-'*80}")
        print(prompt)
        print(f"{'-'*80}\n")

        try:
            # Use existing VideoAIHelpers for AI analysis
            # VideoAIHelpers needs av_controller, but we'll pass None and use direct file path
            from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
            
            ai_helpers = VideoAIHelpers(
                av_controller=None,  # We're passing file path directly
                device_name=self.device_id
            )
            
            # Use analyze_full_image_with_ai which exists
            response = ai_helpers.analyze_full_image_with_ai(
                image_path=screenshot_path,
                user_question=prompt
            )
            
            print(f"🤖 RAW AI RESPONSE:")
            print(f"{'-'*80}")
            print(response)
            print(f"{'-'*80}\n")
            
            # Parse line-by-line response
            # Expected format:
            # profile, sunrise, cast, airplay, search
            # popular_on_tv, show all
            # home, tvguide, replay, movies_and_series, saved, debug
            
            lines = []
            all_items = []
            
            # Split response into lines and parse each
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('Example'):
                    # Extract items from this line
                    items_in_line = [item.strip() for item in line.split(',') if item.strip()]
                    if items_in_line:
                        lines.append(items_in_line)
                        all_items.extend(items_in_line)
            
            # Determine menu structure from lines
            if len(lines) == 1:
                menu_type = 'horizontal'
            elif len(lines) > 1:
                # Check if it's vertical (1 item per line) or grid (multiple items per line)
                if all(len(line) == 1 for line in lines):
                    menu_type = 'vertical'
                else:
                    menu_type = 'mixed'  # Has both horizontal and vertical navigation
            else:
                menu_type = 'unknown'
            
            # Strategy for TV/STB is always DPAD
            strategy = 'test_dpad_directions'
            
            result = {
                'menu_type': menu_type,
                'items': all_items,
                'lines': lines,  # Keep line structure for navigation logic
                'predicted_depth': 2,
                'strategy': strategy
            }
            
            print(f"✅ PARSED RESULT:")
            print(f"{'-'*80}")
            print(f"Items ({len(all_items)}):")
            for i, line in enumerate(lines, 1):
                print(f"Line {i}: {', '.join(line)}")
            print(f"{'-'*80}\n")
            
            return result
            
        except Exception as e:
            print(f"[@screen_analyzer:anticipate_tree] Error: {e}")
            # Return safe defaults on error
            return {
                'menu_type': 'mixed',
                'items': [],
                'predicted_depth': 3,
                'strategy': 'test_all_directions'
            }
    
    def is_new_screen(
        self,
        before_path: str,
        after_path: str,
        action: str
    ) -> Dict:
        """
        Phase 2: After OK/BACK action, determine if we reached new screen
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            action: Action taken (e.g., 'OK', 'BACK')
            
        Returns:
            {
                'is_new_screen': True,
                'context_visible': False,
                'suggested_name': 'settings',
                'screen_type': 'menu',
                'reasoning': 'Completely different screen...'
            }
        """
        from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
        prompt = f"""Compare these two screenshots after action '{action}'.

Please answer:
1. Is this a NEW SCREEN (completely different UI) or SAME SCREEN (just focus changed)?
2. Can you still see the previous menu? (Yes/No)
3. What is a good name for this screen based on visible content?
4. What type of screen is this? (menu, settings, content, info, player, etc.)
5. Brief reasoning for your decision

Return ONLY valid JSON in this exact format:
{{
    "is_new_screen": true,
    "context_visible": false,
    "suggested_name": "settings",
    "screen_type": "menu",
    "reasoning": "Completely different screen, cannot see previous menu"
}}

Context visible = Can you still see elements from the previous screen?
"""

        try:
            # Use existing VideoAIHelpers with both images
            from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
            
            ai_helpers = VideoAIHelpers(
                av_controller=None,  # We're passing file path directly
                device_name=self.device_id
            )
            
            # Use analyze_full_image_with_ai for the after screenshot
            response = ai_helpers.analyze_full_image_with_ai(
                image_path=after_path,
                user_question=prompt
            )
            
            print(f"[@screen_analyzer:is_new_screen] AI response: {response}")
            
            # Parse JSON from response
            result = self._parse_json_response(response)
            
            if not result:
                # Fallback: assume it's a new screen
                return {
                    'is_new_screen': True,
                    'context_visible': False,
                    'suggested_name': 'screen',
                    'screen_type': 'screen',
                    'reasoning': 'Could not determine, assuming new screen'
                }
            
            return result
            
        except Exception as e:
            print(f"[@screen_analyzer:is_new_screen] Error: {e}")
            # Return safe defaults on error
            return {
                'is_new_screen': True,
                'context_visible': False,
                'suggested_name': 'screen',
                'screen_type': 'screen',
                'reasoning': f'Error during analysis: {str(e)}'
            }
    
    def capture_screenshot(self) -> Optional[str]:
        """
        Capture screenshot and save to cold storage:
        - android_mobile: Use ADB native screenshot (exact display buffer)
        - Other devices: Use HDMI capture via VideoAIHelpers
        
        Returns:
            Screenshot file path in COLD storage or None on error
        """
        try:
            import shutil
            from datetime import datetime
            from shared.src.lib.utils.storage_path_utils import get_captures_path, get_capture_folder_from_device_id
            
            # Get device capture folder
            try:
                device_folder = get_capture_folder_from_device_id(self.device_id)
            except ValueError as e:
                print(f"[@screen_analyzer:capture_screenshot] Error getting device folder: {e}")
                return None
            
            # For android_mobile, use native ADB screenshot
            if self.device_model_name and 'mobile' in self.device_model_name.lower() and self.controller:
                success, base64_data, error = self.controller.take_screenshot()
                if success and base64_data:
                    # Convert base64 to image data
                    import base64
                    image_data = base64.b64decode(base64_data)
                    
                    # Save to COLD storage (captures path)
                    captures_path = get_captures_path(device_folder)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"ai_exploration_{timestamp}.png"
                    cold_path = f"{captures_path}/{filename}"
                    
                    # Ensure directory exists
                    import os
                    os.makedirs(captures_path, exist_ok=True)
                    
                    # Write to cold storage
                    with open(cold_path, 'wb') as f:
                        f.write(image_data)
                    
                    print(f"\n{'='*80}")
                    print(f"[@screen_analyzer:capture_screenshot] SCREENSHOT CAPTURED")
                    print(f"{'='*80}")
                    print(f"📸 Local Path: {cold_path}")
                    print(f"📁 Device Folder: {device_folder}")
                    print(f"📝 Filename: {filename}")
                    print(f"{'='*80}\n")
                    
                    return cold_path
            
            # Fallback to HDMI capture for all other devices using device's AV controller
            av_controller = self.device._get_controller('av')
            if not av_controller:
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: No AV controller found for device {self.device_id}")
                return None
            
            print(f"[@screen_analyzer:capture_screenshot] Attempting HDMI capture via AV controller...")
            temp_screenshot = av_controller.take_screenshot()
            
            if not temp_screenshot:
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: AV controller returned None/empty")
                return None
            
            # Verify file exists
            import os
            if not os.path.exists(temp_screenshot):
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: Screenshot file doesn't exist: {temp_screenshot}")
                return None
            
            if temp_screenshot:
                # Copy to cold storage
                captures_path = get_captures_path(device_folder)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"ai_exploration_{timestamp}.png"
                cold_path = f"{captures_path}/{filename}"
                
                # Ensure directory exists
                import os
                os.makedirs(captures_path, exist_ok=True)
                
                # Copy file
                shutil.copy2(temp_screenshot, cold_path)
                print(f"[@screen_analyzer:capture_screenshot] Copied to cold storage: {cold_path}")
                return cold_path
            
            return None
            
        except Exception as e:
            print(f"[@screen_analyzer:capture_screenshot] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        Parse JSON from AI response text
        
        Args:
            response: Raw AI response (may contain text + JSON)
            
        Returns:
            Parsed dict or None if failed
        """
        try:
            # Try direct JSON parse first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end != -1:
                    json_str = response[start:end].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
            
            # Try to find JSON object in text
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            print(f"[@screen_analyzer:_parse_json_response] Failed to parse JSON from: {response[:200]}")
            return None

