#!/usr/bin/env python3
"""
VirtualPyTest Backend Host Application

This application runs the hardware interface service for VirtualPyTest.
It provides device control capabilities and hardware abstraction.

Usage:
    python3 app.py

Environment Variables Required (in .env file):
    SERVER_URL - Base URL of the backend_server (e.g., https://api.virtualpytest.com)
    HOST_URL - Base URL of this host (e.g., https://host1.virtualpytest.com)
    HOST_PORT - Port where Flask app runs (default: 6109)
    HOST_NAME - Name of this host (e.g., sunri-pi1)
    GITHUB_TOKEN - GitHub token for authentication (loaded when needed)
    DEBUG - Set to 'true' to enable debug mode (default: false)
"""

import sys
import os
import time
import atexit
import threading

# Setup path for shared library access
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_host_dir)

# Add project root to path for clear imports (shared.src.lib.*, backend_host.*)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Apply global typing compatibility early to fix third-party package issues
try:
    from shared.src.lib.utils.typing_compatibility import ensure_typing_compatibility
    ensure_typing_compatibility()
except ImportError:
    print("⚠️  Warning: Could not apply typing compatibility fix")

# Add backend_server to path for src.lib.* imports
if backend_host_dir not in sys.path:
    sys.path.insert(0, backend_host_dir)

# Add backend_host/src to path for local imports
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import from shared library and backend_host (using clear import paths)
try:
    # Import shared components
    from shared.src.lib.utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
        DEFAULT_USER_ID
    )
    # Import backend_host controllers and services
    from controllers import *
    from services import *
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    print("❌ Please ensure shared library and backend_host are properly installed")
    print("❌ Run: ./setup/local/install_all.sh")
    sys.exit(1)

# Local route imports  
try:
    from  backend_host.src.lib.utils.host_utils import (
        register_host_with_server,
        start_ping_thread,
        cleanup_on_exit
    )
except ImportError as e:
    print(f"❌ Failed to import host utilities: {e}")
    print("❌ Please ensure shared library is properly installed")
    sys.exit(1)

def register_host_routes(app):
    """Register all host routes - Hardware interface endpoints"""
    print("[@backend_host:routes] Loading host routes...")
    
    try:
        from routes import (
            host_control_routes,
            host_web_routes,
            host_verification_routes,
            host_power_routes,
            host_av_routes,
            host_restart_routes,
            host_system_routes,
            host_translation_routes,
            host_monitoring_routes,
            host_remote_routes,
            host_desktop_bash_routes,
            host_desktop_pyautogui_routes,
            host_script_routes,
            host_verification_appium_routes,
            host_verification_text_routes,
            host_verification_audio_routes,
            host_verification_adb_routes,
            host_verification_image_routes,
            host_verification_video_routes,
            host_verification_web_routes,
            host_actions_routes,
            host_navigation_routes,
            host_ai_routes,
            host_ai_disambiguation_routes,
            host_testcase_routes,
            host_campaign_routes,
            host_transcript_routes,
            host_deployment_routes,
            host_builder_routes,
            host_ai_exploration_routes
        )
        print("[@backend_host:routes] ✅ All route imports completed successfully!")
        
    except ImportError as e:
        print(f"[@backend_host:routes] ❌ CRITICAL: Cannot import host routes: {e}")
        print("[@backend_host:routes] ❌ This indicates missing dependencies or import path issues")
        import traceback
        traceback.print_exc()
        return False
    
    # Register all host blueprints
    blueprints = [
        (host_control_routes.host_control_bp, 'Device control'),
        (host_web_routes.host_web_bp, 'Web automation'),
        (host_verification_routes.host_verification_bp, 'Verification services'),
        (host_power_routes.host_power_bp, 'Power control'),
        (host_av_routes.host_av_bp, 'Audio/Video operations'),
        (host_restart_routes.host_restart_bp, 'Restart video system'),
        (host_system_routes.host_system_bp, 'Host system control'),
        (host_translation_routes.host_translation_bp, 'Translation services'),
        (host_monitoring_routes.host_monitoring_bp, 'Monitoring system'),
        (host_remote_routes.host_remote_bp, 'Remote device control'),
        (host_desktop_bash_routes.host_desktop_bash_bp, 'Bash desktop control'),
        (host_desktop_pyautogui_routes.host_desktop_pyautogui_bp, 'PyAutoGUI desktop control'),
        (host_script_routes.host_script_bp, 'Script execution'),
        (host_verification_appium_routes.host_verification_appium_bp, 'Appium verification'),
        (host_verification_text_routes.host_verification_text_bp, 'Text verification'),
        (host_verification_audio_routes.host_verification_audio_bp, 'Audio verification'),
        (host_verification_adb_routes.host_verification_adb_bp, 'ADB verification'),
        (host_verification_image_routes.host_verification_image_bp, 'Image verification'),
        (host_verification_video_routes.host_verification_video_bp, 'Video verification'),
        (host_verification_web_routes.host_verification_web_bp, 'Web verification'),
        (host_actions_routes.host_actions_bp, 'Action execution'),
        (host_navigation_routes.host_navigation_bp, 'Navigation execution'),
        (host_ai_routes.host_ai_bp, 'AI execution'),
        (host_ai_disambiguation_routes.host_ai_disambiguation_bp, 'AI disambiguation'),
        (host_testcase_routes.host_testcase_bp, 'TestCase Builder'),
        (host_campaign_routes.host_campaign_bp, 'Campaign execution'),
        (host_transcript_routes.host_transcript_bp, 'Transcript services'),
        (host_deployment_routes.host_deployment_bp, 'Deployment scheduling'),
        (host_builder_routes.host_builder_bp, 'Standard blocks'),
        (host_ai_exploration_routes.host_ai_exploration_bp, 'AI tree exploration')
    ]
    
    for blueprint, description in blueprints:
        try:
            app.register_blueprint(blueprint)
            print(f"✅ Registered {description}")
        except Exception as e:
            print(f"❌ Failed to register {description}: {e}")
            return False
    
    return True

