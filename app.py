# app.py
from __future__ import annotations

import requests
import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"


# ----------------------------
# Helpers
# ----------------------------
def call_generate_summary(api_url: str, patient_id: int, use_llm: bool, model: str) -> dict:
    url = f"{api_url.rstrip('/')}/generate_summary"
    payload = {"patient_id": patient_id, "use_llm": use_llm, "model": model}

    resp = requests.post(url, json=payload, timeout=180)

    if resp.status_code != 200:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f"API Error {resp.status_code}: {err}")

    return resp.json()


def extract_citations(text: str) -> list[str]:
    """
    Extracts citation-looking chunks like [Source: ...] from the summary.
    Simple heuristic: pull all bracketed segments containing 'Source:'.
    """
    if not text:
        return []
    out = []
    start = 0
    while True:
        i = text.find("[Source:", start)
        if i == -1:
            break
        j = text.find("]", i)
        if j == -1:
            break
        out.append(text[i : j + 1])
        start = j + 1

    # unique while preserving order
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def set_hospital_theme():
    st.markdown(
        """
        <style>
            /* Page background */
            .stApp {
                background: radial-gradient(circle at 15% 20%, rgba(0, 170, 255, 0.10), transparent 45%),
                            radial-gradient(circle at 85% 10%, rgba(0, 255, 204, 0.08), transparent 45%),
                            linear-gradient(180deg, #0b1220 0%, #070b13 100%);
                color: #E6EEF9;
            }

            /* Remove top padding a bit */
            .block-container { padding-top: 1.5rem; }

            /* Inputs */
            input, textarea {
                border-radius: 12px !important;
            }

            /* Buttons */
            div.stButton > button {
                border-radius: 14px;
                padding: 0.7rem 1.1rem;
                font-weight: 600;
                border: 1px solid rgba(255,255,255,0.12);
                background: linear-gradient(135deg, rgba(0,170,255,0.85), rgba(0,255,204,0.65));
                color: #061019;
                transition: 0.15s;
            }
            div.stButton > button:hover {
                transform: translateY(-1px);
                filter: brightness(1.05);
            }

            /* Cards */
            .card {
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 18px;
                padding: 18px 18px 12px 18px;
                background: rgba(255,255,255,0.04);
                box-shadow: 0 12px 30px rgba(0,0,0,0.25);
            }

            /* Small badge */
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                border: 1px solid rgba(255,255,255,0.14);
                background: rgba(255,255,255,0.06);
                font-size: 12px;
                margin-right: 8px;
            }

            /* Header */
            .title {
                font-size: 36px;
                font-weight: 800;
                margin: 0;
                letter-spacing: 0.3px;
            }
            .subtitle {
                color: rgba(230,238,249,0.75);
                margin-top: 6px;
                font-size: 14px;
            }

            /* Section headers */
            h2, h3 {
                letter-spacing: 0.2px;
            }

            /* Make sidebar match theme */
            section[data-testid="stSidebar"] {
                background: rgba(255,255,255,0.03) !important;
                border-right: 1px solid rgba(255,255,255,0.08);
            }

            /* Hide Streamlit footer */
            footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# App
# ----------------------------
st.set_page_config(page_title="Clinical Summary Generator", page_icon="🩺", layout="wide")
set_hospital_theme()

# HEADER
st.markdown(
    """
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
                <div class="title">🩺 Clinical Summary Generator</div>
                <div class="subtitle">
                    Evidence-based patient story from CSV EHR data • FastAPI Backend • LLM Summary with citations
                </div>
                <div style="margin-top:12px;">
                    <span class="badge">Hospital UI</span>
                    <span class="badge">Citations Enabled</span>
                    <span class="badge">FastAPI + Streamlit</span>
                </div>
            </div>
            <div style="text-align:right; opacity:0.9;">
                <div style="font-weight:700; font-size:14px;">Status</div>
                <div style="font-size:12px; color:rgba(230,238,249,0.72);">Backend must be running</div>
                <div style="margin-top:8px; font-size:12px;">
                    <code style="background:rgba(255,255,255,0.06); padding:6px 10px; border-radius:12px;">
                        uvicorn main:app --reload
                    </code>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# SIDEBAR
st.sidebar.header("⚙️ Configuration")
api_url = st.sidebar.text_input("FastAPI Base URL", DEFAULT_API_URL)
st.sidebar.markdown("---")
use_llm = st.sidebar.toggle("Use LLM", value=True)
model = st.sidebar.text_input("Model", value="gpt-4o-mini")
st.sidebar.markdown("---")
st.sidebar.caption("Tip: For cheapest testing, try gpt-5-nano. If it fails, fall back to gpt-4o-mini.")

# MAIN LAYOUT
left, right = st.columns([1.05, 1.45], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧾 Patient Input")

    patient_id = st.number_input("Patient ID", min_value=1, step=1, value=1002)

    st.markdown("")
    generate = st.button("Generate Clinical Summary", use_container_width=True)

    st.markdown("")
    st.caption("This will call FastAPI: POST `/generate_summary` and display the generated summary with citations.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Quick Notes")
    st.markdown(
        """
- **Primary goal:** tell the patient's clinical story.
- **Citations:** appear like `[Source: vitals.csv | visit_date=...]`
- **Bonus marks:** include evidence with dates & files.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 Generated Output")

    if "result" not in st.session_state:
        st.info("Enter a patient_id and click **Generate Clinical Summary**.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        result = st.session_state["result"]
        summary = result.get("summary", "")
        debug = result.get("debug", {})

        # Status chips
        llm_status = debug.get("llm_status", "unknown")
        ep = debug.get("episode_id", "N/A")

        st.markdown(
            f"""
            <div style="margin-bottom:10px;">
                <span class="badge">Episode: {ep}</span>
                <span class="badge">LLM status: {llm_status}</span>
                <span class="badge">Model: {debug.get('model', 'N/A')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Tabs
        tab1, tab2, tab3 = st.tabs(["📌 Summary", "🔎 Citations", "🧪 Debug"])

        with tab1:
            st.text_area("Clinical Summary", value=summary, height=520)

        with tab2:
            citations = extract_citations(summary)
            if citations:
                st.success(f"Found {len(citations)} citation(s).")
                for c in citations:
                    st.write(f"- {c}")
            else:
                st.warning("No citations detected. (If you used template fallback, citations may be limited.)")

        with tab3:
            st.json(debug)

        st.markdown("</div>", unsafe_allow_html=True)

# ACTION
if generate:
    with st.spinner("Generating clinical summary…"):
        try:
            data = call_generate_summary(api_url, int(patient_id), use_llm, model)
            st.session_state["result"] = data
            st.success("Done ✅")
            st.rerun()

        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to FastAPI backend.")
            st.code("uvicorn main:app --reload", language="bash")

        except Exception as e:
            st.error(f"❌ Error: {e}")
