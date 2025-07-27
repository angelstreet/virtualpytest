#!/usr/bin/env python3
"""
VirtualPyTest Backend Host Application

This application runs the hardware interface service for VirtualPyTest.
It provides device control capabilities and hardware abstraction.

Usage:
    python3 app.py

Environment Variables Required (in .env file):
    SERVER_URL - Base URL of the backend-server (e.g., https://api.virtualpytest.com)
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

# Add shared library to path
shared_lib_path = os.path.join(project_root, 'shared', 'lib')
backend_core_path = os.path.join(project_root, 'backend-core', 'src')

if shared_lib_path not in sys.path:
    sys.path.insert(0, shared_lib_path)
if backend_core_path not in sys.path:
    sys.path.insert(0, backend_core_path)

# Import from shared library and backend-core
try:
    # Import shared components (installed as packages)
    from utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
        DEFAULT_TEAM_ID,
        DEFAULT_USER_ID
    )
    # Import backend-core controllers and services
    from controllers import *
    from services import *
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    print("❌ Please ensure shared library and backend-core are properly installed")
    print("❌ Run: ./setup/local/install_local.sh")
    sys.exit(1)

# Local route imports  
try:
    from utils.host_utils import (
        register_host_with_server,
        start_ping_thread,
        cleanup_on_exit
    )
except ImportError as e:
    print(f"❌ Failed to import local modules: {e}")
    print("❌ Please ensure utils modules exist")
    sys.exit(1)

def register_host_routes(app):
    """Register all host routes - Hardware interface endpoints"""
    from routes import (
        host_rec_routes,
        host_control_routes, 
        host_web_routes,
        host_aiagent_routes,
        host_verification_routes,
        host_power_routes,
        host_av_routes,
        host_remote_routes,
        host_desktop_bash_routes,
        host_desktop_pyautogui_routes,
        host_script_routes,
        host_heatmap_routes
    )
    
    # Register all host blueprints
    blueprints = [
        (host_rec_routes.host_rec_bp, 'Recording operations'),
        (host_control_routes.host_control_bp, 'Device control'),
        (host_web_routes.host_web_bp, 'Web automation'),
        (host_aiagent_routes.host_aiagent_bp, 'AI agent execution'),
        (host_verification_routes.host_verification_bp, 'Verification services'),
        (host_power_routes.host_power_bp, 'Power control'),
        (host_av_routes.host_av_bp, 'Audio/Video operations'),
        (host_remote_routes.host_remote_bp, 'Remote device control'),
        (host_desktop_bash_routes.host_desktop_bash_bp, 'Bash desktop control'),
        (host_desktop_pyautogui_routes.host_desktop_pyautogui_bp, 'PyAutoGUI desktop control'),
        (host_script_routes.host_script_bp, 'Script execution'),
        (host_heatmap_routes.host_heatmap_bp, 'Heatmap data collection')
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
    """Main function for backend-host application"""
    print("🏠 VIRTUALPYTEST BACKEND-HOST")
    print("Starting VirtualPyTest Hardware Interface Service")
    
    # STEP 1: Validate Environment
    print("[@backend-host:main] Step 1: Validating environment...")
    calling_script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = load_environment_variables(mode='host', calling_script_dir=calling_script_dir)
    
    if not validate_core_environment(mode='host'):
        print("[@backend-host:main] ❌ Core environment validation failed")
        sys.exit(1)
    
    # STEP 2: Setup Flask App
    print("[@backend-host:main] Step 2: Setting up Flask application...")
    cleanup_host_ports()
    time.sleep(1)
    
    app = setup_flask_app("VirtualPyTest-Backend-Host")
    
    # Initialize app context
    with app.app_context():
        app.default_team_id = DEFAULT_TEAM_ID
        app.default_user_id = DEFAULT_USER_ID
    
    # STEP 3: Register Routes
    print("[@backend-host:main] Step 3: Registering hardware interface routes...")
    if not register_host_routes(app):
        print("[@backend-host:main] ❌ Failed to register routes")
        sys.exit(1)
    
    # STEP 4: Start Host Services
    print("[@backend-host:main] Step 4: Starting host services...")
    setup_host_cleanup()
    
    # Get configuration
    host_port = int(os.getenv('HOST_PORT', '6109'))
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    host_name = os.getenv('HOST_NAME', 'unknown-host')
    host_url = os.getenv('HOST_URL', f'http://localhost:{host_port}')
    
    print(f"[@backend-host:main] Host Information:")
    print(f"[@backend-host:main]    Host Name: {host_name}")
    print(f"[@backend-host:main]    Host URL: {host_url}")
    print(f"[@backend-host:main]    Host Port: {host_port}")
    
    # Start background services
    start_background_services()
    
    # Start Flask application
    print("[@backend-host:main] 🎉 Backend-Host ready!")
    print(f"[@backend-host:main] 🚀 Starting hardware interface on port {host_port}")
    
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
            'workers': 1,
            'timeout': 60,
        }
        
        StandaloneApplication(app, options).run()
        
    except ImportError:
        print("[@backend-host:main] ❌ Gunicorn required. Install: pip install gunicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"[@backend-host:main] 🛑 Backend-Host shutting down...")
    except Exception as e:
        print(f"[@backend-host:main] ❌ Error starting backend-host: {e}")
        sys.exit(1)
    finally:
        print(f"[@backend-host:main] 👋 Backend-Host application stopped")

if __name__ == '__main__':
    main() 