import threading
import time
from typing import List, Dict, Any


class InputBuffer:
    """Thread-safe buffer that accumulates typed observations from any input source."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[Dict[str, Any]] = []

    def push(self, type: str, content: str) -> None:
        """Add an entry to the buffer."""
        entry = {
            "type": type,
            "content": content,
            "timestamp": time.time()
        }
        with self._lock:
            self._entries.append(entry)

    def pull_all(self) -> List[Dict[str, Any]]:
        """Drain and return all entries."""
        with self._lock:
            entries = self._entries.copy()
            self._entries.clear()
            return entries

    def peek(self) -> List[Dict[str, Any]]:
        """Non-destructive read of all entries."""
        with self._lock:
            return self._entries.copy()
