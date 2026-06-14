import pytest
from multi_agent.features.durable.executor import InMemoryExecutor, Execution


class TestInMemoryExecutor:
    @pytest.mark.asyncio
    async def test_run_success(self):
        executor = InMemoryExecutor()

        async def my_step():
            return "hello from step"

        execution = await executor.run(my_step)
        assert execution.status == "completed"
        assert execution.result == "hello from step"

    @pytest.mark.asyncio
    async def test_run_failure(self):
        executor = InMemoryExecutor()

        async def failing_step():
            raise ValueError("step failed")

        execution = await executor.run(failing_step)
        assert execution.status == "failed"
        assert "step failed" in execution.error

    @pytest.mark.asyncio
    async def test_get_execution(self):
        executor = InMemoryExecutor()

        async def step():
            return "result"

        execution = await executor.run(step)
        fetched = await executor.get(execution.id)
        assert fetched is not None
        assert fetched.id == execution.id
        assert fetched.status == "completed"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        executor = InMemoryExecutor()
        result = await executor.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_execution_has_id(self):
        execution = Execution()
        assert len(execution.id) > 0

    @pytest.mark.asyncio
    async def test_multiple_executions(self):
        executor = InMemoryExecutor()

        async def step_a():
            return "A"

        async def step_b():
            return "B"

        e1 = await executor.run(step_a)
        e2 = await executor.run(step_b)
        assert e1.id != e2.id
        assert (await executor.get(e1.id)).result == "A"
        assert (await executor.get(e2.id)).result == "B"
