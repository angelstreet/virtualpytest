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
            ('/usr/bin/chromium', 'chromium-webkit'),          # Chromium (Debian/Ubuntu default)
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
            # Flags matching the working manual command: docker exec ... chromium
            # Key: NO crash-dumps-dir, NO bash/su wrappers, just direct flags
            # Window flags are chosen so the browser uses the FULL VNC desktop area:
            # - start-maximized: request full-screen window
            # - window-position=0,0: anchor in top-left corner of the virtual display
            return [
                f'--remote-debugging-port={debug_port}',
                '--remote-debugging-address=0.0.0.0',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-crash-reporter',
                '--disable-crashpad',
                '--no-first-run',
                '--disable-breakpad',
                '--disable-dev-shm-usage',
                '--disable-gpu-compositing',          # Reduce GPU errors
                '--disable-features=DbusService,IsolateOrigins,site-per-process',  # Reduce memory usage
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-site-isolation-trials',    # Reduce memory overhead
                '--single-process',
                '--no-zygote',
                '--disable-extensions',
                '--js-flags=--max-old-space-size=256',  # Limit JavaScript heap (256MB)
                '--max-old-space-size=256',           # Additional memory limit
                '--start-maximized',                  # <<< use full width/height of VNC desktop
                '--window-position=0,0',
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
        """Launch lightweight browser with remote debugging.
        
        Uses DIRECT execution approach (same as playwright_utils.py) - no bash/su wrappers.
        This matches the working manual command: docker exec ... chromium --flags
        
        IMPORTANT: Ensures all existing browser processes are killed before launching new one.
        """
        print(f'[WebKitManager] Cleaning up any existing browser processes before launch...')
        
        # 1) Kill ALL browser processes (not just chromium)
        browsers_to_kill = ['chromium', 'chromium-browser', 'chrome', 'google-chrome', 'firefox']
        for browser in browsers_to_kill:
            try:
                result = subprocess.run(['pkill', '-9', browser], capture_output=True, timeout=5)
                if result.returncode == 0:
                    print(f'[WebKitManager] Killed existing {browser} processes')
            except Exception as e:
                pass  # Ignore errors if process doesn't exist
        
        time.sleep(2)  # Give time for processes to fully terminate

        # 2) Kill any process using the debug port (critical for clean launch)
        if cls.is_port_in_use(debug_port):
            print(f'[WebKitManager] Port {debug_port} is in use. Killing processes...')
            try:
                result = subprocess.run(['lsof', '-ti', f':{debug_port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            subprocess.run(['kill', '-9', pid.strip()], timeout=3)
                            print(f'[WebKitManager] Killed process {pid.strip()} using port {debug_port}')
            except Exception as e:
                print(f'[WebKitManager] Error killing processes on port {debug_port}: {e}')
            time.sleep(2)
        
        # 3) Verify port is now free
        if cls.is_port_in_use(debug_port):
            raise RuntimeError(f'Port {debug_port} still in use after cleanup. Cannot launch browser.')
        
        print(f'[WebKitManager] ✓ All existing browsers cleaned up, port {debug_port} is free')

        # 4) Find executable and get flags
        executable_path, browser_type = cls.find_webkit_executable()
        print(f'[WebKitManager] Launching {browser_type} browser: {executable_path}')

        browser_flags = cls.get_webkit_flags(debug_port, browser_type)

        # 5) Build command as LIST (not string!) - same as playwright_utils.py
        cmd_line = [executable_path] + browser_flags
        
        # 6) Set environment with DISPLAY
        env = os.environ.copy()
        env['DISPLAY'] = ':1'
        
        # Log command for debugging
        print(f'[WebKitManager] Command: {" ".join(cmd_line)}')
        print(f'[WebKitManager] Environment DISPLAY: {env.get("DISPLAY")}')
        
        # 7) Launch directly with subprocess.Popen (NO BASH, NO SU!)
        # Use DEVNULL and start_new_session to fully detach from Flask's process group
        process = subprocess.Popen(
            cmd_line,  # LIST of arguments (not a string!)
            env=env,
            stdout=subprocess.DEVNULL,  # Use subprocess constant instead of file handle
            stderr=subprocess.DEVNULL,  # Use subprocess constant instead of file handle
            start_new_session=True      # Detach from parent process group (critical for Flask)
        )
        
        print(f'[WebKitManager] Chromium launched with PID: {process.pid}')

        # 8) Wait for Chrome to be ready
        cls._wait_for_webkit_ready(debug_port, max_wait=30)

        # 9) Optional diagnostics
        try:
            result = subprocess.run(['pgrep', 'chromium'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = [p for p in result.stdout.strip().split('\n') if p]
                print(f'[WebKitManager] Chromium processes: {len(pids)} ({", ".join(pids[:5])})')
            else:
                print('[WebKitManager] Chromium processes: 0')
        except Exception as e:
            print(f'[WebKitManager] pgrep chromium failed: {e}')

        try:
            result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True)
            if f':{debug_port}' in result.stdout:
                print(f'[WebKitManager] ✓ Port {debug_port} LISTENING')
            else:
                print(f'[WebKitManager] ✗ Port {debug_port} NOT listening')
        except Exception as e:
            print(f'[WebKitManager] netstat check failed: {e}')

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
    async def connect_to_webkit(cdp_url: str = 'http://127.0.0.1:9223') -> Tuple[Any, Any, Any, Any]:
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
        cdp_url = f'http://127.0.0.1:{self.debug_port}'  # Use IPv4 explicitly to avoid IPv6 issues
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
    
    def kill_chrome(self, chrome_process=None):
        """Compatibility method - terminates any running lightweight browser process."""
        try:
            # If specific process provided, kill it first
            if chrome_process and chrome_process.poll() is None:
                try:
                    chrome_process.terminate()
                    chrome_process.wait(timeout=3)
                    print(f'[WebKitUtils] Terminated process {chrome_process.pid}')
                except Exception as e:
                    print(f'[WebKitUtils] Error terminating process: {e}')
            
            # Kill any process using the debug port
            if self.webkit_manager.is_port_in_use(self.debug_port):
                print(f'[WebKitUtils] Killing processes on port {self.debug_port}...')
                result = subprocess.run(['lsof', '-ti', f':{self.debug_port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            subprocess.run(['kill', '-9', pid.strip()], timeout=3)
                            print(f'[WebKitUtils] Killed process {pid.strip()}')
                time.sleep(1)
        except Exception as e:
            print(f'[WebKitUtils] Error killing browser: {e}')
    
    @staticmethod
    def run_async(coro):
        """
        Run async coroutine in sync context with proper event loop handling.
        
        Key scenarios:
        1. Main thread with no loop: create one with asyncio.run()
        2. Main thread with stopped loop: use run_until_complete()
        3. Background thread (like async execution): create new loop with asyncio.run()
        4. Already in async context (loop running): ERROR - should use await instead
        """
        import threading
        
        # Check if we're in the main thread
        is_main_thread = threading.current_thread() is threading.main_thread()
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot run async code in already-running event loop. Use await instead.")
            
            # Loop exists but not running
            if is_main_thread:
                return loop.run_until_complete(coro)
            else:
                # In background thread, create new loop
                return asyncio.run(coro)
        except RuntimeError:
            return asyncio.run(coro)


# Convenience functions
def create_webkit_utils(debug_port: int = 9223) -> WebKitUtils:
    """Create a lightweight WebKit utils instance."""
    return WebKitUtils(debug_port=debug_port)


def launch_webkit_for_debugging(debug_port: int = 9223) -> subprocess.Popen:
    """Quick function to launch WebKit with remote debugging."""
    return WebKitManager.launch_webkit_with_debugging(debug_port)