def setup_host_cleanup():
    """Setup cleanup handlers for host"""
    def cleanup():
        print("[@host:main:cleanup] Cleaning up host resources...")
        cleanup_on_exit()
    
    atexit.register(cleanup)

def start_background_services():
    """Start background services for host communication"""
    def start_services():
        time.sleep(2)  # Wait for Flask to start
        register_host_with_server()
        start_ping_thread()
        
        # Start deployment scheduler
        try:
            from backend_host.src.services.deployment_scheduler import get_deployment_scheduler
            print("[@backend_host:main] Starting deployment scheduler...")
            scheduler = get_deployment_scheduler()
            print("[@backend_host:main] ✓ Deployment scheduler started")
        except Exception as e:
            print(f"[@backend_host:main] ⚠️  Deployment scheduler not available: {e}")
        
        # Note: KPI measurement service is started in main() at Step 4.1
    
    thread = threading.Thread(target=start_services, daemon=True)
    thread.start()

def cleanup_host_ports():
    """Clean up any processes using host ports"""
    host_port = int(os.getenv('HOST_PORT', '6109'))
    kill_process_on_port(host_port)

def setup_api_authentication(app):
    """Setup global API key authentication for all /host/* routes"""
    from flask import request, jsonify
    from shared.src.lib.utils.auth_utils import validate_api_key
    
    @app.before_request
    def check_api_key():
        """Global API key check for all /host/* routes"""
        # Only check /host/* routes (not health checks or other endpoints)
        if not request.path.startswith('/host/'):
            return None
        
        # Validate API key
        is_valid, error_response = validate_api_key()
        
        if not is_valid:
            print(f"[@backend_host:auth] ❌ API key validation failed for {request.path}")
            print(f"[@backend_host:auth]    From: {request.remote_addr}")
            print(f"[@backend_host:auth]    Reason: {error_response.get('message')}")
            return jsonify(error_response), 401
        
        # Valid API key - allow request to proceed
        return None

