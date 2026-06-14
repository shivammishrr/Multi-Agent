from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from multi_agent.core.tool import ToolResult
from multi_agent.integrations.a2a.card import AgentCard


class A2ATask(BaseModel):
    id: str
    status: str = "submitted"  # submitted, working, input-required, completed, failed, canceled
    result: str = ""


class A2AClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def get_card(self) -> AgentCard | None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for A2A client") from None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/.well-known/agent-card.json", timeout=10)
                resp.raise_for_status()
                return AgentCard.model_validate(resp.json())
        except Exception:
            return None

    async def send_task(self, task: str, metadata: dict[str, Any] | None = None) -> ToolResult:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for A2A client") from None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/a2a/tasks",
                    json={"task": task, "metadata": metadata or {}},
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                return ToolResult(
                    success=True,
                    output=data.get("result", ""),
                    metadata={"task_id": data.get("id", ""), "status": data.get("status", "")},
                )
        except Exception as e:
            return ToolResult(success=False, output=f"A2A error: {e}")
