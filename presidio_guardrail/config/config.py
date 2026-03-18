"""Custom Presidio PII masking action with OpenTelemetry tracing."""

from __future__ import annotations

from opentelemetry import trace
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from nemoguardrails import RailsConfig
from nemoguardrails.actions import action
from nemoguardrails.library.sensitive_data_detection.actions import (
    _get_analyzer,
    _get_ad_hoc_recognizers,
)

tracer = trace.get_tracer("presidio_guardrail.pii")


def _partial_mask(value: str, visible: int = 3) -> str:
    """Show first `visible` chars, mask the rest with '*'."""
    if len(value) <= visible:
        return "*" * len(value)
    return value[:visible] + "*" * (len(value) - visible)


def init(app):
    """Register the custom PII tracing action with NeMo Guardrails."""
    app.register_action(mask_sensitive_data_with_tracing, "mask_sensitive_data_with_tracing")


@action(is_system_action=True)
async def mask_sensitive_data_with_tracing(
    source: str, text: str, config: RailsConfig
):
    """Mask PII in text using Presidio, emitting an OTel span with entity details.

    Args:
        source: "input", "output", or "retrieval".
        text: The text to analyze and anonymize.
        config: The NeMo Guardrails configuration object.

    Returns:
        The anonymized text with PII replaced by placeholders.
    """
    sdd_config = config.rails.config.sensitive_data_detection
    assert source in ["input", "output", "retrieval"]
    options = getattr(sdd_config, source)

    with tracer.start_as_current_span("pii.mask_sensitive_data") as span:
        span.set_attribute("pii.source", source)
        span.set_attribute("pii.original_text", text)

        # No entities configured — nothing to mask
        if len(options.entities) == 0:
            span.set_attribute("pii.redacted_text", text)
            span.set_attribute("pii.entity_count", 0)
            span.set_attribute("pii.entity_types", [])
            span.set_attribute("pii.entity_originals", [])
            span.set_attribute("pii.entity_replacements", [])
            span.set_attribute("pii.entity_scores", [])
            return text

        analyzer = _get_analyzer()
        operators = {entity: OperatorConfig("replace") for entity in options.entities}

        results = analyzer.analyze(
            text=text,
            language="en",
            entities=options.entities,
            ad_hoc_recognizers=_get_ad_hoc_recognizers(sdd_config),
        )

        anonymizer = AnonymizerEngine()
        masked_results = anonymizer.anonymize(
            text=text, analyzer_results=results, operators=operators
        )

        # Extract per-entity details
        entity_types = [r.entity_type for r in results]
        entity_originals = [_partial_mask(text[r.start:r.end]) for r in results]
        entity_replacements = [f"<{r.entity_type}>" for r in results]
        entity_scores = [r.score for r in results]

        span.set_attribute("pii.redacted_text", masked_results.text)
        span.set_attribute("pii.entity_count", len(results))
        span.set_attribute("pii.entity_types", entity_types)
        span.set_attribute("pii.entity_originals", entity_originals)
        span.set_attribute("pii.entity_replacements", entity_replacements)
        span.set_attribute("pii.entity_scores", entity_scores)

        return masked_results.text
