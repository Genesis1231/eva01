"""
EVA's task memory — tracks what she wants to do.

Pure database operations. The Brain decides when to create/update tasks
via the task tool; the Heart reads open tasks to build pulse prompts.
"""

import re
from datetime import datetime, timezone

from config import logger
from eva.database.db import SQLiteHandler


class TaskDB:
    """SQLite-backed task store for EVA's self-directed goals."""

    def __init__(self, db: SQLiteHandler):
        self._db = db
        self._initialized = False

    async def init_db(self) -> None:
        if self._initialized:
            return
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     TEXT UNIQUE,
                objective   TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'open',
                scratchpad  TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._initialized = True

    async def create(self, objective: str) -> str:
        """Create a new task. Returns a readable ID: firstword-index."""
        prefix = self._first_word_slug(objective)
        now = datetime.now(timezone.utc).isoformat()
        row_id = await self._db.execute_insert(
            "INSERT INTO tasks (objective, status, created_at, updated_at) VALUES (?, 'open', ?, ?)",
            (objective, now, now),
        )
        task_id = f"{prefix}-{row_id}"
        await self._db.execute("UPDATE tasks SET task_id = ? WHERE id = ?", (task_id, row_id))
        return task_id

    @staticmethod
    def _first_word_slug(text: str) -> str:
        """Normalize first objective word for readable task IDs."""
        first_word = (text or "").strip().split(maxsplit=1)[0].lower()
        slug = re.sub(r"[^a-z0-9]+", "", first_word)
        return slug or "task"

    async def get_open(self) -> list[dict]:
        """Return all non-done tasks, oldest first."""
        rows = await self._db.fetchall(
            "SELECT task_id, objective, status, scratchpad FROM tasks WHERE status != 'done' ORDER BY id"
        )
        return [dict(r) for r in rows]

    async def update(self, task_id: str, scratchpad: str) -> None:
        """Update scratchpad and set status to in_progress."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE tasks SET scratchpad = ?, status = 'in_progress', updated_at = ? WHERE task_id = ?",
            (scratchpad, now, task_id),
        )

    async def complete(self, task_id: str) -> None:
        """Mark a task as done."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE tasks SET status = 'done', updated_at = ? WHERE task_id = ?",
            (now, task_id),
        )

    async def summary(self) -> str:
        """Human-readable summary of open tasks."""
        tasks = await self.get_open()
        if not tasks:
            return "No pending tasks."
        lines = []
        for t in tasks:
            line = f"- task_id  {t['task_id']}: [{t['status']}]: {t['objective']}"
            if t["scratchpad"]:
                line += f"\n  Notes: {t['scratchpad']}\n\n"
            lines.append(line)
        return "My tasks:\n" + "\n".join(lines)
