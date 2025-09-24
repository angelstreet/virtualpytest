import os
import sys
from typing import Optional

# Ensure global typing compatibility for all third-party packages
from shared.src.lib.utils.typing_compatibility import ensure_typing_compatibility
ensure_typing_compatibility()

# Import the real supabase package by temporarily manipulating sys.path
def _import_real_supabase():
    """Import the real supabase package, avoiding our local supabase directory."""
    # Temporarily remove paths that might contain our local supabase directory
    original_path = sys.path.copy()
    try:
        # Remove any paths that might contain our local supabase directory
        filtered_path = [p for p in sys.path if not p.endswith('/virtualpytest') and 'shared/lib' not in p]
        sys.path[:] = filtered_path
        
        # Import the real supabase package
        import supabase
        create_client = supabase.create_client
        Client = supabase.Client
        return create_client, Client
    finally:
        # Restore original path
        sys.path[:] = original_path

create_client, Client = _import_real_supabase()

# Global variable to hold the lazily-loaded client
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """Get the Supabase client instance with lazy loading."""
    global _supabase_client
    
    if _supabase_client is None:
        try:
            # Only try to create client when actually needed
            url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key: str = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            
            if url and key:
                # Create client
                _supabase_client = create_client(url, key)
                print(f"[@supabase_utils:get_supabase_client] Supabase client initialized successfully")
            else:
                print(f"[@supabase_utils:get_supabase_client] Supabase environment variables not set, client not available")
                return None
        except Exception as e:
            print(f"[@supabase_utils:get_supabase_client] Failed to initialize Supabase client: {e}")
            return None
    
    return _supabase_client 