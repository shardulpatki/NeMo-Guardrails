# Claude Code Prompt: Streamlit UI for Presidio × NeMo Guardrails Demo

## Context

I have a working Presidio-based PII detection guardrail integrated with NeMo Guardrails. The backend code already exists in a project at `presidio_guardrail/`. The core module is `actions.py` which exposes two key functions:

```python
def detect_pii(text: str) -> list[dict]:
    """Returns list of dicts: {"entity_type", "start", "end", "score", "text"}"""

def redact_pii(text: str) -> str:
    """Returns text with PII replaced by <ENTITY_TYPE> placeholders"""
```

It also has these constants:
```python
DETECT_ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
    "US_SSN", "IBAN_CODE", "IP_ADDRESS", "US_DRIVER_LICENSE",
    "US_PASSPORT", "LOCATION", "DATE_TIME", "NRP",
    "MEDICAL_LICENSE", "URL",
]
CONFIDENCE_THRESHOLD = 0.5
```

And these singleton engine getters:
```python
def get_analyzer() -> AnalyzerEngine
def get_anonymizer() -> AnonymizerEngine
```

I need you to build a **Streamlit app** (`streamlit_app.py`) that provides a polished, interactive UI for demonstrating this guardrail. The app should be placed in the same `presidio_guardrail/` directory and import from `actions.py`.

---

## File to Create: `streamlit_app.py`

### Page Configuration

```python
st.set_page_config(
    page_title="Presidio × NeMo Guardrails",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

---

## Layout: Three Main Sections

The app has a **sidebar** for controls, and the **main area** split into two tabs: "Scanner" (the primary demo) and "Chat Simulation" (shows guardrail in a conversation context).

---

## Section 1: Sidebar — Interactive Controls

### 1A: Confidence Threshold Slider

- Label: "Confidence Threshold"
- Range: 0.0 to 1.0, step 0.05, default 0.5
- Help text: "Minimum confidence score to flag an entity. Lower = catches more but may have false positives."
- This value must be passed to the Presidio analyzer dynamically. Do NOT modify the global `CONFIDENCE_THRESHOLD` constant. Instead, call `analyzer.analyze()` directly with `score_threshold=` set to the slider value. This means the app needs its own scan function that accepts threshold as a parameter rather than using the module-level `detect_pii()` directly.

### 1B: Entity Type Checkboxes

- Header: "Entity Types to Detect"
- Show a checkbox for each entity in `DETECT_ENTITIES`, all checked by default.
- Add a "Select All / Deselect All" toggle above the checkboxes.
- The selected entities list gets passed to `analyzer.analyze(entities=selected_entities)`.

### 1C: Quick Info

- A small `st.info()` box at the bottom of the sidebar:
  - "Powered by Microsoft Presidio + spaCy en_core_web_lg"
  - "Integrated with NVIDIA NeMo Guardrails"

---

## Section 2: Scanner Tab (Main Demo)

This is the primary view your boss sees. It has these sub-sections from top to bottom:

### 2A: Header

- Title: "🛡️ Sensitive Data Detection Guardrail"
- Subtitle in muted text: "Presidio PII detection integrated with NeMo Guardrails — interactive prototype"

### 2B: Sample Message Buttons

- A row of `st.button()` elements (use `st.columns()` to lay them out horizontally).
- Each button pre-fills the text input with a sample message.
- Use these exact samples:

```python
SAMPLES = {
    "📧 Email + Name": "Hi, my name is Sarah Connor and my email is sarah@skynet.com.",
    "💳 Credit Card": "Please charge credit card 4532-0158-2367-9801, expiry 09/26.",
    "🔢 SSN + Address": "My SSN is 276-49-1832 and I live at 742 Evergreen Terrace, Springfield.",
    "📞 Phone + URL": "Call me at (212) 555-0147 or visit https://myportfolio.dev/resume.",
    "👤 Multi-PII": "Patient Robert Garcia, DOB 03/15/1987, email robert.garcia@outlook.com, phone (503) 555-0198.",
    "✅ Clean Text": "The quarterly report shows 15% growth across all EMEA markets.",
}
```

- When a sample button is clicked, store the sample text in `st.session_state.input_text` and use that as the default value of the text area.

### 2C: Text Input Area

- `st.text_area()` with placeholder: "Type or paste text to scan for PII..."
- Height: 120px
- The value should be bound to `st.session_state.input_text`.

### 2D: Scan Button

- `st.button("🔍 Scan for Sensitive Data", type="primary", use_container_width=True)`
- Clicking this triggers the Presidio analysis using the sidebar's threshold and entity type selections.

### 2E: Results Section (only visible after scanning)

After scanning, display results in this order:

#### Metric Cards Row

Use `st.columns(4)` to show four metric cards:

1. **Entities Found** — count of detected entities. Show in red if > 0, green if 0.
2. **Entity Types** — count of unique entity types found.
3. **Confidence Range** — min–max score range of detected entities (e.g., "0.78 – 0.99"), or "N/A" if clean.
4. **Guardrail Action** — "🚫 BLOCKED" (red) if entities found, "✅ PASSED" (green) if clean.

Use `st.metric()` for each.

#### If PII was detected:

**Detected PII Panel** — use `st.markdown()` with `unsafe_allow_html=True` to render the original text with PII spans highlighted. For each detected entity:
- Wrap the entity text in a `<span>` with:
  - Red background: `background-color: rgba(220, 38, 38, 0.12); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 4px; padding: 1px 4px;`
  - A small superscript tag showing the entity type: `<sup style="color: #dc2626; font-size: 10px; font-weight: 600;">ENTITY_TYPE</sup>`
- Build this by iterating through entities sorted by start position (descending, so replacements don't shift offsets) and injecting the HTML spans.
- Wrap the whole thing in a container div with monospace font, light gray background, and padding.

**Redacted Output Panel** — show the redacted text where each PII span is replaced with a styled placeholder:
- Use blue styling for placeholders: `background-color: rgba(37, 99, 235, 0.1); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 4px; padding: 1px 6px; color: #2563eb; font-weight: 600; font-size: 12px;`
- Build this similarly to the highlighted text, but replace entity text with `<ENTITY_TYPE>` in the styled span.

