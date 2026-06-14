from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentCapabilities(BaseModel):
    streaming: bool = False
    push_notifications: bool = False
    state_transition_notifications: bool = False


class AgentCard(BaseModel):
    name: str
    description: str = ""
    url: str = ""
    version: str = "1.0.0"
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: list[str] = Field(default_factory=list)
    default_input_modality: str = "text"
    default_output_modality: str = "text"
