"""
Presidio × NeMo Guardrails — Core Integration Module

Bridges Microsoft Presidio (PII detection/redaction) with NVIDIA NeMo Guardrails
by exposing three @action functions that serve as input and output rails.
"""

from __future__ import annotations

# ── Presidio Imports ──────────────────────────────────────────────────────────
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# ── NeMo Guardrails Imports ──────────────────────────────────────────────────
from nemoguardrails.actions import action

# ── Configuration ────────────────────────────────────────────────────────────

DETECT_ENTITIES: list[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "IBAN_CODE",
    "IP_ADDRESS",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "LOCATION",
    "DATE_TIME",
    "NRP",                # Nationality / Religious / Political group
    "MEDICAL_LICENSE",
    "URL",
]

CONFIDENCE_THRESHOLD: float = 0.35  # Minimum score to flag an entity

# ── Lazy Singleton Engines ───────────────────────────────────────────────────

_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None


def _create_analyzer() -> AnalyzerEngine:
    """Configure and return a Presidio AnalyzerEngine backed by spaCy en_core_web_lg."""
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)

    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["en"],
    )


def get_analyzer() -> AnalyzerEngine:
    """Return the shared AnalyzerEngine, creating it on first call."""
    global _analyzer
    if _analyzer is None:
        _analyzer = _create_analyzer()
    return _analyzer


def get_anonymizer() -> AnonymizerEngine:
    """Return the shared AnonymizerEngine, creating it on first call."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


# ── Core Detection Functions ─────────────────────────────────────────────────


def detect_pii(text: str) -> list[dict]:
    """Scan *text* for PII and return a list of detected entity dicts.

    Each dict contains:
        entity_type  – Presidio entity label (e.g. "EMAIL_ADDRESS")
        start / end  – character offsets in the original text
        score        – confidence score rounded to 2 decimals
        text         – the matched substring
    """
    analyzer = get_analyzer()
    results = analyzer.analyze(
        text=text,
        entities=DETECT_ENTITIES,
        language="en",
        score_threshold=CONFIDENCE_THRESHOLD,
    )
    return [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 2),
            "text": text[r.start : r.end],
        }
        for r in results
    ]


def redact_pii(text: str) -> str:
    """Return *text* with every detected PII span replaced by a type-labeled placeholder.

    Example: ``"sarah@skynet.com"`` → ``"<EMAIL_ADDRESS>"``
    """
    analyzer = get_analyzer()
    anonymizer = get_anonymizer()

    results = analyzer.analyze(
        text=text,
        entities=DETECT_ENTITIES,
        language="en",
        score_threshold=CONFIDENCE_THRESHOLD,
    )

    operators = {
        entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
        for entity in DETECT_ENTITIES
    }

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )
    return anonymized.text


# ── NeMo Guardrails Action Functions ────────────────────────────────────────


@action(name="DetectSensitiveDataInInputAction")
async def detect_sensitive_data_in_input(context: dict) -> dict:
    """Input rail action — scan the user message for PII.

    Returns:
        sensitive_data_detected   – bool
        detected_entities         – list of entity dicts
        redacted_user_message     – cleaned text (or original if clean)
    """
    user_message: str = context.get("user_message", "")
    entities = detect_pii(user_message)
    redacted = redact_pii(user_message) if entities else user_message

    return {
        "sensitive_data_detected": len(entities) > 0,
        "detected_entities": entities,
        "redacted_user_message": redacted,
    }


@action(name="DetectSensitiveDataInOutputAction")
async def detect_sensitive_data_in_output(context: dict) -> dict:
    """Output rail action — scan the bot response for PII.

    Returns:
        output_sensitive_data_detected  – bool
        output_detected_entities        – list of entity dicts
        redacted_bot_message            – cleaned text (or original if clean)
    """
    bot_message: str = context.get("bot_message", "")
    entities = detect_pii(bot_message)
    redacted = redact_pii(bot_message) if entities else bot_message

    return {
        "output_sensitive_data_detected": len(entities) > 0,
        "output_detected_entities": entities,
        "redacted_bot_message": redacted,
    }


@action(name="BlockSensitiveInputAction")
async def block_sensitive_input(detected_entities: list | None = None, context: dict | None = None) -> str:
    """Generate a user-facing warning listing the detected PII types."""
    entities: list[dict] = detected_entities or (context or {}).get("detected_entities", [])
    entity_types = sorted({e["entity_type"] for e in entities})
    label = ", ".join(entity_types)
    return (
        f"\u26a0\ufe0f I detected sensitive information in your message "
        f"({label}). Please remove any personal data before sending."
    )
