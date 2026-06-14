from __future__ import annotations

import json
from typing import Any

from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.llm import LLMClient, LiteLLMClient
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool
from multi_agent.features.codeact.sandbox import CodeActSandbox
from multi_agent.patterns.react import react


async def _plan(
    task: str,
    planner_agent: Agent,
    llm: LLMClient,
    thread: Thread,
    verbose: bool = False,
) -> list[str]:
    plan_prompt = (
        "You are a careful planner. Given a task, break it into 3-8 clear, sequential steps. "
        "Each step should be actionable by an AI agent with Python code execution. "
        "Output ONLY a JSON array of strings, each string being one step. Example:\n"
        '["Research the topic by web search", "Write Python code to analyze the data", "Summarize findings"]'
    )

    plan_thread = thread.fork()
    plan_thread.add_event(Event(
        event_type=EventType.system_message,
        content=plan_prompt,
        agent=planner_agent.name,
    ))
    plan_thread.add_event(Event(
        event_type=EventType.user_message,
        content=f"Task: {task}\n\nCreate a detailed step-by-step plan.",
        agent="user",
    ))

    response = await llm.chat(
        messages=plan_thread.to_llm_messages(),
        model=planner_agent.model,
        temperature=0.2,
    )

    content = response.content
    if verbose:
        print(f"\n=== PLAN ===")
        print(content)
        print(f"=== END PLAN ===\n")

    steps = _parse_steps(content)
    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Plan created with {len(steps)} steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)),
        agent=planner_agent.name,
    ))
    return steps


def _parse_steps(content: str) -> list[str]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    import re
    lines = content.strip().split("\n")
    steps = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+[.)]\s*", line):
            step = re.sub(r"^\d+[.)]\s*", "", line)
            steps.append(step)
        elif line.startswith("- ") or line.startswith("* "):
            steps.append(line[2:])
    if not steps:
        steps = [content]
    return steps


async def _replan(
    task: str,
    steps: list[str],
    completed_step: int,
    results: list[str],
    thread: Thread,
    llm: LLMClient,
    agent: Agent,
    verbose: bool = False,
) -> list[str]:
    results_summary = "\n".join(
        f"Step {i+1}: {steps[i]}\nResult: {results[i][:500]}"
        for i in range(completed_step + 1)
        if i < len(results)
    )
    remaining = steps[completed_step + 1:] if completed_step + 1 < len(steps) else []

    replan_prompt = (
        f"Task: {task}\n\n"
        f"Original plan: {json.dumps(steps)}\n\n"
        f"Completed steps so far:\n{results_summary}\n\n"
        f"Remaining original steps: {json.dumps(remaining)}\n\n"
        "Based on the results so far, do the remaining steps still make sense? "
        "If yes, output the remaining steps as-is. "
        "If the plan needs adjusting (because results changed the approach, or steps are now unnecessary), "
        "output a new list of remaining steps."
        'Output ONLY a JSON array of strings.'
    )

    resp = await llm.chat(
        messages=[{"role": "user", "content": replan_prompt}],
        model=agent.model,
        temperature=0.2,
    )

    new_steps = _parse_steps(resp.content)
    if verbose:
        print(f"\n=== REPLAN (after step {completed_step + 1}) ===")
        print(f"Remaining steps: {json.dumps(new_steps)}")
        print(f"=== END REPLAN ===\n")
    return new_steps


async def plan_and_execute(
    task: str,
    planner_agent: Agent | None = None,
    executor_agent: Agent | None = None,
    llm: LLMClient | None = None,
    sandbox: CodeActSandbox | None = None,
    additional_tools: list[Tool] | None = None,
    max_plan_iterations: int = 3,
    verbose: bool = False,
) -> Thread:
    if llm is None:
        llm = LiteLLMClient()
    if sandbox is None:
        sandbox = CodeActSandbox()
    if planner_agent is None:
        planner_agent = Agent(name="planner", model="gpt-4o", system_prompt="You are a careful planner.")
    if executor_agent is None:
        executor_agent = Agent(name="executor", model="gpt-4o-mini", max_turns=15)

    thread = Thread()
    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Task: {task}\n\nPlanner: {planner_agent.name} ({planner_agent.model})\nExecutor: {executor_agent.name} ({executor_agent.model})",
        agent="system",
    ))

    steps = await _plan(task, planner_agent, llm, thread, verbose=verbose)
    all_results: list[str] = []
    plan_iterations = 0

    step_idx = 0
    while step_idx < len(steps) and plan_iterations < max_plan_iterations:
        plan_iterations += 1
        step = steps[step_idx]

        if verbose:
            print(f"\n{'='*60}")
            print(f"Executing step {step_idx + 1}/{len(steps)}: {step}")
            print(f"{'='*60}")

        step_result = await react(
            task=f"Current step: {step}\n\nContext from previous steps: {''.join(f'Step {i+1}: {r[:300]}\n' for i, r in enumerate(all_results))}",
            agent=executor_agent,
            llm=llm,
            sandbox=sandbox,
            additional_tools=additional_tools,
            verbose=verbose,
        )

        result_content = ""
        for event in reversed(step_result.events):
            if event.event_type == EventType.assistant_message and event.agent == executor_agent.name:
                if not event.metadata.get("tool_calls"):
                    result_content = event.content
                    break

        if not result_content:
            for event in reversed(step_result.events):
                if event.event_type == EventType.tool_result:
                    result_content = event.content[:500]
                    break

        all_results.append(result_content or "(no output)")

        for event in step_result.events:
            thread.add_event(event)

        thread.add_event(Event(
            event_type=EventType.system_message,
            content=f"Step {step_idx + 1} completed. Result: {result_content[:300]}",
            agent=executor_agent.name,
        ))

        if step_idx < len(steps) - 1:
            steps = await _replan(
                task=task,
                steps=steps,
                completed_step=step_idx,
                results=all_results,
                thread=thread,
                llm=llm,
                agent=planner_agent,
                verbose=verbose,
            )
            step_idx += 1
        else:
            step_idx += 1

    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Plan completed. Executed {len(all_results)} steps across {plan_iterations} iterations.",
        agent="system",
    ))

    return thread
