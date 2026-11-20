"""
In-memory pub/sub for streaming orchestrator progress.

A single run has one queue. Each event is a dict with at least:
    { "type": str, "ts": float, ...payload }

Frontend / SSE clients subscribe to the queue for their run_id and receive
events in real time. Bus cleans up automatically when the run ends.
"""
import asyncio
import time
import uuid
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    def new_run(self) -> str:
        run_id = uuid.uuid4().hex
        self._queues[run_id] = asyncio.Queue()
        return run_id

    def emit(self, run_id: str, event_type: str, **payload: Any) -> None:
        q = self._queues.get(run_id)
        if q is None:
            return
        q.put_nowait({
            "type": event_type,
            "ts": time.time(),
            **payload,
        })

    async def next(self, run_id: str) -> dict[str, Any] | None:
        q = self._queues.get(run_id)
        if q is None:
            return None
        return await q.get()

    def close(self, run_id: str) -> None:
        q = self._queues.get(run_id)
        if q is not None:
            q.put_nowait({"type": "end", "ts": time.time()})
        self._queues.pop(run_id, None)


bus = EventBus()
