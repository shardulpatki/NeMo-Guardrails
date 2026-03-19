"""Streamlit UI for Presidio × NeMo Guardrails PII Detection Demo."""

from __future__ import annotations

import html
import os

import streamlit as st
from dotenv import load_dotenv
from presidio_anonymizer.entities import OperatorConfig

import actions

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Presidio × NeMo Guardrails",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        padding: 12px 16px;
        border-radius: 8px;
        background: #f8f9fa;
    }
    .guardrail-msg {
        background: linear-gradient(135deg, #fff5f5, #fff8f0);
        border-left: 4px solid #e53e3e;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 4px 0;
    }
    .pii-container {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        line-height: 1.8;
        font-size: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ────────────────────────────────────────────────────────────

if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Engine loading ───────────────────────────────────────────────────────────


@st.cache_resource
def load_analyzer():
    return actions.get_analyzer()


@st.cache_resource
def load_anonymizer():
    return actions.get_anonymizer()


@st.cache_resource
def load_rails():
    from nemoguardrails import LLMRails, RailsConfig

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    config = RailsConfig.from_path(config_path)
    return LLMRails(config)


try:
    analyzer = load_analyzer()
    anonymizer = load_anonymizer()
except Exception as e:
    st.error(f"Failed to load Presidio engines. Is spaCy `en_core_web_lg` installed?\n\n{e}")
    st.stop()

has_api_key = bool(os.environ.get("OPENAI_API_KEY"))

# ── Helper functions ─────────────────────────────────────────────────────────

SAMPLE_TEXTS = [
    "My name is Sarah Connor and my email is sarah@skynet.com.",
    "Please charge card 4111-1111-1111-1111, exp 09/26.",
    "My SSN is 456-78-9012, I live at 742 Evergreen Terrace.",
    "Call me at (212) 555-1234 or visit https://example.com.",
    "Driver license D12345678, passport no. 912345678.",
    "What is Python?",
]

ASSISTANT_RESPONSES = [
    "I understand you'd like help, but I can't process personal information. How else can I assist you?",
    "I've received your message. For security, any sensitive data was redacted before I saw it. How can I help?",
    "Thanks for your message! I'm here to help with questions and tasks. What would you like to know?",
    "I can help with that! Let me provide some information on the topic.",
]


def scan_text(text: str, threshold: float, entities: list[str]):
    """Run Presidio analysis and anonymization with given settings."""
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=entities,
        score_threshold=threshold,
    )
    operators = {e: OperatorConfig("replace") for e in entities}
    masked = anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)

    entities_list = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 3),
            "text": text[r.start : r.end],
        }
        for r in sorted(results, key=lambda x: x.start)
    ]
    return entities_list, masked.text


def build_highlighted_html(text: str, entities: list[dict]) -> str:
    """Build HTML with PII spans highlighted in red."""
    sorted_ents = sorted(entities, key=lambda e: e["start"])
    parts = []
    prev_end = 0
    for ent in sorted_ents:
        if ent["start"] < prev_end:
            continue
        parts.append(html.escape(text[prev_end : ent["start"]]))
        ent_text = html.escape(text[ent["start"] : ent["end"]])
        parts.append(
            f'<span style="background:#fed7d7;padding:2px 4px;border-radius:4px;">'
            f"{ent_text}"
            f'<sup style="color:#c53030;font-size:0.7em;margin-left:2px;">'
            f"{ent['entity_type']}</sup></span>"
        )
        prev_end = ent["end"]
    parts.append(html.escape(text[prev_end:]))
    return "".join(parts)


def build_redacted_html(text: str, entities: list[dict]) -> str:
    """Build HTML with PII replaced by blue entity-type placeholders."""
    sorted_ents = sorted(entities, key=lambda e: e["start"])
    parts = []
    prev_end = 0
    for ent in sorted_ents:
        if ent["start"] < prev_end:
            continue
        parts.append(html.escape(text[prev_end : ent["start"]]))
        parts.append(
            f'<span style="background:#bee3f8;padding:2px 6px;border-radius:4px;'
            f'font-weight:600;color:#2b6cb0;">'
            f"&lt;{ent['entity_type']}&gt;</span>"
        )
        prev_end = ent["end"]
    parts.append(html.escape(text[prev_end:]))
    return "".join(parts)


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Detection Settings")

    threshold = st.slider(
        "Confidence threshold",
        min_value=0.0,
        max_value=1.0,
        value=actions.CONFIDENCE_THRESHOLD,
        step=0.05,
    )

    st.subheader("Entity types")

    def toggle_all():
        val = st.session_state.get("_select_all_toggle", True)
        for ent in actions.DETECT_ENTITIES:
            st.session_state[f"ent_{ent}"] = val

    select_all = st.toggle("Select all", value=True, key="_select_all_toggle", on_change=toggle_all)

    selected_entities = []
    for ent in actions.DETECT_ENTITIES:
        if f"ent_{ent}" not in st.session_state:
            st.session_state[f"ent_{ent}"] = True
        if st.checkbox(ent, key=f"ent_{ent}"):
            selected_entities.append(ent)

    st.divider()
    st.info(
        "**Powered by Microsoft Presidio + spaCy en_core_web_lg**\n\n"
        "Integrated with NVIDIA NeMo Guardrails"
    )

