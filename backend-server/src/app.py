#!/usr/bin/env python3
"""
VirtualPyTest Backend Server Application

Main API server handling client requests and orchestration.
Provides REST API endpoints, WebSocket handling, and business logic coordination.

Usage: python3 app.py

Environment Variables Required (in .env.server file):
    SERVER_URL - Base URL of this server (e.g., https://api.virtualpytest.com)
    SERVER_PORT - Port for this server (default: 5109)
    GITHUB_TOKEN - GitHub token for authentication (loaded when needed)
    DEBUG - Set to 'true' to enable debug mode (default: false)
"""

import sys
import os
import time
import atexit
import uuid

# Setup path for shared library access
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_server_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_server_dir)

# Add shared library to path
shared_lib_path = os.path.join(project_root, 'shared', 'lib')
if shared_lib_path not in sys.path:
    sys.path.insert(0, shared_lib_path)

# Import from shared library
try:
    from shared.lib.config.settings import shared_config
except ImportError as e:
    print(f"❌ CRITICAL: Cannot import shared config: {e}")
    sys.exit(1)

# Local imports
try:
    from utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
        DEFAULT_TEAM_ID,
        DEFAULT_USER_ID
    )
except ImportError as e:
    print(f"❌ CRITICAL: Cannot import app_utils: {e}")
    print("   Make sure app_utils.py exists in the utils directory")
    sys.exit(1)

def validate_startup_requirements():
    """Validate requirements for server startup"""
    print("[@backend-server:validate] Validating startup requirements...")
    
    calling_script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = load_environment_variables(mode='server', calling_script_dir=calling_script_dir)
    
    if not validate_core_environment(mode='server'):
        print("❌ CRITICAL: Environment validation failed. Check .env.server file")
        sys.exit(1)
    
    print("✅ Startup requirements validated")

def setup_and_cleanup():
    """Setup Flask app and cleanup ports"""
    print("[@backend-server:setup] Setting up Flask application...")
    
    # Get server port and clean it up
    server_port = int(os.getenv('SERVER_PORT', '5109'))
    kill_process_on_port(server_port)
    time.sleep(1)
    
    # Create Flask app
    app = setup_flask_app("VirtualPyTest-Backend-Server")
    
    # Initialize app context
    with app.app_context():
        app.default_team_id = DEFAULT_TEAM_ID
        app.default_user_id = DEFAULT_USER_ID
        app.unique_server_id = str(uuid.uuid4())[:8]
    
    print("✅ Flask application setup completed")
    return app

def register_all_server_routes(app):
    """Register all server routes - Client-facing API endpoints"""
    print("[@backend-server:routes] Loading server routes...")
    
    try:
        from .routes import (
            server_system_routes,
            server_web_routes,
            server_rec_routes,
            common_core_routes
        )
        
        # Register all server blueprints
        blueprints = [
            (server_system_routes.server_system_bp, 'System management'),
            (server_web_routes.server_web_bp, 'Web interface'),
            (server_rec_routes.server_rec_bp, 'Recording operations'),
            (common_core_routes.common_core_bp, 'Common core API')
        ]
        
        for blueprint, description in blueprints:
            try:
                app.register_blueprint(blueprint)
                print(f"✅ Registered {description}")
            except Exception as e:
                print(f"❌ Failed to register {description}: {e}")
                return False
        
        print("✅ All server routes registered successfully")
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL: Cannot load routes: {e}")
        return False

def setup_server_cleanup():
    """Setup cleanup handlers for server"""
    def cleanup():
        print("[@backend-server:cleanup] Cleaning up server resources...")
    
    atexit.register(cleanup)

def start_server(app):
    """Start the backend-server with proper configuration"""
    setup_server_cleanup()
    
    # Get configuration
    server_port = int(os.getenv('SERVER_PORT', '5109'))
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    server_url = os.getenv('SERVER_URL', f'http://localhost:{server_port}')
    
    print(f"[@backend-server:start] Server Information:")
    print(f"[@backend-server:start]    Server URL: {server_url}")
    print(f"[@backend-server:start]    Server Port: {server_port}")
    print(f"[@backend-server:start]    Debug Mode: {debug_mode}")
    
    print("[@backend-server:start] 🎉 Backend-Server ready!")
    print(f"[@backend-server:start] 🚀 Starting API server on port {server_port}")
    
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
            'bind': f'0.0.0.0:{server_port}',
            'workers': 2,  # More workers for API handling
            'timeout': 120,
            'keepalive': 2
        }
        
        StandaloneApplication(app, options).run()
        
    except ImportError:
        print("[@backend-server:start] ❌ Gunicorn required. Install: pip install gunicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print("[@backend-server:start] 🛑 Backend-Server shutting down...")
    except Exception as e:
        print(f"[@backend-server:start] ❌ Error starting backend-server: {e}")
        sys.exit(1)
    finally:
        print("[@backend-server:start] 👋 Backend-Server application stopped")

def main():
    """Main function"""
    print("🖥️ VIRTUALPYTEST BACKEND-SERVER")
    print("Starting VirtualPyTest API Server")
    
    # STEP 1: Validate requirements
    validate_startup_requirements()
    
    # STEP 2: Setup Flask app and cleanup
    app = setup_and_cleanup()
    
    # STEP 3: Register ALL routes
    if not register_all_server_routes(app):
        print("❌ CRITICAL: Cannot start server without all routes")
        sys.exit(1)
    
    # STEP 4: Start server
    start_server(app)

if __name__ == '__main__':
    main() 