"""
App Utilities

Flask application setup and registration utilities.
Focused on app configuration and initialization.
"""

import sys
import os
import time
import subprocess
import psutil
import platform
from flask import Flask, current_app, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# =====================================================
# ENVIRONMENT AND SETUP FUNCTIONS
# =====================================================

def load_environment_variables(mode='server', calling_script_dir=None):
    """Load environment variables from .env file or use system environment variables"""
    env_file = '.env'
    
    # If calling_script_dir is provided, use it; otherwise use current working directory
    if calling_script_dir:
        env_path = os.path.join(calling_script_dir, env_file)
    else:
        env_path = os.path.join(os.getcwd(), env_file)
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded environment from: {env_path}")
    else:
        # Check if we're in a production environment (like Render) where env vars are set directly
        if os.getenv('RENDER') or os.getenv('SERVER_PORT') or os.getenv('PRODUCTION'):
            print(f"🚀 Production environment detected - using system environment variables")
        else:
            print(f"❌ Environment file not found: {env_path}")
            print(f"❌ Please create {env_file} in {os.path.dirname(env_path)}")
            print(f"❌ Use the .env.example as a template")
    
    return env_path

def kill_process_on_port(port):
    """Simple port cleanup - kill any process using the specified port"""
    try:
        print(f"🔍 Checking for processes using port {port}...")
        
        # Skip if running under Flask reloader to avoid conflicts
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            print(f"🔄 Flask reloader detected, skipping port cleanup")
            return
        
        # Find and kill processes using the port
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections():
                    if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                        pid = proc.info['pid']
                        if pid != os.getpid():  # Don't kill ourselves
                            print(f"🎯 Killing process PID {pid} using port {port}")
                            psutil.Process(pid).terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        print(f"✅ Port {port} cleanup completed")
        
    except Exception as e:
        print(f"❌ Error during port cleanup: {e}")

def setup_flask_app(app_name="VirtualPyTest"):
    """Setup and configure Flask application with CORS and WebSocket support"""
    app = Flask(app_name)

    # Configure Flask secret key for session management
    # Use environment variable or generate a default for development
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        # Generate a default secret key for development
        import secrets
        secret_key = secrets.token_hex(32)
        print(f"⚠️ Using generated secret key for development. Set FLASK_SECRET_KEY environment variable for production.")
    
    app.secret_key = secret_key

    # Configure CORS for development
    CORS(app, 
         origins="*",
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         supports_credentials=False
    )

    # Add WebSocket support for async task notifications
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', path='/server/socket.io')
    app.socketio = socketio

    return app

def validate_core_environment(mode='server'):
    """Validate only essential environment variables for startup"""
    print(f"🔍 Validating core {mode.upper()} environment variables...")
    
    if mode == 'server':
        required_vars = {
            'SERVER_URL': 'Server base URL',
            'SERVER_PORT': 'Server port number'
        }
    elif mode == 'host':
        required_vars = {
            'SERVER_URL': 'Server base URL',
            'HOST_URL': 'Host base URL',
            'HOST_NAME': 'Host identifier name',
            'HOST_PORT': 'Host port number'
        }
    else:
        print(f"⚠️ Unknown mode: {mode}")
        return False
    
    missing_vars = []
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            missing_vars.append(f"{var_name} ({description})")
        else:
            display_value = '***' if 'TOKEN' in var_name else value
            print(f"  ✅ {var_name}: {display_value}")
    
    if missing_vars:
        print(f"❌ Missing required core variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print(f"✅ Core {mode} environment variables validated")
    
    # Validate Supabase connectivity
    print(f"🔍 Validating Supabase connectivity...")
    try:
        from shared.lib.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        
        if supabase_client is None:
            print(f"❌ Supabase client initialization failed")
            print(f"   Check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables")
            return False
        
        # Test database connectivity with a simple query
        try:
            # Try to query a system table that should always exist
            result = supabase_client.table('teams').select('id').limit(1).execute()
            print(f"✅ Supabase database connectivity confirmed")
        except Exception as db_error:
            print(f"❌ Supabase database connection failed: {db_error}")
            print(f"   Database may be unreachable or RLS policies may be blocking access")
            return False
            
    except Exception as e:
        print(f"❌ Supabase validation failed: {e}")
        print(f"   Ensure Supabase client dependencies are installed")
        return False
    
    return True



# =====================================================
# LAZY LOADING FUNCTIONS
# =====================================================

def lazy_load_controllers():
    """Lazy load controllers when first needed"""
    try:
        from shared.lib.controllers import ControllerFactory, CONTROLLER_REGISTRY
        from controllers.base_controller import (
            RemoteControllerInterface, 
            AVControllerInterface, 
            VerificationControllerInterface,
            PowerControllerInterface
        )
        print("✅ Controllers loaded successfully (lazy loaded)")
        return True
    except Exception as e:
        print(f"⚠️ Controllers not available: {e}")
        return False

def lazy_load_adb_utils():
    """Lazy load ADB utilities when first needed"""
    try:
        # Import from current directory since we're already in utils
        from . import adb_utils
        print("✅ ADB utilities loaded successfully (lazy loaded)")
        return adb_utils
    except Exception as e:
        print(f"⚠️ ADB utilities not available: {e}")
        return None

def lazy_load_navigation():
    """Lazy load navigation utilities when first needed"""
    try:
        from . import navigation_cache
        from . import navigation_graph
        print("✅ Navigation utilities loaded successfully (placeholder implementation)")
        return {'cache': navigation_cache, 'graph': navigation_graph}
    except Exception as e:
        print(f"⚠️ Navigation utilities not available: {e}")
        return None

def lazy_load_device_models():
    """Lazy load device model utilities when first needed"""
    try:
        # TODO: These utilities need to be implemented or imported correctly
        # import devicemodel_utils
        print("⚠️ Device model utilities not yet implemented")
        return None
    except Exception as e:
        print(f"⚠️ Device model utilities not available: {e}")
        return None

# =====================================================
# FLASK-SPECIFIC HELPER FUNCTIONS
# =====================================================

def check_supabase():
    """Helper function to check if Supabase is available"""
    try:
        from flask import jsonify
        from shared.lib.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        if supabase_client is None:
            return jsonify({'error': 'Supabase not available'}), 503
        return None
    except Exception:
        from flask import jsonify
        return jsonify({'error': 'Supabase not available'}), 503

def check_controllers_available():
    """Helper function to check if controllers are available (lazy loaded)"""
    try:
        controllers_available = lazy_load_controllers()
        if not controllers_available:
            return jsonify({'error': 'Controllers not available'}), 503
        return None
    except Exception:
        return jsonify({'error': 'Controllers not available'}), 503

def get_team_id():
    """Get team_id from request headers or use default for demo"""
    default_team_id = getattr(current_app, 'default_team_id', DEFAULT_TEAM_ID)
    return request.headers.get('X-Team-ID', default_team_id)

def get_user_id():
    """Get user_id from request headers - FAIL FAST if not provided"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise ValueError('X-User-ID header is required but not provided')
    return user_id

# =====================================================
# CONSTANTS
# =====================================================

DEFAULT_TEAM_ID = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
DEFAULT_USER_ID = "eb6cfd93-44ab-4783-bd0c-129b734640f3"