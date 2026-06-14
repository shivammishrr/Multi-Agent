from __future__ import annotations

import copy
import json
from datetime import timezone
from typing import Any

from pydantic import BaseModel, Field

from multi_agent.core.event import Event, EventType


import json

class Thread(BaseModel):
    events: list[Event] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_event(self, event: Event) -> None:
        self.events.append(event)

    def to_llm_messages(self) -> list[dict[str, str]]:
        messages = []
        for event in self.events:
            if event.event_type == EventType.system_message:
                messages.append({"role": "system", "content": event.content})
            elif event.event_type == EventType.user_message:
                messages.append({"role": "user", "content": event.content})
            elif event.event_type == EventType.assistant_message:
                if event.metadata.get("tool_calls"):
                    tc = event.metadata["tool_calls"][0]
                    messages.append({
                        "role": "assistant",
                        "content": event.content or None,
                        "tool_calls": [{
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("input", {})),
                            },
                        }],
                    })
                else:
                    messages.append({"role": "assistant", "content": event.content})
            elif event.event_type == EventType.tool_result:
                messages.append({
                    "role": "tool",
                    "tool_call_id": event.metadata.get("tool_call_id", ""),
                    "content": event.content,
                })
        return messages

    def to_xml_context(self) -> str:
        parts = []
        for event in self.events:
            prefix = event.event_type.value.upper()
            agent_tag = f" agent={event.agent}" if event.agent else ""
            parts.append(f"<{prefix}{agent_tag}>")
            parts.append(event.content)
            parts.append(f"</{prefix}>")
        return "\n".join(parts)

    def fork(self) -> Thread:
        return copy.deepcopy(self)

    def last_event(self) -> Event | None:
        return self.events[-1] if self.events else None

    def total_tokens(self) -> int:
        return sum(len(e.content) for e in self.events)
