from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from multi_agent.core.thread import Thread


StepFn = Callable[..., Coroutine[Any, Any, Any]]


class Execution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: str = ""
    error: str = ""


class DurableExecutor(ABC):

    @abstractmethod
    async def run(self, fn: StepFn, *args: Any, **kwargs: Any) -> Execution:
        ...

    @abstractmethod
    async def get(self, execution_id: str) -> Execution | None:
        ...


class InMemoryExecutor(DurableExecutor):
    def __init__(self, persist_path: str | None = None) -> None:
        self._executions: dict[str, Execution] = {}
        self.persist_path = persist_path

    async def run(self, fn: StepFn, *args: Any, **kwargs: Any) -> Execution:
        execution = Execution(status="running")
        self._executions[execution.id] = execution
        try:
            result = await fn(*args, **kwargs)
            execution.status = "completed"
            if isinstance(result, Thread):
                execution.result = result.events[-1].content if result.events else ""
            else:
                execution.result = str(result)
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
        execution.created_at = datetime.now(timezone.utc)
        self._save()
        return execution

    async def get(self, execution_id: str) -> Execution | None:
        return self._executions.get(execution_id)

    def _save(self) -> None:
        if not self.persist_path:
            return
        data = {eid: e.model_dump() for eid, e in self._executions.items()}
        Path(self.persist_path).write_text(json.dumps(data, default=str))

    def _load(self) -> None:
        if not self.persist_path or not Path(self.persist_path).exists():
            return
        data = json.loads(Path(self.persist_path).read_text())
        self._executions = {eid: Execution(**edata) for eid, edata in data.items()}
