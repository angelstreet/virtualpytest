"""
Playwright Utilities

Chrome process management and async execution utilities for Playwright web automation.
Includes cookie management for automatic consent cookie injection.
Extracted from PlaywrightWebController to improve maintainability.
"""

import os
import time
import subprocess
import socket
import asyncio
from typing import Dict, Any, Tuple

# Import the cookie utils
try:
    from .cookie_utils import CookieManager, auto_accept_cookies
except ImportError:
    # Fallback import for direct usage
    import sys
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from cookie_utils import CookieManager, auto_accept_cookies


class ChromeManager:
    """Manages Chrome process lifecycle for remote debugging."""
    
    @staticmethod
    def kill_chrome_instances():
        """Kill any existing Chrome instances (Linux only)."""
        print('[ChromeManager] Killing any existing Chrome instances...')
        os.system('pkill -9 "Google Chrome"')
        os.system('pkill -9 "chrome"')
        os.system('pkill -9 "chromium"')
        time.sleep(2)
    
    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.bind(('127.0.0.1', port))
                return False
            except socket.error:
                return True
    
    @staticmethod
    def find_chrome_executable() -> str:
        """Find Chrome executable on Linux system."""
        possible_paths = ['/usr/bin/google-chrome', '/usr/bin/chromium-browser']
        for path in possible_paths:
            if os.path.exists(path):
                return path
        raise ValueError('No Chrome executable found in common Linux paths')
    
    @staticmethod
    def get_chrome_flags(debug_port: int = 9222, user_data_dir: str = "/tmp/chrome_debug_profile", window_size: str = "1280x1024") -> list:
        """
        Get Chrome launch flags for remote debugging.
        
        Args:
            debug_port: Debug port for remote debugging
            user_data_dir: Chrome user data directory
            window_size: Browser window size (e.g., "1280x1024" for VNC)
        """
        return [
            f'--remote-debugging-port={debug_port}',
            f'--user-data-dir={user_data_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-features=Translate',
            '--disable-extensions',
            '--window-position=0,0',
            f'--window-size={window_size}',
            '--disable-gpu',
            '--enable-unsafe-swiftshader'
            #'--no-sandbox'  # Important for containers
        ]
    
    @classmethod
    def launch_chrome_with_remote_debugging(cls, debug_port: int = 9222, window_size: str = "1280x1024") -> subprocess.Popen:
        """
        Launch Chrome with remote debugging enabled (Linux only).
        
        Args:
            debug_port: Port for remote debugging
            window_size: Browser window size (default optimized for VNC)
        """
        # Kill existing Chrome instances
        cls.kill_chrome_instances()
        
        # Kill any process using the debug port
        if cls.is_port_in_use(debug_port):
            print(f'[ChromeManager] Port {debug_port} is in use. Killing processes...')
            os.system(f'lsof -ti:{debug_port} | xargs kill -9')
            time.sleep(1)
        
        # Find Chrome executable
        executable_path = cls.find_chrome_executable()
        print(f'[ChromeManager] Launching Chrome with remote debugging: {executable_path}')
        
        # Prepare Chrome flags and user data directory
        user_data_dir = "/tmp/chrome_debug_profile"
        os.makedirs(user_data_dir, exist_ok=True)
        chrome_flags = cls.get_chrome_flags(debug_port, user_data_dir, window_size)
        
        # Launch Chrome with DISPLAY=:1 for VNC visibility
        cmd_line = [executable_path] + chrome_flags
        print(f'[ChromeManager] Chrome command: {" ".join(cmd_line)}')
        print(f'[ChromeManager] Using window size: {window_size} (VNC optimized)')
        
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        
        process = subprocess.Popen(cmd_line, env=env)
        print(f'[ChromeManager] Chrome launched with PID: {process.pid}')
        
        # Wait for Chrome to be ready
        cls._wait_for_chrome_ready(debug_port)
        
        return process
    
    @staticmethod
    def _wait_for_chrome_ready(debug_port: int, max_wait: int = 30):
        """Wait for Chrome to be ready on the debug port."""
        print(f'[ChromeManager] Waiting up to {max_wait} seconds for Chrome on port {debug_port}...')
        
        start_time = time.time()
        port_open = False
        
        while time.time() - start_time < max_wait:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(('127.0.0.1', debug_port))
                s.close()
                port_open = True
                elapsed = time.time() - start_time
                print(f'[ChromeManager] Chrome ready! Port {debug_port} open after {elapsed:.2f}s')
                time.sleep(2)  # Ensure Chrome is fully initialized
                break
            except (socket.timeout, socket.error):
                time.sleep(1)
        
        if not port_open:
            print(f'[ChromeManager] WARNING: Timed out waiting for Chrome port {debug_port}')


