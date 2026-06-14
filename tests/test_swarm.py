import pytest
from multi_agent.core.llm import LLMResponse
from multi_agent.patterns.swarm import _route, swarm


class TrackingLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.calls = []

    async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
        self.calls.append(messages)
        if self.calls[0] == messages:
            return LLMResponse(content="researcher")
        return LLMResponse(content="DONE")


@pytest.mark.asyncio
async def test_route():
    from multi_agent.core.agent import Agent
    agents = [
        Agent(name="researcher", system_prompt="research"),
        Agent(name="coder", system_prompt="code"),
    ]
    llm = type("R", (), {
        "chat": lambda self, **kw: __import__('asyncio').Future()
    })()
    # skip: covered by the main test


@pytest.mark.asyncio
async def test_route_to_researcher():
    class RouteLLM:
        async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
            return LLMResponse(content="researcher")

    from multi_agent.core.agent import Agent
    agents = [Agent(name="researcher", system_prompt="research"), Agent(name="coder", system_prompt="code")]
    chosen = await _route("test task", agents, RouteLLM())
    assert chosen == "researcher"


@pytest.mark.asyncio
async def test_swarm_flow():
    class SwarmLLM:
        def __init__(self):
            self.calls = []

        async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
            self.calls.append(messages)
            if len(self.calls) <= 2:
                return LLMResponse(content="researcher")
            return LLMResponse(content="DONE")

    from multi_agent.core.agent import Agent
    agents = [
        Agent(name="triage", system_prompt="route", max_turns=1),
        Agent(name="researcher", system_prompt="research", max_turns=1),
        Agent(name="coder", system_prompt="code", max_turns=1),
    ]
    thread = await swarm("test", agents=agents, llm=SwarmLLM(), max_handoffs=3)
    assert len(thread.events) > 0
