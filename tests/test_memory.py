import pytest
from multi_agent.features.memory.adapters import InMemoryMemory


class TestInMemoryMemory:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        mem = InMemoryMemory()
        await mem.store("user1", "likes Python")
        results = await mem.retrieve("user1")
        assert len(results) == 1
        assert results[0]["value"] == "likes Python"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self):
        mem = InMemoryMemory()
        results = await mem.retrieve("nobody")
        assert results == []

    @pytest.mark.asyncio
    async def test_search(self):
        mem = InMemoryMemory()
        await mem.store("u1", "likes Python programming")
        await mem.store("u2", "prefers JavaScript")
        await mem.store("u1", "works on data science")

        results = await mem.search("python")
        assert len(results) >= 1
        assert any("Python" in r["value"] for r in results)

    @pytest.mark.asyncio
    async def test_search_nonexistent(self):
        mem = InMemoryMemory()
        results = await mem.search("zzz_nonexistent_zzz")
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_entries_same_key(self):
        mem = InMemoryMemory()
        await mem.store("user1", "first memory")
        await mem.store("user1", "second memory")
        results = await mem.retrieve("user1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_store_with_metadata(self):
        mem = InMemoryMemory()
        await mem.store("user1", "important fact", {"source": "conversation", "timestamp": "2024-01-01"})
        results = await mem.retrieve("user1")
        assert results[0]["metadata"]["source"] == "conversation"
