"""Standalone Presidio PII detection and redaction utilities.

Used by the Streamlit UI for the Scanner tab. The NeMo Guardrails pipeline
(Chat tab) uses config/config.py instead.
"""

from __future__ import annotations

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider, NerModelConfiguration
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from logging_config import get_logger

logger = get_logger("actions")

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
    "NRP",
    "MEDICAL_LICENSE",
    "URL",
]

CONFIDENCE_THRESHOLD: float = 0.5

_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None


def get_analyzer() -> AnalyzerEngine:
    """Return a lazy-initialized singleton AnalyzerEngine with spaCy en_core_web_lg."""
    global _analyzer
    if _analyzer is None:
        logger.info("Initializing AnalyzerEngine (spaCy en_core_web_lg)")
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
        )
        nlp_engine = provider.create_engine()
        nlp_engine.ner_model_configuration = NerModelConfiguration(
            labels_to_ignore=["CARDINAL", "ORDINAL", "QUANTITY"],
        )
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        logger.info("AnalyzerEngine initialized successfully")
    return _analyzer


def get_anonymizer() -> AnonymizerEngine:
    """Return a lazy-initialized singleton AnonymizerEngine."""
    global _anonymizer
    if _anonymizer is None:
        logger.info("Initializing AnonymizerEngine")
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def detect_pii(
    text: str,
    threshold: float = CONFIDENCE_THRESHOLD,
    entities: list[str] | None = None,
) -> list[dict]:
    """Detect PII entities in text.

    Returns a list of dicts with keys: entity_type, start, end, score, text.
    """
    if entities is None:
        entities = DETECT_ENTITIES

    analyzer = get_analyzer()
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=entities,
        score_threshold=threshold,
    )

    logger.info(
        "detect_pii: text_length=%d, threshold=%.2f, found=%d",
        len(text),
        threshold,
        len(results),
    )

    return [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": r.score,
            "text": text[r.start : r.end],
        }
        for r in results
    ]


def redact_pii(
    text: str,
    threshold: float = CONFIDENCE_THRESHOLD,
    entities: list[str] | None = None,
) -> str:
    """Return text with PII replaced by <ENTITY_TYPE> placeholders."""
    if entities is None:
        entities = DETECT_ENTITIES

    analyzer = get_analyzer()
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=entities,
        score_threshold=threshold,
    )

    operators = {entity: OperatorConfig("replace") for entity in entities}
    anonymizer = get_anonymizer()
    masked = anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)

    logger.info("redact_pii: text_length=%d, entities_found=%d", len(text), len(results))

    return masked.text
