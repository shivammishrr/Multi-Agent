from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryAdapter(ABC):

    @abstractmethod
    async def store(self, key: str, value: str, metadata: dict[str, Any] | None = None) -> None:
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        ...


class InMemoryMemory(MemoryAdapter):
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    async def store(self, key: str, value: str, metadata: dict[str, Any] | None = None) -> None:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append({
            "key": key,
            "value": value,
            "metadata": metadata or {},
        })

    async def retrieve(self, key: str) -> list[dict[str, Any]]:
        return self._store.get(key, [])

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for entries in self._store.values():
            for entry in entries:
                if query_lower in entry["value"].lower():
                    results.append(entry)
        return results[:limit]


class Mem0Memory(MemoryAdapter):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._client: Any = None

    async def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from mem0 import MemoryClient
        except ImportError:
            raise ImportError("mem0 is required. Install: pip install mem0ai") from None
        self._client = MemoryClient(api_key=self.api_key) if self.api_key else MemoryClient()
        return self._client

    async def store(self, key: str, value: str, metadata: dict[str, Any] | None = None) -> None:
        client = await self._ensure_client()
        client.add(value, user_id=key, metadata=metadata or {})

    async def retrieve(self, key: str) -> list[dict[str, Any]]:
        client = await self._ensure_client()
        memories = client.get_all(user_id=key)
        return [{"key": key, "value": m.text, "metadata": m.metadata} for m in memories]

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        client = await self._ensure_client()
        memories = client.search(query, limit=limit)
        return [{"key": m.user_id or "", "value": m.text, "metadata": m.metadata, "score": m.score} for m in memories]
