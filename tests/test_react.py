import pytest
from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.tool import Tool, ToolResult, PermissionLevel
from multi_agent.features.codeact.sandbox import CodeActSandbox
from multi_agent.patterns.react import react


class DummyLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        from multi_agent.core.llm import LLMResponse
        return LLMResponse(content="done")


@pytest.mark.asyncio
async def test_react_without_tools():
    llm = DummyLLM(responses=[type("R", (), {"content": "hello!", "tool_calls": [], "stop_reason": "stop", "usage": {}})()])
    agent = Agent(name="test", system_prompt="be helpful")
    thread = await react("say hi", agent=agent, llm=llm)
    assert len(thread.events) >= 3
    assert thread.events[0].event_type == EventType.system_message
    assert thread.events[1].event_type == EventType.user_message
    assert thread.events[2].event_type == EventType.assistant_message


@pytest.mark.asyncio
async def test_react_codeact():
    llm = DummyLLM(responses=[
        type("R", (), {
            "content": "",
            "tool_calls": [{"id": "c1", "name": "python", "input": {"code": "print(2 + 2)"}}],
            "stop_reason": "tool_use",
            "usage": {},
        })(),
        type("R", (), {"content": "the answer is 4", "tool_calls": [], "stop_reason": "stop", "usage": {}})(),
    ])
    agent = Agent(name="codebot", system_prompt="use python", max_turns=5)
    sandbox = CodeActSandbox()
    thread = await react("what is 2+2", agent=agent, llm=llm, sandbox=sandbox)
    events = [e for e in thread.events if e.event_type == EventType.tool_result]
    assert len(events) > 0
    assert "4" in events[0].content


@pytest.mark.asyncio
async def test_react_max_turns():
    dummy_responses = []
    for idx in range(10):
        dummy_responses.append(
            type("R", (), {
                "content": "thinking...",
                "tool_calls": [{"id": f"c{idx}", "name": "python", "input": {"code": "print(1)"}}],
                "stop_reason": "tool_use",
                "usage": {},
            })()
        )
    llm = DummyLLM(responses=dummy_responses)
    agent = Agent(name="looper", system_prompt="loop", max_turns=3)
    sandbox = CodeActSandbox()
    thread = await react("loop", agent=agent, llm=llm, sandbox=sandbox)
    sys_msgs = [e for e in thread.events if e.event_type == EventType.system_message]
    assert any("max turns" in e.content for e in sys_msgs)


@pytest.mark.asyncio
async def test_react_with_additional_tools():
    async def my_tool(query: str) -> ToolResult:
        return ToolResult(success=True, output=f"result for: {query}")

    extra_tool = Tool(
        name="search",
        description="search for things",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        function=my_tool,
    )

    llm = DummyLLM(responses=[
        type("R", (), {
            "content": "",
            "tool_calls": [{"id": "c1", "name": "search", "input": {"query": "hello"}}],
            "stop_reason": "tool_use",
            "usage": {},
        })(),
        type("R", (), {"content": "done searching", "tool_calls": [], "stop_reason": "stop", "usage": {}})(),
    ])
    agent = Agent(name="searcher", system_prompt="search things", max_turns=5)
    thread = await react("search for hello", agent=agent, llm=llm, additional_tools=[extra_tool])
    tool_results = [e for e in thread.events if e.event_type == EventType.tool_result]
    assert len(tool_results) > 0
    assert "result for: hello" in tool_results[0].content
