from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    allow = "allow"
    deny = "deny"
    ask = "ask"
    bubble = "bubble"


class ToolResult(BaseModel):
    success: bool
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)


ToolFn = Callable[..., ToolResult | Coroutine[Any, Any, ToolResult]]


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    function: ToolFn | None = None
    permission: PermissionLevel = PermissionLevel.allow

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        if self.function is None:
            return ToolResult(success=False, output=f"Tool {self.name} has no function implementation")
        result = self.function(**kwargs)
        if isinstance(result, ToolResult):
            return result
        return await result
