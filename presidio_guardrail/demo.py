"""
Presidio × NeMo Guardrails — Standalone CLI Demo

Demonstrates PII detection and redaction using Microsoft Presidio
without requiring an LLM backend.
"""

from __future__ import annotations

import json
import sys

from actions import detect_pii, redact_pii

# ── Sample Inputs ────────────────────────────────────────────────────────────

SAMPLE_INPUTS: list[str] = [
    "Hi, my name is Sarah Connor and my email is sarah@skynet.com.",
    "Please charge credit card 4111-1111-1111-1111, expiry 09/26.",
    "My SSN is 123-45-6789 and I live at 742 Evergreen Terrace.",
    "Call me at (555) 867-5309 or visit https://example.com/profile.",
    "The quarterly report shows 15% growth.",  # Clean — no PII
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def pretty(title: str, width: int = 60) -> None:
    """Print a formatted section header with separator lines."""
    print()
    print("─" * width)
    print(f"  {title}")
    print("─" * width)


# ── Demo Runner ──────────────────────────────────────────────────────────────


def run_demo() -> None:
    """Run the full demo: sample inputs then interactive mode."""

    pretty("Presidio × NeMo Guardrails — PII Detection Demo")
    print()
    print("  Loading Presidio engines (first run loads spaCy model)...")
    print()

    # ── Sample inputs ────────────────────────────────────────────────────────
    for i, text in enumerate(SAMPLE_INPUTS, 1):
        pretty(f"Sample {i}")
        print(f"  INPUT:  {text}")

        entities = detect_pii(text)

        if entities:
            print(f"\n  ENTITIES ({len(entities)} found):")
            print(f"  {json.dumps(entities, indent=2)}")
            redacted = redact_pii(text)
            print(f"\n  REDACTED: {redacted}")
            entity_types = sorted({e['entity_type'] for e in entities})
            print(
                f"\n  🛡️  GUARDRAIL TRIGGERED — "
                f"{len(entities)} entit{'y' if len(entities) == 1 else 'ies'} "
                f"detected: {', '.join(entity_types)}"
            )
        else:
            print("\n  ✅ CLEAN — no sensitive data detected")

    # ── Interactive mode ─────────────────────────────────────────────────────
    pretty("Interactive Mode")
    print('  Type any text to scan for PII. Type "quit" to exit.\n')

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

        entities = detect_pii(user_input)

        if entities:
            print(f"\n  ENTITIES ({len(entities)} found):")
            print(f"  {json.dumps(entities, indent=2)}")
            redacted = redact_pii(user_input)
            print(f"\n  REDACTED: {redacted}")
            entity_types = sorted({e['entity_type'] for e in entities})
            print(
                f"\n  🛡️  GUARDRAIL TRIGGERED — "
                f"{len(entities)} entit{'y' if len(entities) == 1 else 'ies'} "
                f"detected: {', '.join(entity_types)}"
            )
        else:
            print("\n  ✅ CLEAN — no sensitive data detected")

        print()

    pretty("Demo complete")
    print()


if __name__ == "__main__":
    run_demo()
