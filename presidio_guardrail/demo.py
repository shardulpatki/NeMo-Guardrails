"""
Presidio × NeMo Guardrails — PII Detection Demo

Demonstrates PII detection and redaction running through the
NeMo Guardrails pipeline with an OpenAI LLM (gpt-4o-mini).

Flow: User Input → Input Rail (PII redaction via built-in Presidio) → LLM → Response

Tracing: OpenTelemetry spans are emitted for every guardrail call and
written to both the console and ./logs/traces.jsonl.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time

from dotenv import load_dotenv

# Ensure stdout handles Unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Load .env and check for OpenAI API key ───────────────────────────────────
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY is not set.")
    print("Create a .env file in the presidio_guardrail/ directory with:")
    print('  OPENAI_API_KEY=sk-...')
    sys.exit(1)

# ── OpenTelemetry Tracing Setup ──────────────────────────────────────────────
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode

TRACE_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "traces.jsonl")
os.makedirs(os.path.dirname(TRACE_LOG_PATH), exist_ok=True)


class FileSpanExporter(SpanExporter):
    """Writes completed spans as JSON lines to a file."""

    def __init__(self, filepath: str):
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


resource = Resource.create({"service.name": "nemo-guardrails-presidio-demo"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(TRACE_LOG_PATH)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("presidio_guardrail")

# ── NeMo Guardrails ──────────────────────────────────────────────────────────
from nemoguardrails import LLMRails, RailsConfig

# ── Sample Inputs ────────────────────────────────────────────────────────────

SAMPLE_INPUTS: list[str] = [
    "Hi, my name is Sarah Connor and my email is sarah@skynet.com.",
    "Please charge credit card 4111-1111-1111-1111, expiry 09/26.",
    "My SSN is 456-78-9012 and I live at 742 Evergreen Terrace.",
    "Call me at (212) 555-1234 or visit https://example.com/profile.",
    "What is Python?",  # Clean — no PII, will get an LLM response
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def pretty(title: str, width: int = 60) -> None:
    """Print a formatted section header with separator lines."""
    print()
    print("─" * width)
    print(f"  {title}")
    print("─" * width)


def build_rails() -> LLMRails:
    """Load config and create an LLMRails instance."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    config = RailsConfig.from_path(config_path)
    rails = LLMRails(config)
    return rails


def generate_with_tracing(rails: LLMRails, user_input: str) -> str:
    """Run rails.generate wrapped in an OpenTelemetry span."""
    with tracer.start_as_current_span("guardrails.generate") as span:
        span.set_attribute("input.length", len(user_input))

        try:
            response = rails.generate(
                messages=[{"role": "user", "content": user_input}]
            )
            output = response["content"]
            span.set_attribute("output.text", output)
            span.set_attribute("output.length", len(output))
            span.set_status(StatusCode.OK)
            return output
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise


# ── Demo Runner ──────────────────────────────────────────────────────────────


def run_demo() -> None:
    """Run the full demo: sample inputs then interactive mode."""

    pretty("Presidio × NeMo Guardrails — PII Detection Demo (with LLM)")
    print()
    print("  Loading NeMo Guardrails config, Presidio engines, and OpenAI LLM...")
    print()

    with tracer.start_as_current_span("demo.init"):
        rails = build_rails()

    # ── Sample inputs ────────────────────────────────────────────────────────
    for i, text in enumerate(SAMPLE_INPUTS, 1):
        pretty(f"Sample {i}")
        print(f"  INPUT:  {text}")

        output = generate_with_tracing(rails, text)
        print(f"  OUTPUT: {output}")

    # ── Interactive mode ─────────────────────────────────────────────────────
    pretty("Interactive Mode (LLM-backed)")
    print('  Chat with the LLM. PII in your input is redacted before reaching the model.')
    print('  Type "quit" to exit.\n')

    while True:
        try:
            user_input = input("  > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() == "quit":
            break

        if not user_input.strip():
            continue

        output = generate_with_tracing(rails, user_input)
        print(f"  {output}")
        print()

    pretty("Demo complete")
    print(f"\n  Trace log written to: {TRACE_LOG_PATH}\n")

    # Flush remaining spans
    provider.shutdown()


if __name__ == "__main__":
    run_demo()
