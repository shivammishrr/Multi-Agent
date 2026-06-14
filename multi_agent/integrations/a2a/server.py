from __future__ import annotations

import json
import uuid
from typing import Any

from multi_agent.integrations.a2a.card import AgentCard


class A2AServer:
    def __init__(self, card: AgentCard, handler: Any = None) -> None:
        self.card = card
        self.handler = handler
        self._tasks: dict[str, dict[str, Any]] = {}

    def get_card_dict(self) -> dict[str, Any]:
        return self.card.model_dump()

    async def handle_task(self, body: dict[str, Any]) -> dict[str, Any]:
        task_text = body.get("task", "")
        metadata = body.get("metadata", {})
        task_id = str(uuid.uuid4())

        self._tasks[task_id] = {
            "id": task_id,
            "status": "working",
            "task": task_text,
            "metadata": metadata,
        }

        try:
            if self.handler:
                result = await self.handler(task_text, metadata)
            else:
                result = f"Received task: {task_text[:100]}"
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["result"] = str(result)
        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["result"] = str(e)

        return {
            "id": task_id,
            "status": self._tasks[task_id]["status"],
            "result": self._tasks[task_id].get("result", ""),
        }
