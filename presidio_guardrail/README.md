# Presidio × NeMo Guardrails — Sensitive Data Detection

A production-ready guardrail using [Microsoft Presidio](https://github.com/microsoft/presidio) for PII detection integrated with [NVIDIA NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails). Scans both user input and LLM output to block or redact sensitive data before it crosses trust boundaries.

## Architecture

```
User Message
     │
     ▼
┌────────────────────────┐
│   NeMo Guardrails      │
│   ┌──────────────────┐ │
│   │  INPUT RAIL      │ │  ◄── Presidio scans user message
│   │  (Presidio PII)  │ │      PII found → BLOCK + warn user
│   └────────┬─────────┘ │      No PII  → pass through
│            ▼           │
│   ┌──────────────────┐ │
│   │  LLM Processing  │ │  ◄── Your model generates a response
│   └────────┬─────────┘ │
│            ▼           │
│   ┌──────────────────┐ │
│   │  OUTPUT RAIL     │ │  ◄── Presidio scans bot response
│   │  (Presidio PII)  │ │      PII found → REDACT before delivery
│   └──────────────────┘ │
└────────────────────────┘
     │
     ▼
  Safe Response
```

**Input rail** — blocks the message entirely and warns the user. The LLM never sees the PII.

**Output rail** — redacts PII spans with type-labeled placeholders (e.g. `<EMAIL_ADDRESS>`) so the user still gets a useful response.

## Detected Entity Types

| Entity              | Example                          |
|---------------------|----------------------------------|
| `PERSON`            | Sarah Connor                     |
| `EMAIL_ADDRESS`     | sarah@skynet.com                 |
| `PHONE_NUMBER`      | (555) 867-5309                   |
| `CREDIT_CARD`       | 4111-1111-1111-1111              |
| `US_SSN`            | 123-45-6789                      |
| `IBAN_CODE`         | DE89 3704 0044 0532 0130 00      |
| `IP_ADDRESS`        | 192.168.1.1                      |
| `US_DRIVER_LICENSE`  | D1234567                         |
| `US_PASSPORT`       | 123456789                        |
| `LOCATION`          | 742 Evergreen Terrace            |
| `DATE_TIME`         | 09/26, March 15 2024             |
| `NRP`               | Canadian, Buddhist               |
| `MEDICAL_LICENSE`   | DEA# AB1234567                   |
| `URL`               | https://example.com/profile      |

## Quick Start

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
python demo.py
```

The demo runs five sample inputs through Presidio detection and redaction, then drops into an interactive mode where you can type arbitrary text.

## NeMo Guardrails Integration

To use this as a guardrail in your NeMo Guardrails project:

1. Copy `actions.py` into your guardrails config directory.
2. Copy `config/config.yml` and `config/rails.co` into your config folder.
3. The rails will automatically activate on every user/bot message.

## Configuration

### Confidence Threshold

Adjust `CONFIDENCE_THRESHOLD` in `actions.py` (default `0.35`).

- **Higher** (e.g. `0.7`) — fewer false positives, may miss borderline entities.
- **Lower** (e.g. `0.3`) — catches more edge cases, increases false positives.

Regex-based recognizers (SSN, credit card, email) typically score `0.85–1.0`. NER-based recognizers (person names, locations) score `0.6–0.85`.

### Entity Types

Edit the `DETECT_ENTITIES` list in `actions.py` to add or remove entity types.

### LLM Backend

Change the `models` section in `config/config.yml` to point at your preferred backend (OpenAI, NVIDIA, HuggingFace, etc.).

### Custom Recognizers

Add domain-specific patterns (e.g. internal employee IDs, project codes) via Presidio's `RecognizerRegistry` in `actions.py`.

## File Structure

```
presidio_guardrail/
├── actions.py            # Presidio detection + NeMo @action functions
├── demo.py               # Standalone CLI demo (no LLM needed)
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── config/
    ├── config.yml        # NeMo Guardrails YAML configuration
    └── rails.co          # Colang 2.x rail definitions
```
