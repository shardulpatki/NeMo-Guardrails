"""
Presidio × NeMo Guardrails — PII Detection Demo

Demonstrates PII detection and redaction running through the
NeMo Guardrails pipeline with an OpenAI LLM (gpt-4o-mini).

Flow: User Input → Input Rail (PII scan) → LLM → Output Rail (PII scan) → Response
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

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY is not set.")
    print("Create a .env file in the presidio_guardrail/ directory with:")
    print('  OPENAI_API_KEY=sk-...')
    sys.exit(1)

from nemoguardrails import LLMRails, RailsConfig

from actions import (
    detect_sensitive_data_in_input,
    detect_sensitive_data_in_output,
    block_sensitive_input,
)

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
    """Load config and create an LLMRails instance with registered actions."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    config = RailsConfig.from_path(config_path)
    rails = LLMRails(config)

    rails.register_action(detect_sensitive_data_in_input, "DetectSensitiveDataInInputAction")
    rails.register_action(detect_sensitive_data_in_output, "DetectSensitiveDataInOutputAction")
    rails.register_action(block_sensitive_input, "BlockSensitiveInputAction")

    return rails


# ── Demo Runner ──────────────────────────────────────────────────────────────


def run_demo() -> None:
    """Run the full demo: sample inputs then interactive mode."""

    pretty("Presidio × NeMo Guardrails — PII Detection Demo (with LLM)")
    print()
    print("  Loading NeMo Guardrails config, Presidio engines, and OpenAI LLM...")
    print()

    rails = build_rails()

    # ── Sample inputs ────────────────────────────────────────────────────────
    for i, text in enumerate(SAMPLE_INPUTS, 1):
        pretty(f"Sample {i}")
        print(f"  INPUT:  {text}")

        response = rails.generate(
            messages=[{"role": "user", "content": text}]
        )
        print(f"  OUTPUT: {response['content']}")

    # ── Interactive mode ─────────────────────────────────────────────────────
    pretty("Interactive Mode (LLM-backed)")
    print('  Chat with the LLM. PII is blocked on input and redacted on output.')
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

        response = rails.generate(
            messages=[{"role": "user", "content": user_input}]
        )
        print(f"  {response['content']}")
        print()

    pretty("Demo complete")
    print()


if __name__ == "__main__":
    run_demo()
