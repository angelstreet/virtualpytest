"""
Playwright Web Controller Implementation

This controller provides web browser automation functionality using Playwright.
Key features: Chrome remote debugging for thread-safe automation, async Playwright with sync wrappers for browser-use compatibility.
Uses playwright_utils for Chrome management and async execution.
"""

# =============================================================================
# GLOBAL BROWSER ENGINE CONFIGURATION
# =============================================================================
# Change this to switch between browsers easily:
# - "chromium" = Full Chrome browser (default, ~170MB, high memory)
# - "webkit"   = Safari/WebKit engine (lightweight, ~50MB, low memory)
BROWSER_ENGINE = "chromium"  # <-- Change this line to switch browsers
# =============================================================================

import os
import json
import time
from typing import Dict, Any, Optional
from ..base_controller import WebControllerInterface

# Use absolute import for utils from shared library
import sys
import os
# Get path to shared/lib/utils
shared_utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'shared', 'lib', 'utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)

from playwright_utils import PlaywrightUtils
from webkit_utils import WebKitUtils
# Import browseruse_utils only when needed to avoid browser_use dependency at module load
# from browseruse_utils import BrowserUseManager


class PlaywrightWebController(WebControllerInterface):
    """Playwright web controller using async Playwright with sync wrappers for browser-use compatibility."""
    
    # Class-level Chrome process management
    _chrome_process = None
    _chrome_running = False
    
    # Class-level persistent Playwright browser and context (reuse)
    _playwright = None
    _browser = None
    _context = None
    _browser_connected = False
    
    def __init__(self, browser_engine: str = None, **kwargs):
        """
        Initialize the Playwright web controller.
        
        Args:
            browser_engine: "chromium" or "webkit" (uses BROWSER_ENGINE global if None)
        """
        super().__init__("Playwright Web", "playwright")
        #import os
        #os.environ['DEBUG'] = 'pw:api'  # Enable Playwright API debug logs
        #os.environ['PLAYWRIGHT_DEBUG'] = '1'  # Enable additional debug info
        
        # Choose browser engine (use global default if not specified)
        self.browser_engine = browser_engine if browser_engine is not None else BROWSER_ENGINE
        
        if self.browser_engine == "webkit":
            self.utils = WebKitUtils()
            print(f"[@controller:PlaywrightWeb] Initialized with lightweight WebKit browser (global setting)")
        else:
            self.utils = PlaywrightUtils(auto_accept_cookies=True, use_cgroup=False)
            print(f"[@controller:PlaywrightWeb] Initialized with Chromium browser (global setting, cgroup disabled)")
        
        # Command execution state
        self.last_command_output = ""
        self.last_command_error = ""
        self.current_url = ""
        self.page_title = ""
        

    
    @property
    def is_connected(self):
        """Always connected once Chrome is running."""
        # Check if Chrome process is actually still alive
        if self.__class__._chrome_process and self.__class__._chrome_running:
            if self.__class__._chrome_process.poll() is not None:
                # Chrome process has died
                print(f"[PLAYWRIGHT]: Chrome process {self.__class__._chrome_process.pid} has died (exit code: {self.__class__._chrome_process.returncode})")
                self.__class__._chrome_running = False
                self.__class__._browser_connected = False
                self.__class__._chrome_process = None
        
        result = self.__class__._chrome_running
        print(f"[PLAYWRIGHT]: is_connected check - _chrome_running={self._chrome_running}, returning {result}")
        return result
    
    @is_connected.setter
    def is_connected(self, value):
        """Setter for base controller compatibility - only sets True when Chrome launches."""
        if value:
            self.__class__._chrome_running = True
        # Ignore False values - once connected, always connected
    
    async def _get_persistent_page(self, target_url: str = None):
        """Get the persistent page from browser+context. Assumes Chrome is running."""
        # Establish persistent browser+context if not exists
        if not self.__class__._browser_connected or not self.__class__._browser or not self.__class__._context:
            print(f"[PLAYWRIGHT]: Creating persistent browser+context+page...")
            if self.browser_engine == "webkit":
                self.__class__._playwright, self.__class__._browser, self.__class__._context, initial_page = await self.utils.connect_to_webkit(target_url=target_url)
            else:
                self.__class__._playwright, self.__class__._browser, self.__class__._context, initial_page = await self.utils.connect_to_chrome(target_url=target_url)
            self.__class__._browser_connected = True
            print(f"[PLAYWRIGHT]: Persistent {self.browser_engine} browser+context+page established")
            return initial_page
        
        # Get existing page 0 from context (persistent page)
        if len(self.__class__._context.pages) > 0:
            page = self.__class__._context.pages[0]
            print(f"[PLAYWRIGHT]: Using existing persistent page (page 0)")
            return page
        else:
            # No pages exist, create one
            page = await self.__class__._context.new_page()
            print(f"[PLAYWRIGHT]: Created new persistent page")
            return page
    
    async def _cleanup_persistent_browser(self):
        """Clean up persistent browser+context."""
        if self.__class__._browser_connected:
            print(f"[PLAYWRIGHT]: Cleaning up persistent browser+context...")
            if self.__class__._browser:
                await self.__class__._browser.close()
            if self.__class__._playwright:
                await self.__class__._playwright.stop()
            
            self.__class__._playwright = None
            self.__class__._browser = None
            self.__class__._context = None
            self.__class__._browser_connected = False
            print(f"[PLAYWRIGHT]: Persistent browser+context cleaned up")
    
    def connect(self) -> bool:
        """Connect to browser (launch if needed)."""
        browser_name = self.browser_engine.upper()
        print(f"[PLAYWRIGHT]: connect() called - _{self.browser_engine}_running={self._chrome_running}, _process={self._chrome_process}")
        
        if not self._chrome_running:
            try:
                print(f"[PLAYWRIGHT]: {browser_name} not running, launching new process...")
                if self.browser_engine == "webkit":
                    self.__class__._chrome_process = self.utils.launch_webkit()
                else:
                    self.__class__._chrome_process = self.utils.launch_chrome()
                self.__class__._chrome_running = True  # Always connected once launched
                print(f"[PLAYWRIGHT]: {browser_name} launched with remote debugging successfully (PID: {self._chrome_process.pid})")
                
                # Give browser a moment to start up
                import time
                time.sleep(2)
                print(f"[PLAYWRIGHT]: {browser_name} startup delay completed")
                
            except Exception as e:
                error_type = type(e).__name__
                print(f"[PLAYWRIGHT]: Failed to launch {browser_name} - {error_type}: {str(e)}")
                return False
        else:
            print(f"[PLAYWRIGHT]: {browser_name} process already running (PID: {self._chrome_process.pid if self._chrome_process else 'unknown'})")
        
        print(f"[PLAYWRIGHT]: connect() completed - running={self._chrome_running}, is_connected={self.is_connected}")
        return True
    

    
    def open_browser(self) -> Dict[str, Any]:
        """Open/launch the browser window. Simple: connect or kill+restart."""
        async def _async_open_browser():
            try:
                print(f"[PLAYWRIGHT]: Opening browser - connect or kill+restart approach")
                start_time = time.time()
                
                # Simple approach: try to connect, if fails kill and restart
                try:
                    # Try to connect to existing Chrome or launch new one
                    if not self.is_connected:
                        print(f"[PLAYWRIGHT]: Chrome not running, launching...")
                        self.connect()
                    
                    # Get page - if this fails, Chrome is not responding
                    page = await self._get_persistent_page()
                    
                    # Only navigate to Google if page is blank
                    if page.url in ['about:blank', '', 'chrome://newtab/']:
                        await page.goto('https://google.fr')
                    
                    # Update page state
                    self.current_url = page.url
                    self.page_title = await page.title()
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    print(f"[PLAYWRIGHT]: Browser opened and ready")
                    return {
                        'success': True,
                        'error': '',
                        'execution_time': execution_time,
                        'connected': True
                    }
                    
                except Exception as e:
                    # Connection failed - kill everything and restart
                    print(f"[PLAYWRIGHT]: Connection failed ({e}), killing and restarting Chrome...")
                    self.utils.kill_chrome(chrome_process=self.__class__._chrome_process)
                    self.__class__._chrome_process = None
                    self.__class__._chrome_running = False
                    self.__class__._browser_connected = False
                    
                    # Restart Chrome
                    self.connect()
                    page = await self._get_persistent_page()
                    
                    # Navigate to Google
                    await page.goto('https://google.fr')
                    
                    # Update page state
                    self.current_url = page.url
                    self.page_title = await page.title()
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    print(f"[PLAYWRIGHT]: Browser restarted and ready")
                    return {
                        'success': True,
                        'error': '',
                        'execution_time': execution_time,
                        'connected': True
                    }
                
            except Exception as e:
                error_msg = f"Browser open error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0,
                    'connected': False
                }
        
        return self.utils.run_async(_async_open_browser())
    
    def connect_browser(self) -> Dict[str, Any]:
        """Connect to existing Chrome debug session without killing Chrome first."""
        async def _async_connect_existing():
            try:
                print(f"[PLAYWRIGHT]: Connecting to existing Chrome debug session")
                start_time = time.time()
                
                # Try to connect to existing Chrome debug session (no killing Chrome first)
                try:
                    # For existing Chrome, just connect without creating new context
                    self.__class__._playwright, self.__class__._browser, self.__class__._context, page = await self.utils.connect_to_chrome()
                    self.__class__._browser_connected = True
                    
                    # Get current page info from persistent page
                    self.current_url = page.url
                    self.page_title = await page.title() if page.url != 'about:blank' else ''
                    
                    # Connection state will be automatically detected via property
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    
                    print(f"[PLAYWRIGHT]: Connected to existing Chrome debug session")
                    return {
                        'success': True,
                        'error': '',
                        'execution_time': execution_time,
                        'connected': True,
                        'current_url': self.current_url,
                        'page_title': self.page_title
                    }
                    
                except Exception as e:
                    # Chrome debug session not available - try to launch Chrome instead
                    print(f"[PLAYWRIGHT]: No existing Chrome found ({e}), launching new Chrome...")
                    try:
                        # Launch Chrome and connect
                        if not self.connect():
                            raise Exception("Failed to launch Chrome")
                        
                        # Wait 5 seconds for Chrome to fully initialize after launch
                        print(f"[PLAYWRIGHT]: Waiting 5s for Chrome to fully initialize...")
                        time.sleep(5)
                        
                        page = await self._get_persistent_page(target_url='https://google.fr')
                        
                        # Update page state
                        self.current_url = page.url
                        self.page_title = await page.title()
                        
                        execution_time = int((time.time() - start_time) * 1000)
                        print(f"[PLAYWRIGHT]: Launched new Chrome and connected successfully")
                        return {
                            'success': True,
                            'error': '',
                            'execution_time': execution_time,
                            'connected': True,
                            'current_url': self.current_url,
                            'page_title': self.page_title,
                            'launched_new': True
                        }
                    except Exception as launch_error:
                        error_msg = f"Could not connect to existing Chrome and failed to launch new Chrome: {launch_error}"
                        print(f"[PLAYWRIGHT]: {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg,
                            'execution_time': 0,
                            'connected': False
                        }
                
            except Exception as e:
                error_msg = f"Browser connection error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0,
                    'connected': False
                }
        
        return self.utils.run_async(_async_connect_existing())
    
    def close_browser(self) -> Dict[str, Any]:
        """Browser stays open - no closing."""
        print(f"[PLAYWRIGHT]: Browser stays open (no closing)")
        return {
            'success': True,
            'error': '',
            'execution_time': 0,
            'connected': True
        }
    
    def navigate_to_url(self, url: str, timeout: int = 60000, follow_redirects: bool = True) -> Dict[str, Any]:
        """Navigate to a URL using async CDP connection."""
        async def _async_navigate_to_url():
            try:
                # Normalize URL to add protocol if missing
                normalized_url = self.utils.normalize_url(url)
                print(f"[PLAYWRIGHT]: Navigating to {url} (normalized: {normalized_url})")
                start_time = time.time()

                # Assume Chrome is running - no auto-connect checks

                # Get persistent page from browser+context
                page = await self._get_persistent_page(target_url=normalized_url)
                
                # Navigate to URL
                await page.goto(normalized_url, timeout=timeout, wait_until='load')
                
                # Get page info after navigation
                try:
                    # Try to wait for networkidle but don't fail if it times out
                    await page.wait_for_load_state('networkidle', timeout=20000)
                except Exception as e:
                    print(f"[PLAYWRIGHT]: Networkidle timeout ignored: {str(e)}")
                
                self.current_url = page.url
                self.page_title = await page.title()
                
                # Page remains persistent for next actions
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'url': self.current_url,
                    'title': self.page_title,
                    'execution_time': execution_time,
                    'error': '',
                    'normalized_url': normalized_url,
                    'redirected': self.current_url != normalized_url,
                    'follow_redirects': follow_redirects
                }
                
                if result['redirected']:
                    print(f"[PLAYWRIGHT]: Navigation completed with redirect: {normalized_url} -> {self.current_url}")
                else:
                    print(f"[PLAYWRIGHT]: Navigation successful - {self.page_title}")
                return result
                
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                error_type = type(e).__name__
                error_msg = str(e)
                
                print(f"[PLAYWRIGHT]: ❌ NAVIGATION FAILED after {execution_time}ms")
                print(f"[PLAYWRIGHT]: Error Type: {error_type}")
                print(f"[PLAYWRIGHT]: Error Message: {error_msg}")
                print(f"[PLAYWRIGHT]: Target URL: {normalized_url if 'normalized_url' in locals() else url}")
                
                # Try to get current page state for debugging
                try:
                    if 'page' in locals():
                        current_url = page.url
                        current_title = await page.title()
                        print(f"[PLAYWRIGHT]: Current page state - URL: {current_url}, Title: {current_title[:50]}...")
                    else:
                        print(f"[PLAYWRIGHT]: Page object not available for state check")
                except Exception as state_error:
                    print(f"[PLAYWRIGHT]: Could not get page state: {type(state_error).__name__}: {str(state_error)}")
                
                return {
                    'success': False,
                    'error': f"{error_type}: {error_msg}",
                    'error_type': error_type,
                    'url': self.current_url,
                    'title': self.page_title,
                    'execution_time': execution_time,
                    'original_url': url,
                    'normalized_url': normalized_url if 'normalized_url' in locals() else url,
                    'follow_redirects': follow_redirects
                }
        
        return self.utils.run_async(_async_navigate_to_url())
    
    def click_element(self, selector: str) -> Dict[str, Any]:
        """Click an element by selector using async CDP connection.
        
        Args:
            selector: CSS selector, or text content to search for
        """
        async def _async_click_element():
            try:
                print(f"[PLAYWRIGHT]: Clicking element: {selector}")
                start_time = time.time()
                
                # Assume Chrome is running - no auto-connect checks
                
                # Get persistent page from browser+context
                connect_start = time.time()
                page = await self._get_persistent_page()
                connect_time = int((time.time() - connect_start) * 1000)
                print(f"[PLAYWRIGHT]: Persistent page access took {connect_time}ms")
                
                # Try obvious selectors with short timeout
                timeout = 2000  # 2000ms per attempt since 1000 was failing
                
                # Most obvious selectors for text-based elements (including Flutter)
                selectors_to_try = [
                    selector,  # Try exact selector first (could be CSS or text)
                    f"[aria-label='{selector}']",  # Most common for buttons/links
                    f"[aria-label='{selector}' i]",  # Case-insensitive aria-label
                    f"flt-semantics[aria-label='{selector}']",  # Flutter semantics exact
                    f"flt-semantics[aria-label='{selector}' i]",  # Flutter semantics case-insensitive
                    f"button:has-text('{selector}')",  # Actual buttons with text
                    f"a:has-text('{selector}')"  # Links with text
                ]
                
                for i, sel in enumerate(selectors_to_try):
                    try:
                        # Try hover first to trigger any rollover UI elements
                        try:
                            await page.hover(sel, timeout=1000)
                            print(f"[PLAYWRIGHT]: Hover successful for selector {i+1}: {sel}")
                            # Small delay to let hover effects appear
                            await page.wait_for_timeout(200)
                        except Exception:
                            print(f"[PLAYWRIGHT]: Hover failed for selector {i+1}: {sel}, proceeding with click")
                        
                        await page.click(sel, timeout=timeout)
                        execution_time = int((time.time() - start_time) * 1000)
                        print(f"[PLAYWRIGHT]: Click successful using selector {i+1}: {sel}")
                        return {
                            'success': True,
                            'error': '',
                            'execution_time': execution_time
                        }
                    except Exception as e:
                        error_str = str(e)
                        if "intercepts pointer events" in error_str:
                            print(f"[PLAYWRIGHT]: Selector {i+1} blocked by overlay, trying force click: {sel}")
                            try:
                                # Force click bypasses overlay checks
                                await page.click(sel, timeout=timeout, force=True)
                                execution_time = int((time.time() - start_time) * 1000)
                                print(f"[PLAYWRIGHT]: Force click successful using selector {i+1}: {sel}")
                                return {
                                    'success': True,
                                    'error': '',
                                    'execution_time': execution_time,
                                    'method': 'force_click'
                                }
                            except Exception as force_e:
                                print(f"[PLAYWRIGHT]: Force click also failed for selector {i+1}: {sel} - {str(force_e)}")
                        else:
                            print(f"[PLAYWRIGHT]: Selector {i+1} failed ({timeout}ms): {sel} - Exception: {str(e)}")
                        continue
                
                # All selectors failed
                execution_time = int((time.time() - start_time) * 1000)
                error_msg = f"Click failed - element not found with any selector"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                }
                
            except Exception as e:
                error_msg = f"Click error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0,
                    'selector_attempted': selector
                }
        
        return self.utils.run_async(_async_click_element())
    
    def hover_element(self, selector: str) -> Dict[str, Any]:
        """Hover over an element to trigger rollover effects.
        
        Args:
            selector: CSS selector, or text content to search for
        """
        async def _async_hover_element():
            try:
                print(f"[PLAYWRIGHT]: Hovering over element: {selector}")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Try same selectors as click
                selectors_to_try = [
                    selector,
                    f"[aria-label='{selector}']",
                    f"flt-semantics[aria-label='{selector}']",
                ]
                
                for i, sel in enumerate(selectors_to_try):
                    try:
                        await page.hover(sel, timeout=2000)
                        execution_time = int((time.time() - start_time) * 1000)
                        print(f"[PLAYWRIGHT]: Hover successful using selector {i+1}: {sel}")
                        return {
                            'success': True,
                            'error': '',
                            'execution_time': execution_time
                        }
                    except Exception as e:
                        print(f"[PLAYWRIGHT]: Hover selector {i+1} failed: {sel} - {str(e)}")
                        continue
                
                # All selectors failed
                execution_time = int((time.time() - start_time) * 1000)
                error_msg = f"Hover failed - element not found with any selector"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                }
                
            except Exception as e:
                error_msg = f"Hover error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0
                }
        
        return self.utils.run_async(_async_hover_element())
    
    def find_element(self, selector: str) -> Dict[str, Any]:
        """Find an element by selector without clicking it.
        
        Args:
            selector: CSS selector, or text content to search for
        """
        async def _async_find_element():
            try:
                print(f"[PLAYWRIGHT]: Finding element: {selector}")
                start_time = time.time()
                
                # Get persistent page from browser+context
                connect_start = time.time()
                page = await self._get_persistent_page()
                connect_time = int((time.time() - connect_start) * 1000)
                print(f"[PLAYWRIGHT]: Persistent page access took {connect_time}ms")
                
                # Try obvious selectors with short timeout
                timeout = 1000  # 500ms per attempt
                
                # Most obvious selectors for text-based elements (including Flutter)
                selectors_to_try = [
                    selector,  # Try exact selector first (could be CSS or text)
                    f"[aria-label='{selector}']",  # Most common for buttons/links
                    f"[aria-label='{selector}' i]",  # Case-insensitive aria-label
                    f"flt-semantics[aria-label='{selector}']",  # Flutter semantics exact
                    f"flt-semantics[aria-label='{selector}' i]",  # Flutter semantics case-insensitive
                    f"button:has-text('{selector}')",  # Actual buttons with text
                    f"a:has-text('{selector}')"  # Links with text
                ]
                
                for i, sel in enumerate(selectors_to_try):
                    try:
                        element = await page.locator(sel).first
                        await element.wait_for(timeout=timeout)
                        if await element.is_visible():
                            bounding_box = await element.bounding_box()
                            element_info = {}
                            if bounding_box:
                                element_info = {
                                    'x': bounding_box['x'],
                                    'y': bounding_box['y'],
                                    'width': bounding_box['width'],
                                    'height': bounding_box['height']
                                }
                            
                            execution_time = int((time.time() - start_time) * 1000)
                            print(f"[PLAYWRIGHT]: Element found using selector {i+1}: {sel}")
                            return {
                                'success': True,
                                'error': '',
                                'execution_time': execution_time,
                                'element_info': element_info
                            }
                    except Exception:
                        print(f"[PLAYWRIGHT]: Selector {i+1} failed ({timeout}ms): {sel}")
                        continue
                
                # All selectors failed
                execution_time = int((time.time() - start_time) * 1000)
                error_msg = f"Element not found with any selector"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                }
                
            except Exception as e:
                error_msg = f"Find error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0,
                    'selector_attempted': selector
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_find_element())
    
    def input_text(self, selector: str, text: str, timeout: int = 30000) -> Dict[str, Any]:
        """Input text into an element using async CDP connection."""
        async def _async_input_text():
            try:
                print(f"[PLAYWRIGHT]: Inputting text to: {selector}")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Input text
                await page.fill(selector, text, timeout=timeout)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time
                }
                
                print(f"[PLAYWRIGHT]: Text input successful")
                return result
                
            except Exception as e:
                error_msg = f"Input error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_input_text())
    
    def tap_x_y(self, x: int, y: int) -> Dict[str, Any]:
        """Tap/click at specific coordinates using async CDP connection."""
        async def _async_tap_x_y():
            try:
                print(f"[PLAYWRIGHT]: Tapping at coordinates: ({x}, {y})")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Show click animation and coordinates (like Android mobile)
                await self._show_click_animation(page, x, y)
                
                # Click at coordinates
                await page.mouse.click(x, y)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time,
                    'coordinates': {'x': x, 'y': y}
                }
                
                print(f"[PLAYWRIGHT]: Tap successful at ({x}, {y})")
                return result
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = f"Tap error ({error_type}): {str(e)}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                print(f"[PLAYWRIGHT]: Exception details - Type: {error_type}, Args: {e.args}")
                
                # Log connection state for debugging
                print(f"[PLAYWRIGHT]: Connection state - is_connected: {self.is_connected}, _chrome_running: {self._chrome_running}, _browser_connected: {self._browser_connected}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': error_type,
                    'error_details': str(e),
                    'connection_state': {
                        'is_connected': self.is_connected,
                        'chrome_running': self._chrome_running,
                        'browser_connected': self._browser_connected
                    },
                    'execution_time': 0
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_tap_x_y())
    
    def execute_javascript(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript code in the page using async CDP connection."""
        async def _async_execute_javascript():
            try:
                print(f"[PLAYWRIGHT]: Executing JavaScript")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Execute JavaScript
                result = await page.evaluate(script)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                return {
                    'success': True,
                    'result': result,
                    'error': '',
                    'execution_time': execution_time
                }
                
            except Exception as e:
                error_msg = f"JavaScript execution error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'result': None,
                    'error': error_msg,
                    'execution_time': 0
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_execute_javascript())
    
    async def _show_click_animation(self, page, x: int, y: int):
        """Show click animation and coordinates like Android mobile overlay."""
        try:
            js_code = f"""
            (() => {{
                // Create click animation styles if not exists
                const styleId = 'playwright-click-animation-styles';
                if (!document.getElementById(styleId)) {{
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.textContent = `
                        @keyframes playwrightClickPulse {{
                            0% {{
                                transform: scale(0.3);
                                opacity: 1;
                            }}
                            100% {{
                                transform: scale(1.5);
                                opacity: 0;
                            }}
                        }}
                    `;
                    document.head.appendChild(style);
                }}
                
                // Create click animation circle
                const clickAnimation = document.createElement('div');
                clickAnimation.style.cssText = `
                    position: fixed;
                    left: {x - 15}px;
                    top: {y - 15}px;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    background-color: rgba(255, 255, 255, 0.8);
                    border: 2px solid rgba(0, 123, 255, 0.8);
                    z-index: 999999;
                    pointer-events: none;
                    animation: playwrightClickPulse 0.3s ease-out forwards;
                `;
                document.body.appendChild(clickAnimation);
                
                // Create coordinate display
                const coordDisplay = document.createElement('div');
                coordDisplay.style.cssText = `
                    position: fixed;
                    left: {x + 20}px;
                    top: {y - 15}px;
                    background-color: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: monospace;
                    font-weight: bold;
                    z-index: 999999;
                    pointer-events: none;
                    white-space: nowrap;
                `;
                coordDisplay.textContent = '{x}, {y}';
                document.body.appendChild(coordDisplay);
                
                // Remove animation after 300ms
                setTimeout(() => {{
                    if (clickAnimation.parentNode) {{
                        clickAnimation.parentNode.removeChild(clickAnimation);
                    }}
                }}, 300);
                
                // Remove coordinate display after 2 seconds
                setTimeout(() => {{
                    if (coordDisplay.parentNode) {{
                        coordDisplay.parentNode.removeChild(coordDisplay);
                    }}
                }}, 2000);
                
                return true;
            }})()
            """
            
            await page.evaluate(js_code)
            print(f"[PLAYWRIGHT]: Click animation shown at ({x}, {y})")
        except Exception as e:
            print(f"[PLAYWRIGHT]: Click animation failed: {e}")
            # Don't fail the tap if animation fails
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get current page information using async CDP connection."""
        async def _async_get_page_info():
            try:
                print(f"[PLAYWRIGHT]: Getting page info")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Get page info
                self.current_url = page.url
                self.page_title = await page.title()
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'url': self.current_url,
                    'title': self.page_title,
                    'error': '',
                    'execution_time': execution_time
                }
                
                print(f"[PLAYWRIGHT]: Page info retrieved - {self.page_title}")
                return result
                
            except Exception as e:
                error_msg = f"Get page info error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'url': '',
                    'title': '',
                    'execution_time': 0
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_get_page_info())
    
    def activate_semantic(self) -> Dict[str, Any]:
        """Activate semantic placeholder for Flutter web apps."""
        script = """
        (() => {
            const shadowHost = document.querySelector('body > flutter-view > flt-glass-pane');
            if (shadowHost) {
                const shadowRoot = shadowHost.shadowRoot;
                if (shadowRoot) {
                    const element = shadowRoot.querySelector('flt-semantics-placeholder');
                    if (element) {
                        element.click();
                        return true;
                    }
                }
            }
            return false;
        })()
        """
        
        # Try once, if fails wait 1s and retry with connection check
        result = self.execute_javascript(script)
        if not result.get('success'):
            print(f"[PLAYWRIGHT]: First activate_semantic failed ({result.get('error', 'unknown')}), retrying in 1s...")
            import time; time.sleep(1)
            # Check if connection issue and try to recover
            if 'Connection closed' in str(result.get('error', '')):
                print(f"[PLAYWRIGHT]: Connection issue detected, attempting recovery...")
                self._browser_connected = False  # Force reconnection
            result = self.execute_javascript(script)
        result['success'] = True  # Always succeed since this is optional
        return result
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """Press keyboard key using async CDP connection.
        
        Args:
            key: Key to press ('BACK', 'ESCAPE', 'ENTER', 'OK', etc.)
        """
        async def _async_press_key():
            try:
                print(f"[PLAYWRIGHT]: Pressing key: {key}")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Map web-specific keys to Playwright key names
                key_mapping = {
                    'BACK': 'Escape',
                    'ESC': 'Escape', 
                    'ESCAPE': 'Escape',
                    'OK': 'Enter',
                    'ENTER': 'Enter',
                    'HOME': 'Home',
                    'END': 'End',
                    'UP': 'ArrowUp',
                    'DOWN': 'ArrowDown', 
                    'LEFT': 'ArrowLeft',
                    'RIGHT': 'ArrowRight',
                    'TAB': 'Tab',
                    'SPACE': 'Space',
                    'DELETE': 'Delete',
                    'BACKSPACE': 'Backspace',
                    'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4',
                    'F5': 'F5', 'F6': 'F6', 'F7': 'F7', 'F8': 'F8',
                    'F9': 'F9', 'F10': 'F10', 'F11': 'F11', 'F12': 'F12'
                }
                
                playwright_key = key_mapping.get(key.upper(), key)
                
                # Press the key
                await page.keyboard.press(playwright_key)
                
                # Page remains persistent for next actions
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time,
                    'key_pressed': key,
                    'playwright_key': playwright_key
                }
                
                print(f"[PLAYWRIGHT]: Key press successful: {key} -> {playwright_key}")
                return result
                
            except Exception as e:
                error_msg = f"Key press error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0,
                    'key_attempted': key
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_press_key())
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status."""
        try:
            if self.is_connected and self._chrome_running:
                return {
                    'success': True,
                    'current_url': self.current_url,
                    'page_title': self.page_title,
                    'connected': True,
                    'chrome_running': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Chrome not running or not connected',
                    'connected': False,
                    'chrome_running': self._chrome_running
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to check status: {str(e)}',
                'connected': False,
                'chrome_running': False
            }
    
    def browser_use_task(self, task: str) -> Dict[str, Any]:
        """Execute browser-use task using existing Chrome instance."""
        async def _async_browser_use_task():
            try:
                print(f"[PLAYWRIGHT]: Executing browser-use task: {task}")
                
                # Import browseruse_utils only when needed
                try:
                    from browseruse_utils import BrowserUseManager
                except ImportError as e:
                    return {
                        'success': False,
                        'error': f'Browser-use not available: {e}',
                        'task': task,
                        'execution_time': 0
                    }
                
                # Create browser-use manager with existing browser session reuse
                browseruse_manager = BrowserUseManager(self.utils)
                
                # Execute task
                result = await browseruse_manager.execute_task(task)
                
                # Update page state if successful
                if result.get('success') and result.get('page_info', {}).get('final_url'):
                    self.current_url = result['page_info']['final_url']
                    if result.get('page_info', {}).get('final_title'):
                        self.page_title = result['page_info']['final_title']
                
                return result
                
            except Exception as e:
                error_msg = f"Browser-use task error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'task': task,
                    'execution_time': 0
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_browser_use_task())
    
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute web automation command with JSON parameters.
        
        Args:
            command: Command to execute
            params: JSON parameters for the command
            
        Returns:
            Dict: Command execution result
        """
        if params is None:
            params = {}
        
        print(f"[PLAYWRIGHT]: Executing command '{command}' with params: {params}")
        
        if command == 'navigate_to_url':
            url = params.get('url')
            timeout = params.get('timeout', 30000)
            follow_redirects = params.get('follow_redirects', True)
            
            if not url:
                return {
                    'success': False,
                    'error': 'URL parameter is required',
                    'execution_time': 0
                }
                
            return self.navigate_to_url(url, timeout=timeout, follow_redirects=follow_redirects)
        
        elif command == 'click_element':
            selector = params.get('selector')
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return self.click_element(selector)
        
        elif command == 'find_element':
            selector = params.get('selector')
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return self.find_element(selector)
        
        elif command == 'hover_element':
            selector = params.get('selector')
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return self.hover_element(selector)
        
        elif command == 'input_text':
            selector = params.get('selector')
            text = params.get('text', '')
            timeout = params.get('timeout', 30000)
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return self.input_text(selector, text, timeout=timeout)
        
        elif command == 'tap_x_y':
            x = params.get('x')
            y = params.get('y')
            
            if x is None or y is None:
                return {
                    'success': False,
                    'error': 'X and Y coordinates are required',
                    'execution_time': 0
                }
                
            return self.tap_x_y(x, y)
        
        elif command == 'execute_javascript':
            script = params.get('script')
            
            if not script:
                return {
                    'success': False,
                    'error': 'Script parameter is required',
                    'execution_time': 0
                }
                
            return self.execute_javascript(script)
        
        elif command == 'get_page_info':
            return self.get_page_info()
        
        elif command == 'activate_semantic':
            return self.activate_semantic()
        
        elif command == 'open_browser':
            return self.open_browser()
        
        elif command == 'close_browser':
            return self.close_browser()  # Returns success but doesn't actually close
        
        elif command == 'connect_browser':
            return self.connect_browser()
        
        elif command == 'dump_elements':
            element_types = params.get('element_types', 'all')
            include_hidden = params.get('include_hidden', False)
            return self.dump_elements(element_types=element_types, include_hidden=include_hidden)
        
        elif command == 'browser_use_task':
            task = params.get('task', '')
            
            if not task:
                return {
                    'success': False,
                    'error': 'Task parameter is required',
                    'execution_time': 0
                }
            
            return self.browser_use_task(task)
        
        elif command == 'press_key':
            key = params.get('key')
            
            if not key:
                return {
                    'success': False,
                    'error': 'Key parameter is required',
                    'execution_time': 0
                }
            
            return self.press_key(key)
        
        elif command == 'set_viewport_size':
            width = params.get('width')
            height = params.get('height')
            
            if not width or not height:
                return {
                    'success': False,
                    'error': 'Width and height parameters are required',
                    'execution_time': 0
                }
            
            self.set_viewport_size(width, height)
            return {
                'success': True,
                'message': f'Viewport size set to {width}x{height}',
                'execution_time': 0
            }
        
        else:
            print(f"[PLAYWRIGHT]: Unknown command: {command}")
            return {
                'success': False,
                'error': f'Unknown command: {command}',
                'execution_time': 0
            }
    
    def dump_elements(self, element_types: str = "all", include_hidden: bool = False) -> Dict[str, Any]:
        """
        Dump all visible elements from the page for debugging and inspection.
        
        Args:
            element_types: Types of elements to include ('all', 'interactive', 'text', 'links')
            include_hidden: Whether to include hidden elements
        """
        async def _async_dump_elements():
            try:
                print(f"[PLAYWRIGHT]: Dumping elements (type: {element_types}, include_hidden: {include_hidden})")
                start_time = time.time()
                

                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # JavaScript code to extract visible elements
                js_code = f"""
                () => {{
                    const elementTypes = '{element_types}';
                    const includeHidden = {str(include_hidden).lower()};
                    
                    // Define element selectors based on type
                    let selectors = [];
                    
                    if (elementTypes === 'all' || elementTypes === 'interactive') {{
                        selectors.push(
                            'button', 'input', 'select', 'textarea', 'a[href]', 
                            '[onclick]', '[role="button"]', '[tabindex]'
                        );
                    }}
                    
                    if (elementTypes === 'all' || elementTypes === 'text') {{
                        selectors.push('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div');
                    }}
                    
                    if (elementTypes === 'all' || elementTypes === 'links') {{
                        selectors.push('a[href]');
                    }}
                    
                    if (elementTypes === 'all') {{
                        // Add form elements, media, etc.
                        selectors.push('img', 'video', 'iframe', 'form', 'label');
                        // Add Flutter semantic elements
                        selectors.push('flt-semantics', 'flt-semantic-node', '[id^="flt-semantic-node"]');
                    }}
                    
                    // Get all elements matching selectors
                    const allElements = document.querySelectorAll(selectors.join(', '));
                    const elements = [];
                    
                    allElements.forEach((el, index) => {{
                        // Check if element is visible
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const isVisible = rect.width > 0 && rect.height > 0 && 
                                        style.visibility !== 'hidden' && 
                                        style.display !== 'none' &&
                                        rect.top < window.innerHeight && 
                                        rect.bottom > 0;
                        
                        if (isVisible || includeHidden) {{
                            // Generate selector for this element
                            let selector = el.tagName.toLowerCase();
                            
                            // Add ID if available
                            if (el.id) {{
                                selector = '#' + el.id;
                            }} else {{
                                // Add class if available
                                if (el.className && typeof el.className === 'string') {{
                                    const classes = el.className.trim().split(/\\s+/).slice(0, 2);
                                    if (classes.length > 0) {{
                                        selector += '.' + classes.join('.');
                                    }}
                                }}
                                
                                // Add nth-child if no unique identifier
                                if (!el.id && (!el.className || el.className === '')) {{
                                    const parent = el.parentNode;
                                    if (parent) {{
                                        const siblings = Array.from(parent.children).filter(child => 
                                            child.tagName === el.tagName
                                        );
                                        if (siblings.length > 1) {{
                                            const index = siblings.indexOf(el) + 1;
                                            selector += `:nth-child(${{index}})`;
                                        }}
                                    }}
                                }}
                            }}
                            
                            // Get text content (limited to first 100 chars)
                            let textContent = '';
                            if (el.textContent) {{
                                textContent = el.textContent.trim().substring(0, 100);
                                if (el.textContent.trim().length > 100) {{
                                    textContent += '...';
                                }}
                            }}
                            
                            // Get attributes of interest including aria labels
                            const attributes = {{}};
                            if (el.href) attributes.href = el.href;
                            if (el.value) attributes.value = el.value;
                            if (el.placeholder) attributes.placeholder = el.placeholder;
                            if (el.title) attributes.title = el.title;
                            if (el.alt) attributes.alt = el.alt;
                            if (el.type) attributes.type = el.type;
                            if (el.name) attributes.name = el.name;
                            
                            // Aria attributes for accessibility and Flutter semantics
                            if (el.getAttribute('aria-label')) attributes['aria-label'] = el.getAttribute('aria-label');
                            if (el.getAttribute('aria-labelledby')) attributes['aria-labelledby'] = el.getAttribute('aria-labelledby');
                            if (el.getAttribute('aria-describedby')) attributes['aria-describedby'] = el.getAttribute('aria-describedby');
                            if (el.getAttribute('aria-role')) attributes['aria-role'] = el.getAttribute('aria-role');
                            if (el.getAttribute('role')) attributes.role = el.getAttribute('role');
                            if (el.getAttribute('data-semantics-role')) attributes['data-semantics-role'] = el.getAttribute('data-semantics-role');
                            if (el.getAttribute('flt-semantic-role')) attributes['flt-semantic-role'] = el.getAttribute('flt-semantic-role');
                            
                            elements.push({{
                                index: index,
                                tagName: el.tagName.toLowerCase(),
                                selector: selector,
                                textContent: textContent,
                                attributes: attributes,
                                position: {{
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }},
                                isVisible: isVisible,
                                className: el.className,
                                id: el.id || null
                            }});
                        }}
                    }});
                    
                    return {{
                        elements: elements,
                        totalCount: elements.length,
                        visibleCount: elements.filter(el => el.isVisible).length,
                        pageTitle: document.title,
                        pageUrl: window.location.href,
                        viewport: {{
                            width: window.innerWidth,
                            height: window.innerHeight
                        }}
                    }};
                }}
                """
                
                # Execute the JavaScript
                result = await page.evaluate(js_code)
                
                # Page remains persistent for next actions
                
                execution_time = int((time.time() - start_time) * 1000)
                
                print(f"[PLAYWRIGHT]: Found {result['totalCount']} elements ({result['visibleCount']} visible)")
                
                return {
                    'success': True,
                    'elements': result['elements'],
                    'summary': {
                        'total_count': result['totalCount'],
                        'visible_count': result['visibleCount'],
                        'page_title': result['pageTitle'],
                        'page_url': result['pageUrl'],
                        'viewport': result['viewport'],
                        'element_types': element_types,
                        'include_hidden': include_hidden
                    },
                    'execution_time': execution_time,
                    'error': ''
                }
                
            except Exception as e:
                error_msg = f"Dump elements error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elements': [],
                    'summary': {}
                }
        
        # Assume Chrome is running - no connection checks
        return self.utils.run_async(_async_dump_elements())
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions for Playwright web controller."""
        return {
            'Web': [
                # Browser management
                {
                    'id': 'open_browser',
                    'label': 'Open Browser',
                    'command': 'open_browser',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Open the browser window',
                    'requiresInput': False
                },
                {
                    'id': 'close_browser',
                    'label': 'Close Browser',
                    'command': 'close_browser',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Close the browser window',
                    'requiresInput': False
                },
                {
                    'id': 'connect_browser',
                    'label': 'Connect Browser',
                    'command': 'connect_browser',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Connect to existing Chrome debug session',
                    'requiresInput': False
                },
                # Navigation
                {
                    'id': 'navigate_to_url',
                    'label': 'Navigate to URL',
                    'command': 'navigate_to_url',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Navigate to a specific URL',
                    'requiresInput': True,
                    'inputLabel': 'URL',
                    'inputPlaceholder': 'https://google.com'
                },
                # Element interaction
                {
                    'id': 'click_element',
                    'label': 'Click Element',
                    'command': 'click_element',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Click an element by CSS selector or text',
                    'requiresInput': True,
                    'inputLabel': 'Selector or text',
                    'inputPlaceholder': '#submit-button or "Submit"'
                },
                {
                    'id': 'find_element',
                    'label': 'Find Element',
                    'command': 'find_element',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Find an element by CSS selector, text, or aria-label',
                    'requiresInput': True,
                    'inputLabel': 'Selector or text',
                    'inputPlaceholder': 'TV Guide or #flt-semantic-node-6'
                },
                {
                    'id': 'hover_element',
                    'label': 'Hover Element',
                    'command': 'hover_element',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Hover over an element to trigger rollover effects',
                    'requiresInput': True,
                    'inputLabel': 'Selector or text',
                    'inputPlaceholder': '#player-controls or Play Button'
                },
                {
                    'id': 'input_text',
                    'label': 'Input Text',
                    'command': 'input_text',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Type text into an input field',
                    'requiresInput': True,
                    'inputLabel': 'CSS selector and text (comma separated)',
                    'inputPlaceholder': '#username,myusername'
                },
                {
                    'id': 'tap_x_y',
                    'label': 'Click Coordinates',
                    'command': 'tap_x_y',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Click at specific coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                # JavaScript execution
                {
                    'id': 'execute_javascript',
                    'label': 'Execute JavaScript',
                    'command': 'execute_javascript',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Execute custom JavaScript code',
                    'requiresInput': True,
                    'inputLabel': 'JavaScript code',
                    'inputPlaceholder': 'alert("Hello World")'
                },
                # Page information
                {
                    'id': 'get_page_info',
                    'label': 'Get Page Info',
                    'command': 'get_page_info',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Get current page URL and title',
                    'requiresInput': False
                },
                # Flutter web specific
                {
                    'id': 'activate_semantic',
                    'label': 'Activate Semantic',
                    'command': 'activate_semantic',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Activate semantic for Flutter web apps',
                    'requiresInput': False
                },
                # Element inspection
                {
                    'id': 'dump_elements',
                    'label': 'Dump Page Elements',
                    'command': 'dump_elements',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Get all visible elements on the page',
                    'requiresInput': False
                },
                # AI-powered browser automation
                {
                    'id': 'browser_use_task',
                    'label': 'AI Browser Task',
                    'command': 'browser_use_task',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Execute a complex browser task using AI',
                    'requiresInput': True,
                    'inputLabel': 'Task description',
                    'inputPlaceholder': 'Search for Python tutorials on Google'
                },
                # Keyboard controls
                {
                    'id': 'press_key_back',
                    'label': 'Back',
                    'command': 'press_key',
                    'action_type': 'web',
                    'params': {'key': 'BACK'},
                    'description': 'Press Escape key (browser back)',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_ok',
                    'label': 'OK',
                    'command': 'press_key',
                    'action_type': 'web',
                    'params': {'key': 'OK'},
                    'description': 'Press Enter key (confirm)',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_esc',
                    'label': 'Esc',
                    'command': 'press_key',
                    'action_type': 'web',
                    'params': {'key': 'ESCAPE'},
                    'description': 'Press Escape key (cancel)',
                    'requiresInput': False
                }
            ]
        }