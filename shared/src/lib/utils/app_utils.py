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
import logging
from flask import Flask, current_app, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests


# =====================================================
# LOGGING FILTER FOR SOCKET.IO POLLING REQUESTS
# =====================================================

class SocketIOPollingFilter(logging.Filter):
    """Filter out noisy socket.io polling/websocket debug logs"""
    
    FILTERED_PATTERNS = [
        '/socket.io/?EIO=',
        'transport=polling',
        'transport=websocket',
    ]
    
    def filter(self, record):
        # Allow the record if it doesn't match any filtered patterns
        message = record.getMessage()
        for pattern in self.FILTERED_PATTERNS:
            if pattern in message:
                return False  # Suppress this log
        return True  # Allow this log

# =====================================================
# ENVIRONMENT AND SETUP FUNCTIONS
# =====================================================

def load_environment_variables(mode='server', calling_script_dir=None):
    """Load environment variables from project-level .env file and service-specific .env"""
    print(f"[@app_utils:load_environment_variables] Loading environment variables (mode={mode})...")
    
    # Find project root (where .env should be)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # Go up to project root
    project_env_path = os.path.join(project_root, '.env')
    
    print(f"[@app_utils:load_environment_variables] Current directory: {current_dir}")
    print(f"[@app_utils:load_environment_variables] Project root: {project_root}")
    print(f"[@app_utils:load_environment_variables] Looking for project .env at: {project_env_path}")
    
    # Load project-level .env first (NEVER override OS environment variables from Render)
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path, override=False)  # OS env vars (Render) take priority
        print(f"✅ Loaded project environment from: {project_env_path} (OS env vars take priority)")
        
        # Check for critical variables after loading
        host_name = os.getenv('HOST_NAME')
        print(f"[@app_utils:load_environment_variables] Project .env HOST_NAME: {host_name}")
    else:
        # Check if we're on Render with environment variables already set
        render_env = os.getenv('RENDER', 'false').lower() == 'true'
        server_url = os.getenv('SERVER_URL')
        
        if render_env or server_url:
            print(f"✅ Running with OS environment variables (Render or Docker)")
            print(f"[@app_utils:load_environment_variables] SERVER_URL={server_url}")
        else:
            print(f"⚠️  Project environment file not found: {project_env_path}")
            print(f"⚠️  Create .env in project root for local development: cp env.example .env")
    
    # Load service-specific .env if calling_script_dir is provided (for host)
    if calling_script_dir:
        service_env_path = os.path.join(calling_script_dir, '.env')
        print(f"[@app_utils:load_environment_variables] Looking for service .env at: {service_env_path}")
        
        if os.path.exists(service_env_path):
            load_dotenv(service_env_path, override=False)  # OS env vars still take priority
            print(f"✅ Loaded service environment from: {service_env_path} (OS env vars take priority)")
            
            # Check for critical variables after loading
            host_name = os.getenv('HOST_NAME')
            device1_name = os.getenv('DEVICE1_NAME')
            print(f"[@app_utils:load_environment_variables] Service .env HOST_NAME: {host_name}")
            print(f"[@app_utils:load_environment_variables] Service .env DEVICE1_NAME: {device1_name}")
        else:
            print(f"⚠️  Service environment file not found: {service_env_path}")
    
    # List all environment variables with DEVICE in the name
    print(f"[@app_utils:load_environment_variables] Checking for device configuration...")
    device_vars = [var for var in os.environ.keys() if 'DEVICE' in var]
    for var in device_vars:
        print(f"[@app_utils:load_environment_variables]   {var}={os.environ.get(var)}")
    
    return project_env_path

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
                            try:
                                psutil.Process(pid).kill()  # Force kill instead of terminate
                            except psutil.AccessDenied:
                                # Try with system command as fallback
                                print(f"🔐 Access denied for PID {pid}, trying system kill...")
                                import subprocess
                                try:
                                    subprocess.run(['sudo', 'kill', '-9', str(pid)], 
                                                 check=True, capture_output=True)
                                    print(f"✅ Successfully killed PID {pid} with sudo")
                                except subprocess.CalledProcessError:
                                    print(f"❌ Failed to kill PID {pid} even with sudo")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        print(f"✅ Port {port} cleanup completed")
        
    except Exception as e:
        print(f"❌ Error during port cleanup: {e}")

def setup_flask_app(app_name="VirtualPyTest"):
    """Setup and configure Flask application with CORS and WebSocket support"""
    app = Flask(app_name)
    
    # Suppress noisy socket.io polling/websocket logs from werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(SocketIOPollingFilter())

    # Configure Flask secret key for session management
    # Use environment variable or generate a default for development
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        # Generate a default secret key for development
        import secrets
        secret_key = secrets.token_hex(32)
        print(f"⚠️ Using generated secret key for development. Set FLASK_SECRET_KEY environment variable for production.")
    
    app.secret_key = secret_key

    # Configure CORS for development and production
    # Allow all local network IPs (192.168.x.x) plus production domains
    import re
    
    allowed_origins = [
        # Production domains
        "https://dev.virtualpytest.com",
        "https://virtualpytest.com",
        "https://www.virtualpytest.com",
        # Vercel deployments (including specific user-scoped domains)
        # Matches all Vercel preview and production URLs with any number of dashes
        # Examples: virtualpytest.vercel.app, virtualpytest-h9f7zer45-angelstreets-projects.vercel.app
        re.compile(r"^https://[a-zA-Z0-9\-]+\.vercel\.app$"),
        # Localhost - explicit ports for Flask-SocketIO compatibility (regex not supported)
        "http://localhost:5073",   # Vite dev server
        "http://localhost:5109",   # Backend server
        "http://localhost:3000",   # Common dev port (Grafana, etc.)
        "http://127.0.0.1:5073",
        "http://127.0.0.1:5109",
        # Localhost regex for Flask-CORS (non-SocketIO routes)
        re.compile(r"^https?://localhost(:\d+)?$"),
        re.compile(r"^https?://127\.0\.0\.1(:\d+)?$"),
        # Local network IPs: 192.168.x.x (any port, HTTP or HTTPS)
        re.compile(r"^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$")
    ]
    
    CORS(app, 
         origins=allowed_origins,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept", "DNT", "User-Agent", "X-Requested-With", "If-Modified-Since", "Cache-Control"],
         supports_credentials=True
    )

    # Add WebSocket support for async task notifications
    from flask_socketio import SocketIO
    # SocketIO also accepts regex patterns in the list
    socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='threading', path='/server/socket.io')
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
        from shared.src.lib.utils.supabase_utils import get_supabase_client
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


# =====================================================
# FLASK-SPECIFIC HELPER FUNCTIONS
# =====================================================

def check_supabase():
    """Helper function to check if Supabase is available"""
    try:
        from flask import jsonify
        from shared.src.lib.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        if supabase_client is None:
            return jsonify({'error': 'Supabase not available'}), 503
        return None
    except Exception:
        from flask import jsonify
        return jsonify({'error': 'Supabase not available'}), 503


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