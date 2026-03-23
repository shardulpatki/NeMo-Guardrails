"""
Presidio x NeMo Guardrails — PII Detection Demo

Demonstrates PII detection and redaction running through the
NeMo Guardrails pipeline with an OpenAI LLM (gpt-4o-mini).

Flow: User Input -> Input Rail (PII redaction via built-in Presidio) -> LLM -> Response

Tracing: OpenTelemetry spans are emitted for every guardrail call and
written to ./logs/traces.jsonl.
Logging: Structured logs with trace correlation are written to ./logs/app.log.
"""

from __future__ import annotations

import io
import os
import sys

from dotenv import load_dotenv

# Ensure stdout handles Unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Load .env and check for OpenAI API key ───────────────────────────────────
load_dotenv()

# ── Logging & Tracing Setup ──────────────────────────────────────────────────
from logging_config import setup_logging, get_logger
from tracing_config import setup_tracing, get_tracer, TRACE_LOG_PATH

setup_logging()
provider = setup_tracing("nemo-guardrails-presidio-demo")
logger = get_logger("demo")
tracer = get_tracer("presidio_guardrail")

from opentelemetry.trace import StatusCode

if not os.environ.get("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY is not set. Create a .env file with: OPENAI_API_KEY=sk-...")
    print("ERROR: OPENAI_API_KEY is not set.")
    print("Create a .env file in the presidio_guardrail/ directory with:")
    print('  OPENAI_API_KEY=sk-...')
    sys.exit(1)

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
    print("\u2500" * width)
    print(f"  {title}")
    print("\u2500" * width)


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
        logger.info("Generating response, input_length=%d", len(user_input))

        try:
            # Note: Colang 2.x does not support the "log" option in rails.generate().
            # NeMo internal logging is captured via Python logging instead.
            response = rails.generate(
                messages=[{"role": "user", "content": user_input}]
            )
            output = response["content"]

            # Only log output text if explicitly opted in (PII safety)
            if os.environ.get("TRACE_LOG_OUTPUT_TEXT", "").lower() == "true":
                span.set_attribute("output.text", output)
            span.set_attribute("output.length", len(output))
            span.set_status(StatusCode.OK)
            logger.info("Response generated, output_length=%d", len(output))
            return output
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            logger.exception("Error during rails.generate")
            raise


# ── Demo Runner ──────────────────────────────────────────────────────────────


def run_demo() -> None:
    """Run the full demo: sample inputs then interactive mode."""

    pretty("Presidio \u00d7 NeMo Guardrails \u2014 PII Detection Demo (with LLM)")
    logger.info("Starting demo, loading NeMo Guardrails config...")
    print()
    print("  Loading NeMo Guardrails config, Presidio engines, and OpenAI LLM...")
    print()

    with tracer.start_as_current_span("demo.init"):
        rails = build_rails()
    logger.info("Rails initialized successfully")

    # ── Sample inputs ────────────────────────────────────────────────────────
    for i, text in enumerate(SAMPLE_INPUTS, 1):
        pretty(f"Sample {i}")
        print(f"  INPUT:  {text}")
        logger.info("Processing sample %d/%d", i, len(SAMPLE_INPUTS))

        output = generate_with_tracing(rails, text)
        print(f"  OUTPUT: {output}")

    # ── Interactive mode ─────────────────────────────────────────────────────
    pretty("Interactive Mode (LLM-backed)")
    print('  Chat with the LLM. PII in your input is redacted before reaching the model.')
    print('  Type "quit" to exit.\n')
    logger.info("Entering interactive mode")

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
    logger.info("Demo complete, trace log at %s", TRACE_LOG_PATH)

    # Flush remaining spans
    provider.shutdown()


if __name__ == "__main__":
    run_demo()
