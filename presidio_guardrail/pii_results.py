"""Shared state for PII scan results between NeMo Guardrails actions and Streamlit UI."""

from __future__ import annotations

_last_results: dict = {"entities": [], "redacted_text": None}


def store_scan_results(entities: list[dict], redacted_text: str) -> None:
    """Store PII scan results (called by the NeMo Guardrails action)."""
    _last_results["entities"] = entities
    _last_results["redacted_text"] = redacted_text


def get_last_scan_results() -> tuple[list[dict], str | None]:
    """Return (entities, redacted_text) from the most recent scan, then clear them."""
    entities = _last_results["entities"]
    redacted_text = _last_results["redacted_text"]
    _last_results["entities"] = []
    _last_results["redacted_text"] = None
    return entities, redacted_text
