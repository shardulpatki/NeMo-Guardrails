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
cd presidio_guardrail
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

Create a `.env` file (see `.env.example`):

```
OPENAI_API_KEY=sk-...
```

### Run the CLI Demo

```bash
python demo.py
```

Runs five sample inputs through Presidio detection and redaction, then drops into interactive mode. Traces are written to `logs/traces.jsonl`.

### Run the Streamlit UI

```bash
streamlit run streamlit_app.py
```

Opens an interactive web app at `http://localhost:8501` with two tabs:

- **Scanner** — paste or select sample text, adjust the confidence threshold and entity types via the sidebar, and see highlighted PII with redacted output.
- **Chat Simulation** — simulates a conversation where the guardrail intercepts PII before it reaches the LLM. Uses the OpenAI API when `OPENAI_API_KEY` is set, otherwise returns simulated responses.

## NeMo Guardrails Integration

To use this as a guardrail in your NeMo Guardrails project:

1. Copy `actions.py` into your guardrails config directory.
2. Copy `config/config.yml` and `config/rails.co` into your config folder.
3. The rails will automatically activate on every user/bot message.

## Tracing (OpenTelemetry)

The project includes custom OpenTelemetry instrumentation (NeMo's built-in `config.tracing` is incompatible with Colang 2.x).

- **Service name:** `nemo-guardrails-presidio-demo`
- **Exporters:** Console + `FileSpanExporter` (writes to `logs/traces.jsonl`)
- **Span attributes:** redacted text, entity count, entity types, confidence scores, partial-masked originals (first 3 characters visible), and replacements.

Tracing is configured in `config/config.py` and emitted from the custom action in `actions.py`.

## Configuration

### Confidence Threshold

The default threshold is `0.35` (set in `config/config.yml`). In the Streamlit UI you can adjust it dynamically via the sidebar slider.

- **Higher** (e.g. `0.7`) — fewer false positives, may miss borderline entities.
- **Lower** (e.g. `0.3`) — catches more edge cases, increases false positives.

Regex-based recognizers (SSN, credit card, email) typically score `0.85–1.0`. NER-based recognizers (person names, locations) score `0.6–0.85`.

### Entity Types

The 14 detected entity types are configured in `config/config.yml` under `rails.config.sensitive_data_detection`. In the Streamlit UI you can toggle individual entity types on/off.

### LLM Backend

Change the `models` section in `config/config.yml` to point at your preferred backend (OpenAI, NVIDIA, HuggingFace, etc.). The default is `gpt-4o-mini`.

### Custom Recognizers

Add domain-specific patterns (e.g. internal employee IDs, project codes) via Presidio's `RecognizerRegistry` in `actions.py`.

## File Structure

```
presidio_guardrail/
├── actions.py            # Presidio detection + NeMo @action functions + tracing
├── demo.py               # CLI demo with LLM and OpenTelemetry tracing
├── streamlit_app.py      # Interactive Streamlit web UI
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
├── README.md             # This file
├── config/
│   ├── config.yml        # NeMo Guardrails YAML configuration
│   ├── config.py         # Custom OpenTelemetry tracing setup
│   └── rails.co          # Colang 2.x rail definitions
└── logs/
    └── traces.jsonl      # OpenTelemetry trace output (git-ignored)
```
