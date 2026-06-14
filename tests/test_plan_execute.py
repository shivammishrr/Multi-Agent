import pytest
import json
from multi_agent.core.llm import LLMResponse
from multi_agent.patterns.plan_execute import _parse_steps, _plan, plan_and_execute


def test_parse_json_steps():
    content = '["step one", "step two", "step three"]'
    steps = _parse_steps(content)
    assert steps == ["step one", "step two", "step three"]


def test_parse_numbered_steps():
    content = "1. first step\n2. second step\n3. third step"
    steps = _parse_steps(content)
    assert steps == ["first step", "second step", "third step"]


def test_parse_mixed_returns_single():
    content = "just a single step because the task is simple"
    steps = _parse_steps(content)
    assert len(steps) == 1


class DummyPlanLLM:
    def __init__(self, plan_response):
        self.plan_response = plan_response

    async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
        return LLMResponse(content=self.plan_response)


@pytest.mark.asyncio
async def test_plan_creation():
    from multi_agent.core.agent import Agent
    from multi_agent.core.thread import Thread

    plan_json = json.dumps(["research topic", "write code", "summarize"])
    llm = DummyPlanLLM(plan_json)
    agent = Agent(name="planner", model="gpt-4o")
    thread = Thread()
    steps = await _plan("test task", agent, llm, thread)
    assert len(steps) == 3
    assert steps == ["research topic", "write code", "summarize"]
    assert any("3 steps" in e.content for e in thread.events if e.event_type.value == "system_message")


def _make_dummy_resp(text, tool_calls=None):
    return type("R", (), {"content": text, "tool_calls": tool_calls or [], "stop_reason": "stop", "usage": {}})()


@pytest.mark.asyncio
async def test_plan_execute_flow():
    calls = []

    class TrackingLLM:
        async def chat(self, messages, tools=None, model=None, temperature=0.0, max_tokens=4096):
            calls.append(model)
            if len(calls) == 1:
                return LLMResponse(content=json.dumps(["do step one", "do step two"]))
            return LLMResponse(content="step done")

    from multi_agent.core.agent import Agent
    agent_p = Agent(name="planner", model="gpt-4o")
    agent_e = Agent(name="executor", model="gpt-4o-mini", max_turns=1)
    thread = await plan_and_execute(
        "test task", planner_agent=agent_p, executor_agent=agent_e, llm=TrackingLLM(), max_plan_iterations=2
    )
    assert len(thread.events) > 0
    final_events = [e for e in thread.events if e.event_type.value == "system_message"]
    assert any("Plan completed" in e.content for e in final_events)
