from __future__ import annotations

from typing import Any

from multi_agent.core.tool import PermissionLevel, Tool, ToolResult
from multi_agent.features.permissions.config import PermissionConfig


class PermissionCLI:
    def __init__(self, config: PermissionConfig | None = None) -> None:
        self.config = config or PermissionConfig()

    async def check(self, tool: Tool, **kwargs: Any) -> PermissionLevel:
        level = self.config.get_permission(tool.name, tool.description)

        if level == PermissionLevel.allow:
            return PermissionLevel.allow

        if level == PermissionLevel.deny:
            return PermissionLevel.deny

        if level == PermissionLevel.bubble:
            return PermissionLevel.bubble

        return await self._ask_user(tool, **kwargs)

    async def _ask_user(self, tool: Tool, **kwargs: Any) -> PermissionLevel:
        args_str = "\n  ".join(f"{k}={v}" for k, v in kwargs.items())
        print(f"\n Tool: {tool.name}")
        print(f" Description: {tool.description}")
        if args_str:
            print(f" Args: {args_str}")

        while True:
            choice = input(" Allow (a) | Deny (d) | Allow always (aa) | Deny always (dd) | Bubble (b) >> ").strip().lower()
            if choice in ("a", ""):
                return PermissionLevel.allow
            if choice == "aa":
                self.config.set_permission(tool.name, PermissionLevel.allow)
                self.config.save()
                print(f" -> {tool.name} set to ALWAYS ALLOW")
                return PermissionLevel.allow
            if choice == "d":
                return PermissionLevel.deny
            if choice == "dd":
                self.config.set_permission(tool.name, PermissionLevel.deny)
                self.config.save()
                print(f" -> {tool.name} set to ALWAYS DENY")
                return PermissionLevel.deny
            if choice == "b":
                return PermissionLevel.bubble

    async def wrap_tool(self, tool: Tool) -> Tool:
        original_fn = tool.function

        async def guarded_fn(**kwargs: Any) -> ToolResult:
            level = await self.check(tool, **kwargs)
            if level == PermissionLevel.deny:
                return ToolResult(success=False, output=f"Permission denied for {tool.name}")
            if level == PermissionLevel.bubble:
                return ToolResult(success=False, output=f"Permission bubbled for {tool.name}")
            if original_fn is None:
                return ToolResult(success=False, output=f"Tool {tool.name} has no function")
            result = original_fn(**kwargs)
            if isinstance(result, ToolResult):
                return result
            return await result

        tool.function = guarded_fn
        return tool