def main():
    """Main function for backend_host application"""
    print("🏠 VIRTUALPYTEST backend_host")
    print("Starting VirtualPyTest Hardware Interface Service")
    
    # STEP 1: Validate Environment
    print("[@backend_host:main] Step 1: Validating environment...")
    calling_script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = load_environment_variables(mode='host', calling_script_dir=calling_script_dir)
    
    if not validate_core_environment(mode='host'):
        print("[@backend_host:main] ❌ Core environment validation failed")
        sys.exit(1)
    
    # Print database URL for verification
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL', 'NOT SET')
    print(f"[@backend_host:main] 🗄️  Database Configuration:")
    print(f"[@backend_host:main]    NEXT_PUBLIC_SUPABASE_URL: {supabase_url}")
    print("[@backend_host:main] ✅ Environment validated")
    
    # STEP 2: Setup Flask App
    print("[@backend_host:main] Step 2: Setting up Flask application...")
    cleanup_host_ports()
    time.sleep(1)
    
    # STEP 2.1: Clear navigation file cache on startup
    print("[@backend_host:main] Step 2.1: Clearing navigation file cache...")
    try:
        from shared.src.lib.utils.navigation_cache import clear_unified_cache
        clear_unified_cache()  # Clear all file caches
        print("[@backend_host:main] ✅ Navigation file cache cleared")
    except Exception as e:
        print(f"[@backend_host:main] ⚠️  Failed to clear navigation cache: {e}")
    
    app = setup_flask_app("VirtualPyTest-backend_host")
    
    with app.app_context():
        app.default_user_id = DEFAULT_USER_ID
        
        # STEP 2.5: Initialize host devices with executors
        print("[@backend_host:main] Step 2.5: Initializing host devices with executors...")
        try:
            from backend_host.src.controllers.controller_manager import get_host
            
            host = get_host()
            
            # Create device registry for routes to access
            app.host_devices = {}
            for device in host.get_devices():
                app.host_devices[device.device_id] = device
                print(f"[@backend_host:main] ✓ Registered device: {device.device_id} ({device.device_model})")
                
            # Verify executors were created
                if hasattr(device, 'action_executor') and device.action_executor:
                    print(f"[@backend_host:main]   ✓ ActionExecutor ready")
                if hasattr(device, 'navigation_executor') and device.navigation_executor:
                    print(f"[@backend_host:main]   ✓ NavigationExecutor ready")
                if hasattr(device, 'verification_executor') and device.verification_executor:
                    print(f"[@backend_host:main]   ✓ VerificationExecutor ready")
                if hasattr(device, 'standard_block_executor') and device.standard_block_executor:
                    print(f"[@backend_host:main]   ✓ StandardBlockExecutor ready")
                if hasattr(device, 'ai_executor') and device.ai_executor:
                    print(f"[@backend_host:main]   ✓ AIExecutor ready")
            
            print(f"[@backend_host:main] ✅ Initialized {len(app.host_devices)} devices with executors")
            
        except Exception as e:
            print(f"[@backend_host:main] ❌ Failed to initialize host devices: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # STEP 3: Register Routes
    print("[@backend_host:main] Step 3: Registering hardware interface routes...")
    if not register_host_routes(app):
        print("[@backend_host:main] ❌ CRITICAL: Failed to register host routes")
        print("[@backend_host:main] ❌ Cannot start host without all routes properly loaded")
        sys.exit(1)
    
    # STEP 3.5: Setup Global API Key Authentication
    print("[@backend_host:main] Step 3.5: Setting up API key authentication...")
    setup_api_authentication(app)
    print("[@backend_host:main] ✅ API key authentication enabled for all /host/* routes")
    
    # STEP 4: Start Host Services
    print("[@backend_host:main] Step 4: Starting host services...")
    setup_host_cleanup()
    
    # STEP 4.1: KPI Executor runs as separate systemd service (kpi-executor.service)
    print("[@backend_host:main] Step 4.1: KPI Executor")
    print("[@backend_host:main]   Note: KPI Executor runs as separate service (backend_host/scripts/kpi_executor.py)")
    print("[@backend_host:main]   Queue: JSON files in /tmp/kpi_queue/")
    
    # Get configuration
    host_port = int(os.getenv('HOST_PORT', '6109'))
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    host_name = os.getenv('HOST_NAME', 'unknown-host')
    host_url = os.getenv('HOST_URL', f'http://localhost:{host_port}')
    
    print(f"[@backend_host:main] Host Information:")
    print(f"[@backend_host:main]    Host Name: {host_name}")
    print(f"[@backend_host:main]    Host URL: {host_url}")
    print(f"[@backend_host:main]    Host Port: {host_port}")
    
    # Start background services
    start_background_services()
    
    # Start Flask application
    print("[@backend_host:main] 🎉 backend_host ready!")
    print(f"[@backend_host:main] 🚀 Starting hardware interface on port {host_port}")
    
    try:
        import gunicorn.app.base
        
        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                config = {key: value for key, value in self.options.items()
                        if key in self.cfg.settings and value is not None}
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            'bind': f'0.0.0.0:{host_port}',
            'workers': 1,  # Single worker for shared in-memory cache consistency (navigation cache)
            'threads': 1,  # 1 thread to handle async playwright
            'timeout': 3600  # 1 hour timeout to match server timeout
        }
        
        StandaloneApplication(app, options).run()
        
    except ImportError:
        print("[@backend_host:main] ❌ Gunicorn required. Install: pip install gunicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"[@backend_host:main] 🛑 backend_host shutting down...")
    except Exception as e:
        print(f"[@backend_host:main] ❌ Error starting backend_host: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print(f"[@backend_host:main] 👋 backend_host application stopped")

if __name__ == '__main__':
    main() 