class AsyncExecutor:
    """Handles async execution in sync contexts for Playwright operations."""
    
    @staticmethod
    def run_async(coro):
        """Run async coroutine in sync context with smart event loop handling."""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new thread for this
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(coro)


class PlaywrightConnection:
    """Manages Playwright connections to Chrome via CDP."""
    
    @staticmethod
    async def connect_to_chrome(cdp_url: str = 'http://localhost:9222') -> Tuple[Any, Any, Any, Any]:
        """Connect to Chrome via CDP and return playwright, browser, context, page."""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        
        if len(browser.contexts) == 0:
            context = await browser.new_context()
            page = await context.new_page()
        else:
            context = browser.contexts[0]
            if len(context.pages) == 0:
                page = await context.new_page()
            else:
                page = context.pages[0]
        
        return playwright, browser, context, page
    
    @staticmethod
    async def cleanup_connection(playwright, browser):
        """Clean up Playwright connection."""
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


class PlaywrightUtils:
    """Main utility class combining Chrome management, Playwright operations, and cookie management."""
    
    def __init__(self, auto_accept_cookies: bool = True, window_size: str = "auto"):
        """
        Initialize PlaywrightUtils.
        
        Args:
            auto_accept_cookies: Whether to automatically inject consent cookies
            window_size: Browser window size ('auto' for dynamic sizing, or custom like '1280x1024')
        """
        self.chrome_manager = ChromeManager()
        self.async_executor = AsyncExecutor()
        self.connection = PlaywrightConnection()
        self.cookie_manager = CookieManager() if auto_accept_cookies else None
        self.auto_accept_cookies = auto_accept_cookies
        self.window_size = window_size
        self.viewport_size = self._calculate_viewport_size(window_size)
        print(f'[PlaywrightUtils] Initialized with auto_accept_cookies={auto_accept_cookies}, window_size={window_size}')
    
    def _calculate_viewport_size(self, window_size: str) -> dict:
        """Calculate viewport size based on panel visibility and window size."""
        if window_size == "auto":
            # Dynamic sizing based on typical panel configurations
            # VNC desktop resolution is typically 1280x1024
            base_width = 1280
            base_height = 1024
            
            # Common panel configurations for web automation:
            # 1. Full screen mode (VNC only) - use full VNC resolution
            # 2. Split mode (VNC + Terminal) - reduce width to account for terminal panel
            # 3. Embedded mode (VNC in browser page) - reduce both dimensions
            
            # For now, use a good default that works well in most cases
            # This optimizes for the embedded browser panel in the web interface
            viewport_width = int(base_width * 0.75)  # ~960px - leaves space for panels
            viewport_height = int(base_height * 0.80)  # ~819px - leaves space for header/controls
            
            return {"width": viewport_width, "height": viewport_height}
        else:
            # Parse custom window size
            try:
                width, height = window_size.split('x')
                return {"width": int(width), "height": int(height)}
            except:
                print(f'[PlaywrightUtils] Warning: Invalid window_size format "{window_size}", using auto-sizing')
                return self._calculate_viewport_size("auto")
    
    def update_viewport_for_context(self, context: str = "embedded") -> dict:
        """
        Update viewport size based on usage context.
        
        Args:
            context: 'embedded' (browser page), 'modal' (popup), 'fullscreen' (dedicated)
            
        Returns:
            New viewport size dict
        """
        base_width = 1280
        base_height = 1024
        
        if context == "embedded":
            # Browser automation panel in web interface
            viewport_width = int(base_width * 0.75)   # Account for side panels
            viewport_height = int(base_height * 0.80)  # Account for header/controls
        elif context == "modal":
            # Popup/modal window
            viewport_width = int(base_width * 0.90)   # Slight reduction for modal frame
            viewport_height = int(base_height * 0.85)  # Account for modal header
        elif context == "fullscreen":
            # Full VNC resolution
            viewport_width = base_width
            viewport_height = base_height
        else:
            # Default to embedded mode
            viewport_width = int(base_width * 0.75)
            viewport_height = int(base_height * 0.80)
        
        self.viewport_size = {"width": viewport_width, "height": viewport_height}
        print(f'[PlaywrightUtils] Updated viewport for {context} context: {viewport_width}x{viewport_height}')
        return self.viewport_size
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by adding protocol if missing.
        
        Args:
            url: Input URL that may be missing protocol
            
        Returns:
            Normalized URL with https:// prefix if needed
        """
        if not url:
            return url
        
        url = url.strip()
        
        # If URL already has a protocol, return as-is
        if url.startswith(('http://', 'https://', 'ftp://', 'file://')):
            return url
        
        # Special cases for local URLs
        if url.startswith(('localhost', '127.0.0.1', '0.0.0.0')) or ':' in url.split('.')[0]:
            return f'http://{url}'
        
        # For all other URLs, default to https
        return f'https://{url}'
    
    def _parse_window_size(self, window_size: str) -> dict:
        """Parse window size string to viewport dict (legacy method for compatibility)."""
        return self._calculate_viewport_size(window_size)
    
    def launch_chrome(self, debug_port: int = 9222) -> subprocess.Popen:
        """Launch Chrome with remote debugging and dynamic window size."""
        # Convert viewport size back to window size for Chrome launch
        if self.window_size == "auto":
            chrome_window_size = f"{self.viewport_size['width']}x{self.viewport_size['height']}"
        else:
            chrome_window_size = self.window_size
        
        return self.chrome_manager.launch_chrome_with_remote_debugging(debug_port, chrome_window_size)
    
    def kill_chrome(self):
        """Kill Chrome instances."""
        self.chrome_manager.kill_chrome_instances()
    
    def run_async(self, coro):
        """Run async coroutine in sync context."""
        return self.async_executor.run_async(coro)
    
    async def connect_to_chrome(self, cdp_url: str = 'http://localhost:9222', target_url: str = None):
        """
        Connect to Chrome via CDP with automatic cookie injection.
        
        Args:
            cdp_url: Chrome debug protocol URL
            target_url: URL that will be visited (for auto-cookie detection)
            
        Returns:
            Tuple of (playwright, browser, context, page)
        """
        playwright, browser, context, page = await self.connection.connect_to_chrome(cdp_url)
        
        # Set viewport to match the window size for consistent scaling
        await page.set_viewport_size(self.viewport_size)
        print(f'[PlaywrightUtils] Set viewport to {self.viewport_size["width"]}x{self.viewport_size["height"]} (matches window size)')
        
        # Auto-inject cookies if enabled and target URL provided
        if self.auto_accept_cookies and self.cookie_manager and target_url:
            try:
                await self.cookie_manager.auto_accept_cookies_for_url(context, target_url)
                print(f'[PlaywrightUtils] Auto-injected cookies for {target_url}')
            except Exception as e:
                print(f'[PlaywrightUtils] Warning: Failed to inject cookies for {target_url}: {e}')
        
        return playwright, browser, context, page
    
    async def cleanup_connection(self, playwright, browser):
        """Clean up connection."""
        await self.connection.cleanup_connection(playwright, browser)
    

    
    async def inject_cookies_for_sites(self, context, sites: list):
        """
        Manually inject cookies for specific sites.
        
        Args:
            context: Playwright browser context
            sites: List of site names (e.g., ['youtube', 'google'])
        """
        if self.cookie_manager:
            await self.cookie_manager.inject_cookies(context, sites)
        else:
            print('[PlaywrightUtils] Warning: Cookie manager not initialized')
    
    def get_available_cookie_configs(self) -> list:
        """Get list of available cookie configurations."""
        if self.cookie_manager:
            return self.cookie_manager.get_available_configs()
        return []


# Convenience functions for external use
def create_playwright_utils(auto_accept_cookies: bool = True, window_size: str = "auto") -> PlaywrightUtils:
    """Create a PlaywrightUtils instance."""
    return PlaywrightUtils(auto_accept_cookies=auto_accept_cookies, window_size=window_size)


def launch_chrome_for_debugging(debug_port: int = 9222, window_size: str = "auto") -> subprocess.Popen:
    """Quick function to launch Chrome with remote debugging."""
    if window_size == "auto":
        # Use default auto-sizing
        utils = create_playwright_utils(window_size="auto")
        computed_size = f"{utils.viewport_size['width']}x{utils.viewport_size['height']}"
        return ChromeManager.launch_chrome_with_remote_debugging(debug_port, computed_size)
    else:
        return ChromeManager.launch_chrome_with_remote_debugging(debug_port, window_size)


def run_async_playwright(coro):
    """Quick function to run async Playwright code in sync context."""
    return AsyncExecutor.run_async(coro)


def get_available_cookie_sites() -> list:
    """Quick function to get available cookie sites."""
    manager = CookieManager()
    return manager.get_available_configs()


# Browser-use compatibility functions
async def get_playwright_context_with_cookies(target_url: str = None, window_size: str = "auto"):
    """
    Get a Playwright context with auto-injected cookies for browser-use compatibility.
    
    Args:
        target_url: URL to inject cookies for
        window_size: Browser window size (auto-sizing by default)
        
    Returns:
        Tuple of (playwright, browser, context, page)
    """
    utils = PlaywrightUtils(auto_accept_cookies=True, window_size=window_size)
    return await utils.connect_to_chrome(target_url=target_url) 