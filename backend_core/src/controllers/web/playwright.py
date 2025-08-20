"""
Playwright Web Controller Implementation

This controller provides web browser automation functionality using Playwright.
Key features: Chrome remote debugging for thread-safe automation, async Playwright with sync wrappers for browser-use compatibility.
Uses playwright_utils for Chrome management and async execution.
"""

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
    
    def __init__(self, **kwargs):
        """
        Initialize the Playwright web controller.
        """
        super().__init__("Playwright Web", "playwright")
        
        # Simple initialization with persistent user data
        self.utils = PlaywrightUtils(auto_accept_cookies=True)
        
        # Command execution state
        self.last_command_output = ""
        self.last_command_error = ""
        self.current_url = ""
        self.page_title = ""
        
        print(f"[@controller:PlaywrightWeb] Initialized with async Playwright + Chrome remote debugging + auto-cookie acceptance + persistent user data")
    
    async def _get_persistent_page(self, target_url: str = None):
        """Get the persistent page from browser+context. Creates browser+context+page if needed."""
        # Auto-connect Chrome if not connected
        if not self.is_connected or not self._chrome_running:
            print(f"[PLAYWRIGHT]: Auto-connecting Chrome...")
            self.connect()  # This launches Chrome if needed
        
        # Establish persistent browser+context if not exists
        if not self.__class__._browser_connected or not self.__class__._browser or not self.__class__._context:
            print(f"[PLAYWRIGHT]: Creating persistent browser+context+page...")
            self.__class__._playwright, self.__class__._browser, self.__class__._context, initial_page = await self.utils.connect_to_chrome(target_url=target_url)
            self.__class__._browser_connected = True
            print(f"[PLAYWRIGHT]: Persistent browser+context+page established")
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
        """Connect to Chrome (launch if needed)."""
        print(f"[PLAYWRIGHT]: connect() called - _chrome_running={self._chrome_running}, _chrome_process={self._chrome_process}")
        
        if not self._chrome_running:
            try:
                print(f"[PLAYWRIGHT]: Chrome not running, launching new Chrome process...")
                self.__class__._chrome_process = self.utils.launch_chrome()
                self.__class__._chrome_running = True
                print(f"[PLAYWRIGHT]: Chrome launched with remote debugging successfully (PID: {self._chrome_process.pid})")
            except Exception as e:
                print(f"[PLAYWRIGHT]: Failed to launch Chrome: {e}")
                return False
        else:
            print(f"[PLAYWRIGHT]: Chrome process already running (PID: {self._chrome_process.pid if self._chrome_process else 'unknown'})")
        
        self.is_connected = True
        print(f"[PLAYWRIGHT]: connect() completed - _chrome_running={self._chrome_running}, is_connected={self.is_connected}")
        return True
    
    def disconnect(self) -> bool:
        """Disconnect and cleanup Chrome."""
        print(f"[PLAYWRIGHT]: disconnect() called - _chrome_running={self._chrome_running}, _chrome_process={self._chrome_process}")
        
        # Clean up persistent browser connection first
        print(f"[PLAYWRIGHT]: Starting browser connection cleanup...")
        try:
            self.utils.run_async(self._cleanup_persistent_browser())
            print(f"[PLAYWRIGHT]: Browser connection cleanup completed")
        except Exception as cleanup_error:
            print(f"[PLAYWRIGHT]: Browser connection cleanup failed: {type(cleanup_error).__name__}: {str(cleanup_error)}")
        
        if self._chrome_running and self._chrome_process:
            try:
                print(f"[PLAYWRIGHT]: Gracefully closing Chrome process (PID: {self._chrome_process.pid})")
                
                # Use graceful close (handles all fallbacks and waiting internally)
                self.utils.kill_chrome(chrome_process=self._chrome_process)
                print(f"[PLAYWRIGHT]: Chrome process terminated")
                
            except Exception as e:
                print(f"[PLAYWRIGHT]: Error during Chrome shutdown: {type(e).__name__}: {str(e)}")
            finally:
                # Clean up state regardless
                print(f"[PLAYWRIGHT]: Cleaning up Chrome process state...")
                self.__class__._chrome_process = None
                self.__class__._chrome_running = False
                print(f"[PLAYWRIGHT]: Chrome process state cleaned up")
        else:
            print(f"[PLAYWRIGHT]: No Chrome process to terminate (running={self._chrome_running}, process={self._chrome_process})")
        
        self.is_connected = False
        print(f"[PLAYWRIGHT]: disconnect() completed - _chrome_running={self._chrome_running}, is_connected={self.is_connected}")
        return True
    
    def open_browser(self) -> Dict[str, Any]:
        """Open/launch the browser window."""
        async def _async_open_browser():
            try:
                print(f"[PLAYWRIGHT]: Opening browser with natural sizing")
                start_time = time.time()
                
                # First, ensure Chrome is launched (this will launch if not running)
                if not self.is_connected:
                    print(f"[PLAYWRIGHT]: Chrome not connected, launching...")
                    if not self.connect():
                        return {
                            'success': False,
                            'error': 'Failed to launch Chrome',
                            'execution_time': 0,
                            'connected': False
                        }
                else:
                    print(f"[PLAYWRIGHT]: Chrome already connected")
                
                # Test connection to Chrome and ensure page is ready
                try:
                    page = await self._get_persistent_page(target_url='https://google.fr')
                except Exception as e:
                    # Chrome is not responding, kill and relaunch
                    if "ECONNREFUSED" in str(e) or "connect" in str(e).lower():
                        print(f"[PLAYWRIGHT]: Chrome not responding, killing and relaunching...")
                        self.utils.kill_chrome()
                        self.__class__._chrome_process = None
                        self.__class__._chrome_running = False
                        self.__class__._browser_connected = False
                        self.is_connected = False
                        
                        # Try to connect again
                        if not self.connect():
                            raise Exception("Failed to relaunch Chrome after connection failure")
                        page = await self._get_persistent_page(target_url='https://google.fr')
                    else:
                        raise
                
                # Navigate to Google France for a nicer default page
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
                    page = await self._get_persistent_page()
                    
                    # Get current page info from persistent page
                    self.current_url = page.url
                    self.page_title = await page.title() if page.url != 'about:blank' else ''
                    
                    # Mark as connected
                    self.is_connected = True
                    
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
                    # Chrome debug session not available
                    error_msg = f"Could not connect to existing Chrome debug session: {e}. Make sure Chrome is running with --remote-debugging-port=9222"
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
        """Close browser (disconnect Chrome)."""
        try:
            print(f"[PLAYWRIGHT]: Closing browser")
            start_time = time.time()
            
            # Add timeout protection for disconnect operation
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Browser close operation timed out after 5 seconds")
            
            # Set 5-second timeout for graceful disconnect
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                self.disconnect()
                signal.alarm(0)  # Cancel the alarm
                print(f"[PLAYWRIGHT]: Graceful disconnect completed")
            except TimeoutError as timeout_error:
                print(f"[PLAYWRIGHT]: Graceful disconnect timed out after 5s, force killing Chrome...")
                # Force kill Chrome process if it exists
                if self._chrome_process:
                    try:
                        import os
                        os.kill(self._chrome_process.pid, 9)  # SIGKILL
                        print(f"[PLAYWRIGHT]: Force killed Chrome process (PID: {self._chrome_process.pid})")
                    except Exception as kill_error:
                        print(f"[PLAYWRIGHT]: Failed to force kill Chrome: {str(kill_error)}")
                
                # Force cleanup state
                self.__class__._chrome_process = None
                self.__class__._chrome_running = False
                self.is_connected = False
                print(f"[PLAYWRIGHT]: Force cleanup completed")
            finally:
                signal.signal(signal.SIGALRM, old_handler)  # Restore original handler
                signal.alarm(0)  # Make sure alarm is cancelled
            
            # Clear page state
            self.current_url = ""
            self.page_title = ""
            
            execution_time = int((time.time() - start_time) * 1000)
            
            print(f"[PLAYWRIGHT]: Browser closed successfully in {execution_time}ms")
            return {
                'success': True,
                'error': '',
                'execution_time': execution_time,
                'connected': False
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"Browser close error: {type(e).__name__}: {str(e)}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': execution_time,
                'connected': False
            }
    
    def navigate_to_url(self, url: str, timeout: int = 60000, follow_redirects: bool = True) -> Dict[str, Any]:
        """Navigate to a URL using async CDP connection."""
        async def _async_navigate_to_url():
            try:
                # Normalize URL to add protocol if missing
                normalized_url = self.utils.normalize_url(url)
                print(f"[PLAYWRIGHT]: Navigating to {url} (normalized: {normalized_url})")
                start_time = time.time()
                

                
                # Get persistent page from browser+context
                page = await self._get_persistent_page(target_url=normalized_url)
                print(f"[PLAYWRIGHT]: Got persistent page, starting navigation to {normalized_url}")
                
                # Navigate to URL with pragmatic loading strategy
                navigation_start = time.time()
                
                # First try to load with domcontentloaded (main content ready)
                try:
                    await page.goto(normalized_url, timeout=timeout, wait_until='domcontentloaded')
                    navigation_time = int((time.time() - navigation_start) * 1000)
                    print(f"[PLAYWRIGHT]: Main page content loaded in {navigation_time}ms")
                    
                    # Then try to wait for full load, but don't fail if it times out
                    full_load_start = time.time()
                    try:
                        await page.wait_for_load_state('load', timeout=20000)  # 20 second limit
                        full_load_time = int((time.time() - full_load_start) * 1000)
                        print(f"[PLAYWRIGHT]: Full page load completed in additional {full_load_time}ms")
                    except Exception as load_timeout:
                        full_load_time = int((time.time() - full_load_start) * 1000)
                        print(f"[PLAYWRIGHT]: Full load timeout after {full_load_time}ms ({type(load_timeout).__name__}), but continuing since main content is ready")
                        
                except Exception as goto_error:
                    navigation_time = int((time.time() - navigation_start) * 1000)
                    print(f"[PLAYWRIGHT]: Main page navigation FAILED after {navigation_time}ms: {type(goto_error).__name__}: {str(goto_error)}")
                    raise goto_error
                
                # Get page info after navigation
                try:
                    current_url = page.url
                    current_title = await page.title()
                    print(f"[PLAYWRIGHT]: Page loaded - URL: {current_url}, Title: {current_title[:100]}...")
                except Exception as page_info_error:
                    print(f"[PLAYWRIGHT]: Failed to get page info: {type(page_info_error).__name__}: {str(page_info_error)}")
                    raise page_info_error
                
                # Try to wait for networkidle but don't fail if it times out
                networkidle_start = time.time()
                try:
                    print(f"[PLAYWRIGHT]: Waiting for networkidle state (timeout: 20s)...")
                    await page.wait_for_load_state('networkidle', timeout=20000)
                    networkidle_time = int((time.time() - networkidle_start) * 1000)
                    print(f"[PLAYWRIGHT]: Networkidle achieved in {networkidle_time}ms")
                except Exception as e:
                    networkidle_time = int((time.time() - networkidle_start) * 1000)
                    print(f"[PLAYWRIGHT]: Networkidle timeout after {networkidle_time}ms - {type(e).__name__}: {str(e)} (this is expected and ignored)")
                
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'url': '',
                'title': ''
            }
        
        return self.utils.run_async(_async_navigate_to_url())
    
    def click_element(self, search_term: str) -> Dict[str, Any]:
        """Click an element by finding it through dump search first.
        
        Args:
            search_term: Text to search for in element content, aria-label, or exact selector
        """
        try:
            print(f"[PLAYWRIGHT]: Clicking element using smart search: {search_term}")
            start_time = time.time()
            
            # First, find the element using our dump-based search
            find_result = self.find_element(search_term)
            
            if not find_result.get('success'):
                return {
                    'success': False,
                    'error': f"Could not find element: {find_result.get('error', 'Unknown error')}",
                    'execution_time': int((time.time() - start_time) * 1000)
                }
            
            element_info = find_result.get('element_info', {})
            exact_selector = element_info.get('selector')
            
            if not exact_selector:
                return {
                    'success': False,
                    'error': "No exact selector found for element",
                    'execution_time': int((time.time() - start_time) * 1000)
                }
            
            print(f"[PLAYWRIGHT]: Found exact selector '{exact_selector}' for '{search_term}', now clicking...")
            
            # Now click using the exact selector found from dump
            async def _async_click_exact():
                try:
                    page = await self._get_persistent_page()
                    await page.click(exact_selector, timeout=5000)
                    return True
                except Exception as e:
                    print(f"[PLAYWRIGHT]: Click failed with exact selector '{exact_selector}': {e}")
                    return False
            
            click_success = self.utils.run_async(_async_click_exact())
            execution_time = int((time.time() - start_time) * 1000)
            
            if click_success:
                print(f"[PLAYWRIGHT]: Click successful using exact selector '{exact_selector}'")
                return {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time,
                    'used_selector': exact_selector,
                    'element_info': element_info,
                    'search_term': search_term
                }
            else:
                return {
                    'success': False,
                    'error': f"Click failed with exact selector '{exact_selector}'",
                    'execution_time': execution_time,
                    'found_selector': exact_selector
                }
                
        except Exception as e:
            error_msg = f"Click element error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': 0
            }
    
    def find_element(self, search_term: str) -> Dict[str, Any]:
        """Find an element by searching through dump results.
        
        Args:
            search_term: Text to search for in element content, aria-label, or exact selector
        """
        try:
            print(f"[PLAYWRIGHT]: Finding element using dump search: {search_term}")
            start_time = time.time()
            
            # First, dump all elements to get the real selectors
            dump_result = self.dump_elements()
            
            if not dump_result.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to dump elements: {dump_result.get('error', 'Unknown error')}",
                    'execution_time': int((time.time() - start_time) * 1000)
                }
            
            elements = dump_result.get('elements', [])
            print(f"[PLAYWRIGHT]: Searching through {len(elements)} dumped elements")
            
            # Search for matching element
            found_element = None
            match_type = None
            
            for element in elements:
                if element.get('selector') == search_term:
                    found_element = element
                    match_type = 'exact_selector'
                    break
                elif element.get('id') == search_term:
                    found_element = element
                    match_type = 'exact_id'
                    break
                elif element.get('attributes', {}).get('aria-label', '').lower() == search_term.lower():
                    found_element = element
                    match_type = 'aria_label'
                    break
            
            execution_time = int((time.time() - start_time) * 1000)
            
            if found_element:
                print(f"[PLAYWRIGHT]: Found {match_type} match: {found_element['selector']}")
                return {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time,
                    'element_info': {
                        'selector': found_element['selector'],
                        'x': found_element['position']['x'],
                        'y': found_element['position']['y'],
                        'width': found_element['position']['width'],
                        'height': found_element['position']['height'],
                        'aria_label': found_element.get('attributes', {}).get('aria-label'),
                        'text_content': found_element.get('textContent')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"No elements found matching '{search_term}'",
                    'execution_time': execution_time,
                    'total_elements_searched': len(elements)
                }
            
        except Exception as e:
            error_msg = f"Find element error: {e}"
            print(f"[PLAYWRIGHT]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_time': 0
            }
    
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'execution_time': 0
            }
        
        return self.utils.run_async(_async_input_text())
    
    def tap_x_y(self, x: int, y: int) -> Dict[str, Any]:
        """Tap/click at specific coordinates using async CDP connection."""
        async def _async_tap_x_y():
            try:
                print(f"[PLAYWRIGHT]: Tapping at coordinates: ({x}, {y})")
                start_time = time.time()
                
                # Get persistent page from browser+context
                page = await self._get_persistent_page()
                
                # Click at coordinates
                await page.mouse.click(x, y)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                result = {
                    'success': True,
                    'error': '',
                    'execution_time': execution_time
                }
                
                print(f"[PLAYWRIGHT]: Tap successful")
                return result
                
            except Exception as e:
                error_msg = f"Tap error: {e}"
                print(f"[PLAYWRIGHT]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': 0
                }
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'execution_time': 0
            }
        
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'result': None,
                'execution_time': 0
            }
        
        return self.utils.run_async(_async_execute_javascript())
    
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'url': '',
                'title': '',
                'execution_time': 0
            }
        
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
        
        return self.execute_javascript(script)
    
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'execution_time': 0
            }
        
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'task': task,
                'execution_time': 0
            }
        
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
            element_id = params.get('element_id')
            
            if not element_id:
                return {
                    'success': False,
                    'error': 'element_id parameter is required',
                    'execution_time': 0
                }
                
            return self.click_element(element_id)
        
        elif command == 'find_element':
            element_id = params.get('element_id')
            
            if not element_id:
                return {
                    'success': False,
                    'error': 'element_id parameter is required',
                    'execution_time': 0
                }
                
            return self.find_element(element_id)
        
        elif command == 'input_text':
            element_id = params.get('element_id')
            text = params.get('text', '')
            timeout = params.get('timeout', 30000)
            
            if not element_id:
                return {
                    'success': False,
                    'error': 'element_id parameter is required',
                    'execution_time': 0
                }
                
            return self.input_text(element_id, text, timeout=timeout)
        
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
            return self.close_browser()
        
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
        
        if not self.is_connected:
            return {
                'success': False,
                'error': 'Not connected to browser',
                'elements': [],
                'summary': {}
            }
        
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