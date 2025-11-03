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

# Import the cookie utils from shared library
try:
    from shared.src.lib.utils.cookie_utils import CookieManager, auto_accept_cookies
except ImportError:
    print("Warning: Cookie utilities not available. Cookie management will be limited.")
    # Create dummy classes to prevent import errors
    class CookieManager:
        def __init__(self, *args, **kwargs): pass
        def auto_accept_cookies(self, *args, **kwargs): return False
    def auto_accept_cookies(*args, **kwargs): return False


def resolve_user_data_dir(user_data_dir: str) -> str:
    """Resolve user_data_dir to absolute path from project root."""
    if os.path.isabs(user_data_dir):
        return user_data_dir
    
    # Simple: go up 3 levels from /shared/lib/utils to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.abspath(os.path.join(project_root, user_data_dir.lstrip('./')))


class ChromeManager:
    """Manages Chrome process lifecycle for remote debugging."""
    
    @staticmethod
    def close_chrome_gracefully(debug_port: int = 9222, chrome_process = None):
        """Close Chrome gracefully via CDP, fallback to process termination."""
        print('[ChromeManager] Closing Chrome gracefully...')
        
        # First try CDP shutdown using Browser.close command
        try:
            import requests
            print('[ChromeManager] Attempting CDP shutdown...')
            
            # Send Browser.close command via CDP
            response = requests.post(f'http://localhost:{debug_port}/json/runtime/evaluate',
                                   json={
                                       'expression': 'window.chrome && window.chrome.app ? window.chrome.app.window.current().close() : window.close()'
                                   }, timeout=3)
            
            if response.status_code == 200:
                print('[ChromeManager] CDP shutdown command sent successfully')
                time.sleep(3)  # Give Chrome time to shut down gracefully
                
                # Check if Chrome actually closed
                try:
                    check_response = requests.get(f'http://localhost:{debug_port}/json', timeout=1)
                    if check_response.status_code != 200:
                        print('[ChromeManager] Chrome closed successfully via CDP')
                        return
                except:
                    print('[ChromeManager] Chrome closed successfully via CDP')
                    return
                    
        except Exception as e:
            print(f'[ChromeManager] CDP shutdown failed: {e}')
        
        # Fallback to process termination (but use SIGTERM first, not SIGKILL)
        if chrome_process and chrome_process.poll() is None:
            print('[ChromeManager] Using process termination fallback...')
            chrome_process.terminate()  # SIGTERM - allows graceful shutdown
            try:
                chrome_process.wait(timeout=10)  # Give more time for graceful shutdown
                print('[ChromeManager] Chrome process terminated gracefully')
            except subprocess.TimeoutExpired:
                print('[ChromeManager] Graceful termination timeout, force killing...')
                chrome_process.kill()  # Only use SIGKILL as last resort
                chrome_process.wait()
    
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
    def get_chrome_flags(debug_port: int = 9222, user_data_dir: str = "./backend_host/config/user_data") -> list:
        """
        Get Chrome launch flags for remote debugging with persistent data.
        
        Args:
            debug_port: Debug port for remote debugging
            user_data_dir: Chrome user data directory (relative to project root)
        """
        return [
            f'--remote-debugging-port={debug_port}',
            f'--user-data-dir={user_data_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--start-fullscreen',  # Launch Chrome in fullscreen mode
            '--disable-features=Translate,InfiniteSessionRestore,TabRestore,MediaRouter',
            '--disable-extensions',
            '--disable-session-crashed-bubble',  # Disable restore session popup
            '--disable-infobars',  # Disable info bars including restore prompts
            '--disable-background-timer-throttling',  # Prevent background issues
            '--disable-backgrounding-occluded-windows',  # Prevent window management issues
            '--disable-renderer-backgrounding',  # Keep renderer active
            '--disable-ipc-flooding-protection',  # Prevent IPC issues
            '--hide-crashed-bubble',  # Hide crash bubbles
            '--disable-component-extensions-with-background-pages',  # Disable background extensions
            '--disable-popup-blocking',  # Disable popup blocking (for automation)
            '--disable-prompt-on-repost',  # Disable repost confirmation prompts
            '--disable-hang-monitor',  # Disable hang detection
            '--disable-client-side-phishing-detection',  # Disable phishing detection popups
            '--disable-default-apps',  # Disable default app prompts
            '--disable-domain-reliability',  # Disable domain reliability reporting
            '--disable-background-networking',  # Disable background networking
            '--metrics-recording-only',  # Only record metrics, don't send
            '--no-crash-upload',  # Don't upload crash reports
            '--hide-crash-restore-bubble',  # Hide crash restore bubble
            '--disable-dev-shm-usage',  # Overcome limited resource problems on Pi
            '--memory-pressure-off',  # Disable memory pressure system
            '--max_old_space_size=512',  # Limit V8 heap size to 512MB
            '--enable-unsafe-swiftshader',  # Enable unsafe SwiftShader for GPU acceleration
            '--disable-gpu',  # Disable GPU acceleration to prevent GPU-related crashes
            '--force-fieldtrials=*BackgroundTracing/default/',  # Disable background tracing
            '--disable-crash-reporter',  # Disable crash reporter
            '--disable-logging',  # Disable logging that tracks crashes
            '--silent-debugger-extension-api',  # Silence debugger extension API
        ]
    
    @classmethod
    def launch_chrome_with_remote_debugging(cls, debug_port: int = 9222, user_data_dir: str = "./backend_host/config/user_data", 
                                          use_cgroup: bool = True, cpu_quota: str = "100%", memory_max: str = "4G", memory_high: str = "3G") -> subprocess.Popen:
        """
        Launch Chrome with remote debugging and persistent data.
        
        Args:
            debug_port: Port for remote debugging
            user_data_dir: Chrome user data directory (relative to project root)
            use_cgroup: Whether to use systemd-run with cgroup v2 resource limits
            cpu_quota: CPU quota limit (e.g., "50%" for 50% of one core)
            memory_max: Maximum memory limit (e.g., "1G", "512M")
            memory_high: Memory high limit for early pressure (e.g., "768M")
        """
        # Close existing Chrome instances gracefully
        cls.close_chrome_gracefully(debug_port)
        
        # Kill any process using the debug port
        if cls.is_port_in_use(debug_port):
            print(f'[ChromeManager] Port {debug_port} is in use. Killing processes...')
            # Use subprocess to avoid xargs executing kill with no arguments
            try:
                result = subprocess.run(['lsof', '-ti', f':{debug_port}'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            subprocess.run(['kill', '-9', pid.strip()], timeout=3)
                            print(f'[ChromeManager] Killed process {pid.strip()} using port {debug_port}')
                else:
                    print(f'[ChromeManager] No processes found using port {debug_port}')
            except subprocess.TimeoutExpired:
                print(f'[ChromeManager] Timeout finding processes on port {debug_port}')
            except Exception as e:
                print(f'[ChromeManager] Error killing processes on port {debug_port}: {e}')
            time.sleep(1)
        
        # Find Chrome executable
        executable_path = cls.find_chrome_executable()
        print(f'[ChromeManager] Launching Chrome with remote debugging: {executable_path}')
        
        # Prepare Chrome flags and user data directory (path should already be resolved)
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Clean up crash detection files only (keep session data for passwords/cookies)
        crash_files = ['Crash Reports', 'chrome_debug.log', 'Singleton*']
        for crash_file in crash_files:
            crash_path = os.path.join(user_data_dir, crash_file)
            if os.path.exists(crash_path):
                try:
                    if os.path.isfile(crash_path):
                        os.remove(crash_path)
                    elif os.path.isdir(crash_path):
                        import shutil
                        shutil.rmtree(crash_path)
                except Exception as e:
                    pass  # Ignore cleanup errors
        
        print(f'[ChromeManager] Using persistent profile: {user_data_dir}')
        
        chrome_flags = cls.get_chrome_flags(debug_port, user_data_dir)
        
        # Log all flags being applied
        print(f'[ChromeManager] Chrome flags being applied:')
        for i, flag in enumerate(chrome_flags, 1):
            print(f'[ChromeManager]   {i}. {flag}')
        
        # Construct Chrome command
        chrome_cmd = [executable_path] + chrome_flags
        
        # Build final command with optional cgroup v2 support
        if use_cgroup:
            print(f'[ChromeManager] Using cgroup v2 SOFT resource limits: CPUWeight=100, MemoryHigh={memory_high}, MemorySwapMax={memory_max}')
            
            # Build systemd-run command with cgroup v2 SOFT resource limits (throttle, don't kill)
            cmd_line = [
                'systemd-run',
                '--scope',
                '--user',
                f'-p=CPUWeight=100',          # Relative CPU priority (default weight)
                f'-p=MemoryHigh={memory_high}',  # Soft memory limit - throttles but doesn't kill
                f'-p=MemorySwapMax={memory_max}', # Allow swap usage up to memory_max
                f'-p=OOMScoreAdjust=500',     # Make less likely to be killed by OOM killer
                '--property=KillMode=mixed',  # Allow proper cleanup
                '--property=Type=forking',    # Handle Chrome's forking behavior
                '--slice=user-chrome.slice'   # Put in dedicated slice for better management
            ] + chrome_cmd
            
            print(f'[ChromeManager] Full systemd-run command: {" ".join(cmd_line)}')
        else:
            cmd_line = chrome_cmd
            print(f'[ChromeManager] Full Chrome command: {" ".join(cmd_line)}')
        
        # Set environment
        env = os.environ.copy()
        env["DISPLAY"] = ":1"
        
        # Launch Chrome (with or without cgroup limits) - capture stderr to detect errors
        process = subprocess.Popen(cmd_line, env=env, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print(f'[ChromeManager] Chrome launched with PID: {process.pid}')
        
        # Add process monitoring for debugging
        print(f'[ChromeManager] Chrome command line: {" ".join(cmd_line)}')
        print(f'[ChromeManager] Environment DISPLAY: {env.get("DISPLAY", "not set")}')
        
        # Wait for Chrome to be ready - pass process to check for early failures
        cls._wait_for_chrome_ready(debug_port, process)
        
        return process
    
    @staticmethod
    def _wait_for_chrome_ready(debug_port: int, process: subprocess.Popen = None, max_wait: int = 30):
        """
        Wait for Chrome to be ready on the debug port.
        
        Args:
            debug_port: Port to check
            process: Chrome process to monitor for early failures
            max_wait: Maximum seconds to wait
            
        Raises:
            RuntimeError: If Chrome process fails to start
        """
        print(f'[ChromeManager] Waiting up to {max_wait} seconds for Chrome on port {debug_port}...')
        
        start_time = time.time()
        port_open = False
        
        while time.time() - start_time < max_wait:
            # Check if process has exited early (indicates failure)
            if process:
                poll_result = process.poll()
                if poll_result is not None:
                    # Process has exited - get stderr output
                    try:
                        _, stderr = process.communicate(timeout=1)
                        stderr_text = stderr.decode('utf-8', errors='replace').strip() if stderr else ''
                    except Exception as e:
                        stderr_text = f'(failed to read stderr: {e})'
                    
                    error_msg = f'Chrome process exited prematurely with code {poll_result}'
                    if stderr_text:
                        error_msg += f'\nStderr: {stderr_text}'
                    
                    # Check for common errors
                    if 'not found' in stderr_text.lower():
                        error_msg += '\n\nChromium executable not found. Please install chromium-browser.'
                    
                    print(f'[ChromeManager] ERROR: {error_msg}')
                    raise RuntimeError(error_msg)
            
            # Try to connect to debug port
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
            error_msg = f'Timed out waiting for Chrome port {debug_port} after {max_wait} seconds'
            
            # If process is still running but port never opened
            if process and process.poll() is None:
                error_msg += '\nChrome process is still running but debug port is not accessible.'
            
            print(f'[ChromeManager] ERROR: {error_msg}')
            raise RuntimeError(error_msg)


class AsyncExecutor:
    """Handles async execution in sync contexts for Playwright operations."""
    
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
        # If we're on the Playwright worker thread, dispatch onto its dedicated loop
        try:
            if threading.current_thread().name == "PlaywrightWorker":
                from backend_host.src.lib.web_worker import WebWorker
                return WebWorker.instance().run_coro(coro)
        except Exception:
            # Fallback to legacy behavior if worker not available
            pass
        
        # Check if we're in the main thread
        is_main_thread = threading.current_thread() is threading.main_thread()
        
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            
            # Check if loop is running
            if loop.is_running():
                # We're in an async context - this shouldn't happen
                raise RuntimeError("Cannot run async code in already-running event loop. Use await instead.")
            
            # Loop exists but not running
            if is_main_thread:
                # In main thread, reuse the loop
                return loop.run_until_complete(coro)
            else:
                # In background thread, create new loop (don't reuse main thread's loop)
                return asyncio.run(coro)
                
        except RuntimeError:
            # No event loop exists in this thread - create one
            return asyncio.run(coro)


class PlaywrightConnection:
    """Manages Playwright connections to Chrome via CDP."""
    
    @staticmethod
    async def connect_to_chrome(cdp_url: str = 'http://localhost:9222') -> Tuple[Any, Any, Any, Any]:
        """Connect to Chrome via CDP and return playwright, browser, context, page."""
        from playwright.async_api import async_playwright
        
        try:
            print(f'[PlaywrightConnection] Starting Playwright and connecting to Chrome at {cdp_url}')
            playwright = await async_playwright().start()
            print(f'[PlaywrightConnection] Playwright started, attempting CDP connection...')
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
            print(f'[PlaywrightConnection] Successfully connected to Chrome via CDP')
            
            if len(browser.contexts) == 0:
                # Create new context with browser default viewport
                print(f'[PlaywrightConnection] No existing contexts, creating new context...')
                context = await browser.new_context()
                page = await context.new_page()
                print(f'[PlaywrightConnection] Created new context with browser default viewport')
            else:
                print(f'[PlaywrightConnection] Found {len(browser.contexts)} existing contexts, using first one...')
                context = browser.contexts[0]
                if len(context.pages) == 0:
                    print(f'[PlaywrightConnection] No pages in context, creating new page...')
                    page = await context.new_page()
                else:
                    print(f'[PlaywrightConnection] Found {len(context.pages)} pages in context, using first one...')
                    page = context.pages[0]
                print(f'[PlaywrightConnection] Using existing context with browser default viewport')
            
            print(f'[PlaywrightConnection] Connection established successfully')
            return playwright, browser, context, page
            
        except Exception as e:
            error_type = type(e).__name__
            print(f'[PlaywrightConnection] Connection failed - {error_type}: {str(e)}')
            print(f'[PlaywrightConnection] CDP URL: {cdp_url}')
            
            # Check if it's a connection refused error
            if 'ECONNREFUSED' in str(e) or 'Connection refused' in str(e):
                print(f'[PlaywrightConnection] Chrome is not running or not accepting connections on {cdp_url}')
            elif 'timeout' in str(e).lower():
                print(f'[PlaywrightConnection] Connection timeout - Chrome may be starting up or overloaded')
            
            raise Exception(f"CDP connection failed ({error_type}): {str(e)}")
    
    @staticmethod
    async def cleanup_connection(playwright, browser):
        """Clean up Playwright connection."""
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


class PlaywrightUtils:
    """Main utility class combining Chrome management, Playwright operations, and cookie management."""
    
    def __init__(self, auto_accept_cookies: bool = True, user_data_dir: str = "./backend_host/config/user_data",
                 use_cgroup: bool = False, cpu_quota: str = "100%", memory_max: str = "4G", memory_high: str = "3G"):
        """
        Initialize PlaywrightUtils with auto-sizing browser.
        
        Args:
            auto_accept_cookies: Whether to automatically inject consent cookies
            user_data_dir: Chrome user data directory for persistent sessions
            use_cgroup: Whether to use systemd-run with cgroup v2 resource limits
            cpu_quota: CPU quota limit (e.g., "50%" for 50% of one core)
            memory_max: Maximum memory limit (e.g., "1G", "512M")
            memory_high: Memory high limit for early pressure (e.g., "768M")
        """
        self.chrome_manager = ChromeManager()
        self.async_executor = AsyncExecutor()
        self.connection = PlaywrightConnection()
        self.cookie_manager = CookieManager() if auto_accept_cookies else None
        self.auto_accept_cookies = auto_accept_cookies
        self.user_data_dir = resolve_user_data_dir(user_data_dir)
        
        # Cgroup v2 resource limits
        self.use_cgroup = use_cgroup
        self.cpu_quota = cpu_quota
        self.memory_max = memory_max
        self.memory_high = memory_high
        
        cgroup_status = f"cgroup={use_cgroup}" if use_cgroup else "cgroup=disabled"
        if use_cgroup:
            cgroup_status += f" (CPU={cpu_quota}, Mem={memory_max}/{memory_high})"
        
        print(f'[PlaywrightUtils] Initialized with auto_accept_cookies={auto_accept_cookies}, viewport=auto (browser default), user_data_dir={self.user_data_dir}, {cgroup_status}')
    
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
    
    def launch_chrome(self, debug_port: int = 9222) -> subprocess.Popen:
        """Launch Chrome with remote debugging and persistent data."""
        # Launch Chrome maximized with persistent user data directory and optional cgroup limits
        return self.chrome_manager.launch_chrome_with_remote_debugging(
            debug_port, 
            user_data_dir=self.user_data_dir,
            use_cgroup=self.use_cgroup,
            cpu_quota=self.cpu_quota,
            memory_max=self.memory_max,
            memory_high=self.memory_high
        )
    
    def kill_chrome(self, chrome_process=None):
        """Close Chrome instances gracefully."""
        self.chrome_manager.close_chrome_gracefully(chrome_process=chrome_process)
    
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
        # Connect with browser default viewport
        playwright, browser, context, page = await self.connection.connect_to_chrome(cdp_url)
        
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
def create_playwright_utils(auto_accept_cookies: bool = True, user_data_dir: str = "./backend_host/config/user_data",
                           use_cgroup: bool = False, cpu_quota: str = "100%", memory_max: str = "4G", memory_high: str = "3G") -> PlaywrightUtils:
    """Create a PlaywrightUtils instance."""
    return PlaywrightUtils(auto_accept_cookies=auto_accept_cookies, user_data_dir=user_data_dir,
                          use_cgroup=use_cgroup, cpu_quota=cpu_quota, memory_max=memory_max, memory_high=memory_high)


def launch_chrome_for_debugging(debug_port: int = 9222, user_data_dir: str = "./backend_host/config/user_data",
                               use_cgroup: bool = False, cpu_quota: str = "100%", memory_max: str = "4G", memory_high: str = "3G") -> subprocess.Popen:
    """Quick function to launch Chrome with remote debugging and persistent data."""
    resolved_user_data_dir = resolve_user_data_dir(user_data_dir)
    return ChromeManager.launch_chrome_with_remote_debugging(debug_port, user_data_dir=resolved_user_data_dir,
                                                            use_cgroup=use_cgroup, cpu_quota=cpu_quota, 
                                                            memory_max=memory_max, memory_high=memory_high)


def run_async_playwright(coro):
    """Quick function to run async Playwright code in sync context."""
    return AsyncExecutor.run_async(coro)


def get_available_cookie_sites() -> list:
    """Quick function to get available cookie sites."""
    manager = CookieManager()
    return manager.get_available_configs()


# Browser-use compatibility functions
async def get_playwright_context_with_cookies(target_url: str = None):
    """
    Get a Playwright context with auto-injected cookies for browser-use compatibility.
    
    Args:
        target_url: URL to inject cookies for
        
    Returns:
        Tuple of (playwright, browser, context, page)
    """
    utils = PlaywrightUtils(auto_accept_cookies=True)
    return await utils.connect_to_chrome(target_url=target_url) 