**Entity Detail Table** — use `st.dataframe()` to show a table of all detected entities with columns:
- Entity Type
- Detected Text
- Confidence Score (formatted as percentage, e.g., "97%")
- Position (start–end character indices)

Sort by confidence score descending.

#### If text is clean:

- Show `st.success("✅ No sensitive data detected — message passes through to LLM")` in a prominent box.

---

## Section 3: Chat Simulation Tab

This tab simulates a real conversation where the guardrail intervenes. It uses Streamlit's chat UI components.

### How it works:

- Store chat history in `st.session_state.chat_history` as a list of dicts: `{"role": "user" | "assistant" | "guardrail", "content": str}`.
- Show a `st.chat_input("Type a message...")` at the bottom.
- When the user sends a message:
  1. Add it to chat history as role "user".
  2. Run PII detection on it (using sidebar threshold and entity selections).
  3. If PII found:
     - Add a "guardrail" message: "⚠️ **Guardrail triggered** — Detected: {comma-separated entity types}. Message blocked."
     - Show the redacted version in a collapsed `st.expander("View redacted version")` within the guardrail message.
     - Do NOT generate an assistant response (the LLM never sees the message).
  4. If clean:
     - Add a simulated "assistant" response. Use a hardcoded set of generic helpful responses:
       ```python
       ASSISTANT_RESPONSES = [
           "I'd be happy to help with that! Let me look into it for you.",
           "That's a great question. Based on the information provided...",
           "Sure, I can assist with that. Here's what I found...",
           "Thanks for your question! Let me provide some details...",
           "Absolutely, here's what you need to know about that topic...",
       ]
       ```
     - Pick one at random (or cycle through them).
- Render the full chat history using `st.chat_message()`:
  - "user" messages: standard user avatar
  - "assistant" messages: standard assistant avatar
  - "guardrail" messages: use `st.chat_message("guardrail", avatar="🛡️")` with a red-tinted warning style

### Chat tab also has:

- A "Clear Chat" button at the top right.
- A small info banner: "This simulates how the guardrail works in a real LLM conversation. Try sending messages with PII to see the guardrail intervene."

---

## Custom CSS

Inject custom CSS at the top of the app using `st.markdown()` with `unsafe_allow_html=True` to:

- Style the metric cards with slightly more padding.
- Add a subtle top border accent to the main content area.
- Make the guardrail chat messages have a light red/orange background tint to visually distinguish them.
- Ensure the highlighted PII text container has proper line-height and padding for readability.

Keep the CSS minimal — Streamlit's default theme is already clean. Just add accents for the guardrail-specific elements.

---

## Technical Requirements

### Imports from actions.py

The app should import:
```python
from actions import get_analyzer, get_anonymizer, DETECT_ENTITIES
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
```

### Custom scan function

Because the sidebar controls threshold and entity types dynamically, create a local function in the Streamlit app:

```python
def scan_text(text: str, threshold: float, entities: list[str]) -> tuple[list[dict], str]:
    """
    Run Presidio analysis with custom threshold and entity list.
    Returns (entities_list, redacted_text).
    """
    analyzer = get_analyzer()
    anonymizer = get_anonymizer()

    results = analyzer.analyze(
        text=text,
        entities=entities,
        language="en",
        score_threshold=threshold,
    )

    entities_found = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 2),
            "text": text[r.start:r.end],
        }
        for r in results
    ]

    operators = {
        entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
        for entity in entities
    }

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    return entities_found, anonymized.text
```

