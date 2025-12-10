"""
Trigger Handler

Wires up event bus → analysis queue → analyzer agent.
Handles automatic analysis when scripts/testcases complete.
"""

import logging
from typing import Optional

from .event_bus import (
    get_event_bus,
    get_analysis_queue,
    ExecutionEvent,
    TriggerType,
)


logger = logging.getLogger(__name__)


class TriggerHandler:
    """
    Handles event-triggered analysis.
    
    Subscribes to execution events and routes them to the analysis queue.
    The queue processes events in background, not blocking chat requests.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self) -> None:
        """
        Initialize trigger handler - call once on app startup.
        
        Subscribes to execution events and sets up queue callback.
        """
        if self._initialized:
            logger.info("TriggerHandler already initialized")
            return
        
        event_bus = get_event_bus()
        analysis_queue = get_analysis_queue()
        
        # Subscribe to execution events → route to queue
        event_bus.subscribe(
            TriggerType.SCRIPT_COMPLETED.value,
            self._handle_execution_event
        )
        event_bus.subscribe(
            TriggerType.TESTCASE_COMPLETED.value,
            self._handle_execution_event
        )
        
        # Set callback for queue processing
        analysis_queue.set_callback(self._process_analysis)
        
        self._initialized = True
        logger.info("TriggerHandler initialized - listening for execution events")
    
    def _handle_execution_event(self, event: ExecutionEvent) -> None:
        """
        Handle execution completion event.
        
        Routes failed executions to analysis queue.
        Passed executions are stored but not queued for analysis.
        """
        logger.info(f"Received execution event: {event.script_name} (success={event.success})")
        
        # Only queue failed executions for analysis
        if not event.success:
            analysis_queue = get_analysis_queue()
            analysis_queue.enqueue(event)
            logger.info(f"Queued failed execution for analysis: {event.script_name}")
        else:
            logger.info(f"Skipping analysis for passed execution: {event.script_name}")
    
    def _process_analysis(self, event: ExecutionEvent) -> dict:
        """
        Process queued analysis event.
        
        This is called by the background worker thread.
        Performs actual analysis using the analyzer agent.
        """
        logger.info(f"Processing analysis for: {event.script_name}")
        
        try:
            # Import here to avoid circular imports
            from .manager import QAManagerAgent
            from .session import Session
            
            # Create analyzer agent instance
            analyzer = QAManagerAgent(agent_id='analyzer')
            session = Session()
            
            # Inject execution context into session
            session.set_context('execution_id', event.execution_id)
            session.set_context('report_url', event.report_url)
            session.set_context('logs_url', event.logs_url)
            session.set_context('script_name', event.script_name)
            session.set_context('device_id', event.device_id)
            session.set_context('host_name', event.host_name)
            session.set_context('trigger_type', 'event')  # Mark as event-triggered
            
            # Generate analysis prompt
            prompt = event.to_analysis_prompt()
            
            # Process synchronously (we're in background thread)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = {"status": "completed", "events": []}
                
                async def run_analysis():
                    async for evt in analyzer.process_message(prompt, session):
                        result["events"].append(evt.to_dict())
                        if evt.type.value == "message":
                            result["analysis"] = evt.content
                
                loop.run_until_complete(run_analysis())
                
            finally:
                loop.close()
            
            logger.info(f"Analysis completed for: {event.script_name}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {event.script_name}: {e}")
            return {"status": "failed", "error": str(e)}
    
    def shutdown(self) -> None:
        """Shutdown trigger handler"""
        analysis_queue = get_analysis_queue()
        analysis_queue.shutdown()
        self._initialized = False
        logger.info("TriggerHandler shutdown")


# Singleton instance
_trigger_handler: Optional[TriggerHandler] = None


def get_trigger_handler() -> TriggerHandler:
    """Get the singleton trigger handler instance"""
    global _trigger_handler
    if _trigger_handler is None:
        _trigger_handler = TriggerHandler()
    return _trigger_handler


def initialize_triggers() -> None:
    """
    Initialize trigger handling - call once on app startup.
    
    Example:
        from backend_server.src.agent.core.trigger_handler import initialize_triggers
        initialize_triggers()
    """
    handler = get_trigger_handler()
    handler.initialize()

