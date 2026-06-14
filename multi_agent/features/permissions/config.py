from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from multi_agent.core.tool import PermissionLevel


class Rule(BaseModel):
    pattern: str = ""
    permission: PermissionLevel = PermissionLevel.ask


class PermissionConfig(BaseModel):
    rules: list[Rule] = Field(default_factory=lambda: [
        Rule(pattern="*", permission=PermissionLevel.allow),
    ])
    store_path: str = ""

    @classmethod
    def from_file(cls, path: str = ".permissions.json") -> "PermissionConfig":
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            return cls.model_validate(data)
        return cls(store_path=path)

    def save(self) -> None:
        if not self.store_path:
            return
        Path(self.store_path).write_text(self.model_dump_json(indent=2))

    def get_permission(self, tool_name: str, tool_description: str = "") -> PermissionLevel:
        wildcard: Rule | None = None
        for rule in self.rules:
            if rule.pattern == "*":
                wildcard = rule
            elif rule.pattern == tool_name:
                return rule.permission
        if wildcard is not None:
            return wildcard.permission
        return PermissionLevel.ask

    def set_permission(self, tool_name: str, permission: PermissionLevel) -> None:
        for rule in self.rules:
            if rule.pattern == tool_name:
                rule.permission = permission
                return
        self.rules.append(Rule(pattern=tool_name, permission=permission))
