"""
Playwright Web Controller Implementation

This controller provides web browser automation functionality using Playwright SYNC API.
Key features: Chrome remote debugging, sync Playwright for thread safety (no async complexity).
Uses playwright_utils for Chrome management.
"""

# =============================================================================
# GLOBAL BROWSER ENGINE CONFIGURATION
# =============================================================================
# Change this to switch between browsers easily:
# - "chromium" = Full Chrome browser (default, ~170MB, high memory)
# - "webkit"   = Safari/WebKit engine (lightweight, ~50MB, low memory)
BROWSER_ENGINE = "webkit"  # <-- Change this line to switch browsers
# =============================================================================

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, Tuple, List

# =============================================================
# Single decorator to guarantee execution on controller loop
# =============================================================
def ensure_controller_loop(func):
    async def wrapper(self, *args, **kwargs):
        import asyncio
        # Ensure controller loop exists
        self._ensure_loop()
        controller_loop = self.__class__._loop
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if current_loop is controller_loop:
            return await func(self, *args, **kwargs)
        fut = self._submit_to_controller_loop(func(self, *args, **kwargs))
        if current_loop is None:
            return fut.result()
        return await asyncio.wrap_future(fut)
    return wrapper
from ..base_controller import WebControllerInterface

# Use absolute import for utils from shared library
import sys
import os
# Get path to shared/lib/utils
shared_utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'shared', 'lib', 'utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)

from  backend_host.src.lib.utils.playwright_utils import PlaywrightUtils
from  backend_host.src.lib.utils.webkit_utils import WebKitUtils
# Import browseruse_utils only when needed to avoid browser_use dependency at module load
# from  backend_host.src.lib.utils.browseruse_utils import BrowserUseManager

# Import verification mixin
from .playwright_verifications import PlaywrightVerificationsMixin


