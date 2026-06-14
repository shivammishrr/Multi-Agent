from __future__ import annotations

import json
from typing import Any

from multi_agent.core.tool import Tool, ToolResult, PermissionLevel


class MCPClient:
    def __init__(self, command: str | list[str] | None = None, url: str | None = None) -> None:
        self._command = command
        self._url = url
        self._proc: Any = None
        self._session: Any = None
        self._tools: list[Tool] = []

    async def connect(self) -> None:
        if self._url:
            await self._connect_http()
        elif self._command:
            await self._connect_stdio()
        else:
            raise ValueError("Either command or url must be provided")

    async def _connect_stdio(self) -> None:
        import asyncio.subprocess
        import sys

        if isinstance(self._command, list):
            cmd = self._command
        else:
            cmd = self._command.split()

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "multi-agent", "version": "0.1.0"},
            },
            "id": 1,
        })
        self._send(init_msg)
        resp = await self._recv()
        if resp and resp.get("result"):
            tools_msg = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2,
            })
            self._send(tools_msg)
            tools_resp = await self._recv()
            self._parse_tools(tools_resp)

    def _send(self, msg: str) -> None:
        if self._proc and self._proc.stdin:
            self._proc.stdin.write((msg + "\n").encode("utf-8"))

    async def _recv(self) -> dict[str, Any] | None:
        if self._proc and self._proc.stdout:
            line = await self._proc.stdout.readline()
            if line:
                try:
                    return json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    pass
        return None

    async def _connect_http(self) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for HTTP MCP transport") from None

        async with httpx.AsyncClient() as client:
            init_resp = await client.post(
                self._url,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "multi-agent", "version": "0.1.0"},
                    },
                    "id": 1,
                },
            )
            init_data = init_resp.json()
            if init_data.get("result"):
                tools_resp = await client.post(
                    self._url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": 2,
                    },
                )
                self._parse_tools(tools_resp.json())

    def _parse_tools(self, resp: dict[str, Any] | None) -> None:
        if resp is None:
            return
        tools = resp.get("result", {}).get("tools", [])
        for t in tools:
            tool = Tool(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("inputSchema", {}),
                permission=PermissionLevel.ask,
            )
            self._tools.append(tool)

    @property
    def tools(self) -> list[Tool]:
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        call_msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 3,
        })

        if self._proc:
            self._send(call_msg)
            resp = await self._recv()
        elif self._url:
            try:
                import httpx
            except ImportError:
                raise ImportError("httpx required for HTTP MCP transport") from None
            async with httpx.AsyncClient() as client:
                resp = (await client.post(self._url, json=json.loads(call_msg))).json()
        else:
            return ToolResult(success=False, output="MCP client not connected")

        if resp is None:
            return ToolResult(success=False, output="No response from MCP server")

        result = resp.get("result", {})
        content = result.get("content", [])
        output = "\n".join(
            c.get("text", "") for c in content if c.get("type") == "text"
        )
        is_error = result.get("isError", False)
        return ToolResult(success=not is_error, output=output)

    async def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
