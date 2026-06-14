import json
import pytest
from multi_agent.core.llm import LLMResponse
from multi_agent.patterns.orchestrator_workers import _decompose, _synthesize, orchestrator_workers


class DummyLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return LLMResponse(content="done")


@pytest.mark.asyncio
async def test_decompose_json():
    llm = DummyLLM(responses=[
        LLMResponse(content=json.dumps(["research A", "research B", "research C"])),
    ])
    from multi_agent.core.agent import Agent
    agent = Agent(name="orch", model="gpt-4o")
    steps = await _decompose("test task", 3, agent, llm)
    assert steps == ["research A", "research B", "research C"]


@pytest.mark.asyncio
async def test_synthesize():
    llm = DummyLLM(responses=[
        LLMResponse(content="Here is the combined answer: ..."),
    ])
    from multi_agent.core.agent import Agent
    agent = Agent(name="synth", model="gpt-4o")
    results = [("sub1", "result1"), ("sub2", "result2")]
    synthesis = await _synthesize("task", results, agent, llm)
    assert "combined" in synthesis


@pytest.mark.asyncio
async def test_orchestrator_workers_flow():
    class TrackingLLM:
        def __init__(self):
            self.calls = []

        async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
            self.calls.append(messages)
            if len(self.calls) == 1:
                return LLMResponse(content=json.dumps(["task A", "task B"]))
            return LLMResponse(content="done")

    from multi_agent.core.agent import Agent
    agent = Agent(name="orch", model="gpt-4o", max_turns=1)
    thread = await orchestrator_workers("test", num_workers=2, agent=agent, llm=TrackingLLM())
    assert len(thread.events) > 0
    assistant_msgs = [e for e in thread.events if e.event_type.value == "assistant_message"]
    assert len(assistant_msgs) > 0