class PlaywrightWebController(PlaywrightVerificationsMixin, WebControllerInterface):
    """Playwright web controller using async Playwright with sync wrappers for browser-use compatibility."""
    
    # Class-level Chrome process management
    _chrome_process = None
    _chrome_running = False
    
    # Class-level persistent Playwright browser and context (reuse)
    _playwright = None
    _browser = None
    _context = None
    _browser_connected = False
    
    # Dedicated controller event loop (single place for all Playwright ops)
    _loop = None
    _loop_thread = None
    
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
            print(f"[@controller:PlaywrightWeb] Initialized with lightweight WebKit browser (global setting, SYNC API)")
        else:
            self.utils = PlaywrightUtils(auto_accept_cookies=True, use_cgroup=False)
            print(f"[@controller:PlaywrightWeb] Initialized with Chromium browser (global setting, cgroup disabled, SYNC API)")
        
        # Command execution state
        self.last_command_output = ""
        self.last_command_error = ""
        self.current_url = ""
        self.page_title = ""

    # =============================================================
    # Controller loop management (single long-lived asyncio loop)
    # =============================================================
    def _ensure_loop(self):
        """Ensure a dedicated event loop thread exists for Playwright ops."""
        if self.__class__._loop and self.__class__._loop_thread and self.__class__._loop_thread.is_alive():
            return
        import threading, asyncio
        def _loop_worker():
            loop = asyncio.new_event_loop()
            self.__class__._loop = loop
            asyncio.set_event_loop(loop)
            loop.run_forever()
        t = threading.Thread(target=_loop_worker, name="PlaywrightControllerLoop", daemon=True)
        t.start()
        self.__class__._loop_thread = t
        # Give the loop a brief moment to start
        import time as _time
        start = _time.time()
        while self.__class__._loop is None and (_time.time() - start) < 1.0:
            _time.sleep(0.01)
    
    def _submit_to_controller_loop(self, coro):
        """Submit a coroutine to the controller loop and return a concurrent.futures.Future."""
        self._ensure_loop()
        import asyncio
        return asyncio.run_coroutine_threadsafe(coro, self.__class__._loop)

    # _redirect_if_needed removed; unified with @ensure_controller_loop

    def _reset_state(self):
        """Reset class-level persistent browser state flags and references."""
        self.__class__._playwright = None
        self.__class__._browser = None
        self.__class__._context = None
        self.__class__._browser_connected = False
    
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
    
    @ensure_controller_loop
    async def _get_persistent_page(self, target_url: str = None):
        """Get the persistent page from browser+context, creating/connecting if needed."""
        # Ensure we have a connected browser/context
        # Prefer concrete browser/context objects over boolean flags to avoid stale state
        if not self.__class__._browser or not self.__class__._context:
            # Try to establish a connection (does NOT kill Chrome)
            connect_result = await self.connect_browser()
            if not connect_result or not connect_result.get('success'):
                raise RuntimeError(f"Unable to get persistent page: connect_browser failed: {connect_result.get('error') if isinstance(connect_result, dict) else 'unknown error'}")

        context = self.__class__._context
        if context is None:
            raise RuntimeError("Unable to get persistent page: browser context is not available")

        # Reuse first page if any, else create a new page
        try:
            pages = context.pages
            if pages and len(pages) > 0:
                page = pages[0]
            else:
                page = await context.new_page()
        except Exception as e:
            raise RuntimeError(f"Failed to acquire page from context: {type(e).__name__}: {str(e)}")

        return page
    
    async def _cleanup_persistent_browser(self):
        """Clean up persistent browser+context."""
        print(f"[PLAYWRIGHT]: Cleaning up persistent browser+context...")
        try:
            if self.__class__._browser:
                await self.__class__._browser.close()
        except Exception as e:
            print(f"[PLAYWRIGHT]: Browser close error ignored: {type(e).__name__}: {str(e)}")
        try:
            if self.__class__._playwright:
                await self.__class__._playwright.stop()
        except Exception as e:
            print(f"[PLAYWRIGHT]: Playwright stop error ignored: {type(e).__name__}: {str(e)}")
        
        # Kill Chrome process started via ChromeManager
        try:
            if self.__class__._chrome_process:
                self.utils.kill_chrome(chrome_process=self.__class__._chrome_process)
        except Exception as e:
            print(f"[PLAYWRIGHT]: Chrome kill error ignored: {type(e).__name__}: {str(e)}")
        
        # Reset flags/state
        self.__class__._playwright = None
        self.__class__._browser = None
        self.__class__._context = None
        self.__class__._browser_connected = False
        self.__class__._chrome_process = None
        self.__class__._chrome_running = False
        print(f"[PLAYWRIGHT]: Persistent browser+context cleaned up and Chrome process terminated")

    async def _cleanup_persistent_browser_with_timeout(self, timeout_seconds: int = 10):
        """Cleanup wrapper that enforces a timeout so it never blocks navigation."""
        import asyncio
        try:
            await asyncio.wait_for(self._cleanup_persistent_browser(), timeout=timeout_seconds)
        except Exception as e:
            print(f"[PLAYWRIGHT]: Cleanup timed out or failed: {type(e).__name__}: {str(e)}")
    
    @ensure_controller_loop
    async def connect(self) -> bool:
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
                self.__class__._chrome_running = True
                print(f"[PLAYWRIGHT]: {browser_name} launched with remote debugging successfully (PID: {self._chrome_process.pid})")
                
                await asyncio.sleep(2)
                print(f"[PLAYWRIGHT]: {browser_name} startup delay completed")
                
            except Exception as e:
                error_type = type(e).__name__
                print(f"[PLAYWRIGHT]: Failed to launch {browser_name} - {error_type}: {str(e)}")
                return False
        else:
            print(f"[PLAYWRIGHT]: {browser_name} process already running (PID: {self._chrome_process.pid if self._chrome_process else 'unknown'})")
        
        print(f"[PLAYWRIGHT]: connect() completed - running={self._chrome_running}, is_connected={self.is_connected}")
        return True
    

    
    @ensure_controller_loop
    async def open_browser(self) -> Dict[str, Any]:
        """Open/launch the browser window. Simple: connect or kill+restart."""
        try:
            print(f"[PLAYWRIGHT]: Opening browser - connect or kill+restart approach")
            start_time = time.time()
            
            # Simple approach: try to connect, if fails kill and restart
            try:
                # Try to connect to existing Chrome or launch new one
                if not self.is_connected:
                    print(f"[PLAYWRIGHT]: Chrome not running, launching...")
                await self.connect()
                
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
                await self.connect()
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
                    'connected': True,
                    'current_url': self.current_url,
                    'page_title': self.page_title,
                    'reused_connection': True
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
        
    @ensure_controller_loop
    async def connect_browser(self) -> Dict[str, Any]:
        """Connect to existing Chrome debug session without killing Chrome first.
        OPTIMIZED: Skip reconnection if already connected, skip sleep if Chrome already running.
        """
        import asyncio  # ✅ Import asyncio at the start of the method
        try:
            start_time = time.time()
            
            # ✅ OPTIMIZATION 1: Check if already connected - skip reconnection
            if self.__class__._chrome_running and self.__class__._browser_connected and self.__class__._browser and self.__class__._context:
                print(f"[PLAYWRIGHT]: Already connected to Chrome (PID: {self.__class__._chrome_process.pid if self.__class__._chrome_process else 'unknown'}), reusing connection")
                
                # Verify by accessing context/pages directly (avoid circular _get_persistent_page call)
                try:
                    context = self.__class__._context
                    pages = context.pages
                    page = pages[0] if pages and len(pages) > 0 else await context.new_page()
                    self.current_url = page.url
                    self.page_title = await page.title() if page.url != 'about:blank' else ''
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    print(f"[PLAYWRIGHT]: Reused existing connection (verified via context/pages)")
                    return {
                        'success': True,
                        'error': '',
                        'execution_time': execution_time,
                        'connected': True,
                        'current_url': self.current_url,
                        'page_title': self.page_title,
                        'reused_connection': True
                    }
                except Exception as verify_error:
                    print(f"[PLAYWRIGHT]: Connection verification failed ({verify_error}), will reconnect...")
                    # Fall through to reconnection logic
            
            print(f"[PLAYWRIGHT]: Connecting to Chrome debug session")
            
            # ✅ OPTIMIZATION 2: Track if Chrome was already running before connect()
            chrome_was_already_running = self.__class__._chrome_running
            
            # Try to connect to existing Chrome debug session (no killing Chrome first)
            try:
                # For existing Chrome, just connect without creating new context
                self.__class__._playwright, self.__class__._browser, self.__class__._context, page = await self.utils.connect_to_chrome()
                self.__class__._browser_connected = True
                
                # Get current page info from persistent page
                self.current_url = page.url
                self.page_title = await page.title() if page.url != 'about:blank' else ''
                
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
                    connect_result = await self.connect()
                    if not connect_result:
                        raise Exception("Failed to launch Chrome")
                    
                    # ✅ OPTIMIZATION 3: Only sleep if we JUST launched Chrome (not already running)
                    if not chrome_was_already_running:
                        print(f"[PLAYWRIGHT]: Chrome was just launched, waiting 5s for initialization...")
                        await asyncio.sleep(5)
                    else:
                        print(f"[PLAYWRIGHT]: Chrome was already running, skipping initialization delay")
                    
                    # Now connect to the Chrome debug session to get browser/context/page
                    self.__class__._playwright, self.__class__._browser, self.__class__._context, page = await self.utils.connect_to_chrome()
                    self.__class__._browser_connected = True
                    
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
                        'launched_new': not chrome_was_already_running
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
    
    def close_browser(self) -> Dict[str, Any]:
        """Schedule async cleanup without blocking the navigation thread."""
        print(f"[PLAYWRIGHT]: Scheduling non-blocking browser cleanup")
        # Pre-emptively mark disconnected so next actions reconnect if needed
        self.__class__._browser_connected = False
        scheduled = False
        try:
            # Ensure cleanup runs on the controller loop where Playwright objects live
            fut = self._submit_to_controller_loop(self._cleanup_persistent_browser_with_timeout(10))
            scheduled = True
        except RuntimeError:
            # No running loop (unlikely since execute_command is async) - best effort fallback: do nothing blocking
            print(f"[PLAYWRIGHT]: No running asyncio loop; skipping async cleanup scheduling")
        return {
            'success': True,
            'error': '',
            'execution_time': 0,
            'connected': False,
            'scheduled_async_cleanup': scheduled
        }
    
    @ensure_controller_loop
    async def navigate_to_url(self, url: str, timeout: int = 60000, follow_redirects: bool = True) -> Dict[str, Any]:
        """Navigate to a URL."""
        start_time = time.time()
        try:
            normalized_url = self.utils.normalize_url(url)
            print(f"[PLAYWRIGHT]: Navigating to {url} (normalized: {normalized_url}) with timeout {timeout}ms")

            page = await self._get_persistent_page(target_url=normalized_url)
            
            # Wait for basic page load only - verifications will check readiness
            await page.goto(normalized_url, timeout=timeout, wait_until='load')
            
            self.current_url = page.url
            self.page_title = await page.title()
            
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
        
    @ensure_controller_loop
    async def click_element(self, element_id: str) -> Dict[str, Any]:
        """Click an element using dump-first approach (like Android mobile).
        Supports pipe-separated fallback: "Settings|Preferences|Options"
        
        Args:
            element_id: Element text, CSS selector, or aria-label to search for (unified with Android parameter name)
                        Can use pipe "|" to specify multiple options (tries each until one succeeds)
        """
        try:
            print(f"[PLAYWRIGHT]: Clicking element using dump-first approach: {element_id}")
            start_time = time.time()
            
            # Parse pipe-separated terms for fallback support
            terms = [t.strip() for t in element_id.split('|')] if '|' in element_id else [element_id]
            
            if len(terms) > 1:
                print(f"[PLAYWRIGHT]: Using fallback strategy with {len(terms)} terms: {terms}")
            
            # Try each term until one succeeds
            last_error = None
            for i, term in enumerate(terms):
                if len(terms) > 1:
                    print(f"[PLAYWRIGHT]: Attempt {i+1}/{len(terms)}: Searching for '{term}'")
                
                # Step 1: Find element using dump-first (same as Android mobile)
                find_result = await self.find_element(term)
                
                if not find_result.get('success'):
                    last_error = f"Element not found: {find_result.get('error', 'Unknown error')}"
                    if len(terms) > 1:
                        print(f"[PLAYWRIGHT]: Term '{term}' not found, trying next...")
                    continue
                
                # Step 2: Click the found element using coordinates (like Android mobile)
                element_info = find_result.get('element_info', {})
                position = element_info.get('position', {})
                
                if not position or 'x' not in position:
                    last_error = f"Element found but no coordinates available"
                    if len(terms) > 1:
                        print(f"[PLAYWRIGHT]: Term '{term}' found but no coordinates, trying next...")
                    continue
                
                # Calculate center coordinates
                center_x = position['x'] + (position.get('width', 0) / 2)
                center_y = position['y'] + (position.get('height', 0) / 2)
                
                # Log with element_id for consistency
                found_element_id = element_info.get('element_id', 'unknown')
                matched_value = element_info.get('matched_value', '')
                print(f"[PLAYWRIGHT]: Found element (ID={found_element_id}, value='{matched_value}'), clicking at coordinates ({center_x:.0f}, {center_y:.0f})")
                
                # Step 3: Click using coordinates (reuse tap_x_y logic)
                tap_result = await self.tap_x_y(int(center_x), int(center_y))
                
                if tap_result.get('success'):
                    execution_time = int((time.time() - start_time) * 1000)
                    if len(terms) > 1:
                        print(f"[PLAYWRIGHT]: Click successful using term '{term}'")
                    else:
                        print(f"[PLAYWRIGHT]: Click successful using dump-first approach")
                    return {
                        'success': True,
                        'error': '',
                        'execution_time': execution_time,
                        'method': 'dump_search_click',
                        'coordinates': {'x': int(center_x), 'y': int(center_y)},
                        'element_info': element_info
                    }
                else:
                    last_error = f"Element found but click failed: {tap_result.get('error', 'Unknown error')}"
                    if len(terms) > 1:
                        print(f"[PLAYWRIGHT]: Term '{term}' click failed, trying next...")
                    continue
            
            # All terms failed
            execution_time = int((time.time() - start_time) * 1000)
            print(f"[PLAYWRIGHT]: All terms failed. Last error: {last_error}")
            return {
                'success': False,
                'error': last_error or 'Element not found',
                'execution_time': execution_time
            }
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"Click error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': execution_time,
                'selector_attempted': element_id
            }
    
    @ensure_controller_loop
    async def hover_element(self, selector: str) -> Dict[str, Any]:
        """Hover over an element to trigger rollover effects.
        
        Args:
            selector: CSS selector, or text content to search for
        """
        try:
            print(f"[PLAYWRIGHT]: Hovering over element: {selector}")
            start_time = time.time()
            
            # Get persistent page from browser+context
            page = await self._get_persistent_page()
            
            # Try same selectors as click
            selectors_to_try = [
                selector,
                f"[aria-label='{selector}']",
                f"[flt-semantics[aria-label='{selector}']",
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
        
    @ensure_controller_loop
    async def find_element(self, selector: str) -> Dict[str, Any]:
        """Find an element by searching within dumped elements (like Android mobile).
        
        Args:
            selector: CSS selector, text content, or aria-label to search for
        """
        try:
            print(f"[PLAYWRIGHT]: Finding element using dump-first approach: {selector}")
            start_time = time.time()
            
            # Step 1: Dump all elements first (like Android mobile)
            dump_result = await self.dump_elements()
            
            if not dump_result.get('success'):
                execution_time = int((time.time() - start_time) * 1000)
                error_msg = f"Failed to dump elements: {dump_result.get('error', 'Unknown error')}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                }
            
            elements = dump_result.get('elements', [])
            print(f"[PLAYWRIGHT]: Searching within {len(elements)} dumped elements")
            
            # DEBUG: Log first 20 elements for verification
            print(f"[PLAYWRIGHT]: === DUMPED ELEMENTS (first 20 of {len(elements)}) ===")
            for i, el in enumerate(elements[:20]):
                # Clean up text: remove extra whitespace/newlines and limit to 50 chars
                raw_text = el.get('textContent', '').strip()
                clean_text = ' '.join(raw_text.split())  # Remove all extra whitespace
                display_text = clean_text[:50] + '...' if len(clean_text) > 50 else clean_text
                
                aria = el.get('attributes', {}).get('aria-label', '').strip()
                selector = el.get('selector', '')
                
                print(f"[PLAYWRIGHT]:   {i+1}. {el.get('tagName', 'unknown')} - text: '{display_text}' - aria: '{aria}' - selector: '{selector}'")
            if len(elements) > 20:
                print(f"[PLAYWRIGHT]:   ... and {len(elements) - 20} more elements")
            print(f"[PLAYWRIGHT]: === END DUMPED ELEMENTS ===")
            
            # Step 2: Search within dumped elements (same logic as Android mobile)
            matches = self._search_dumped_elements(selector, elements)
            
            if matches:
                # Found element - return coordinates like Android mobile does
                first_match = matches[0]
                execution_time = int((time.time() - start_time) * 1000)
                
                # Log with element_id like click_element does
                element_id = first_match.get('element_id', 'unknown')
                matched_value = first_match.get('matched_value', '')
                print(f"[PLAYWRIGHT]: Element found in dump: {first_match['match_reason']} (ID={element_id}, value='{matched_value}')")
                return {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time,
                    'result': {  # Use 'result' key like clicks do for frontend compatibility
                        'x': first_match['position']['x'],
                        'y': first_match['position']['y'], 
                        'width': first_match['position']['width'],
                        'height': first_match['position']['height']
                    },
                    'element_info': first_match,
                    'method': 'dump_search'
                }
            else:
                execution_time = int((time.time() - start_time) * 1000)
                error_msg = f"Element '{selector}' not found in {len(elements)} dumped elements"
                print(f"[PLAYWRIGHT]: {error_msg}")
                
                # Log available elements for debugging (like Android mobile does)
                print(f"[PLAYWRIGHT]: Available elements:")
                for i, el in enumerate(elements[:10]):  # Show first 10
                    # Clean up text: remove extra whitespace/newlines and limit to 40 chars
                    raw_text = el.get('textContent', '').strip()
                    clean_text = ' '.join(raw_text.split())
                    display_text = clean_text[:40] + '...' if len(clean_text) > 40 else clean_text
                    aria = el.get('attributes', {}).get('aria-label', '').strip()
                    print(f"[PLAYWRIGHT]:   {i+1}. {el.get('tagName', 'unknown')} - text: '{display_text}' - aria: '{aria}'")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                }
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"Find error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': execution_time,
                'selector_attempted': selector
            }
    
    def _search_dumped_elements(self, search_term: str, elements: list) -> list:
        """Search within dumped elements with smart prioritization (exact matches first)."""
        search_lower = search_term.strip().lower()
        exact_matches = []
        partial_matches = []
        
        for element in elements:
            element_matches = []
            is_exact = False
            
            # Check textContent (like Android mobile text attribute)
            text_content = element.get('textContent', '').strip()
            if text_content:
                if text_content.lower() == search_lower:
                    # Exact match - highest priority
                    element_matches.append({
                        "attribute": "textContent",
                        "value": text_content,
                        "reason": f"Exact match '{search_term}' in text content",
                        "priority": 1
                    })
                    is_exact = True
                elif search_lower in text_content.lower():
                    # Partial match - lower priority
                    element_matches.append({
                        "attribute": "textContent",
                        "value": text_content,
                        "reason": f"Contains '{search_term}' in text content",
                        "priority": 2
                    })
            
            # Check aria-label (like Android mobile content_desc)
            aria_label = element.get('attributes', {}).get('aria-label', '').strip()
            if aria_label:
                if aria_label.lower() == search_lower:
                    element_matches.append({
                        "attribute": "aria-label", 
                        "value": aria_label,
                        "reason": f"Exact match '{search_term}' in aria-label",
                        "priority": 1
                    })
                    is_exact = True
                elif search_lower in aria_label.lower():
                    element_matches.append({
                        "attribute": "aria-label", 
                        "value": aria_label,
                        "reason": f"Contains '{search_term}' in aria-label",
                        "priority": 2
                    })
            
            # Check selector/id (like Android mobile resource_id)
            selector = element.get('selector', '').strip()
            if selector and search_lower in selector.lower():
                element_matches.append({
                    "attribute": "selector",
                    "value": selector,
                    "reason": f"Contains '{search_term}' in selector",
                    "priority": 3
                })
            
            # Check className (like Android mobile class_name)
            class_name = element.get('className', '').strip()
            if class_name and search_lower in class_name.lower():
                element_matches.append({
                    "attribute": "className",
                    "value": class_name,
                    "reason": f"Contains '{search_term}' in class name",
                    "priority": 3
                })
            
            # If matches found, add to results with prioritization
            if element_matches:
                primary_match = element_matches[0]
                element_index = element.get('index', 0)
                
                match_info = {
                    "element_id": f"element_{element_index}",  # Add element_id like Android does
                    "element_index": element_index,
                    "matched_attribute": primary_match["attribute"],
                    "matched_value": primary_match["value"],
                    "match_reason": primary_match["reason"],
                    "search_term": search_term,
                    "position": element.get('position', {}),
                    "selector": element.get('selector', ''),
                    "full_element": element,
                    "priority": primary_match["priority"]
                }
                
                # Separate exact and partial matches
                if is_exact:
                    exact_matches.append(match_info)
                else:
                    partial_matches.append(match_info)
        
        # Return exact matches first, then partial matches
        # Also sort by text length (shorter = more specific) within each category
        exact_matches.sort(key=lambda x: len(x["matched_value"]))
        partial_matches.sort(key=lambda x: len(x["matched_value"]))
        
        return exact_matches + partial_matches
    
    @ensure_controller_loop
    async def input_text(self, selector: str, text: str, wait_time: int = 200) -> Dict[str, Any]:
        """Input text into an element."""
        try:
            print(f"[PLAYWRIGHT]: Inputting text to: {selector}")
            start_time = time.time()
            
            # Get persistent page from browser+context
            page = await self._get_persistent_page()
            
                # Input text
            await page.fill(selector, text)
                
            await asyncio.sleep(wait_time / 1000)
            
            result = {
                'success': True,
                'error': '',
            'execution_time': int((time.time() - start_time) * 1000)
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
        
    @ensure_controller_loop
    async def tap_x_y(self, x: int, y: int) -> Dict[str, Any]:
        """Tap/click at specific coordinates."""
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
            print(f"[PLAYWRIGHT]: Connection state - is_connected: {self.is_connected}, _chrome_running: {self.__class__._chrome_running}, _browser_connected: {self.__class__._browser_connected}")
            
            return {
                'success': False,
                'error': error_msg,
                'error_type': error_type,
                'error_details': str(e),
                'connection_state': {
                    'is_connected': self.is_connected,
                    'chrome_running': self.__class__._chrome_running,
                    'browser_connected': self.__class__._browser_connected
                },
                'execution_time': 0
            }
        
    @ensure_controller_loop
    async def execute_javascript(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript code in the page."""
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
    
    @ensure_controller_loop
    async def get_page_info(self) -> Dict[str, Any]:
        """Get current page information."""
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
        
    @ensure_controller_loop
    async def activate_semantic(self) -> Dict[str, Any]:
        """Activate semantic placeholder for Flutter web apps."""
        script = """
        (() => {
            // Try new structure first (Flutter 3.x+): direct DOM element
            let element = document.querySelector('flt-semantics-placeholder');
            if (element) {
                console.log('[Flutter] Found flt-semantics-placeholder in direct DOM (new structure)');
                element.click();
                return {success: true, structure: 'direct-dom'};
            }
            
            // Try old structure: inside shadow DOM
            const shadowHost = document.querySelector('body > flutter-view > flt-glass-pane');
            if (shadowHost && shadowHost.shadowRoot) {
                element = shadowHost.shadowRoot.querySelector('flt-semantics-placeholder');
                if (element) {
                    console.log('[Flutter] Found flt-semantics-placeholder in shadow DOM (old structure)');
                    element.click();
                    return {success: true, structure: 'shadow-dom'};
                }
            }
            
            // Try alternative direct selector
            element = document.querySelector('body > flt-semantics-placeholder');
            if (element) {
                console.log('[Flutter] Found flt-semantics-placeholder as body child');
                element.click();
                return {success: true, structure: 'body-child'};
            }
            
            console.log('[Flutter] flt-semantics-placeholder not found in any structure');
            return {success: false, structure: 'not-found'};
        })()
        """
        
        # Try once, if fails wait 1s and retry with connection check
        result = await self.execute_javascript(script)
        if not result.get('success'):
            print(f"[PLAYWRIGHT]: First activate_semantic failed ({result.get('error', 'unknown')}), retrying in 1s...")
            import asyncio
            await asyncio.sleep(1)
            # Check if connection issue and try to recover
            if 'Connection closed' in str(result.get('error', '')):
                print(f"[PLAYWRIGHT]: Connection issue detected, attempting recovery...")
                self.__class__._browser_connected = False  # Force reconnection
            result = await self.execute_javascript(script)
        
        # Log the structure found
        if result.get('success') and result.get('result'):
            js_result = result.get('result', {})
            if isinstance(js_result, dict):
                structure = js_result.get('structure', 'unknown')
                print(f"[PLAYWRIGHT]: Semantic activated using {structure} structure")
        
        result['success'] = True  # Always succeed since this is optional
        return result
    
    @ensure_controller_loop
    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press keyboard key.
        
        Args:
            key: Key to press ('BACK', 'ESCAPE', 'ENTER', 'OK', etc.)
        """
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
        
    @ensure_controller_loop
    async def scroll(self, direction: str, amount: int = 300) -> Dict[str, Any]:
        """Scroll the page in a specific direction.
        
        Args:
            direction: Direction to scroll ('up', 'down', 'left', 'right')
            amount: Number of pixels to scroll (default 300)
        """
        try:
            print(f"[PLAYWRIGHT]: Scrolling {direction} by {amount}px")
            start_time = time.time()
            
            # Get persistent page from browser+context
            page = await self._get_persistent_page()
            
            # Map direction to scroll deltas
            direction_map = {
                'up': (0, -amount),
                'down': (0, amount),
                'left': (-amount, 0),
                'right': (amount, 0)
            }
            
            if direction.lower() not in direction_map:
                return {
                    'success': False,
                    'error': f"Invalid direction '{direction}'. Use 'up', 'down', 'left', or 'right'",
                    'execution_time': 0
                }
            
            delta_x, delta_y = direction_map[direction.lower()]
            
            # Execute scroll using mouse wheel
            await page.mouse.wheel(delta_x, delta_y)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            result = {
                'success': True,
                'error': '',
                'execution_time': execution_time,
                'direction': direction,
                'amount': amount,
                'delta_x': delta_x,
                'delta_y': delta_y
            }
            
            print(f"[PLAYWRIGHT]: Scroll successful: {direction} {amount}px")
            return result
            
        except Exception as e:
            error_msg = f"Scroll error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': 0,
                'direction': direction,
                'amount': amount
            }
    
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
    
    @ensure_controller_loop
    async def browser_use_task(self, task: str, max_steps: int = 20) -> Dict[str, Any]:
        """Execute browser-use task using existing Chrome instance on controller loop.
        
        Args:
            task: Task description for browser-use
            max_steps: Maximum steps for browser-use agent (default: 20)
        """
        try:
            print(f"[PLAYWRIGHT]: Executing browser-use task: {task} (max_steps={max_steps})")
            start_time = time.time()
            
            # Import browseruse_utils only when needed
            try:
                from backend_host.src.lib.utils.browseruse_utils import BrowserUseManager
            except ImportError as e:
                return {
                    'success': False,
                    'error': f'Browser-use not available: {e}',
                    'task': task,
                    'execution_time': 0
                }
            
            # Create browser-use manager with our utils
            manager = BrowserUseManager(self.utils)
            
            # Execute task (already runs on controller loop via @ensure_controller_loop)
            result = await manager.execute_task(task, max_steps=max_steps)
            
            execution_time = int((time.time() - start_time) * 1000)
            print(f"[PLAYWRIGHT]: Browser-use task completed in {execution_time}ms")
            
            return result
            
        except Exception as e:
            error_msg = f"Browser-use task error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': error_msg,
                'task': task,
                'execution_time': int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
            }
        
    async def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute web automation command with JSON parameters.
        
        Args:
            command: Command to execute
            params: JSON parameters for the command
            
        Returns:
            Dict: Command execution result
        """
        # Thread ownership no longer needed with sync API!

        if params is None:
            params = {}
        
        import threading, asyncio
        print(f"[PLAYWRIGHT]: Executing command '{command}' with params: {params} (thread={threading.current_thread().name})")

        # Ensure we always execute Playwright ops on the controller loop to avoid loop-affinity issues
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        controller_loop = self.__class__._loop
        if controller_loop is None:
            # Initialize loop lazily
            self._ensure_loop()
            controller_loop = self.__class__._loop
        
        # If we're NOT on the controller loop, resubmit this call onto the controller loop and await its result
        if current_loop is None or current_loop is not controller_loop:
            fut = self._submit_to_controller_loop(self.execute_command(command, params))
            if current_loop is None:
                # If no running loop (unlikely inside async), block and return result
                return fut.result()
            else:
                # Bridge concurrent.futures.Future to awaitable in current loop
                return await asyncio.wrap_future(fut)
        
        # ============== From here on, we are on the controller loop ==============
        if command == 'navigate_to_url':
            url = params.get('url')
            # Use wait_time (standard action param) OR timeout (legacy) with default fallback
            timeout = params.get('wait_time') or params.get('timeout', 30000)
            follow_redirects = params.get('follow_redirects', True)
            
            if not url:
                return {
                    'success': False,
                    'error': 'URL parameter is required',
                    'execution_time': 0
                }
                
            return await self.navigate_to_url(url, timeout=timeout, follow_redirects=follow_redirects)
        
        elif command == 'click_element':
            element_id = params.get('element_id') or params.get('selector')  # Support both for backward compatibility during transition
            
            if not element_id:
                return {
                    'success': False,
                    'error': 'element_id parameter is required',
                    'execution_time': 0
                }
                
            return await self.click_element(element_id)
        
        elif command == 'find_element':
            selector = params.get('selector')
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return await self.find_element(selector)
        
        elif command == 'hover_element':
            selector = params.get('selector')
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return await self.hover_element(selector)
        
        elif command == 'input_text':
            selector = params.get('selector')
            text = params.get('text', '')
            timeout = params.get('timeout', 3000)
            
            if not selector:
                return {
                    'success': False,
                    'error': 'selector parameter is required',
                    'execution_time': 0
                }
                
            return await self.input_text(selector, text, wait_time=timeout)
        
        elif command == 'tap_x_y':
            x = params.get('x')
            y = params.get('y')
            
            if x is None or y is None:
                return {
                    'success': False,
                    'error': 'X and Y coordinates are required',
                    'execution_time': 0
                }
                
            return await self.tap_x_y(x, y)
        
        elif command == 'execute_javascript':
            script = params.get('script')
            
            if not script:
                return {
                    'success': False,
                    'error': 'Script parameter is required',
                    'execution_time': 0
                }
                
            return await self.execute_javascript(script)
        
        elif command == 'get_page_info':
            return await self.get_page_info()
        
        elif command == 'activate_semantic':
            return await self.activate_semantic()
        
        elif command == 'open_browser':
            return await self.open_browser()
        
        elif command == 'close_browser':
            return self.close_browser()  # Returns success but doesn't actually close
        
        elif command == 'connect_browser':
            return await self.connect_browser()
        
        elif command == 'dump_elements':
            element_types = params.get('element_types', 'all')
            include_hidden = params.get('include_hidden', False)
            return await self.dump_elements(element_types=element_types, include_hidden=include_hidden)
        
        elif command == 'browser_use_task':
            task = params.get('task', '')
            max_steps = params.get('max_steps', 20)
            
            if not task:
                return {
                    'success': False,
                    'error': 'Task parameter is required',
                    'execution_time': 0
                }
            
            return await self.browser_use_task(task, max_steps=max_steps)
        
        elif command == 'press_key':
            key = params.get('key')
            
            if not key:
                return {
                    'success': False,
                    'error': 'Key parameter is required',
                    'execution_time': 0
                }
            
            return await self.press_key(key)
        
        elif command == 'scroll':
            direction = params.get('direction')
            amount = params.get('amount', 300)
            
            if not direction:
                return {
                    'success': False,
                    'error': 'Direction parameter is required (up, down, left, right)',
                    'execution_time': 0
                }
            
            return await self.scroll(direction, amount)
        
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
    
    @ensure_controller_loop
    async def dump_elements(self, element_types: str = "all", include_hidden: bool = False) -> Dict[str, Any]:
        """
        Dump all visible elements from the page for debugging and inspection.
        
        Args:
            element_types: Types of elements to include ('all', 'interactive', 'text', 'links')
            include_hidden: Whether to include hidden elements
        """
        try:
            print(f"[PLAYWRIGHT]: Dumping elements (type: {element_types}, include_hidden: {include_hidden})")
            start_time = time.time()
            
            # Get persistent page from browser+context
            page = await self._get_persistent_page()
            print(f"[PLAYWRIGHT]: Got persistent page (url={page.url}), preparing to evaluate JS")
            
            # Check if page is still responsive
            try:
                await page.evaluate("() => true")
                print(f"[PLAYWRIGHT]: Page is responsive, proceeding with element dump")
            except Exception as check_error:
                error_msg = f"Page connectivity check failed: {type(check_error).__name__}: {str(check_error)}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elements': [],
                    'summary': {},
                    'execution_time': 0
                }
            
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
            
            # Execute the JavaScript with proper timeout and error handling
            try:
                print(f"[PLAYWRIGHT]: Starting page.evaluate() with 5s timeout")
                import asyncio as _asyncio
                result = await _asyncio.wait_for(page.evaluate(js_code), timeout=5.0)
                print(f"[PLAYWRIGHT]: page.evaluate() completed successfully")
            except _asyncio.TimeoutError:
                error_msg = "Element dump timed out after 5 seconds - page may be unresponsive"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elements': [],
                    'summary': {},
                    'execution_time': int((time.time() - start_time) * 1000)
                }
            except Exception as eval_error:
                error_msg = f"Element dump evaluation error: {type(eval_error).__name__}: {str(eval_error)}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elements': [],
                    'summary': {},
                    'execution_time': int((time.time() - start_time) * 1000)
                }
            
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
        
    async def getMenuInfo(self, area: dict = None, context = None) -> Dict[str, Any]:
        """
        Extract menu info from web elements (Playwright-based alternative to OCR getMenuInfo)
        Same interface as text.getMenuInfo but uses dump_elements instead of OCR
        
        Args:
            area: Optional area to filter elements (x, y, width, height)
            context: Execution context for metadata storage
            
        Returns:
            Same format as text.getMenuInfo:
            {
                success: bool,
                output_data: {
                    parsed_data: dict,
                    raw_output: str
                },
                message: str
            }
        """
        print(f"[@controller:PlaywrightWeb:getMenuInfo] Params: area={area}, context={context is not None}")
        
        try:
            # 1. Dump web elements (already exists)
            print(f"[@controller:PlaywrightWeb:getMenuInfo] Dumping web elements...")
            dump_result = await self.dump_elements(element_types='all', include_hidden=False)
            
            if not dump_result.get('success'):
                error = dump_result.get('error', 'Unknown error')
                print(f"[@controller:PlaywrightWeb:getMenuInfo] FAIL: Element dump failed: {error}")
                return {
                    'success': False,
                    'output_data': {},
                    'message': f'Failed to dump elements: {error}'
                }
            
            elements = dump_result.get('elements', [])
            print(f"[@controller:PlaywrightWeb:getMenuInfo] Dumped {len(elements)} web elements")
            
            # 2. Filter by area if specified
            filtered_elements = elements
            if area:
                filtered_elements = []
                for elem in elements:
                    pos = elem.get('position', {})
                    elem_x = pos.get('x', 0)
                    elem_y = pos.get('y', 0)
                    elem_width = pos.get('width', 0)
                    elem_height = pos.get('height', 0)
                    
                    # Check if element overlaps with area
                    area_x = area.get('x', 0)
                    area_y = area.get('y', 0)
                    area_width = area.get('width', 99999)
                    area_height = area.get('height', 99999)
                    
                    # Element is in area if it overlaps
                    if (elem_x < area_x + area_width and
                        elem_x + elem_width > area_x and
                        elem_y < area_y + area_height and
                        elem_y + elem_height > area_y):
                        filtered_elements.append(elem)
                
                print(f"[@controller:PlaywrightWeb:getMenuInfo] Filtered to {len(filtered_elements)} elements in area")
            
            # 3. Parse key-value pairs from element text
            parsed_data = {}
            for elem in filtered_elements:
                text = elem.get('textContent', '').strip()
                
                # Skip empty text
                if not text or len(text) < 2:
                    continue
                
                # Parse key-value pairs
                # Pattern 1: "Key: Value" (colon separator)
                if ':' in text and len(text) < 100:  # Reasonable length for key-value
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().replace(' ', '_').replace('-', '_')
                        value = parts[1].strip()
                        if key and value:  # Both must be non-empty
                            parsed_data[key] = value
                            print(f"  • {key} = {value}")
                
                # Pattern 2: "Key\nValue" (newline separator)
                elif '\n' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        key = lines[0].strip().replace(' ', '_').replace('-', '_')
                        value = '\n'.join(lines[1:]).strip()
                        if key and value:  # Both must be non-empty
                            parsed_data[key] = value
                            print(f"  • {key} = {value}")
            
            print(f"[@controller:PlaywrightWeb:getMenuInfo] Parsed {len(parsed_data)} key-value pairs")
            
            if not parsed_data:
                print(f"[@controller:PlaywrightWeb:getMenuInfo] WARNING: No key-value pairs found in web elements")
            
            # 4. Auto-store to context.metadata (same as OCR version)
            if context:
                from datetime import datetime
                
                # Initialize metadata if not exists
                if not hasattr(context, 'metadata'):
                    context.metadata = {}
                
                # Append parsed data directly to metadata (flat structure)
                for key, value in parsed_data.items():
                    context.metadata[key] = value
                
                # Add extraction metadata
                context.metadata['extraction_method'] = 'web_elements'
                context.metadata['extraction_timestamp'] = datetime.now().isoformat()
                context.metadata['element_count'] = len(filtered_elements)
                
                # Add page info
                summary = dump_result.get('summary', {})
                context.metadata['page_title'] = summary.get('page_title', '')
                context.metadata['page_url'] = summary.get('page_url', '')
                
                if area:
                    context.metadata['extraction_area'] = str(area)
                
                print(f"[@controller:PlaywrightWeb:getMenuInfo] ✅ AUTO-APPENDED to context.metadata (FLAT)")
                print(f"[@controller:PlaywrightWeb:getMenuInfo] Metadata keys: {list(context.metadata.keys())}")
                print(f"[@controller:PlaywrightWeb:getMenuInfo] New fields added: {list(parsed_data.keys())}")
            else:
                print(f"[@controller:PlaywrightWeb:getMenuInfo] WARNING: No context provided, metadata not stored")
            
            # 5. Prepare output data with FULL raw dump for debugging
            raw_dump = []
            for elem in filtered_elements:
                raw_dump.append({
                    'index': elem.get('index'),
                    'tagName': elem.get('tagName'),
                    'selector': elem.get('selector'),
                    'textContent': elem.get('textContent'),
                    'className': elem.get('className'),
                    'id': elem.get('id'),
                    'attributes': elem.get('attributes', {}),
                    'position': elem.get('position', {}),
                    'isVisible': elem.get('isVisible'),
                    'aria-label': elem.get('attributes', {}).get('aria-label'),
                    'role': elem.get('attributes', {}).get('role'),
                    'href': elem.get('attributes', {}).get('href'),
                    'title': elem.get('attributes', {}).get('title')
                })
            
            output_data = {
                'parsed_data': parsed_data,
                'raw_dump': raw_dump,  # Full structured dump for debugging
                'element_count': len(filtered_elements)
            }
            
            print(f"[@controller:PlaywrightWeb:getMenuInfo] 📤 RETURNING output_data with {len(parsed_data)} parsed_data entries")
            print(f"[@controller:PlaywrightWeb:getMenuInfo] 📤 output_data keys: {list(output_data.keys())}")
            
            # 6. Return same format as text.getMenuInfo
            message = f'Parsed {len(parsed_data)} fields from {len(filtered_elements)} web elements'
            
            print(f"[@controller:PlaywrightWeb:getMenuInfo] ✅ SUCCESS: {message}")
            
            return {
                'success': True,
                'output_data': output_data,
                'message': message
            }
            
        except Exception as e:
            error_msg = f"Error extracting menu info from web elements: {str(e)}"
            print(f"[@controller:PlaywrightWeb:getMenuInfo] ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'output_data': {},
                'message': error_msg
            }
    
    # Note: get_available_verifications is defined below with ALL verifications combined
    
    # Note: execute_verification is defined below with ALL commands combined
    
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
                    'label': 'Click Element by Text',
                    'command': 'click_element',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Click an element by text/ID (same as Android - dump UI first, then click)',
                    'requiresInput': True,
                    'inputLabel': 'Element Text/ID',
                    'inputPlaceholder': 'Submit Button'
                },
                {
                    'id': 'find_element',
                    'label': 'Find Element',
                    'command': 'find_element',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Find an element by text/selector/aria-label (returns element ID and position like click_element)',
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
                    'id': 'press_key',
                    'label': 'Press Key',
                    'command': 'press_key',
                    'action_type': 'web',
                    'params': {},
                    'description': 'Press keyboard key',
                    'requiresInput': True,
                    'inputLabel': 'Key',
                    'inputPlaceholder': 'UP',
                    'options': ['BACK', 'ESC', 'ESCAPE', 'OK', 'ENTER', 'HOME', 'END', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'TAB', 'SPACE', 'DELETE', 'BACKSPACE', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']
                },
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
                },
                # Scroll controls
                {
                    'id': 'scroll_up',
                    'label': 'Scroll Up',
                    'command': 'scroll',
                    'action_type': 'web',
                    'params': {'direction': 'up', 'amount': 300},
                    'description': 'Scroll page up by 300 pixels',
                    'requiresInput': False
                },
                {
                    'id': 'scroll_down',
                    'label': 'Scroll Down',
                    'command': 'scroll',
                    'action_type': 'web',
                    'params': {'direction': 'down', 'amount': 300},
                    'description': 'Scroll page down by 300 pixels',
                    'requiresInput': False
                },
                {
                    'id': 'scroll_left',
                    'label': 'Scroll Left',
                    'command': 'scroll',
                    'action_type': 'web',
                    'params': {'direction': 'left', 'amount': 300},
                    'description': 'Scroll page left by 300 pixels',
                    'requiresInput': False
                },
                {
                    'id': 'scroll_right',
                    'label': 'Scroll Right',
                    'command': 'scroll',
                    'action_type': 'web',
                    'params': {'direction': 'right', 'amount': 300},
                    'description': 'Scroll page right by 300 pixels',
                    'requiresInput': False
                }
            ]
        }
    
    # Note: All verification methods (waitForElementToAppear, waitForElementToDisappear, 
    # checkElementExists, getMenuInfo, execute_verification, get_available_verifications) 
    # are now in PlaywrightVerificationsMixin (playwright_verifications.py)