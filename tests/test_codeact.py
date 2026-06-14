import pytest
from multi_agent.features.codeact.sandbox import CodeActSandbox


class TestCodeActSandbox:
    @pytest.mark.asyncio
    async def test_simple_print(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("print('hello world')")
        assert result.success is True
        assert "hello world" in result.output

    @pytest.mark.asyncio
    async def test_math(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("print(2 + 2)")
        assert result.output.strip() == "4"

    @pytest.mark.asyncio
    async def test_variable_persistence(self):
        sandbox = CodeActSandbox()
        r1 = await sandbox.run("x = 42")
        assert r1.success is True
        r2 = await sandbox.run("print(x)")
        assert "42" in r2.output

    @pytest.mark.asyncio
    async def test_error_handling(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("print(1/0)")
        assert result.success is False
        assert "ZeroDivisionError" in result.output

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("print(")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_imports_blocked_by_default(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("import os; print(os.name)")
        assert result.success is False
        assert "disabled" in result.output

    @pytest.mark.asyncio
    async def test_allowed_imports(self):
        sandbox = CodeActSandbox(allow_imports=True, allowed_modules=["math"])
        result = await sandbox.run("import math; print(math.sqrt(16))")
        assert result.success is True
        assert "4.0" in result.output

    @pytest.mark.asyncio
    async def test_no_output(self):
        sandbox = CodeActSandbox()
        result = await sandbox.run("x = 1 + 2")
        assert result.success is True
        assert "(no output)" in result.output

    @pytest.mark.asyncio
    async def test_reset(self):
        sandbox = CodeActSandbox()
        await sandbox.run("x = 99")
        sandbox.reset()
        result = await sandbox.run("print(x)")
        assert "NameError" in result.output or result.success is False
