#!/usr/bin/env python3
"""
VirtualPyTest Backend Server Application

Main API server handling client requests and orchestration.
Provides REST API endpoints, WebSocket handling, and business logic coordination.

Usage: python3 app.py

Environment Variables Required (in .env file):
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

# Add project root to path for clear imports (shared.lib.*, backend_core.*)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from shared library (using clear import paths)
try:
    from shared.lib.utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
        DEFAULT_TEAM_ID,
        DEFAULT_USER_ID
    )
except ImportError as e:
    print(f"❌ CRITICAL: Cannot import app_utils: {e}")
    print("   Make sure shared/lib/utils/app_utils.py exists")
    sys.exit(1)

def validate_startup_requirements():
    """Validate requirements for server startup"""
    print("[@backend_server:validate] Validating startup requirements...")
    
    env_path = load_environment_variables(mode='server')
    
    if not validate_core_environment(mode='server'):
        print("❌ CRITICAL: Environment validation failed. Check .env file")
        sys.exit(1)
    
    print("✅ Startup requirements validated")

def setup_and_cleanup():
    """Setup Flask app and cleanup ports"""
    print("[@backend_server:setup] Setting up Flask application...")
    
    # Get server port and clean it up
    server_port = int(os.getenv('SERVER_PORT', '5109'))
    kill_process_on_port(server_port)
    time.sleep(1)
    
    # Create Flask app
    app = setup_flask_app("VirtualPyTest-backend_server")
    
    # Initialize app context
    with app.app_context():
        app.default_team_id = DEFAULT_TEAM_ID
        app.default_user_id = DEFAULT_USER_ID
        app.unique_server_id = str(uuid.uuid4())[:8]
    
    print("✅ Flask application setup completed")
    return app

def register_all_server_routes(app):
    """Register all server routes - Client-facing API endpoints"""
    print("[@backend_server:routes] Loading server routes...")
    
    try:
        from routes import (
            server_system_routes,
            server_web_routes,
            server_rec_routes,
            common_core_routes,
            server_control_routes,
            server_actions_routes,
            server_device_routes,
            server_navigation_routes,
            server_navigation_trees_routes,
            server_pathfinding_routes,
            server_alerts_routes,
            server_verification_common_routes,
            server_heatmap_routes,
            server_navigation_execution_routes,
            server_devicemodel_routes,
            server_remote_routes,
            server_aiagent_routes,
            server_aitestcase_routes,
            server_desktop_bash_routes,
            server_power_routes,
            server_desktop_pyautogui_routes,
            server_stream_proxy_routes,
            server_validation_routes,
            server_campaign_routes,
            server_testcase_routes,
            server_userinterface_routes,
            server_mcp_routes,
            server_av_routes,
            server_execution_results_routes,
            server_script_routes,
            server_script_results_routes,
            server_campaign_results_routes,
            server_frontend_routes
        )
        
        # Register all server blueprints
        blueprints = [
            (server_system_routes.server_system_bp, 'System management'),
            (server_web_routes.server_web_bp, 'Web interface'),
            (server_rec_routes.server_rec_bp, 'Recording operations'),
            (common_core_routes.core_bp, 'Common core API'),
            (server_control_routes.server_control_bp, 'Device control operations'),
            (server_actions_routes.server_actions_bp, 'Action management'),
            (server_device_routes.server_device_bp, 'Device management'),
            (server_navigation_routes.server_navigation_bp, 'Navigation operations'),
            (server_navigation_trees_routes.server_navigation_trees_bp, 'Navigation trees'),
            (server_pathfinding_routes.server_pathfinding_bp, 'Navigation pathfinding'),
            (server_alerts_routes.server_alerts_bp, 'Alert management'),
            (server_verification_common_routes.server_verification_common_bp, 'Verification operations'),
            (server_heatmap_routes.server_heatmap_bp, 'Heatmap generation'),
            (server_navigation_execution_routes.server_navigation_execution_bp, 'Navigation execution'),
            (server_devicemodel_routes.server_devicemodel_bp, 'Device model management'),
            (server_remote_routes.server_remote_bp, 'Remote control operations'),
            (server_aiagent_routes.server_aiagent_bp, 'AI agent operations'),
            (server_aitestcase_routes.server_aitestcase_bp, 'AI test case generation'),
            (server_desktop_bash_routes.server_desktop_bash_bp, 'Desktop bash control'),
            (server_power_routes.server_power_bp, 'Power management'),
            (server_desktop_pyautogui_routes.server_desktop_pyautogui_bp, 'Desktop automation'),
            (server_stream_proxy_routes.server_stream_proxy_bp, 'Stream proxy'),
            (server_validation_routes.server_validation_bp, 'Validation operations'),
            (server_campaign_routes.server_campaign_bp, 'Campaign management'),
            (server_testcase_routes.server_testcase_bp, 'Test case management'),
            (server_userinterface_routes.server_userinterface_bp, 'User interface management'),
            (server_mcp_routes.server_mcp_bp, 'MCP operations'),
            (server_av_routes.server_av_bp, 'Audio/Video operations'),
            (server_execution_results_routes.server_execution_results_bp, 'Execution results'),
            (server_script_routes.server_script_bp, 'Script management'),
            (server_script_results_routes.server_script_results_bp, 'Script results'),
            (server_campaign_results_routes.server_campaign_results_bp, 'Campaign results'),
            (server_frontend_routes.server_frontend_bp, 'Frontend control')
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
        print("[@backend_server:cleanup] Cleaning up server resources...")
    
    atexit.register(cleanup)

def start_server(app):
    """Start the backend_server with proper configuration"""
    setup_server_cleanup()
    
    # Get configuration
    server_port = int(os.getenv('SERVER_PORT', '5109'))
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    server_url = os.getenv('SERVER_URL', f'http://localhost:{server_port}')
    
    print(f"[@backend_server:start] Server Information:")
    print(f"[@backend_server:start]    Server URL: {server_url}")
    print(f"[@backend_server:start]    Server Port: {server_port}")
    print(f"[@backend_server:start]    Debug Mode: {debug_mode}")
    
    print("[@backend_server:start] 🎉 backend_server ready!")
    print(f"[@backend_server:start] 🚀 Starting API server on port {server_port} with SocketIO support")
    print(f"[@backend_server:start] 🔌 WebSocket enabled for async task notifications")
    
    try:
        # Validate SocketIO before starting
        if not hasattr(app, 'socketio'):
            print("[@backend_server:start] ❌ SocketIO not initialized on app")
            print("[@backend_server:start] 🔧 Available app attributes:", [attr for attr in dir(app) if not attr.startswith('_')])
            sys.exit(1)
            
        socketio = app.socketio
        print(f"[@backend_server:start] ✅ SocketIO instance: {type(socketio)}")
        
        # Additional debugging for Render environment
        print(f"[@backend_server:start] 🔧 Environment debug:")
        print(f"    RENDER: {os.getenv('RENDER', 'false')}")
        print(f"    Working Directory: {os.getcwd()}")
        print(f"    Server Port: {server_port}")
        print(f"    Available routes: {len(app.url_map._rules) if hasattr(app, 'url_map') else 'unknown'}")
        
        print("[@backend_server:start] 🚀 Calling socketio.run()...")
        
        # Add signal handlers for graceful shutdown
        import signal
        def signal_handler(signum, frame):
            print(f"[@backend_server:start] 🛑 Received signal {signum}, shutting down gracefully...")
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Add error monitoring
        import threading
        def monitor_health():
            import time
            time.sleep(10)  # Wait for startup
            while True:
                try:
                    print("[@backend_server:monitor] ❤️ Health check - app still running")
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    print(f"[@backend_server:monitor] ❌ Health check failed: {e}")
                    break
        
        if os.getenv('RENDER', 'false').lower() == 'true':
            monitor_thread = threading.Thread(target=monitor_health, daemon=True)
            monitor_thread.start()
            print("[@backend_server:start] 🔍 Health monitoring started for Render")
        
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=server_port, 
                    debug=debug_mode,
                    allow_unsafe_werkzeug=True,
                    log_output=True,
                    use_reloader=False)
        
    except ImportError as e:
        print(f"[@backend_server:start] ❌ Import error: {e}")
        print("[@backend_server:start] Flask-SocketIO required. Install: pip install flask-socketio")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("[@backend_server:start] 🛑 backend_server shutting down...")
    except Exception as e:
        print(f"[@backend_server:start] ❌ Error starting backend_server: {e}")
        print(f"[@backend_server:start] ❌ Error type: {type(e).__name__}")
        import traceback
        print("[@backend_server:start] 📋 Full traceback:")
        traceback.print_exc()
        print(f"[@backend_server:start] 🔧 Current working directory: {os.getcwd()}")
        print(f"[@backend_server:start] 🔧 Python executable: {sys.executable}")
        print(f"[@backend_server:start] 🔧 Python version: {sys.version}")
        # Don't exit immediately on Render - let supervisor handle restart
        if os.getenv('RENDER', 'false').lower() == 'true':
            print("[@backend_server:start] 🔄 On Render - sleeping before restart...")
            time.sleep(5)
        sys.exit(1)
    finally:
        print("[@backend_server:start] 👋 backend_server application stopped")

def main():
    """Main function"""
    print("🖥️ VIRTUALPYTEST backend_server")
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