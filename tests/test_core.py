import pytest
from datetime import datetime, timezone

from multi_agent.core.event import Event, EventType
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool, PermissionLevel, ToolResult
from multi_agent.core.agent import Agent
from multi_agent.core.store import InMemoryStore


class TestEvent:
    def test_create_event(self):
        event = Event(event_type=EventType.user_message, content="hello")
        assert event.event_type == EventType.user_message
        assert event.content == "hello"
        assert isinstance(event.timestamp, datetime)

    def test_error_event(self):
        event = Event(event_type=EventType.error, content="something broke")
        assert event.event_type == EventType.error

    def test_event_with_metadata(self):
        event = Event(event_type=EventType.tool_call, content="", metadata={"tool": "bash", "args": ["ls"]})
        assert event.metadata["tool"] == "bash"


class TestThread:
    def test_empty_thread(self):
        t = Thread()
        assert len(t.events) == 0

    def test_add_event(self):
        t = Thread()
        e = Event(event_type=EventType.user_message, content="hi")
        t.add_event(e)
        assert len(t.events) == 1
        assert t.last_event() == e

    def test_to_llm_messages(self):
        t = Thread()
        t.add_event(Event(event_type=EventType.system_message, content="you are a bot"))
        t.add_event(Event(event_type=EventType.user_message, content="hello"))
        t.add_event(Event(event_type=EventType.assistant_message, content="world"))
        messages = t.to_llm_messages()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_fork(self):
        t = Thread()
        t.add_event(Event(event_type=EventType.user_message, content="hi"))
        t2 = t.fork()
        t2.add_event(Event(event_type=EventType.user_message, content="bye"))
        assert len(t.events) == 1
        assert len(t2.events) == 2

    def test_to_xml_context(self):
        t = Thread()
        t.add_event(Event(event_type=EventType.system_message, content="be helpful"))
        t.add_event(Event(event_type=EventType.user_message, content="hello", agent="user1"))
        xml = t.to_xml_context()
        assert "<SYSTEM_MESSAGE>" in xml
        assert "<USER_MESSAGE agent=user1>" in xml

    def test_total_tokens(self):
        t = Thread()
        t.add_event(Event(event_type=EventType.user_message, content="hello world"))
        assert t.total_tokens() == 11


class TestTool:
    def test_create_tool(self):
        def my_fn(x: int) -> ToolResult:
            return ToolResult(success=True, output=str(x * 2))
        tool = Tool(name="double", description="double a number", function=my_fn)
        assert tool.name == "double"
        assert tool.permission == PermissionLevel.allow

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        async def my_fn(x: int) -> ToolResult:
            return ToolResult(success=True, output=str(x * 2))
        tool = Tool(name="double", description="double a number", function=my_fn)
        result = await tool.execute(x=5)
        assert result.success is True
        assert result.output == "10"

    @pytest.mark.asyncio
    async def test_execute_no_function(self):
        tool = Tool(name="noop", description="no function")
        result = await tool.execute()
        assert result.success is False

    def test_to_openai_tool(self):
        tool = Tool(name="test", description="a test", parameters={"type": "object"})
        ot = tool.to_openai_tool()
        assert ot["function"]["name"] == "test"


class TestAgent:
    def test_create_agent(self):
        agent = Agent(name="bob", system_prompt="be helpful")
        assert agent.name == "bob"
        assert agent.model == "gpt-4o"

    def test_agent_with_tools(self):
        tool = Tool(name="calc", description="calculator")
        agent = Agent(name="calc_bot", tools=[tool], system_prompt="do math")
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "calc"


class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        store = InMemoryStore()
        thread = Thread()
        thread.add_event(Event(event_type=EventType.user_message, content="hello"))
        await store.save("test-1", thread)
        loaded = await store.get("test-1")
        assert loaded is not None
        assert len(loaded.events) == 1
        assert loaded.events[0].content == "hello"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        store = InMemoryStore()
        result = await store.get("nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        store = InMemoryStore()
        thread = Thread()
        await store.save("t", thread)
        await store.delete("t")
        assert await store.get("t") is None

    @pytest.mark.asyncio
    async def test_list_ids(self):
        store = InMemoryStore()
        await store.save("a", Thread())
        await store.save("b", Thread())
        ids = await store.list_ids()
        assert sorted(ids) == ["a", "b"]
