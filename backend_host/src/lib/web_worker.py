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
        # Dedicated inner thread that will execute ALL Playwright work to avoid
        # any interaction with threads that may have an asyncio event loop.
        self._sync_q: "queue.Queue[Callable[[], Dict[str, Any]]]" = queue.Queue()
        self._sync_res_q: "queue.Queue[Dict[str, Any] | Exception]" = queue.Queue()
        self._sync_thread: threading.Thread = threading.Thread(
            target=self._sync_loop,
            name="PlaywrightSync",
            daemon=True,
        )
        self._sync_thread.start()
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
        # Initialize Playwright/browser/page lazily inside run_fn if needed.
        while True:
            task: WebTask = self._q.get()
            try:
                # Execute the task inside the dedicated PlaywrightSync thread.
                result = self._run_in_sync_thread(task.run_fn)
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

    def _run_in_sync_thread(self, run_fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        """Run function in the dedicated PlaywrightSync thread and return result.
        Ensures all Playwright Sync API calls live on a single thread without
        any asyncio event loop interference.
        """
        done = threading.Event()
        result_holder: Dict[str, Any] = {}
        error_holder: Dict[str, Any] = {}

        def wrapper():
            try:
                res = run_fn()
                self._sync_res_q.put(res)
            except Exception as e:  # noqa: BLE001
                self._sync_res_q.put(e)
            finally:
                done.set()

        self._sync_q.put(wrapper)
        done.wait()
        res = self._sync_res_q.get()
        if isinstance(res, Exception):
            raise res
        return res

    def _sync_loop(self):
        """Dedicated loop that executes Playwright tasks on a clean thread.
        This thread must never create or run an asyncio event loop.
        """
        while True:
            fn = self._sync_q.get()
            try:
                fn()
            finally:
                # Ensure queue task completion semantics if needed later
                pass


