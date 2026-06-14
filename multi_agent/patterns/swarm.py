from __future__ import annotations

import json as json_mod
from typing import Any

from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.llm import LLMClient, LiteLLMClient
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool
from multi_agent.features.codeact.sandbox import CodeActSandbox
from multi_agent.patterns.react import react


async def _route(
    task: str,
    agents: list[Agent],
    llm: LLMClient,
    verbose: bool = False,
) -> str:
    agent_descriptions = "\n".join(
        f"- {a.name}: {a.system_prompt[:100]}"
        for a in agents
    )
    route_prompt = (
        f"Given this task: {task}\n\n"
        f"Available agents:\n{agent_descriptions}\n\n"
        "Which agent should handle this? Reply with ONLY the agent name."
    )

    resp = await llm.chat(
        messages=[{"role": "user", "content": route_prompt}],
        temperature=0.1,
    )

    chosen = resp.content.strip()
    valid_names = {a.name.lower() for a in agents}
    for agent in agents:
        if agent.name.lower() in chosen.lower():
            if verbose:
                print(f"\n=== ROUTED TO: {agent.name} ===")
            return agent.name
    return agents[0].name if agents else "assistant"


async def swarm(
    task: str,
    agents: list[Agent] | None = None,
    llm: LLMClient | None = None,
    sandbox: CodeActSandbox | None = None,
    additional_tools: list[Tool] | None = None,
    max_handoffs: int = 5,
    verbose: bool = False,
) -> Thread:
    if llm is None:
        llm = LiteLLMClient()
    if sandbox is None:
        sandbox = CodeActSandbox()
    if agents is None or len(agents) == 0:
        agents = [
            Agent(name="triage", system_prompt="Route tasks to the right specialist.", max_turns=2),
            Agent(name="researcher", system_prompt="Research topics and gather information.", max_turns=10),
            Agent(name="coder", system_prompt="Write and execute Python code.", max_turns=15),
        ]

    thread = Thread()
    agent_names = ", ".join(a.name for a in agents)
    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Task: {task}\nAvailable agents: {agent_names}\nMax handoffs: {max_handoffs}",
        agent="system",
    ))

    current_task = task
    current_agent_name = await _route(current_task, agents, llm, verbose=verbose)
    handoff_count = 0

    while handoff_count < max_handoffs:
        handoff_count += 1
        current_agent = next((a for a in agents if a.name == current_agent_name), agents[0])

        if verbose:
            print(f"\n{'='*50}")
            print(f"Handoff {handoff_count}: {current_agent.name} handling: {current_task[:100]}")

        result_thread = await react(
            task=current_task,
            agent=current_agent,
            llm=llm,
            sandbox=sandbox,
            additional_tools=additional_tools,
            verbose=verbose,
        )

        for event in result_thread.events:
            thread.add_event(event)

        if current_agent_name in ("triage", "supervisor") or handoff_count >= max_handoffs:
            break

        result_content = ""
        for event in reversed(result_thread.events):
            if event.event_type == EventType.assistant_message and not event.metadata.get("tool_calls"):
                result_content = event.content
                break

        handoff_prompt = (
            f"Current task: {task}\n"
            f"Completed by: {current_agent.name}\n"
            f"Result: {result_content[:500]}\n"
            f"Is this task complete or does it need another agent? "
            f"Available agents: {agent_names}\n"
            f"Reply with the next agent's name if handoff needed, or 'DONE' if complete."
        )

        resp = await llm.chat(
            messages=[{"role": "user", "content": handoff_prompt}],
            temperature=0.1,
        )

        decision = resp.content.strip()
        if "DONE" in decision.upper():
            if verbose:
                print(f"\n=== SWARM DONE after {handoff_count} handoffs ===")
            break

        next_agent = None
        for agent in agents:
            if agent.name.lower() in decision.lower():
                next_agent = agent
                break
        if next_agent is None or next_agent.name == current_agent_name:
            break

        current_task = f"Continuing from {current_agent.name}: {result_content[:300]}"
        current_agent_name = next_agent.name

        thread.add_event(Event(
            event_type=EventType.system_message,
            content=f"Handoff: {current_agent.name} -> {next_agent.name}",
            agent="system",
        ))

    return thread
