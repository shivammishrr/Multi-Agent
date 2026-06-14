import json
import pytest
from pathlib import Path
from multi_agent.core.tool import PermissionLevel, Tool, ToolResult
from multi_agent.features.permissions.config import PermissionConfig, Rule
from multi_agent.features.permissions.cli import PermissionCLI


class TestPermissionConfig:
    def test_default_permission(self):
        config = PermissionConfig()
        assert config.get_permission("anything") == PermissionLevel.allow

    def test_custom_rules(self):
        config = PermissionConfig(rules=[
            Rule(pattern="*", permission=PermissionLevel.allow),
            Rule(pattern="bash", permission=PermissionLevel.ask),
            Rule(pattern="write_file", permission=PermissionLevel.deny),
        ])
        assert config.get_permission("bash") == PermissionLevel.ask
        assert config.get_permission("write_file") == PermissionLevel.deny
        assert config.get_permission("read_file") == PermissionLevel.allow

    def test_set_permission(self):
        config = PermissionConfig()
        config.set_permission("dangerous_tool", PermissionLevel.deny)
        assert config.get_permission("dangerous_tool") == PermissionLevel.deny
        config.set_permission("dangerous_tool", PermissionLevel.ask)
        assert config.get_permission("dangerous_tool") == PermissionLevel.ask

    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "perms.json")
        config = PermissionConfig(store_path=path)
        config.set_permission("bash", PermissionLevel.deny)
        config.save()

        loaded = PermissionConfig.from_file(path)
        assert loaded.get_permission("bash") == PermissionLevel.deny
        assert loaded.get_permission("other") == PermissionLevel.allow

    def test_file_not_found_returns_default(self):
        config = PermissionConfig.from_file("/nonexistent/perms.json")
        assert config.get_permission("anything") == PermissionLevel.allow


class TestPermissionCLI:
    @pytest.mark.asyncio
    async def test_allow_immediately(self):
        config = PermissionConfig(rules=[
            Rule(pattern="safe_tool", permission=PermissionLevel.allow),
        ])
        cli = PermissionCLI(config)
        tool = Tool(name="safe_tool", description="a safe tool")
        level = await cli.check(tool)
        assert level == PermissionLevel.allow

    @pytest.mark.asyncio
    async def test_deny_immediately(self):
        config = PermissionConfig(rules=[
            Rule(pattern="danger", permission=PermissionLevel.deny),
        ])
        cli = PermissionCLI(config)
        tool = Tool(name="danger", description="dangerous tool")
        level = await cli.check(tool)
        assert level == PermissionLevel.deny

    @pytest.mark.asyncio
    async def test_bubble_immediately(self):
        config = PermissionConfig(rules=[
            Rule(pattern="parent_tool", permission=PermissionLevel.bubble),
        ])
        cli = PermissionCLI(config)
        tool = Tool(name="parent_tool", description="for parent agent")
        level = await cli.check(tool)
        assert level == PermissionLevel.bubble

    @pytest.mark.asyncio
    async def test_wrap_tool_allowed(self):
        async def my_fn() -> ToolResult:
            return ToolResult(success=True, output="done")
        tool = Tool(name="my_tool", description="test", function=my_fn)
        config = PermissionConfig(rules=[Rule(pattern="my_tool", permission=PermissionLevel.allow)])
        cli = PermissionCLI(config)
        wrapped = await cli.wrap_tool(tool)
        result = await wrapped.execute()
        assert result.success is True
        assert result.output == "done"

    @pytest.mark.asyncio
    async def test_wrap_tool_denied(self):
        async def my_fn() -> ToolResult:
            return ToolResult(success=True, output="done")
        tool = Tool(name="my_tool", description="test", function=my_fn)
        config = PermissionConfig(rules=[Rule(pattern="my_tool", permission=PermissionLevel.deny)])
        cli = PermissionCLI(config)
        wrapped = await cli.wrap_tool(tool)
        result = await wrapped.execute()
        assert result.success is False
        assert "denied" in result.output
