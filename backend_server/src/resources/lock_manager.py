"""
Resource Lock Manager

Manages exclusive locks on resources (devices, trees, userinterfaces)
to enable safe parallel execution. Includes priority-based queuing.
"""

import asyncio
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from database import get_async_db
from events import EventBus, Event, EventPriority, get_event_bus


class LockStatus(Enum):
    """Resource lock status"""
    AVAILABLE = "available"
    LOCKED = "locked"
    QUEUED = "queued"


@dataclass
class ResourceLock:
    """Resource lock information"""
    resource_id: str
    resource_type: str
    owner_id: str
    owner_type: str
    acquired_at: datetime
    expires_at: datetime
    priority: int
    team_id: str = 'default'


class ResourceLockManager:
    """
    Resource Lock Manager
    
    Provides exclusive lock acquisition and priority-based queuing.
    Integrates with Event Bus to notify on lock changes.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize Resource Lock Manager
        
        Args:
            event_bus: Event bus for publishing lock events (optional)
        """
        self.db = get_async_db()
        self.event_bus = event_bus or get_event_bus()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start periodic cleanup of expired locks"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        print("[@lock_manager] ✅ Started periodic cleanup")
    
    async def stop(self):
        """Stop cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        print("[@lock_manager] Stopped")
    
    async def acquire(
        self, 
        resource_id: str, 
        resource_type: str,
        owner_id: str,
        owner_type: str = 'agent',
        timeout_seconds: int = 3600, 
        priority: int = 3,
        team_id: str = 'default'
    ) -> bool:
        """
        Try to acquire lock on resource
        
        Args:
            resource_id: Resource identifier (e.g., 'device1', 'tree_abc')
            resource_type: Resource type ('device', 'tree', 'userinterface')
            owner_id: Lock owner identifier
            owner_type: Owner type ('agent', 'user', 'system')
            timeout_seconds: Lock duration in seconds
            priority: Lock priority (lower = higher priority)
            team_id: Team namespace
            
        Returns:
            True if lock acquired, False if queued
        """
        # Clean up expired locks first
        await self._cleanup_expired()
        
        # Check if resource is available
        is_available = await self._is_available(resource_id)
        
        if is_available:
            # Acquire lock immediately
            expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
            
            query = """
                INSERT INTO resource_locks (
                    resource_id, resource_type, owner_id, owner_type,
                    acquired_at, expires_at, priority, team_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            try:
                lock_id = await self.db.fetchval(
                    query,
                    resource_id,
                    resource_type,
                    owner_id,
                    owner_type,
                    datetime.utcnow(),
                    expires_at,
                    priority,
                    team_id
                )
                
                # Publish event
                await self.event_bus.publish(Event(
                    type="resource.acquired",
                    payload={
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "owner_id": owner_id,
                        "expires_at": expires_at.isoformat()
                    },
                    priority=EventPriority.NORMAL,
                    team_id=team_id
                ))
                
                print(f"[@lock_manager] 🔒 Acquired: {resource_id} by {owner_id}")
                return True
                
            except Exception as e:
                print(f"[@lock_manager] ❌ Failed to acquire lock: {e}")
                # Resource might have been locked between check and insert
                # Fall through to queuing logic
        
        # Resource locked - add to queue
        await self._add_to_queue(
            resource_id,
            owner_id,
            priority,
            timeout_seconds,
            team_id
        )
        
        return False
    
    async def release(
        self, 
        resource_id: str, 
        owner_id: str,
        team_id: str = 'default'
    ) -> bool:
        """
        Release lock on resource
        
        Args:
            resource_id: Resource identifier
            owner_id: Lock owner (must match)
            team_id: Team namespace
            
        Returns:
            True if released, False if not locked or wrong owner
        """
        query = """
            DELETE FROM resource_locks
            WHERE resource_id = $1 
            AND owner_id = $2
            AND team_id = $3
            AND expires_at > NOW()
            RETURNING id, resource_type
        """
        
        result = await self.db.fetchrow(query, resource_id, owner_id, team_id)
        
        if not result:
            print(f"[@lock_manager] ⚠️ Cannot release: {resource_id} (not locked by {owner_id})")
            return False
        
        # Publish event
        await self.event_bus.publish(Event(
            type="resource.released",
            payload={
                "resource_id": resource_id,
                "resource_type": result['resource_type'],
                "owner_id": owner_id
            },
            priority=EventPriority.NORMAL,
            team_id=team_id
        ))
        
        print(f"[@lock_manager] 🔓 Released: {resource_id} by {owner_id}")
        
        # Process queue for this resource
        await self._process_queue(resource_id, team_id)
        
        return True
    
    async def is_available(self, resource_id: str) -> bool:
        """
        Check if resource is available
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            True if available, False if locked
        """
        return await self._is_available(resource_id)
    
    async def get_status(
        self, 
        resource_id: str,
        team_id: str = 'default'
    ) -> Dict:
        """
        Get current status of resource
        
        Args:
            resource_id: Resource identifier
            team_id: Team namespace
            
        Returns:
            Dictionary with status, owner, and queue information
        """
        # Use database function for atomic check
        query = "SELECT * FROM get_resource_lock_status($1)"
        result = await self.db.fetchrow(query, resource_id)
        
        if result and result['is_locked']:
            return {
                'status': LockStatus.LOCKED.value,
                'owner_id': result['owner_id'],
                'expires_at': result['expires_at'].isoformat(),
                'queue_length': result['queue_length']
            }
        else:
            # Get queue length even if not locked
            queue_query = """
                SELECT COUNT(*) as queue_length
                FROM resource_lock_queue
                WHERE resource_id = $1 AND team_id = $2
            """
            queue_result = await self.db.fetchval(queue_query, resource_id, team_id)
            
            return {
                'status': LockStatus.AVAILABLE.value,
                'owner_id': None,
                'expires_at': None,
                'queue_length': queue_result or 0
            }
    
    async def _is_available(self, resource_id: str) -> bool:
        """Check if resource is currently available"""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM resource_locks 
                WHERE resource_id = $1 
                AND expires_at > NOW()
            )
        """
        is_locked = await self.db.fetchval(query, resource_id)
        return not is_locked
    
    async def _add_to_queue(
        self,
        resource_id: str,
        owner_id: str,
        priority: int,
        timeout_seconds: int,
        team_id: str
    ):
        """Add lock request to queue"""
        query = """
            INSERT INTO resource_lock_queue (
                resource_id, owner_id, priority, 
                timeout_seconds, team_id
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        await self.db.execute(
            query,
            resource_id,
            owner_id,
            priority,
            timeout_seconds,
            team_id
        )
        
        # Get queue position
        position_query = """
            SELECT COUNT(*) + 1 as position
            FROM resource_lock_queue
            WHERE resource_id = $1 
            AND team_id = $2
            AND (priority < $3 OR (priority = $3 AND queued_at < NOW()))
        """
        position = await self.db.fetchval(position_query, resource_id, team_id, priority)
        
        # Publish event
        await self.event_bus.publish(Event(
            type="resource.queued",
            payload={
                "resource_id": resource_id,
                "owner_id": owner_id,
                "position": position,
                "priority": priority
            },
            priority=EventPriority.NORMAL,
            team_id=team_id
        ))
        
        print(f"[@lock_manager] 📝 Queued: {resource_id} for {owner_id} (position={position})")
    
    async def _process_queue(self, resource_id: str, team_id: str):
        """Process queue for released resource"""
        # Get next in queue (highest priority, earliest queued)
        query = """
            DELETE FROM resource_lock_queue
            WHERE id = (
                SELECT id FROM resource_lock_queue
                WHERE resource_id = $1 AND team_id = $2
                ORDER BY priority ASC, queued_at ASC
                LIMIT 1
            )
            RETURNING owner_id, priority, timeout_seconds
        """
        
        next_request = await self.db.fetchrow(query, resource_id, team_id)
        
        if next_request:
            # Auto-acquire lock for next in queue
            # Note: In real implementation, we'd notify the waiting agent
            # For now, just publish an event that the agent can subscribe to
            await self.event_bus.publish(Event(
                type="resource.ready",
                payload={
                    "resource_id": resource_id,
                    "owner_id": next_request['owner_id']
                },
                priority=EventPriority.HIGH,
                team_id=team_id
            ))
            
            print(f"[@lock_manager] 🔔 Ready: {resource_id} for {next_request['owner_id']}")
    
    async def _cleanup_expired(self):
        """Remove expired locks"""
        query = """
            DELETE FROM resource_locks
            WHERE expires_at < NOW()
            RETURNING resource_id, owner_id
        """
        
        expired = await self.db.fetch(query)
        
        if expired:
            print(f"[@lock_manager] 🧹 Cleaned up {len(expired)} expired locks")
            
            # Process queues for released resources
            for lock in expired:
                await self._process_queue(lock['resource_id'], 'default')  # TODO: track team_id
    
    async def _periodic_cleanup(self):
        """Periodic cleanup task (runs every 30 seconds)"""
        while self._running:
            try:
                await asyncio.sleep(30)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[@lock_manager] ❌ Cleanup error: {e}")


# Global instance
_lock_manager: Optional[ResourceLockManager] = None

def get_lock_manager() -> ResourceLockManager:
    """Get or create global lock manager instance"""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = ResourceLockManager()
    return _lock_manager

