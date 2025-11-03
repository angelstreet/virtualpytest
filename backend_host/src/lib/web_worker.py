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
from typing import Callable, Dict, Any, Optional, Awaitable


class WebTask:
    def __init__(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[Any], Awaitable[Dict[str, Any]]]):
        self.execution_id: str = str(uuid.uuid4())
        self.kind: str = kind
        self.payload: Dict[str, Any] = payload
        self.run_fn: Callable[[Any], Awaitable[Dict[str, Any]]] = run_fn
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
        
        # Persistent async loop
        self.loop = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        
        self._thread: threading.Thread = threading.Thread(
            target=self._worker_thread,
            name="PlaywrightAsyncWorker",
            daemon=True,
        )
        self._thread.start()

    @classmethod
    def instance(cls) -> "WebWorker":
        with cls._lock:
            if not cls._instance:
                cls._instance = WebWorker()
        return cls._instance

    def submit_async(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[Any], Awaitable[Dict[str, Any]]]) -> str:
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

    def submit_sync(self, kind: str, payload: Dict[str, Any], run_fn: Callable[[Any], Awaitable[Dict[str, Any]]]) -> Dict[str, Any]:
        task_id = self.submit_async(kind, payload, run_fn)
        while True:
            status = self.get_status(task_id)
            if status['status'] == 'completed':
                return status['result']
            elif status['status'] == 'error':
                return {'success': False, 'error': status['error']}
            time.sleep(0.1)

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

    def _worker_thread(self):
        import asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.loop.run_until_complete(self._init_playwright())
        self.loop.create_task(self._queue_processor())
        self.loop.run_forever()

    async def _init_playwright(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        print("[WebWorker] Persistent Playwright initialized")

    def _process_queue(self):
        while True:
            task = self._q.get()
            future = asyncio.run_coroutine_threadsafe(self._run_task(task), self.loop)
            result = future.result()
            # Handle result...

    async def _run_task(self, task):
        try:
            # Pass persistent page to run_fn if needed
            result = await task.run_fn(self._page)
            task.result = result
            # Update executions
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

    async def _queue_processor(self):
        while True:
            task = await self.loop.run_in_executor(None, self._q.get)
            try:
                result = await task.run_fn(self._page)
                with self._exec_lock:
                    if task.execution_id in self._executions:
                        self._executions[task.execution_id].update({
                            'status': 'completed',
                            'result': result,
                            'progress': 100,
                            'message': result.get('message', 'Completed')
                        })
            except Exception as e:
                with self._exec_lock:
                    if task.execution_id in self._executions:
                        self._executions[task.execution_id].update({
                            'status': 'error',
                            'error': str(e),
                            'message': f'Failed: {e}'
                        })
            finally:
                task.done.set()


