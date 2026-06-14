import pytest
from multi_agent.integrations.a2a.card import AgentCard, AgentCapabilities
from multi_agent.integrations.a2a.client import A2AClient
from multi_agent.integrations.a2a.server import A2AServer


class TestAgentCard:
    def test_create_card(self):
        card = AgentCard(name="test-agent", description="a test agent", url="http://localhost:8080")
        assert card.name == "test-agent"
        assert card.version == "1.0.0"

    def test_card_capabilities_default(self):
        card = AgentCard(name="a")
        assert card.capabilities.streaming is False

    def test_card_to_dict(self):
        card = AgentCard(name="test", skills=["research", "code"])
        d = card.model_dump()
        assert d["name"] == "test"
        assert len(d["skills"]) == 2


class TestA2AServer:
    @pytest.mark.asyncio
    async def test_handle_task(self):
        card = AgentCard(name="test-agent")
        server = A2AServer(card)
        result = await server.handle_task({"task": "do something"})
        assert "id" in result
        assert result["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_handle_task_with_handler(self):
        card = AgentCard(name="test-agent")

        async def handler(task, metadata):
            return f"handled: {task}"

        server = A2AServer(card, handler=handler)
        result = await server.handle_task({"task": "hello"})
        assert result["status"] == "completed"
        assert "handled: hello" in result["result"]

    @pytest.mark.asyncio
    async def test_handle_task_error(self):
        card = AgentCard(name="test-agent")

        async def handler(task, metadata):
            raise ValueError("oops")

        server = A2AServer(card, handler=handler)
        result = await server.handle_task({"task": "fail"})
        assert result["status"] == "failed"

    def test_get_card_dict(self):
        card = AgentCard(name="my-agent")
        server = A2AServer(card)
        d = server.get_card_dict()
        assert d["name"] == "my-agent"
