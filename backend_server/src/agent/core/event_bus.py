"""
Agent Event Bus

Pub/Sub event bus for triggering agents based on execution events.
Enables automatic analyzer triggering when scripts/testcases complete.

Architecture:
- Event-triggered analysis: Queued, processed by background worker
- Chat-triggered analysis: Immediate, separate from queue
"""

import asyncio
import logging
import threading
import queue
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Callable, List, Optional


logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Event types that can trigger agents"""
    SCRIPT_COMPLETED = "script.completed"
    TESTCASE_COMPLETED = "testcase.completed"
    CHAT_MESSAGE = "chat.message"


@dataclass
class ExecutionEvent:
    """
    Event emitted when script/testcase execution completes.
    Contains all data needed for analysis.
    """
    trigger_type: TriggerType
    
    # Execution identification
    execution_id: str
    script_name: str
    
    # Results
    success: bool
    exit_code: int
    execution_time_ms: int
    
    # URLs for analysis
    report_url: str
    logs_url: str
    
    # Device context
    host_name: str
    device_id: str
    
    # Optional metadata
    parameters: Optional[str] = None
    userinterface_name: Optional[str] = None
    team_id: Optional[str] = None
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Additional context (extensible)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "trigger_type": self.trigger_type.value,
            "execution_id": self.execution_id,
            "script_name": self.script_name,
            "success": self.success,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "report_url": self.report_url,
            "logs_url": self.logs_url,
            "host_name": self.host_name,
            "device_id": self.device_id,
            "parameters": self.parameters,
            "userinterface_name": self.userinterface_name,
            "team_id": self.team_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }
    
    def to_analysis_prompt(self) -> str:
        """Generate analysis prompt from execution data"""
        status = "✅ PASSED" if self.success else "❌ FAILED"
        duration_s = self.execution_time_ms / 1000
        
        return f"""Analyze execution result:

**Script**: {self.script_name}
**Status**: {status}
**Duration**: {duration_s:.1f}s
**Device**: {self.device_id} on {self.host_name}

**Report URL**: {self.report_url}
**Logs URL**: {self.logs_url}

