import json
import pytest
from multi_agent.core.llm import LLMResponse
from multi_agent.patterns.hierarchical import hierarchical


@pytest.mark.asyncio
async def test_hierarchical_flow():
    class TrackingLLM:
        def __init__(self):
            self.calls = []

        async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
            self.calls.append(messages)
            if len(self.calls) == 1:
                return LLMResponse(content=json.dumps({"researcher": "research topic", "coder": "implement solution"}))
            return LLMResponse(content="done")

    from multi_agent.core.agent import Agent
    supervisor = Agent(name="supervisor", model="gpt-4o", max_turns=1)
    workers = [
        Agent(name="researcher", model="gpt-4o-mini", max_turns=1),
        Agent(name="coder", model="gpt-4o-mini", max_turns=1),
    ]
    thread = await hierarchical("build a web app", supervisor_agent=supervisor, workers=workers, llm=TrackingLLM())
    assert len(thread.events) > 0
    system_msgs = [e for e in thread.events if e.event_type.value == "system_message"]
    assert any("Supervisor delegated" in e.content for e in system_msgs)
