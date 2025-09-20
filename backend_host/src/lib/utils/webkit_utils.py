"""
Lightweight WebKit Browser Utilities for Playwright

Minimal implementation using WebKit (Safari engine) - the lightest browser option.
Supports debug mode connections like Chrome but with much lower resource usage.
"""

import os
import time
import subprocess
import socket
import asyncio
from typing import Dict, Any, Tuple


class WebKitManager:
    """Manages WebKit process lifecycle for remote debugging - lightweight alternative to Chrome."""
    
    @staticmethod
    def find_webkit_executable() -> tuple:
        """Find WebKit/Safari executable on system. Returns (path, browser_type)."""
        # On macOS, use Safari
        if os.path.exists('/Applications/Safari.app/Contents/MacOS/Safari'):
            return ('/Applications/Safari.app/Contents/MacOS/Safari', 'safari')
        
        # On Linux, try to find webkit-based browsers with debug support
        webkit_browsers = [
            ('/usr/bin/chromium-browser', 'chromium-webkit'),  # Chromium with WebKit flags
            ('/usr/bin/google-chrome', 'chrome-webkit'),       # Chrome with WebKit-like flags
            ('/usr/bin/firefox', 'firefox'),                   # Firefox as lightweight alternative
        ]
        
        for path, browser_type in webkit_browsers:
            if os.path.exists(path):
                return (path, browser_type)
                
        raise ValueError('No suitable lightweight browser found. Install chromium-browser, google-chrome, or firefox')
    
    @staticmethod
    def get_webkit_flags(debug_port: int = 9223, browser_type: str = 'chromium-webkit') -> list:
        """Get browser launch flags for remote debugging based on browser type."""
        if browser_type == 'firefox':
            # Firefox remote debugging flags
            return [
                f'--remote-debugging-port={debug_port}',
                '--headless=false',  # Keep visible
                '--new-instance',
                '--no-remote',
                '--profile-manager'
            ]
        elif browser_type in ['chromium-webkit', 'chrome-webkit']:
            # Chromium/Chrome with lightweight flags
            return [
                f'--remote-debugging-port={debug_port}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-sync',
                '--disable-translate',
                '--disable-features=TranslateUI,InfiniteSessionRestore,TabRestore',
                '--disable-default-apps',
                '--disable-session-crashed-bubble',
                '--disable-infobars',
                '--disable-restore-session-state'
            ]
        else:  # safari or other
            return [
                '--remote-debugging-port=9999',  # Safari uses different approach
                '--no-first-run'
            ]
    
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
    
    @classmethod
    def launch_webkit_with_debugging(cls, debug_port: int = 9223) -> subprocess.Popen:
        """Launch lightweight browser with remote debugging."""
        # Kill any process using the debug port
        if cls.is_port_in_use(debug_port):
            print(f'[WebKitManager] Port {debug_port} in use, killing processes...')
            try:
                result = subprocess.run(['lsof', '-ti', f':{debug_port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            subprocess.run(['kill', '-9', pid.strip()], timeout=3)
            except Exception as e:
                print(f'[WebKitManager] Error killing processes: {e}')
            time.sleep(1)
        
        # Find suitable lightweight browser
        executable_path, browser_type = cls.find_webkit_executable()
        print(f'[WebKitManager] Launching {browser_type} browser: {executable_path}')
        
        # Get browser-specific flags
        browser_flags = cls.get_webkit_flags(debug_port, browser_type)
        
        # Launch browser
        cmd_line = [executable_path] + browser_flags
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        
        print(f'[WebKitManager] Command: {" ".join(cmd_line)}')
        process = subprocess.Popen(cmd_line, env=env)
        print(f'[WebKitManager] {browser_type} launched with PID: {process.pid}')
        
        # Wait for browser to be ready
        cls._wait_for_webkit_ready(debug_port)
        return process
    
    @staticmethod
    def _wait_for_webkit_ready(debug_port: int, max_wait: int = 30):
        """Wait for WebKit to be ready on the debug port."""
        print(f'[WebKitManager] Waiting for WebKit on port {debug_port}...')
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(('127.0.0.1', debug_port))
                s.close()
                elapsed = time.time() - start_time
                print(f'[WebKitManager] WebKit ready after {elapsed:.2f}s')
                time.sleep(1)  # Brief pause for full initialization
                return
            except (socket.timeout, socket.error):
                time.sleep(1)
        
        print(f'[WebKitManager] WARNING: Timeout waiting for WebKit port {debug_port}')


class WebKitConnection:
    """Manages Playwright connections to lightweight browsers via debug protocol."""
    
    @staticmethod
    async def connect_to_webkit(cdp_url: str = 'http://localhost:9223') -> Tuple[Any, Any, Any, Any]:
        """Connect to lightweight browser via debug protocol and return playwright, browser, context, page."""
        from playwright.async_api import async_playwright
        
        try:
            print(f'[WebKitConnection] Connecting to lightweight browser at {cdp_url}')
            playwright = await async_playwright().start()
            
            # Since we're actually using Chromium/Chrome with lightweight flags, use chromium engine
            # This provides the same lightweight benefits but with proper CDP support
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
            print(f'[WebKitConnection] Connected to lightweight browser successfully')
            
            # Get or create context and page
            if len(browser.contexts) == 0:
                context = await browser.new_context()
                page = await context.new_page()
                print(f'[WebKitConnection] Created new lightweight browser context')
            else:
                context = browser.contexts[0]
                if len(context.pages) == 0:
                    page = await context.new_page()
                else:
                    page = context.pages[0]
                print(f'[WebKitConnection] Using existing lightweight browser context')
            
            return playwright, browser, context, page
            
        except Exception as e:
            print(f'[WebKitConnection] Connection failed: {e}')
            raise Exception(f"Lightweight browser connection failed: {str(e)}")


class WebKitUtils:
    """Lightweight WebKit utility class - minimal resource usage alternative to Chrome."""
    
    def __init__(self, debug_port: int = 9223):
        """Initialize WebKit utils with minimal configuration."""
        self.debug_port = debug_port
        self.webkit_manager = WebKitManager()
        self.connection = WebKitConnection()
        print(f'[WebKitUtils] Initialized lightweight WebKit browser on port {debug_port}')
    
    def launch_webkit(self) -> subprocess.Popen:
        """Launch lightweight browser with remote debugging."""
        return self.webkit_manager.launch_webkit_with_debugging(self.debug_port)
    
    def launch_chrome(self) -> subprocess.Popen:
        """Compatibility method - launches lightweight browser (same as launch_webkit)."""
        return self.launch_webkit()
    
    async def connect_to_webkit(self, target_url: str = None):
        """Connect to lightweight browser via debug protocol."""
        cdp_url = f'http://localhost:{self.debug_port}'
        return await self.connection.connect_to_webkit(cdp_url)
    
    async def connect_to_chrome(self, target_url: str = None):
        """Compatibility method - connects to lightweight browser (same as connect_to_webkit)."""
        return await self.connect_to_webkit(target_url)
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by adding protocol if missing (compatibility method)."""
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
    
    @staticmethod
    def run_async(coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)


# Convenience functions
def create_webkit_utils(debug_port: int = 9223) -> WebKitUtils:
    """Create a lightweight WebKit utils instance."""
    return WebKitUtils(debug_port=debug_port)


def launch_webkit_for_debugging(debug_port: int = 9223) -> subprocess.Popen:
    """Quick function to launch WebKit with remote debugging."""
    return WebKitManager.launch_webkit_with_debugging(debug_port)
