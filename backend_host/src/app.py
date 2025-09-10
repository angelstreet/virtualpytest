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

# Add project root to path for clear imports (shared.lib.*, backend_core.*)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from shared library and backend_core (using clear import paths)
try:
    # Import shared components
    from shared.lib.utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
        DEFAULT_TEAM_ID,
        DEFAULT_USER_ID
    )
    # Import backend_core controllers and services
    from backend_core.src.controllers import *
    from backend_core.src.services import *
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    print("❌ Please ensure shared library and backend_core are properly installed")
    print("❌ Run: ./setup/local/install_all.sh")
    sys.exit(1)

# Local route imports  
try:
    from shared.lib.utils.host_utils import (
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
    from routes import (
        host_control_routes, 
        host_web_routes,
        host_aiagent_routes,
        host_ai_generation_routes,
        host_aitestcase_routes,
        host_verification_routes,
        host_power_routes,
        host_av_routes,
        host_remote_routes,
        host_desktop_bash_routes,
        host_desktop_pyautogui_routes,
        host_script_routes,
        host_heatmap_routes,
        host_verification_appium_routes,
        host_verification_text_routes,
        host_verification_audio_routes,
        host_verification_adb_routes,
        host_verification_image_routes,
        host_verification_video_routes
    )
    
    # Register all host blueprints
    blueprints = [
        (host_control_routes.host_control_bp, 'Device control'),
        (host_web_routes.host_web_bp, 'Web automation'),
        (host_aiagent_routes.host_aiagent_bp, 'AI agent execution'),
        (host_ai_generation_routes.host_ai_generation_bp, 'AI interface generation'),
        (host_aitestcase_routes.host_aitestcase_bp, 'AI test case execution'),
        (host_verification_routes.host_verification_bp, 'Verification services'),
        (host_power_routes.host_power_bp, 'Power control'),
        (host_av_routes.host_av_bp, 'Audio/Video operations'),
        (host_remote_routes.host_remote_bp, 'Remote device control'),
        (host_desktop_bash_routes.host_desktop_bash_bp, 'Bash desktop control'),
        (host_desktop_pyautogui_routes.host_desktop_pyautogui_bp, 'PyAutoGUI desktop control'),
        (host_script_routes.host_script_bp, 'Script execution'),
        (host_heatmap_routes.host_heatmap_bp, 'Heatmap data collection'),
        (host_verification_appium_routes.host_verification_appium_bp, 'Appium verification'),
        (host_verification_text_routes.host_verification_text_bp, 'Text verification'),
        (host_verification_audio_routes.host_verification_audio_bp, 'Audio verification'),
        (host_verification_adb_routes.host_verification_adb_bp, 'ADB verification'),
        (host_verification_image_routes.host_verification_image_bp, 'Image verification'),
        (host_verification_video_routes.host_verification_video_bp, 'Video verification')
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
    
    thread = threading.Thread(target=start_services, daemon=True)
    thread.start()

def cleanup_host_ports():
    """Clean up any processes using host ports"""
    host_port = int(os.getenv('HOST_PORT', '6109'))
    kill_process_on_port(host_port)

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
    
    # STEP 2: Setup Flask App
    print("[@backend_host:main] Step 2: Setting up Flask application...")
    cleanup_host_ports()
    time.sleep(1)
    
    app = setup_flask_app("VirtualPyTest-backend_host")
    
    # Initialize app context
    with app.app_context():
        app.default_team_id = DEFAULT_TEAM_ID
        app.default_user_id = DEFAULT_USER_ID
    
    # STEP 3: Register Routes
    print("[@backend_host:main] Step 3: Registering hardware interface routes...")
    if not register_host_routes(app):
        print("[@backend_host:main] ❌ Failed to register routes")
        sys.exit(1)
    
    # STEP 4: Start Host Services
    print("[@backend_host:main] Step 4: Starting host services...")
    setup_host_cleanup()
    
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
            'workers': 2,  # " devices management and hardware control"
            'threads': 1,  # 1 thread to handle async playwright
            'timeout': 3600,  # 1 hour timeout to match server timeout
        }
        
        StandaloneApplication(app, options).run()
        
    except ImportError:
        print("[@backend_host:main] ❌ Gunicorn required. Install: pip install gunicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"[@backend_host:main] 🛑 backend_host shutting down...")
    except Exception as e:
        print(f"[@backend_host:main] ❌ Error starting backend_host: {e}")
        sys.exit(1)
    finally:
        print(f"[@backend_host:main] 👋 backend_host application stopped")

if __name__ == '__main__':
    main() 