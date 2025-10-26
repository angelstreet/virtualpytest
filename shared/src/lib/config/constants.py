"""
Application Constants and Configuration

Single source of truth for all hardcoded values, magic numbers, and configuration.
Shared across backend_server, backend_host, and all services.

USAGE:
    from shared.src.lib.config.constants import CACHE_CONFIG, HTTP_CONFIG
    ttl = CACHE_CONFIG['LONG_TTL']
    timeout = HTTP_CONFIG['DEFAULT_TIMEOUT']
"""

# =====================================================
# CACHE CONFIGURATION (TTL in seconds)
# =====================================================

CACHE_CONFIG = {
    # Very short cache - for frequently changing data (30 seconds)
    # Used for: Host restart status
    'VERY_SHORT_TTL': 30,
    
    # Short cache - for dynamic data (2 minutes)
    # Used for: Server hosts data, Script lists
    'SHORT_TTL': 2 * 60,
    
    # Medium cache - for semi-static data (5 minutes)
    # Used for: Navigation trees, heatmap analysis
    'MEDIUM_TTL': 5 * 60,
    
    # Long cache - for static data (24 hours)
    # Used for: Stream URLs, metadata, device models, user interfaces
    'LONG_TTL': 24 * 60 * 60,
}

# =====================================================
# HTTP CONFIGURATION (timeouts in seconds)
# =====================================================

HTTP_CONFIG = {
    # Request timeouts
    'ULTRA_SHORT_TIMEOUT': 3,      # Ultra-fast operations (ADB connect, device list)
    'VERY_SHORT_TIMEOUT': 5,       # Quick operations
    'SHORT_TIMEOUT': 30,           # Default operations
    'DEFAULT_TIMEOUT': 60,         # Standard timeout
    'NAVIGATION_TIMEOUT': 180,     # Navigation/Action execution (3 minutes)
    'LONG_TIMEOUT': 300,           # Long operations (5 minutes)
    
    # Retry configuration
    'DEFAULT_RETRY_ATTEMPTS': 3,
    'RETRY_DELAY_BASE': 1.0,
}

# =====================================================
# HEATMAP CONFIGURATION
# =====================================================

HEATMAP_CONFIG = {
    # CPU limiting - max worker threads
    'MAX_WORKER_THREADS': 2,
    
    # Process priority setting
    'PROCESS_PRIORITY_LOW': True,
}


