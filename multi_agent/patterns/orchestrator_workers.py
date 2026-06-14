from __future__ import annotations

import asyncio
import json
from typing import Any

from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.llm import LLMClient, LiteLLMClient
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool
from multi_agent.features.codeact.sandbox import CodeActSandbox
from multi_agent.patterns.react import react


async def _decompose(
    task: str,
    num_workers: int,
    orchestrator_agent: Agent,
    llm: LLMClient,
    verbose: bool = False,
) -> list[str]:
    decompose_prompt = (
        f"Given this task: {task}\n\n"
        f"Split it into {num_workers} parallel sub-tasks that can be worked on independently. "
        "Each sub-task should be self-contained and have a clear deliverable. "
        'Output ONLY a JSON array of strings, each being a sub-task description. '
        f'Example with {num_workers} sub-tasks:\n'
    )
    example = [f"Sub-task {i+1}" for i in range(num_workers)]
    decompose_prompt += json.dumps(example)

    resp = await llm.chat(
        messages=[
            {"role": "system", "content": "You are good at decomposing tasks into parallel work items."},
            {"role": "user", "content": decompose_prompt},
        ],
        model=orchestrator_agent.model,
        temperature=0.3,
    )

    try:
        sub_tasks = json.loads(resp.content)
        if isinstance(sub_tasks, list) and all(isinstance(s, str) for s in sub_tasks):
            return sub_tasks
    except (json.JSONDecodeError, TypeError):
        pass

    lines = [l.strip() for l in resp.content.strip().split("\n") if l.strip()]
    lines = [l for l in lines if l[0:1].isdigit() or l.startswith("- ")]
    if lines:
        import re
        lines = [re.sub(r"^\d+[.)]\s*", "", l) for l in lines]
        lines = [l[2:] if l.startswith("- ") else l for l in lines]
    return lines[:num_workers] if lines else [task]


async def _synthesize(
    task: str,
    sub_task_results: list[tuple[str, str]],
    orchestrator_agent: Agent,
    llm: LLMClient,
    verbose: bool = False,
) -> str:
    results_text = "\n\n".join(
        f"Sub-task: {st}\nResult: {r[:1000]}"
        for st, r in sub_task_results
    )
    synthesis_prompt = (
        f"Original task: {task}\n\n"
        f"Here are the results from parallel workers:\n\n{results_text}\n\n"
        "Synthesize a comprehensive final answer. Combine findings, resolve conflicts, "
        "and present a clear, well-structured response."
    )

    resp = await llm.chat(
        messages=[
            {"role": "system", "content": "You are a skilled synthesizer. Combine parallel research results into a coherent answer."},
            {"role": "user", "content": synthesis_prompt},
        ],
        model=orchestrator_agent.model,
        temperature=0.3,
    )

    return resp.content


async def orchestrator_workers(
    task: str,
    num_workers: int = 3,
    agent: Agent | None = None,
    llm: LLMClient | None = None,
    sandbox: CodeActSandbox | None = None,
    additional_tools: list[Tool] | None = None,
    verbose: bool = False,
) -> Thread:
    if llm is None:
        llm = LiteLLMClient()
    if sandbox is None:
        sandbox = CodeActSandbox()
    if agent is None:
        agent = Agent(name="orchestrator", model="gpt-4o", system_prompt="You orchestrate parallel work.")

    thread = Thread()
    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Task: {task}\nOrchestrator: {agent.name} ({agent.model})",
        agent="system",
    ))

    sub_tasks = await _decompose(task, num_workers, agent, llm, verbose=verbose)
    num_workers_actual = len(sub_tasks)

    if verbose:
        print(f"\n=== DECOMPOSED INTO {num_workers_actual} SUB-TASKS ===")
        for i, st in enumerate(sub_tasks):
            print(f"  Worker {i+1}: {st}")

    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Decomposed into {num_workers_actual} parallel sub-tasks:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sub_tasks)),
        agent=agent.name,
    ))

    worker_agent = Agent(
        name="worker",
        system_prompt="You are a worker agent. Complete your assigned sub-task efficiently. Use Python code when needed.",
        model=agent.model,
        max_turns=15,
    )

    async def run_worker(worker_id: int, sub_task: str) -> tuple[int, str, str]:
        try:
            worker_thread = await react(
                task=sub_task,
                agent=worker_agent,
                llm=llm,
                sandbox=sandbox,
                additional_tools=additional_tools,
                verbose=verbose,
            )
            result = ""
            for event in reversed(worker_thread.events):
                if event.event_type == EventType.assistant_message and not event.metadata.get("tool_calls"):
                    result = event.content
                    break
            if not result:
                for event in reversed(worker_thread.events):
                    if event.event_type == EventType.tool_result:
                        result = event.content[:500]
                        break
            return worker_id, sub_task, result or "(no output)"
        except Exception as e:
            return worker_id, sub_task, f"Error: {e}"

    tasks_list = [run_worker(i, st) for i, st in enumerate(sub_tasks)]
    results = await asyncio.gather(*tasks_list)

    sub_task_results = []
    for wid, st, result in sorted(results, key=lambda x: x[0]):
        sub_task_results.append((st, result))
        thread.add_event(Event(
            event_type=EventType.system_message,
            content=f"Worker {wid + 1} result for: {st}\n{result[:500]}",
            agent=worker_agent.name,
        ))
        if verbose:
            print(f"\nWorker {wid + 1} completed: {result[:200]}")

    synthesis = await _synthesize(task, sub_task_results, agent, llm, verbose=verbose)
    thread.add_event(Event(
        event_type=EventType.assistant_message,
        content=synthesis,
        agent=agent.name,
    ))

    if verbose:
        print(f"\n=== SYNTHESIS ===")
        print(synthesis[:500])

    return thread