### Session State Initialization

At the top of the app, initialize:
```python
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
```

### Caching

Use `@st.cache_resource` to cache the Presidio engine initialization:
```python
@st.cache_resource
def load_engines():
    """Load Presidio engines once and cache across reruns."""
    return get_analyzer(), get_anonymizer()
```

This prevents the spaCy model from reloading on every Streamlit rerun.

---

## HTML Builder Functions

Create two helper functions for building the highlighted and redacted HTML:

### `build_highlighted_html(text, entities)`

- Sort entities by `start` position descending (process right-to-left so offset replacements don't cascade).
- For each entity, replace `text[start:end]` with:
  ```html
  <span style="background-color: rgba(220,38,38,0.12); border: 1px solid rgba(220,38,38,0.3); border-radius: 4px; padding: 1px 4px;">
    ORIGINAL_TEXT<sup style="color: #dc2626; font-size: 10px; font-weight: 600; margin-left: 2px;">ENTITY_TYPE</sup>
  </span>
  ```
- HTML-escape the non-entity portions of the text to prevent XSS.
- Wrap the final result in:
  ```html
  <div style="font-family: monospace; font-size: 14px; line-height: 2; padding: 16px; background-color: #f8f8f8; border-radius: 8px; border: 1px solid #e0e0e0;">
    {html_content}
  </div>
  ```

### `build_redacted_html(text, entities)`

- Same right-to-left processing as above.
- Replace each entity span with:
  ```html
  <span style="background-color: rgba(37,99,235,0.1); border: 1px solid rgba(37,99,235,0.2); border-radius: 4px; padding: 1px 6px; color: #2563eb; font-weight: 600; font-size: 12px;">
    &lt;ENTITY_TYPE&gt;
  </span>
  ```
- Same wrapper div as the highlighted version.

---

## Dependencies

Add `streamlit` to `requirements.txt`. The app should work with:
```
streamlit>=1.30.0
```

All other dependencies (presidio-analyzer, presidio-anonymizer, spacy) are already in the existing requirements.txt.

---

## Running the App

The app runs with:
```bash
streamlit run streamlit_app.py
```

---

## Style and UX Guidelines

- Use `st.divider()` between major sections for visual separation.
- Use `st.caption()` for help text and explanations.
- Use `st.columns()` for horizontal layouts (metric cards, sample buttons).
- Wrap the PII highlighted text and redacted text in `st.container()` with clear labels using `st.subheader()`.
- Add a small loading spinner (`st.spinner("Scanning...")`) around the Presidio analysis call.
- In the entity detail table, color the confidence score column: green for > 0.9, yellow for 0.7–0.9, red for < 0.7. Use `st.dataframe()` with column config for this.
- Make the "Scan" button prominent and full-width.
- Keep the Scanner tab as the default active tab.

---

## Error Handling

- Wrap the Presidio engine loading in a try/except. If spaCy model isn't installed, show:
  ```python
  st.error("⚠️ spaCy model not found. Run: python -m spacy download en_core_web_lg")
  st.stop()
  ```
- If the text area is empty when "Scan" is clicked, show `st.warning("Please enter some text to scan.")`.
- Handle any Presidio analysis errors gracefully with `st.error()`.

---

## Complete Feature Checklist

Make sure all of these are implemented:

- [ ] Page config with title, icon, wide layout
- [ ] Sidebar: confidence threshold slider (0.0–1.0, step 0.05, default 0.5)
- [ ] Sidebar: entity type checkboxes with select all/deselect all
- [ ] Sidebar: info box about Presidio + NeMo
- [ ] Scanner tab: title and subtitle
- [ ] Scanner tab: 6 sample message buttons in a horizontal row
- [ ] Scanner tab: text area input (120px height)
- [ ] Scanner tab: full-width primary scan button
- [ ] Scanner tab: 4 metric cards (entities found, types, confidence range, action)
- [ ] Scanner tab: highlighted text with red PII spans and superscript type labels
- [ ] Scanner tab: redacted text with blue entity type placeholders
- [ ] Scanner tab: entity detail table with type, text, score, position
- [ ] Scanner tab: success message for clean text
- [ ] Chat tab: chat interface with st.chat_message and st.chat_input
- [ ] Chat tab: guardrail intervention with shield avatar and warning styling
- [ ] Chat tab: redacted version in expander within guardrail messages
- [ ] Chat tab: simulated assistant responses for clean messages
- [ ] Chat tab: clear chat button
- [ ] Chat tab: info banner explaining the simulation
- [ ] Cached engine loading with @st.cache_resource
- [ ] Session state for input text, scan results, chat history
- [ ] Error handling for missing spaCy model
- [ ] Custom CSS for guardrail message styling
- [ ] Loading spinner during analysis