# ── Tabs ─────────────────────────────────────────────────────────────────────

scanner_tab, chat_tab = st.tabs(["🔍 Scanner", "💬 Chat Simulation"])

# ── Scanner Tab ──────────────────────────────────────────────────────────────

with scanner_tab:
    st.title("🛡️ Sensitive Data Detection Guardrail")
    st.caption("Inspect what the Presidio detection engine finds in your text")

    # Sample buttons
    cols = st.columns(6)
    for i, (col, sample) in enumerate(zip(cols, SAMPLE_TEXTS)):
        label = sample[:28] + "…" if len(sample) > 30 else sample
        if col.button(label, key=f"sample_{i}", use_container_width=True):
            st.session_state.input_text = sample
            st.session_state.scan_results = None
            st.rerun()

    text_input = st.text_area(
        "Enter text to scan",
        key="input_text",
        height=120,
        placeholder="Type or paste text here, or click a sample above…",
    )

    if st.button("🔍 Scan for Sensitive Data", type="primary", use_container_width=True):
        if not text_input.strip():
            st.warning("Please enter some text to scan.")
        elif not selected_entities:
            st.warning("Please select at least one entity type.")
        else:
            with st.spinner("Scanning…"):
                entities_found, redacted_text = scan_text(
                    text_input, threshold, selected_entities
                )
                st.session_state.scan_results = {
                    "entities": entities_found,
                    "redacted": redacted_text,
                    "original": text_input,
                }

    # Results
    results = st.session_state.scan_results
    if results is not None:
        ents = results["entities"]

        if ents:
            scores = [e["score"] for e in ents]
            unique_types = list({e["entity_type"] for e in ents})

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Entities found", len(ents))
            m2.metric("Unique types", len(unique_types))
            m3.metric("Confidence range", f"{min(scores):.2f} – {max(scores):.2f}")
            m4.metric("Guardrail action", "🚫 BLOCK PII")

            st.subheader("Detected PII")
            st.markdown(
                f'<div class="pii-container">{build_highlighted_html(results["original"], ents)}</div>',
                unsafe_allow_html=True,
            )

            st.subheader("Redacted Output")
            st.markdown(
                f'<div class="pii-container">{build_redacted_html(results["original"], ents)}</div>',
                unsafe_allow_html=True,
            )

            st.subheader("Entity Details")
            import pandas as pd

            df = pd.DataFrame(ents)
            df = df.sort_values("score", ascending=False).reset_index(drop=True)
            df.columns = ["Entity Type", "Start", "End", "Score", "Text"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No sensitive data detected — message passes through to LLM")

# ── Chat Simulation Tab ─────────────────────────────────────────────────────

with chat_tab:
    st.title("💬 NeMo Guardrails Chat Simulation")

    st.info(
        "This demonstrates the **NeMo Guardrails pipeline**. "
        "Messages go through the input rail for PII detection before reaching the LLM."
    )

    # Clear chat button
    col_spacer, col_clear = st.columns([5, 1])
    with col_clear:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    if not has_api_key:
        st.warning(
            "⚠️ `OPENAI_API_KEY` not set — chat will use simulated responses. "
            "Set the key in `.env` for real LLM responses via NeMo Guardrails."
        )

    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "guardrail":
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(
                    f'<div class="guardrail-msg">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("redacted"):
                    with st.expander("View redacted text"):
                        st.code(msg["redacted"], language=None)
        else:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type a message…"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # PII detection using sidebar settings
        pii_entities, redacted_text = scan_text(prompt, threshold, selected_entities)

        if pii_entities:
            types_found = list({e["entity_type"] for e in pii_entities})
            guardrail_content = (
                f"**🛡️ PII Detected** — Found {len(pii_entities)} entit{'y' if len(pii_entities) == 1 else 'ies'} "
                f"({', '.join(types_found)}). Input will be redacted before reaching the LLM."
            )
            st.session_state.chat_history.append({
                "role": "guardrail",
                "content": guardrail_content,
                "redacted": redacted_text,
            })

        # Generate response
        if has_api_key:
            try:
                rails = load_rails()
                response = rails.generate(
                    messages=[{"role": "user", "content": prompt}]
                )
                assistant_text = response["content"]
            except Exception as e:
                assistant_text = f"Error from NeMo Guardrails: {e}"
        else:
            idx = len(st.session_state.chat_history) % len(ASSISTANT_RESPONSES)
            assistant_text = ASSISTANT_RESPONSES[idx]

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": assistant_text,
        })
        st.rerun()
