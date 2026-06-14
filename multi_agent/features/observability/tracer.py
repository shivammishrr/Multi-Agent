from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class Span:
    def __init__(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.name = name
        self.attributes = attributes or {}
        self.start_time = time.monotonic()
        self.end_time: float | None = None
        self.events: list[dict[str, Any]] = []

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.monotonic()})

    def close(self) -> None:
        self.end_time = time.monotonic()

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.monotonic()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "attributes": self.attributes,
            "duration_ms": round(self.duration_ms, 2),
            "events": self.events,
        }


class OTelTracer:
    def __init__(self, service_name: str = "multi-agent") -> None:
        self.service_name = service_name
        self._spans: list[Span] = []
        self._stack: list[Span] = []
        self._exporters: list[Any] = []

    @asynccontextmanager
    async def span(self, name: str, attributes: dict[str, Any] | None = None) -> AsyncIterator[Span]:
        span = Span(name, attributes)
        self._spans.append(span)
        self._stack.append(span)
        try:
            yield span
        finally:
            span.close()
            self._stack.pop()

    def add_exporter(self, exporter: Any) -> None:
        self._exporters.append(exporter)

    def get_trace(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._spans]

    def export(self) -> None:
        trace = self.get_trace()
        for exporter in self._exporters:
            try:
                exporter(trace)
            except Exception:
                pass


class ConsoleExporter:
    def __call__(self, trace: list[dict[str, Any]]) -> None:
        print(f"\n=== TRACE ({len(trace)} spans) ===")
        for span in trace:
            events_str = f" ({len(span['events'])} events)" if span["events"] else ""
            print(f"  {span['name']}: {span['duration_ms']}ms{events_str}")
        print()


class JSONExporter:
    def __init__(self, path: str = "trace.json") -> None:
        self.path = path

    def __call__(self, trace: list[dict[str, Any]]) -> None:
        from pathlib import Path
        Path(self.path).write_text(json.dumps(trace, indent=2))
