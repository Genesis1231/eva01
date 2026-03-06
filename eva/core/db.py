"""Shared async SQLite handler for EVA core databases."""

import asyncio
from typing import Any, Iterable
import aiosqlite

from config import DATA_DIR, SQLITE_DB_NAME

class SQLiteHandler:
    """Centralized connection and query helper for async SQLite access."""

    
    def __init__(self):
        self._connections: dict[str, aiosqlite.Connection] = {}
        self._write_locks: dict[str, asyncio.Lock] = {}
        self._init_lock = asyncio.Lock()
        self._db_dir = DATA_DIR / "database"

    async def _get_connection(self, db_name: str = SQLITE_DB_NAME) -> aiosqlite.Connection:
        """ Get or create a connection for the specified database name."""
        
        conn = self._connections.get(db_name)
        if conn is not None:
            return conn

        # Locked initialization to prevent race conditions during startup
        async with self._init_lock:
            if db_name in self._connections:
                return self._connections[db_name]

            self._db_dir.mkdir(parents=True, exist_ok=True)
            db_path = self._db_dir / db_name
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA busy_timeout=5000;")
            await conn.execute("PRAGMA foreign_keys=ON;")
            await conn.commit()

            self._connections[db_name] = conn
            self._write_locks[db_name] = asyncio.Lock()
            return conn

    async def execute(
        self, 
        query: str, 
        params: tuple[Any, ...] = (), 
        db_name: str = SQLITE_DB_NAME
    ) -> None:
        """ Execute a query that modifies the database (INSERT, UPDATE, DELETE)."""
        conn = await self._get_connection(db_name)
        async with self._write_locks[db_name]:
            await conn.execute(query, params)
            await conn.commit()

    async def executemany(
        self,
        query: str,
        params_list: list[tuple[Any, ...]],
        db_name: str = SQLITE_DB_NAME,
    ) -> None:
        """ Execute a query with multiple sets of parameters."""
        conn = await self._get_connection(db_name)
        async with self._write_locks[db_name]:
            await conn.executemany(query, params_list)
            await conn.commit()

    async def fetchall(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        db_name: str = SQLITE_DB_NAME,
    ) -> Iterable[aiosqlite.Row]:
        """ Execute a SELECT query and return all results."""
        conn = await self._get_connection(db_name)
        async with conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def fetchone(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        db_name: str = SQLITE_DB_NAME,
    ) -> aiosqlite.Row | None:
        """ Execute a SELECT query and return a single result."""
        conn = await self._get_connection(db_name)
        async with conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def close(self, db_name: str = SQLITE_DB_NAME) -> None:
        """ Close the connection for the specified database name."""
        async with self._init_lock:
            conn = self._connections.pop(db_name, None)
            self._write_locks.pop(db_name, None)
            if conn is not None:
                await conn.close()

    async def close_all(self) -> None:
        """ Close all database connections."""
        async with self._init_lock:
            for conn in self._connections.values():
                await conn.close()
            self._connections.clear()
            self._write_locks.clear()

