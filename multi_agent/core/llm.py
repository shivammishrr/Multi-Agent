from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    stop_reason: str = "stop"
    usage: dict[str, Any] = Field(default_factory=dict)


class LLMClient(ABC):

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...


class LiteLLMClient(LLMClient):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        try:
            from litellm import acompletion
        except ImportError:
            raise ImportError("litellm is required for LiteLLMClient. Install: pip install 'multi-agent[llm]'") from None

        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url
        if tools:
            kwargs["tools"] = tools

        resp = await acompletion(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args_raw = tc.function.arguments
                if isinstance(args_raw, str):
                    try:
                        args_raw = json.loads(args_raw)
                    except json.JSONDecodeError:
                        pass
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args_raw,
                })

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "stop",
            usage=dict(resp.usage or {}),
        )
