from __future__ import annotations

import json
from typing import Any

from multi_agent.core.agent import Agent
from multi_agent.core.event import Event, EventType
from multi_agent.core.llm import LLMClient, LLMResponse, LiteLLMClient
from multi_agent.core.thread import Thread
from multi_agent.core.tool import Tool, ToolResult, PermissionLevel
from multi_agent.features.codeact.sandbox import CodeActSandbox


def _make_codeact_tool(sandbox: CodeActSandbox) -> Tool:
    async def run_code(code: str) -> ToolResult:
        return await sandbox.run(code)

    return Tool(
        name="python",
        description="Execute Python code. Use this to perform calculations, process data, or run any Python logic. Print your results.",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute. Use print() to output results.",
                }
            },
            "required": ["code"],
        },
        function=run_code,
        permission=PermissionLevel.allow,
    )


async def react(
    task: str,
    agent: Agent | None = None,
    llm: LLMClient | None = None,
    sandbox: CodeActSandbox | None = None,
    thread: Thread | None = None,
    additional_tools: list[Tool] | None = None,
    verbose: bool = False,
) -> Thread:
    if agent is None:
        agent = Agent(
            name="assistant",
            system_prompt="You are a helpful AI assistant. Use the python tool to write and execute code. "
            "Always print your results so I can see them.",
        )

    if llm is None:
        llm = LiteLLMClient()

    if sandbox is None:
        sandbox = CodeActSandbox()

    codeact_tool = _make_codeact_tool(sandbox)
    all_tools = [codeact_tool] + (additional_tools or [])
    tool_schemas = [t.to_openai_tool() for t in all_tools if t.permission != PermissionLevel.deny]

    if thread is None:
        thread = Thread()
        thread.add_event(Event(
            event_type=EventType.system_message,
            content=agent.system_prompt,
            agent=agent.name,
        ))
        thread.add_event(Event(
            event_type=EventType.user_message,
            content=task,
            agent="user",
        ))

    turn = 0
    while turn < agent.max_turns:
        turn += 1
        messages = thread.to_llm_messages()

        if verbose:
            print(f"\n--- Turn {turn} ---")

        response = await llm.chat(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            model=agent.model,
        )

        if response.tool_calls:
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_input = tc["input"]
                tool_id = tc.get("id", f"call_{turn}")

                thread.add_event(Event(
                    event_type=EventType.assistant_message,
                    content=f"Calling tool: {tool_name}",
                    agent=agent.name,
                    metadata={
                        "tool_calls": [{
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }],
                    },
                ))

                matched_tool = next((t for t in all_tools if t.name == tool_name), None)
                if matched_tool is None:
                    result = ToolResult(success=False, output=f"Unknown tool: {tool_name}")
                elif matched_tool.permission == PermissionLevel.deny:
                    result = ToolResult(success=False, output=f"Tool {tool_name} is denied")
                else:
                    if isinstance(tool_input, str):
                        try:
                            tool_input = json.loads(tool_input)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if isinstance(tool_input, dict):
                        result = await matched_tool.execute(**tool_input)
                    else:
                        result = ToolResult(success=False, output=f"Invalid tool input: {tool_input}")

                if verbose:
                    print(f"  {tool_name}: {result.output[:200]}")

                thread.add_event(Event(
                    event_type=EventType.tool_result,
                    content=result.output,
                    agent=agent.name,
                    metadata={"tool_call_id": tool_id, "tool": tool_name, "success": result.success},
                ))

        if response.content:
            thread.add_event(Event(
                event_type=EventType.assistant_message,
                content=response.content,
                agent=agent.name,
            ))

            if not response.tool_calls:
                if verbose:
                    print(f"  Response: {response.content[:200]}")
                break

    else:
        thread.add_event(Event(
            event_type=EventType.system_message,
            content=f"Reached max turns ({agent.max_turns}). Stopping.",
            agent=agent.name,
        ))

    return thread
