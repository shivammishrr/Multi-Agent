from __future__ import annotations

from typing import Any

from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.llm import LLMClient, LiteLLMClient
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool
from multi_agent.features.codeact.sandbox import CodeActSandbox
from multi_agent.patterns.react import react


async def hierarchical(
    task: str,
    supervisor_agent: Agent | None = None,
    workers: list[Agent] | None = None,
    llm: LLMClient | None = None,
    sandbox: CodeActSandbox | None = None,
    additional_tools: list[Tool] | None = None,
    verbose: bool = False,
) -> Thread:
    if llm is None:
        llm = LiteLLMClient()
    if sandbox is None:
        sandbox = CodeActSandbox()
    if supervisor_agent is None:
        supervisor_agent = Agent(
            name="supervisor",
            model="gpt-4o",
            system_prompt="You are a supervisor. Delegate tasks to workers and synthesize their results.",
        )
    if workers is None or len(workers) == 0:
        workers = [
            Agent(name="researcher", model="gpt-4o-mini", max_turns=10),
            Agent(name="coder", model="gpt-4o-mini", max_turns=15),
        ]

    thread = Thread()
    worker_names = ", ".join(w.name for w in workers)
    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Task: {task}\nSupervisor: {supervisor_agent.name}\nWorkers: {worker_names}",
        agent="system",
    ))

    delegation_prompt = (
        f"Task: {task}\n\n"
        f"Available workers: {worker_names}\n\n"
        "Decide which worker(s) should handle this task and what each should do. "
        "Output your decision as a JSON object with worker names as keys and task descriptions as values. "
        "Example: {\"researcher\": \"research the topic\", \"coder\": \"implement the solution\"}"
    )

    resp = await llm.chat(
        messages=[
            {"role": "system", "content": supervisor_agent.system_prompt},
            {"role": "user", "content": delegation_prompt},
        ],
        model=supervisor_agent.model,
        temperature=0.2,
    )

    import json as json_mod
    try:
        assignments: dict[str, str] = json_mod.loads(resp.content)
    except (json_mod.JSONDecodeError, TypeError):
        assignments = {workers[0].name: task}

    if verbose:
        print(f"\n=== SUPERVISOR ASSIGNMENTS ===")
        for w, t in assignments.items():
            print(f"  {w} -> {t}")

    thread.add_event(Event(
        event_type=EventType.system_message,
        content=f"Supervisor delegated:\n" + "\n".join(f"  {w}: {t}" for w, t in assignments.items()),
        agent=supervisor_agent.name,
    ))

    results: dict[str, str] = {}
    for worker_name, worker_task in assignments.items():
        worker = next((w for w in workers if w.name == worker_name), None)
        if worker is None:
            results[worker_name] = f"Worker '{worker_name}' not found"
            continue

        if verbose:
            print(f"\n--- Worker: {worker_name} ---")
            print(f"  Task: {worker_task}")

        worker_thread = await react(
            task=worker_task,
            agent=worker,
            llm=llm,
            sandbox=sandbox,
            additional_tools=additional_tools,
            verbose=verbose,
        )

        result_content = ""
        for event in reversed(worker_thread.events):
            if event.event_type == EventType.assistant_message and not event.metadata.get("tool_calls"):
                result_content = event.content
                break
        if not result_content:
            for event in reversed(worker_thread.events):
                if event.event_type == EventType.tool_result:
                    result_content = event.content[:500]
                    break

        results[worker_name] = result_content or "(no output)"
        for event in worker_thread.events:
            thread.add_event(event)

        thread.add_event(Event(
            event_type=EventType.system_message,
            content=f"{worker_name} completed: {results[worker_name][:300]}",
            agent=worker.name,
        ))

    results_text = "\n\n".join(f"{w}: {r[:1000]}" for w, r in results.items())
    synthesis_prompt = (
        f"Original task: {task}\n\n"
        f"Worker results:\n{results_text}\n\n"
        "Synthesize the results into a final coherent response."
    )

    synthesis = await llm.chat(
        messages=[
            {"role": "system", "content": supervisor_agent.system_prompt},
            {"role": "user", "content": synthesis_prompt},
        ],
        model=supervisor_agent.model,
    )

    thread.add_event(Event(
        event_type=EventType.assistant_message,
        content=synthesis.content,
        agent=supervisor_agent.name,
    ))

    if verbose:
        print(f"\n=== SUPERVISOR SYNTHESIS ===")
        print(synthesis.content[:500])

    return thread
