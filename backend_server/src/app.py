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
if backend_server_dir not in sys.path:
    sys.path.insert(0, backend_server_dir)

# Add backend_server/src to path for local imports
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import from shared library (using clear import paths)
try:
    from shared.src.lib.utils.app_utils import (
        load_environment_variables,
        kill_process_on_port,
        setup_flask_app,
        validate_core_environment,
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
        app.default_user_id = DEFAULT_USER_ID
        app.unique_server_id = str(uuid.uuid4())[:8]
    
    print("✅ Flask application setup completed")
    return app

# Grafana proxy removed - use direct access to http://localhost:3000 or nginx proxy

def register_all_server_routes(app):
    """Register all server routes - Client-facing API endpoints"""
    print("[@backend_server:routes] Loading server routes...")
    
    try:
        # Import routes one by one with debug prints to identify adb_utils import issue
        print("[@backend_server:routes] 🔍 Importing server_system_routes...")
        from routes import server_system_routes
        print("[@backend_server:routes] ✅ server_system_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_web_routes...")
        from routes import server_web_routes
        print("[@backend_server:routes] ✅ server_web_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_core_routes...")
        from routes import server_core_routes
        print("[@backend_server:routes] ✅ server_core_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing auto_proxy...")
        from routes import auto_proxy
        print("[@backend_server:routes] ✅ auto_proxy imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_control_routes...")
        from routes import server_control_routes
        print("[@backend_server:routes] ✅ server_control_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_actions_routes...")
        from routes import server_actions_routes
        print("[@backend_server:routes] ✅ server_actions_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_device_routes...")
        from routes import server_device_routes
        print("[@backend_server:routes] ✅ server_device_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_navigation_routes...")
        from routes import server_navigation_routes
        print("[@backend_server:routes] ✅ server_navigation_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_navigation_trees_routes...")
        from routes import server_navigation_trees_routes
        print("[@backend_server:routes] ✅ server_navigation_trees_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_pathfinding_routes...")
        from routes import server_pathfinding_routes
        print("[@backend_server:routes] ✅ server_pathfinding_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_alerts_routes...")
        from routes import server_alerts_routes
        print("[@backend_server:routes] ✅ server_alerts_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_verification_routes...")
        from routes import server_verification_routes
        print("[@backend_server:routes] ✅ server_verification_routes imported successfully")
        
        # server_navigation_execution_routes replaced by auto_proxy
        
        print("[@backend_server:routes] 🔍 Importing server_devicemodel_routes...")
        from routes import server_devicemodel_routes
        print("[@backend_server:routes] ✅ server_devicemodel_routes imported successfully")
        
        # server_remote_routes replaced by auto_proxy
        
        # server_ai_execution_routes replaced by auto_proxy
        
        print("[@backend_server:routes] 🔍 Importing server_ai_testcase_routes...")
        from routes import server_ai_testcase_routes
        print("[@backend_server:routes] ✅ server_ai_testcase_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_ai_generation_routes...")
        from routes import server_ai_generation_routes
        print("[@backend_server:routes] ✅ server_ai_generation_routes imported successfully")
        
        # server_ai_tools_routes replaced by auto_proxy
        
        # server_desktop_bash_routes replaced by auto_proxy
        
        # server_power_routes replaced by auto_proxy
        
        # server_desktop_pyautogui_routes replaced by auto_proxy
        
        print("[@backend_server:routes] 🔍 Importing server_stream_proxy_routes...")
        from routes import server_stream_proxy_routes
        print("[@backend_server:routes] ✅ server_stream_proxy_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_validation_routes...")
        from routes import server_validation_routes
        print("[@backend_server:routes] ✅ server_validation_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_campaign_routes...")
        from routes import server_campaign_routes
        print("[@backend_server:routes] ✅ server_campaign_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_testcase_routes...")
        from routes import server_testcase_routes
        print("[@backend_server:routes] ✅ server_testcase_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_userinterface_routes...")
        from routes import server_userinterface_routes
        print("[@backend_server:routes] ✅ server_userinterface_routes imported successfully")
        
        
        # server_av_routes replaced by auto_proxy
        
        # server_restart_routes replaced by auto_proxy
        
        # server_monitoring_routes replaced by auto_proxy
        
        print("[@backend_server:routes] 🔍 Importing server_execution_results_routes...")
        from routes import server_execution_results_routes
        print("[@backend_server:routes] ✅ server_execution_results_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_script_routes...")
        from routes import server_script_routes
        print("[@backend_server:routes] ✅ server_script_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_script_results_routes...")
        from routes import server_script_results_routes
        print("[@backend_server:routes] ✅ server_script_results_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_metrics_routes...")
        from routes import server_metrics_routes
        print("[@backend_server:routes] ✅ server_metrics_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_heatmap_routes...")
        from routes import server_heatmap_routes
        print("[@backend_server:routes] ✅ server_heatmap_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_campaign_results_routes...")
        from routes import server_campaign_results_routes
        print("[@backend_server:routes] ✅ server_campaign_results_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_frontend_routes...")
        from routes import server_frontend_routes
        print("[@backend_server:routes] ✅ server_frontend_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_ai_queue_routes...")
        from routes import server_ai_queue_routes
        print("[@backend_server:routes] ✅ server_ai_queue_routes imported successfully")
        
        # server_translation_routes replaced by auto_proxy
        
        print("[@backend_server:routes] 🔍 Importing server_api_testing_routes...")
        from routes import server_api_testing_routes
        print("[@backend_server:routes] ✅ server_api_testing_routes imported successfully")
        
        print("[@backend_server:routes] 🔍 Importing server_device_flags_routes...")
        from routes import server_device_flags_routes
        print("[@backend_server:routes] ✅ server_device_flags_routes imported successfully")
        
        print("[@backend_server:routes] 🎉 All route imports completed successfully!")
        
        # Register all server blueprints
        blueprints = [
            # Core system routes (keep these - have server logic)
            (server_system_routes.server_system_bp, 'System management'),
            (server_web_routes.server_web_bp, 'Web interface'),
            (server_core_routes.server_core_bp, 'Server core API'),
            (server_control_routes.server_control_bp, 'Device control operations'),
            (server_actions_routes.server_actions_bp, 'Action operations'),
            (server_device_routes.server_device_bp, 'Device management'),
            (server_navigation_routes.server_navigation_bp, 'Navigation operations'),
            (server_navigation_trees_routes.server_navigation_trees_bp, 'Navigation trees'),
            (server_pathfinding_routes.server_pathfinding_bp, 'Navigation pathfinding'),
            (server_alerts_routes.server_alerts_bp, 'Alert management'),
            (server_verification_routes.server_verification_bp, 'Verification operations'),
            (server_devicemodel_routes.server_devicemodel_bp, 'Device model management'),
            (server_ai_testcase_routes.server_ai_testcase_bp, 'AI test case operations'),
            (server_ai_generation_routes.server_ai_generation_bp, 'AI interface generation'),
            (server_stream_proxy_routes.server_stream_proxy_bp, 'Stream proxy'),
            (server_validation_routes.server_validation_bp, 'Validation operations'),
            (server_campaign_routes.server_campaign_bp, 'Campaign management'),
            (server_testcase_routes.server_testcase_bp, 'Test case management'),
            (server_userinterface_routes.server_userinterface_bp, 'User interface management'),
            (server_execution_results_routes.server_execution_results_bp, 'Execution results'),
            (server_script_routes.server_script_bp, 'Script management'),
            (server_script_results_routes.server_script_results_bp, 'Script results'),
            (server_metrics_routes.server_metrics_bp, 'Metrics API'),
            (server_heatmap_routes.server_heatmap_bp, 'Heatmap API'),
            (server_campaign_results_routes.server_campaign_results_bp, 'Campaign results'),
            (server_frontend_routes.server_frontend_bp, 'Frontend control'),
            (server_ai_queue_routes.server_ai_queue_bp, 'AI queue monitoring'),
            (server_api_testing_routes.server_api_testing_bp, 'API testing system'),
            (server_device_flags_routes.device_flags_bp, 'Device flags management'),
            
            # Auto proxy (replaces 12 pure proxy route files + 18 verification proxy routes)
            (auto_proxy.auto_proxy_bp, 'Auto proxy (replaces actions, ai-execution, ai-tools, av, desktop-bash, desktop-pyautogui, monitoring, navigation-execution, power, remote, restart, translation + 18 verification routes)')
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
        
        # Add error monitoring and server metrics collection
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
        
        def collect_server_metrics():
            import time
            # Use server-specific system stats instead of host stats
            from  backend_server.src.lib.utils.server_utils import get_server_system_stats
            from shared.src.lib.supabase.system_metrics_db import store_system_metrics
            
            time.sleep(15)  # Wait for startup
            while True:
                try:
                    # Get server system stats (use server-specific function)
                    server_stats = get_server_system_stats()
                    
                    # Debug: Show actual metrics values
                    temp_str = f", Temp={server_stats.get('cpu_temperature_celsius', 'N/A')}°C" if 'cpu_temperature_celsius' in server_stats else ""
                    print(f"[@backend_server:debug] 🔍 Raw server stats: CPU={server_stats.get('cpu_percent', 'N/A')}%, RAM={server_stats.get('memory_percent', 'N/A')}%, Disk={server_stats.get('disk_percent', 'N/A')}%{temp_str}")
                    
                    # Store server metrics in system_metrics table
                    store_system_metrics('server', server_stats)
                    print("[@backend_server:metrics] 📊 Server metrics collected and stored")
                    
                    # Server doesn't have devices, so no incident processing needed
                    # Each host manages its own device incidents directly
                    
                    # Align to minute boundaries for synchronized data collection
                    current_time = time.time()
                    next_minute = (int(current_time / 60) + 1) * 60
                    time.sleep(next_minute - current_time)
                except Exception as e:
                    print(f"[@backend_server:metrics] ❌ Metrics collection error: {e}")
                    time.sleep(60)  # Continue trying
        
        if os.getenv('RENDER', 'false').lower() == 'true':
            monitor_thread = threading.Thread(target=monitor_health, daemon=True)
            monitor_thread.start()
            print("[@backend_server:start] 🔍 Health monitoring started for Render")
        
        # Start server metrics collection thread (always run)
        metrics_thread = threading.Thread(target=collect_server_metrics, daemon=True)
        metrics_thread.start()
        print("[@backend_server:start] 📊 Server metrics collection started")
        
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