"""Shared OpenTelemetry tracing setup for all entry points."""

from __future__ import annotations

import json
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

TRACE_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "traces.jsonl"
)

_provider: TracerProvider | None = None


class FileSpanExporter(SpanExporter):
    """Writes completed spans as JSON lines to a file."""

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath

    def export(self, spans):
        with open(self._filepath, "a", encoding="utf-8") as f:
            for span in spans:
                record = {
                    "name": span.name,
                    "trace_id": format(span.context.trace_id, "032x"),
                    "span_id": format(span.context.span_id, "016x"),
                    "parent_span_id": (
                        format(span.parent.span_id, "016x") if span.parent else None
                    ),
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": (
                        (span.end_time - span.start_time) / 1e6
                        if span.end_time and span.start_time
                        else None
                    ),
                    "status": span.status.status_code.name,
                    "attributes": dict(span.attributes) if span.attributes else {},
                }
                f.write(json.dumps(record) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def setup_tracing(service_name: str) -> TracerProvider:
    """Configure and return an OpenTelemetry TracerProvider.

    Idempotent — safe to call multiple times (e.g. Streamlit reruns).

    Reads from environment variables:
        OTEL_CONSOLE_EXPORT:          Set to 'true' to enable ConsoleSpanExporter.
        OTEL_EXPORTER_OTLP_ENDPOINT:  OTLP collector URL for production export.
    """
    global _provider
    if _provider is not None:
        return _provider

    os.makedirs(os.path.dirname(TRACE_LOG_PATH), exist_ok=True)

    resource = Resource.create({"service.name": service_name})
    _provider = TracerProvider(resource=resource)

    # Always write spans to JSONL file
    _provider.add_span_processor(
        SimpleSpanProcessor(FileSpanExporter(TRACE_LOG_PATH))
    )

    # Optional: console export for development
    if os.environ.get("OTEL_CONSOLE_EXPORT", "").lower() == "true":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        _provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # Optional: OTLP export for production (Jaeger, Datadog, etc.)
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        _provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )

    trace.set_tracer_provider(_provider)
    return _provider


def get_tracer(name: str) -> trace.Tracer:
    """Return a named tracer from the global provider."""
    return trace.get_tracer(name)
