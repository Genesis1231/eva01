"""
Sense Buffer - The incoming event bus for EVA's perception layer.

Bridges sync sense threads (camera, microphone) into the async LangGraph
event loop via asyncio.Queue + loop.call_soon_threadsafe.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SenseEntry:
    """A single perception event from any sense modality."""
    type: str               # e.g., "observation", "audio", "user_message"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class SenseBuffer:
    """
    Thread-safe bridge from sync sense threads to the async LangGraph loop.

    Sync threads call push() freely — it uses call_soon_threadsafe to
    schedule the enqueue on the running event loop.  LangGraph awaits
    get() or get_all() to consume events.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[SenseEntry] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending: list[SenseEntry] = []   # entries buffered before loop attach

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the running event loop.  Called once at startup.

        Any entries accumulated before the loop was attached (pre-loop
        pushes, e.g. during module init) are flushed into the queue now.
        """
        self._loop = loop
        for entry in self._pending:
            self._queue.put_nowait(entry)
        self._pending.clear()

    # ------------------------------------------------------------------
    # Producer side (sync — safe to call from any thread)
    # ------------------------------------------------------------------

    def push(self, type: str, content: str) -> None:
        """Enqueue a sense event.  Safe to call from any plain thread.

        If the event loop is attached, schedules put_nowait on the loop
        via call_soon_threadsafe (the only correct way to touch an asyncio
        Queue from outside the loop's thread).  If no loop is attached yet,
        holds the entry in a plain list so nothing is lost during startup.
        """
        entry = SenseEntry(type=type, content=content)
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._queue.put_nowait, entry)
        else:
            self._pending.append(entry)

    # ------------------------------------------------------------------
    # Consumer side (async — LangGraph / coroutines only)
    # ------------------------------------------------------------------

    async def get(self) -> SenseEntry:
        """Wait for and return the next sense event (blocks until one arrives)."""
        return await self._queue.get()

    async def get_all(self) -> list[SenseEntry]:
        """Drain every event currently in the queue without blocking.

        Returns an empty list immediately if the queue is empty.
        """
        events: list[SenseEntry] = []
        while not self._queue.empty():
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events

    # ------------------------------------------------------------------
    # Introspection / test helpers
    # ------------------------------------------------------------------

    def peek(self) -> list[dict]:
        """Return a snapshot of queued entries as dicts (non-destructive).

        Includes both pre-loop pending entries and queued entries, in
        arrival order.  Reads directly from the underlying deque —
        acceptable for tests and diagnostics; do not use in hot paths.
        """
        pending_dicts = [_entry_to_dict(e) for e in self._pending]
        queued_dicts = [_entry_to_dict(e) for e in list(self._queue._queue)]  # type: ignore[attr-defined]
        return pending_dicts + queued_dicts

    def pull_all(self) -> list[dict]:
        """Drain and return all queued entries as dicts.

        Kept for test compatibility.  In production, prefer the async
        get() / get_all() interface.
        """
        entries: list[dict] = []
        # Drain from pending (pre-loop buffer) first
        for entry in self._pending:
            entries.append(_entry_to_dict(entry))
        self._pending.clear()
        # Drain from the asyncio queue
        while not self._queue.empty():
            try:
                entries.append(_entry_to_dict(self._queue.get_nowait()))
            except asyncio.QueueEmpty:
                break
        return entries

    def empty(self) -> bool:
        """True when both pending list and queue are empty."""
        return not self._pending and self._queue.empty()


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _entry_to_dict(entry: SenseEntry) -> dict:
    return {
        "type": entry.type,
        "content": entry.content,
        "timestamp": entry.timestamp,
    }