Fetch the report and logs to determine:
1. Classification: TRUE_FAILURE, FALSE_POSITIVE, or INCONCLUSIVE
2. Root cause analysis
3. Recommendation: TRUST, REVIEW, or DISCARD"""


class AgentEventBus:
    """
    Singleton event bus for agent triggers.
    
    Agents subscribe to trigger types (script.completed, testcase.completed).
    When events are published, subscribed callbacks are invoked.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[str, List[Callable]] = {}
            cls._instance._recent_events: List[ExecutionEvent] = []
            cls._instance._max_recent = 100
            logger.info("AgentEventBus initialized")
        return cls._instance
    
    def subscribe(self, trigger_type: str, callback: Callable) -> None:
        """
        Subscribe a callback to a trigger type.
        
        Args:
            trigger_type: Event type to subscribe to (e.g., 'script.completed')
            callback: Async function to call when event occurs
        """
        if trigger_type not in self._subscribers:
            self._subscribers[trigger_type] = []
        self._subscribers[trigger_type].append(callback)
        logger.info(f"Subscribed to {trigger_type}: {callback.__name__}")
    
    def unsubscribe(self, trigger_type: str, callback: Callable) -> bool:
        """Remove a subscription"""
        if trigger_type in self._subscribers:
            try:
                self._subscribers[trigger_type].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    async def publish(self, event: ExecutionEvent) -> int:
        """
        Publish an execution event to all subscribers.
        
        Args:
            event: ExecutionEvent to publish
            
        Returns:
            Number of subscribers notified
        """
        trigger = event.trigger_type.value
        logger.info(f"Publishing event: {trigger} for {event.script_name}")
        
        # Store in recent events
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events.pop(0)
        
        # Notify subscribers
        count = 0
        if trigger in self._subscribers:
            for callback in self._subscribers[trigger]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(event))
                    else:
                        callback(event)
                    count += 1
                except Exception as e:
                    logger.error(f"Error in subscriber {callback.__name__}: {e}")
        
        logger.info(f"Notified {count} subscribers for {trigger}")
        return count
    
    def publish_sync(self, event: ExecutionEvent) -> None:
        """
        Publish event synchronously (for non-async contexts).
        Creates a new event loop if needed.
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.publish(event))
        except RuntimeError:
            # No running loop - store event for later
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_recent:
                self._recent_events.pop(0)
            logger.info(f"Stored event for later processing: {event.trigger_type.value}")
    
    def get_recent_events(self, limit: int = 10) -> List[ExecutionEvent]:
        """Get most recent events"""
        return self._recent_events[-limit:]
    
    def get_last_event(self) -> Optional[ExecutionEvent]:
        """Get the most recent event"""
        return self._recent_events[-1] if self._recent_events else None
    
    def get_subscribers(self, trigger_type: str) -> List[str]:
        """Get list of subscriber names for a trigger type"""
        if trigger_type in self._subscribers:
            return [cb.__name__ for cb in self._subscribers[trigger_type]]
        return []


# Singleton instance
event_bus = AgentEventBus()


def get_event_bus() -> AgentEventBus:
    """Get the singleton event bus instance"""
    return event_bus


class AnalysisQueue:
    """
    Background queue for event-triggered analysis.
    
    Architecture:
    - Event bus → Queue (non-blocking)
    - Background worker processes queue
    - Chat requests bypass queue (immediate response)
    
    This ensures:
    1. Chat analysis is always responsive
    2. Event-triggered analysis doesn't block
    3. Multiple executions are processed in order
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._queue: queue.Queue = queue.Queue()
            cls._instance._processing: bool = False
            cls._instance._current_task: Optional[ExecutionEvent] = None
            cls._instance._worker_thread: Optional[threading.Thread] = None
            cls._instance._shutdown: bool = False
            cls._instance._results: Dict[str, Dict[str, Any]] = {}
            cls._instance._max_results = 100
            cls._instance._callback: Optional[Callable] = None
            logger.info("AnalysisQueue initialized")
        return cls._instance
    
    def set_callback(self, callback: Callable) -> None:
        """
        Set the callback function to process queued events.
        
        Args:
            callback: Async or sync function that takes ExecutionEvent
        """
        self._callback = callback
        logger.info(f"Analysis callback set: {callback.__name__}")
    
    def enqueue(self, event: ExecutionEvent) -> str:
        """
        Add event to analysis queue (non-blocking).
        
        Returns:
            Queue position info
        """
        self._queue.put(event)
        position = self._queue.qsize()
        logger.info(f"Queued analysis for {event.script_name} (position: {position})")
        
        # Start worker if not running
        self._ensure_worker_running()
        
        return f"Queued at position {position}"
    
    def _ensure_worker_running(self) -> None:
        """Start background worker if not already running"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._shutdown = False
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="AnalysisQueueWorker"
            )
            self._worker_thread.start()
            logger.info("Analysis queue worker started")
    
    def _worker_loop(self) -> None:
        """Background worker that processes the queue"""
        logger.info("Analysis worker loop started")
        
        while not self._shutdown:
            try:
                # Wait for event with timeout (allows shutdown check)
                event = self._queue.get(timeout=1.0)
                
                self._processing = True
                self._current_task = event
                
                logger.info(f"Processing queued analysis: {event.script_name}")
                
                if self._callback:
                    try:
                        # Run callback (may be async)
                        if asyncio.iscoroutinefunction(self._callback):
                            # Create new event loop for thread
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                result = loop.run_until_complete(self._callback(event))
                            finally:
                                loop.close()
                        else:
                            result = self._callback(event)
                        
                        # Store result
                        self._store_result(event.execution_id, {
                            "status": "completed",
                            "result": result,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        logger.info(f"Completed analysis: {event.script_name}")
                        
                    except Exception as e:
                        logger.error(f"Analysis failed for {event.script_name}: {e}")
                        self._store_result(event.execution_id, {
                            "status": "failed",
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                self._queue.task_done()
                self._current_task = None
                self._processing = False
                
            except queue.Empty:
                # No events, continue waiting
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
                self._processing = False
                self._current_task = None
        
        logger.info("Analysis worker loop stopped")
    
    def _store_result(self, execution_id: str, result: Dict[str, Any]) -> None:
        """Store analysis result with size limit"""
        self._results[execution_id] = result
        
        # Trim old results
        if len(self._results) > self._max_results:
            oldest = list(self._results.keys())[0]
            del self._results[oldest]
    
    def get_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis result by execution ID"""
        return self._results.get(execution_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_size": self._queue.qsize(),
            "processing": self._processing,
            "current_task": self._current_task.script_name if self._current_task else None,
            "worker_alive": self._worker_thread.is_alive() if self._worker_thread else False,
            "completed_count": len(self._results)
        }
    
    def shutdown(self) -> None:
        """Stop the worker thread"""
        self._shutdown = True
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            logger.info("Analysis queue worker stopped")


# Singleton instance
analysis_queue = AnalysisQueue()


def get_analysis_queue() -> AnalysisQueue:
    """Get the singleton analysis queue instance"""
    return analysis_queue

