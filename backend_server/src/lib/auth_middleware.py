"""
User Authentication Middleware for Supabase JWT

This middleware validates END USER authentication (different from service API_KEY).
Supabase JWT tokens are validated to identify and authorize frontend users.

DO NOT confuse with:
- API_KEY (X-API-Key header) - for backend_server → backend_host service calls
- MCP_SECRET_KEY - for MCP protocol authentication
- FLASK_SECRET_KEY - for Flask session encryption

This is for USER authentication: Frontend → Backend Server
"""

import os
import jwt
from functools import wraps
from flask import request, jsonify
from typing import Optional, Callable

# Get Supabase JWT secret from environment
# Note: For Supabase, the JWT secret is the ANON_KEY (used for signature verification)
SUPABASE_JWT_SECRET = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')


def require_user_auth(f: Callable) -> Callable:
    """
    Decorator to require Supabase user authentication.
    Validates JWT token from Authorization header.
    
    This is for USER authentication (frontend users).
    Does NOT interfere with API_KEY service authentication.
    
    Usage:
        @app.route('/api/protected')
        @require_user_auth
        def protected_route():
            user_id = request.user_id  # Available after auth
            user_role = request.user_role
            ...
    
    Sets request attributes:
        - request.user_id: Supabase user ID
        - request.user_email: User email
        - request.user_role: User role (from JWT or 'viewer' default)
        - request.user_metadata: Full user metadata
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if JWT secret is configured
        if not SUPABASE_JWT_SECRET:
            print("[@auth_middleware] WARNING: SUPABASE JWT secret not configured")
            return jsonify({
                'error': 'Server configuration error',
                'message': 'User authentication not configured'
            }), 500
        
        # Get Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Authorization header is required'
            }), 401
        
        # Check Bearer token format
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Invalid Authorization format',
                'message': 'Expected: Authorization: Bearer <token>'
            }), 401
        
        # Extract token
        token = auth_header.replace('Bearer ', '').strip()
        
        try:
            # Decode and verify Supabase JWT
            # Supabase uses HS256 algorithm with the anon key as secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated',
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_aud': True
                }
            )
            
            # Extract user information from JWT payload
            request.user_id = payload.get('sub')  # Subject = user ID
            request.user_email = payload.get('email')
            request.user_role = payload.get('user_metadata', {}).get('role', 'viewer')
            request.user_metadata = payload.get('user_metadata', {})
            
            # Log successful authentication
            print(f"[@auth_middleware] ✅ User authenticated: {request.user_email} (role: {request.user_role})")
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expired',
                'message': 'Please log in again'
            }), 401
        
        except jwt.InvalidAudienceError:
            return jsonify({
                'error': 'Invalid token audience',
                'message': 'Token not valid for this service'
            }), 401
        
        except jwt.InvalidTokenError as e:
            print(f"[@auth_middleware] ❌ Invalid token: {str(e)}")
            return jsonify({
                'error': 'Invalid token',
                'message': 'Authentication failed'
            }), 401
        
        except Exception as e:
            print(f"[@auth_middleware] ❌ Auth error: {str(e)}")
            return jsonify({
                'error': 'Authentication error',
                'message': str(e)
            }), 401
        
        # Token valid, proceed to route
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to require specific user roles.
    Must be used AFTER @require_user_auth.
    
    Usage:
        @app.route('/api/admin-only')
        @require_user_auth
        @require_role('admin')
        def admin_route():
            ...
        
        @app.route('/api/testers')
        @require_user_auth
        @require_role('admin', 'tester')
        def tester_route():
            ...
    
    Args:
        allowed_roles: One or more role names (e.g., 'admin', 'tester', 'viewer')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user_role is set (requires @require_user_auth first)
            if not hasattr(request, 'user_role'):
                return jsonify({
                    'error': 'Configuration error',
                    'message': '@require_role must be used after @require_user_auth'
                }), 500
            
            user_role = request.user_role
            
            # Check if user has one of the allowed roles
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This endpoint requires one of these roles: {", ".join(allowed_roles)}',
                    'user_role': user_role
                }), 403
            
            print(f"[@auth_middleware] ✅ Role check passed: {user_role} in {allowed_roles}")
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission.
    Must be used AFTER @require_user_auth.
    
    Permissions are checked from:
    1. Role-based permissions (admin has all)
    2. Custom user permissions (stored in user_metadata)
    
    Usage:
        @app.route('/api/testing')
        @require_user_auth
        @require_permission('api_testing')
        def api_testing():
            ...
    
    Args:
        permission: Permission name (e.g., 'api_testing', 'manage_devices')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not hasattr(request, 'user_role'):
                return jsonify({
                    'error': 'Configuration error',
                    'message': '@require_permission must be used after @require_user_auth'
                }), 500
            
            user_role = request.user_role
            user_metadata = getattr(request, 'user_metadata', {})
            
            # Admin has all permissions
            if user_role == 'admin':
                print(f"[@auth_middleware] ✅ Admin has permission: {permission}")
                return f(*args, **kwargs)
            
            # Check custom permissions in user metadata
            user_permissions = user_metadata.get('permissions', [])
            
            # Role-based permissions (fallback)
            role_permissions = {
                'tester': [
                    'view_dashboard', 'run_tests', 'create_test_cases',
                    'edit_test_cases', 'view_reports', 'api_testing',
                    'jira_integration', 'manage_devices', 'view_monitoring',
                    'create_campaigns', 'edit_campaigns'
                ],
                'viewer': ['view_dashboard', 'view_reports', 'view_monitoring']
            }
            
            allowed_permissions = set(user_permissions) | set(role_permissions.get(user_role, []))
            
            if permission not in allowed_permissions:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This endpoint requires permission: {permission}',
                    'user_role': user_role
                }), 403
            
            print(f"[@auth_middleware] ✅ Permission check passed: {permission}")
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def optional_user_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication.
    Validates JWT if present, but doesn't require it.
    
    Usage:
        @app.route('/api/public-or-authenticated')
        @optional_user_auth
        def mixed_route():
            if hasattr(request, 'user_id'):
                # User is authenticated
                ...
            else:
                # Anonymous access
                ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '').strip()
            
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=['HS256'],
                    audience='authenticated'
                )
                
                request.user_id = payload.get('sub')
                request.user_email = payload.get('email')
                request.user_role = payload.get('user_metadata', {}).get('role', 'viewer')
                request.user_metadata = payload.get('user_metadata', {})
                
            except Exception as e:
                # Invalid token, but we don't reject - just continue without auth
                print(f"[@auth_middleware] ⚠️  Optional auth failed: {str(e)}")
                pass
        
        return f(*args, **kwargs)
    
    return decorated_function


# Aliases for common usage patterns
require_auth = require_user_auth
require_admin = require_role('admin')

