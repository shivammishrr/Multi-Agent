from __future__ import annotations

from pydantic import BaseModel, Field

from multi_agent.core.tool import Tool


class Agent(BaseModel):
    name: str
    system_prompt: str = ""
    tools: list[Tool] = Field(default_factory=list)
    model: str = "gpt-4o"
    max_turns: int = 25
