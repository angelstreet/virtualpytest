"""
Environment Utilities for VirtualPyTest Shared Library

Utilities to help services provide environment variables to shared components.
This avoids the need for duplicate .env files in the shared library.
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


def load_service_env(service_name: str, service_dir: str = None) -> Dict[str, str]:
    """
    Load environment variables for a specific service.
    
    Args:
        service_name: Name of the service (backend-server, backend-host, frontend)
        service_dir: Optional directory to look for .env file (defaults to current dir)
        
    Returns:
        Dictionary of environment variables for the service
    """
    if service_dir is None:
        service_dir = os.getcwd()
    
    # Look for .env file in service directory
    env_file = os.path.join(service_dir, '.env')
    
    if os.path.exists(env_file):
        # Load into a temporary environment
        temp_env = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    temp_env[key.strip()] = value.strip()
        
        logger.info(f"Loaded {len(temp_env)} environment variables for {service_name}")
        return temp_env
    else:
        logger.warning(f"No .env file found for {service_name} in {service_dir}")
        return {}


def get_cloudflare_env_vars(service_env: Dict[str, str] = None) -> Dict[str, str]:
    """
    Extract Cloudflare R2 environment variables from service environment.
    
    Args:
        service_env: Service environment dictionary (defaults to os.environ)
        
    Returns:
        Dictionary containing only Cloudflare R2 related environment variables
    """
    if service_env is None:
        service_env = dict(os.environ)
    
    cloudflare_vars = {}
    cloudflare_keys = [
        'CLOUDFLARE_R2_ENDPOINT',
        'CLOUDFLARE_R2_ACCESS_KEY_ID', 
        'CLOUDFLARE_R2_SECRET_ACCESS_KEY',
        'CLOUDFLARE_R2_PUBLIC_URL'
    ]
    
    for key in cloudflare_keys:
        if key in service_env:
            cloudflare_vars[key] = service_env[key]
    
    logger.debug(f"Extracted {len(cloudflare_vars)} Cloudflare environment variables")
    return cloudflare_vars


def get_supabase_env_vars(service_env: Dict[str, str] = None) -> Dict[str, str]:
    """
    Extract Supabase environment variables from service environment.
    
    Args:
        service_env: Service environment dictionary (defaults to os.environ)
        
    Returns:
        Dictionary containing only Supabase related environment variables
    """
    if service_env is None:
        service_env = dict(os.environ)
    
    supabase_vars = {}
    supabase_keys = [
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY'
    ]
    
    for key in supabase_keys:
        if key in service_env:
            supabase_vars[key] = service_env[key]
    
    logger.debug(f"Extracted {len(supabase_vars)} Supabase environment variables")
    return supabase_vars


def initialize_shared_services(service_name: str, service_dir: str = None) -> Dict[str, str]:
    """
    Initialize shared services with environment variables from the calling service.
    
    This is the main function services should call to set up shared utilities.
    
    Args:
        service_name: Name of the calling service
        service_dir: Directory containing .env file (defaults to current dir)
        
    Returns:
        Dictionary of loaded environment variables
    """
    # Load service environment
    service_env = load_service_env(service_name, service_dir)
    
    # If no service .env found, use os.environ
    if not service_env:
        service_env = dict(os.environ)
    
    # Initialize CloudflareUtils with service environment
    from .cloudflare_utils import get_cloudflare_utils
    cloudflare_env = get_cloudflare_env_vars(service_env)
    get_cloudflare_utils(cloudflare_env)
    
    logger.info(f"Initialized shared services for {service_name}")
    return service_env


# Convenience functions for different services
def init_backend_server_shared(server_dir: str = None) -> Dict[str, str]:
    """Initialize shared services for backend-server."""
    return initialize_shared_services('backend-server', server_dir)


def init_backend_host_shared(host_dir: str = None) -> Dict[str, str]:
    """Initialize shared services for backend-host."""
    return initialize_shared_services('backend-host', host_dir)


def init_frontend_shared(frontend_dir: str = None) -> Dict[str, str]:
    """Initialize shared services for frontend (if needed)."""
    return initialize_shared_services('frontend', frontend_dir) 