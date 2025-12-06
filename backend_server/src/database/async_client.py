"""
Async PostgreSQL Client for Event System

Provides async database access using asyncpg for event-driven operations.
Coexists with existing Supabase client for backward compatibility.
"""

import os
import asyncpg
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

class AsyncDatabase:
    """Async PostgreSQL client wrapper"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_string: Optional[str] = None
    
    async def connect(self):
        """Initialize connection pool"""
        if self._pool is not None:
            return
        
        # Get connection string from environment (Supabase DB URI)
        self._connection_string = os.getenv('SUPABASE_DB_URI')
        
        if not self._connection_string:
            raise ValueError("SUPABASE_DB_URI environment variable not set")
        
        try:
            self._pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60,
                # Disable statement caching for pgbouncer compatibility (Supabase uses pgbouncer)
                statement_cache_size=0
            )
            print("[@async_db] ✅ Async PostgreSQL pool initialized (pgbouncer-compatible)")
        except Exception as e:
            print(f"[@async_db] ❌ Failed to create connection pool: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            print("[@async_db] Connection pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        if self._pool is None:
            await self.connect()
        
        async with self._pool.acquire() as connection:
            yield connection
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute SELECT query and return all rows"""
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute SELECT query and return first row"""
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetchval(self, query: str, *args) -> Any:
        """Execute SELECT query and return single value"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute(self, query: str, *args) -> str:
        """Execute INSERT/UPDATE/DELETE query"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets"""
        async with self.acquire() as conn:
            await conn.executemany(query, args_list)

# Global instance
_async_db: Optional[AsyncDatabase] = None

def get_async_db() -> AsyncDatabase:
    """Get or create async database instance"""
    global _async_db
    if _async_db is None:
        _async_db = AsyncDatabase()
    return _async_db

