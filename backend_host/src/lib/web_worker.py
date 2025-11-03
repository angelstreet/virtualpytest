"""
Dedicated Playwright Worker Thread

Owns a single long-lived thread where ALL Playwright operations execute.
Provides async (execution_id-based) and sync submission APIs.
"""

from __future__ import annotations

import threading
import queue
import time
import uuid
from typing import Callable, Dict, Any, Optional
import asyncio


class WebTask:
    def __init__(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[], Dict[str, Any]]):
        self.execution_id: str = str(uuid.uuid4())
        self.kind: str = kind
        self.payload: Dict[str, Any] = payload
        self.run_fn: Callable[[], Dict[str, Any]] = run_fn
        self.done: threading.Event = threading.Event()
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None


class WebWorker:
    _instance: Optional["WebWorker"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        self._q: "queue.Queue[WebTask]" = queue.Queue()
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._exec_lock: threading.Lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_ready: threading.Event = threading.Event()
        self._thread: threading.Thread = threading.Thread(
            target=self._loop,
            name="PlaywrightWorker",
            daemon=True,
        )
        self._thread.start()

    @classmethod
    def instance(cls) -> "WebWorker":
        with cls._lock:
            if not cls._instance:
                cls._instance = WebWorker()
        return cls._instance

    def submit_async(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[], Dict[str, Any]]) -> str:
        task = WebTask(kind, payload, run_fn)
        with self._exec_lock:
            self._executions[task.execution_id] = {
                'execution_id': task.execution_id,
                'status': 'running',
                'result': None,
                'error': None,
                'start_time': time.time(),
                'progress': 0,
                'message': f'{kind} started'
            }
        self._q.put(task)
        return task.execution_id

    def submit_sync(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        task = WebTask(kind, payload, run_fn)
        self._q.put(task)
        task.done.wait()
        if task.error:
            return {'success': False, 'error': task.error}
        return task.result or {'success': False, 'error': 'No result'}

    def get_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        with self._exec_lock:
            status = self._executions.get(execution_id)
            if not status:
                return None
            elapsed = int((time.time() - status['start_time']) * 1000)
            # Return a copy without start_time
            view = dict(status)
            view['elapsed_time_ms'] = elapsed
            view.pop('start_time', None)
            return view

    def _loop(self):
        # Create and own a dedicated asyncio event loop in this worker thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()

        # Process tasks; run_fn may call into code that schedules coroutines on this loop via run_coro()
        while True:
            task: WebTask = self._q.get()
            try:
                result = task.run_fn()
                task.result = result
                with self._exec_lock:
                    if task.execution_id in self._executions:
                        self._executions[task.execution_id].update({
                            'status': 'completed',
                            'result': result,
                            'progress': 100,
                            'message': result.get('message', 'Completed')
                        })
            except Exception as e:
                task.error = str(e)
                with self._exec_lock:
                    if task.execution_id in self._executions:
                        self._executions[task.execution_id].update({
                            'status': 'error',
                            'error': str(e),
                            'message': f'Failed: {e}'
                        })
            finally:
                task.done.set()

    def run_coro(self, coro):
        """Synchronously run a coroutine on the worker's event loop.
        - If called from the worker thread: run_until_complete (loop not running).
        - If called from another thread: run_coroutine_threadsafe.
        """
        import threading
        self._loop_ready.wait(timeout=5)
        if not self._loop:
            raise RuntimeError("Playwright worker loop not initialized")
        if threading.current_thread().name == "PlaywrightWorker":
            return self._loop.run_until_complete(coro)
        else:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result()


