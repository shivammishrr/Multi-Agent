import pytest
from multi_agent.features.observability.tracer import OTelTracer, ConsoleExporter, JSONExporter, Span


class TestSpan:
    def test_create_span(self):
        span = Span("test")
        assert span.name == "test"
        assert span.start_time > 0
        assert span.end_time is None
        assert span.duration_ms >= 0

    def test_close_span(self):
        span = Span("test")
        span.close()
        assert span.end_time is not None
        assert span.duration_ms > 0

    def test_add_event(self):
        span = Span("test")
        span.add_event("step1", {"key": "val"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "step1"

    def test_to_dict(self):
        span = Span("test", {"key": "val"})
        span.add_event("step")
        span.close()
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["attributes"] == {"key": "val"}
        assert "duration_ms" in d
        assert len(d["events"]) == 1


class TestOTelTracer:
    @pytest.mark.asyncio
    async def test_trace_span(self):
        tracer = OTelTracer("test-svc")
        assert tracer.service_name == "test-svc"

        async with tracer.span("operation1") as span:
            span.add_event("substep")

        trace = tracer.get_trace()
        assert len(trace) == 1
        assert trace[0]["name"] == "operation1"
        assert trace[0]["duration_ms"] >= 0
        assert len(trace[0]["events"]) == 1

    @pytest.mark.asyncio
    async def test_nested_spans(self):
        tracer = OTelTracer()

        async with tracer.span("outer"):
            async with tracer.span("inner"):
                pass

        trace = tracer.get_trace()
        assert len(trace) == 2
        names = [s["name"] for s in trace]
        assert "outer" in names
        assert "inner" in names

    @pytest.mark.asyncio
    async def test_export(self):
        tracer = OTelTracer()
        exported = []

        def exporter(trace):
            exported.extend(trace)

        tracer.add_exporter(exporter)
        async with tracer.span("test"):
            pass

        tracer.export()
        assert len(exported) == 1
        assert exported[0]["name"] == "test"


class TestExporters:
    def test_console_exporter(self):
        exporter = ConsoleExporter()
        exporter([{"name": "test", "duration_ms": 10.0, "attributes": {}, "events": []}])

    def test_json_exporter(self, tmp_path):
        path = str(tmp_path / "test_trace.json")
        exporter = JSONExporter(path)
        exporter([{"name": "test", "duration_ms": 10.0, "attributes": {}, "events": []}])
        import json
        from pathlib import Path
        data = json.loads(Path(path).read_text())
        assert len(data) == 1
        assert data[0]["name"] == "test"
