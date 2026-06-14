from __future__ import annotations

from multi_agent.core.thread import Thread


def format_as_xml(thread: Thread, system_prompt: str = "") -> str:
    parts = [f"<SYSTEM>{system_prompt}</SYSTEM>"] if system_prompt else []
    for event in thread.events:
        tag = event.event_type.value.upper()
        agent_attr = f' agent="{event.agent}"' if event.agent else ""
        parts.append(f"<{tag}{agent_attr}>")
        parts.append(event.content)
        parts.append(f"</{tag}>")
    return "\n".join(parts)


def format_as_markdown(thread: Thread, system_prompt: str = "") -> str:
    parts = [f"# System\n{system_prompt}"] if system_prompt else []
    role_labels = {
        "user_message": "## User",
        "assistant_message": "## Assistant",
        "tool_call": "## Tool Call",
        "tool_result": "## Tool Result",
        "system_message": "## System",
        "error": "## Error",
    }
    for event in thread.events:
        label = role_labels.get(event.event_type.value, "## Unknown")
        agent_info = f" ({event.agent})" if event.agent else ""
        parts.append(f"{label}{agent_info}\n{event.content}")
    return "\n\n".join(parts)
