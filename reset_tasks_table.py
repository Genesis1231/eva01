"""Reset EVA tasks table to use autoincrement id + assigned task_id.

This script intentionally drops all current task rows.
Usage:
    python reset_tasks_table.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DATA_DIR, SQLITE_DB_NAME


def main() -> None:
    db_path = Path(DATA_DIR) / "database" / SQLITE_DB_NAME
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS tasks")
        conn.execute("DROP TABLE IF EXISTS task_id_sequence")
        conn.execute(
            """
            CREATE TABLE tasks (
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
        conn.commit()

    print(f"Reset tasks table at: {db_path}")


if __name__ == "__main__":
    main()
