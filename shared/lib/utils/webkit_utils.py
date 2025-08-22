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
    def find_webkit_executable() -> str:
        """Find WebKit/Safari executable on system."""
        # On macOS, use Safari
        if os.path.exists('/Applications/Safari.app/Contents/MacOS/Safari'):
            return '/Applications/Safari.app/Contents/MacOS/Safari'
        
        # On Linux, try to find webkit-based browsers
        possible_paths = [
            '/usr/bin/epiphany-browser',  # GNOME Web (WebKit)
            '/usr/bin/midori',            # Midori (WebKit)
            '/usr/bin/surf',              # Surf (WebKit)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        raise ValueError('No WebKit-based browser found. Install epiphany-browser, midori, or surf on Linux')
    
    @staticmethod
    def get_webkit_flags(debug_port: int = 9223) -> list:
        """Get WebKit launch flags for remote debugging."""
        return [
            f'--remote-debugging-port={debug_port}',
            '--no-first-run',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-sync',
            '--disable-translate',
            '--disable-features=TranslateUI',
            '--no-default-browser-check',
            '--disable-default-apps'
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
        """Launch WebKit browser with remote debugging."""
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
        
        # Find WebKit executable
        executable_path = cls.find_webkit_executable()
        print(f'[WebKitManager] Launching WebKit browser: {executable_path}')
        
        # Get WebKit flags
        webkit_flags = cls.get_webkit_flags(debug_port)
        
        # Launch WebKit
        cmd_line = [executable_path] + webkit_flags
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        
        process = subprocess.Popen(cmd_line, env=env)
        print(f'[WebKitManager] WebKit launched with PID: {process.pid}')
        
        # Wait for WebKit to be ready
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
    """Manages Playwright connections to WebKit via debug protocol."""
    
    @staticmethod
    async def connect_to_webkit(cdp_url: str = 'http://localhost:9223') -> Tuple[Any, Any, Any, Any]:
        """Connect to WebKit via debug protocol and return playwright, browser, context, page."""
        from playwright.async_api import async_playwright
        
        try:
            print(f'[WebKitConnection] Connecting to WebKit at {cdp_url}')
            playwright = await async_playwright().start()
            
            # Connect to WebKit browser
            browser = await playwright.webkit.connect_over_cdp(cdp_url)
            print(f'[WebKitConnection] Connected to WebKit successfully')
            
            # Get or create context and page
            if len(browser.contexts) == 0:
                context = await browser.new_context()
                page = await context.new_page()
                print(f'[WebKitConnection] Created new WebKit context')
            else:
                context = browser.contexts[0]
                if len(context.pages) == 0:
                    page = await context.new_page()
                else:
                    page = context.pages[0]
                print(f'[WebKitConnection] Using existing WebKit context')
            
            return playwright, browser, context, page
            
        except Exception as e:
            print(f'[WebKitConnection] Connection failed: {e}')
            raise Exception(f"WebKit connection failed: {str(e)}")


class WebKitUtils:
    """Lightweight WebKit utility class - minimal resource usage alternative to Chrome."""
    
    def __init__(self, debug_port: int = 9223):
        """Initialize WebKit utils with minimal configuration."""
        self.debug_port = debug_port
        self.webkit_manager = WebKitManager()
        self.connection = WebKitConnection()
        print(f'[WebKitUtils] Initialized lightweight WebKit browser on port {debug_port}')
    
    def launch_webkit(self) -> subprocess.Popen:
        """Launch WebKit with remote debugging."""
        return self.webkit_manager.launch_webkit_with_debugging(self.debug_port)
    
    async def connect_to_webkit(self, target_url: str = None):
        """Connect to WebKit via debug protocol."""
        cdp_url = f'http://localhost:{self.debug_port}'
        return await self.connection.connect_to_webkit(cdp_url)
    
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
