from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from multi_agent.core.thread import Thread


class ThreadStore(ABC):

    @abstractmethod
    async def get(self, thread_id: str) -> Thread | None:
        ...

    @abstractmethod
    async def save(self, thread_id: str, thread: Thread) -> None:
        ...

    @abstractmethod
    async def delete(self, thread_id: str) -> None:
        ...

    @abstractmethod
    async def list_ids(self) -> list[str]:
        ...


class InMemoryStore(ThreadStore):
    def __init__(self) -> None:
        self._store: dict[str, Thread] = {}

    async def get(self, thread_id: str) -> Thread | None:
        return self._store.get(thread_id)

    async def save(self, thread_id: str, thread: Thread) -> None:
        self._store[thread_id] = thread

    async def delete(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)

    async def list_ids(self) -> list[str]:
        return list(self._store.keys())


class SQLiteStore(ThreadStore):
    def __init__(self, db_path: str = "threads.db") -> None:
        self.db_path = str(Path(db_path).resolve())
        self._conn: sqlite3.Connection | None = None

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, data TEXT)"
            )
        return self._conn

    async def get(self, thread_id: str) -> Thread | None:
        conn = self._ensure_conn()
        row = conn.execute("SELECT data FROM threads WHERE id = ?", (thread_id,)).fetchone()
        if row is None:
            return None
        return Thread.model_validate_json(row[0])

    async def save(self, thread_id: str, thread: Thread) -> None:
        conn = self._ensure_conn()
        conn.execute(
            "INSERT OR REPLACE INTO threads (id, data) VALUES (?, ?)",
            (thread_id, thread.model_dump_json()),
        )
        conn.commit()

    async def delete(self, thread_id: str) -> None:
        conn = self._ensure_conn()
        conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        conn.commit()

    async def list_ids(self) -> list[str]:
        conn = self._ensure_conn()
        rows = conn.execute("SELECT id FROM threads").fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
