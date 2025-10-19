# app.py
import os
import json
import time
from io import StringIO
from contextlib import redirect_stdout
import streamlit as st

import main as engine  # run_pipeline, load_brand_guidelines, TOKENS

st.set_page_config(page_title="Marketing Campaign Assistant", layout="wide")

st.title("📣 Marketing Campaign Assistant")
st.caption("Instagram caption + cinematic image prompt — powered by your local Ollama model")

# ---- Sidebar: runtime knobs ----
with st.sidebar:
    st.header("Runtime")
    model = st.text_input("Ollama model", value=getattr(engine, "OLLAMA_MODEL", "phi3:mini"))
    host = st.text_input("Ollama host", value=getattr(engine, "OLLAMA_HOST", "http://127.0.0.1:11434"))
    if st.button("Apply model/host"):
        engine.OLLAMA_MODEL = model
        engine.OLLAMA_HOST = host
        engine.CHAT_URL = f"{host}/api/chat"
        engine.GEN_URL  = f"{host}/api/generate"
        st.success(f"Set model={model} host={host}")

# ---- Brand loader (no upload; read from file in folder) ----
def _load_brand_from_disk():
    # Prefer brand_guideline.json if that's what you have; else default loader
    if os.path.exists("brand_guideline.json"):
        return engine.load_brand_guidelines("brand_guideline.json")
    return engine.load_brand_guidelines()  # default looks for brand_guidelines.json

default_brand = _load_brand_from_disk()

# ---- Defaults ----
default_audience_label = "UK football fans 18–24"
default_locale = "en-GB"
default_paragraph = "Promote Voyager Shoes as the boot for explorers. Focus on the journey."
default_topic = "football"
default_month = "2025-10"

# ---- Input form (no JSON, no file upload) ----
with st.form("campaign_form"):
    st.subheader("Input")
    col1, col2 = st.columns(2)
    with col1:
        audience_label = st.text_input("Target Audience Label", value=default_audience_label)
        locale = st.text_input("Locale (e.g., en-GB)", value=default_locale)
        topic = st.text_input("Topic", value=default_topic)
    with col2:
        month = st.text_input("Month (YYYY-MM)", value=default_month)
        st.text_input("Brand file on disk", value=("brand_guideline.json" if os.path.exists("brand_guideline.json") else "brand_guidelines.json"), disabled=True)

    draft = st.text_area("Campaign Draft Paragraph", value=default_paragraph, height=120)

    run_btn = st.form_submit_button("Generate")

# ---- Run ----
if run_btn:
    sample = {
        "target_audience": {"label": audience_label, "locale": locale},
        "campaign_draft_paragraph": draft,
        "topic": topic,
        "month": month,
        "brand_guidelines": default_brand,
    }

    engine.TOKENS["input"] = 0
    engine.TOKENS["output"] = 0

    buf = StringIO()
    start = time.perf_counter()
    with redirect_stdout(buf):
        try:
            result = engine.run_pipeline(sample)
        except Exception as e:
            print(f"[ERROR] {e}")
            result = {"status": "error", "message": str(e)}
    elapsed = time.perf_counter() - start
    logs = buf.getvalue()

    # ---- Output (form-style, full metadata) ----
    st.subheader("Output")

    if result.get("status") == "error":
        st.error(result.get("message", "Unknown error"))
    else:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Instagram Caption (copy-ready)**")
            st.text_area("", value=result.get("instagram_post_text", ""), height=220, label_visibility="collapsed")

            st.markdown("**Alt Text**")
            st.text_area("", value=result.get("alt_text", ""), height=80, label_visibility="collapsed")

        with c2:
            st.markdown("**Image Generation Prompt**")
            st.text_area("", value=result.get("image_generation_prompt", ""), height=220, label_visibility="collapsed")

            st.markdown("**Metadata**")
            md = result.get("metadata", {}) or {}
            m1, m2, m3 = st.columns([2,2,1])
            m1.text_area("Objective", md.get("objective", ""), height=80, disabled=True)
            m2.text_area("Primary KPI", md.get("primary_kpi", ""), height=80, disabled=True)
            m3.text_input("Trend Source", md.get("trend_source", "n/a"), disabled=True)
            st.checkbox("Constraints applied", value=bool(md.get("constraints_applied", False)), disabled=True)

        # Logs & totals
        st.subheader("Agent timings & token usage")
        st.code(logs or "(no logs)")

        tot_in = engine.TOKENS.get("input", 0)
        tot_out = engine.TOKENS.get("output", 0)
        t1, t2, t3 = st.columns(3)
        t1.metric("Total input tokens", tot_in)
        t2.metric("Total output tokens", tot_out)
        t3.metric("Total elapsed (s)", f"{elapsed:.2f}")

else:
    st.info("Fill the form and click **Generate** to run the pipeline.")

st.caption("Runs your local Ollama model for creative steps; brand/QA enforced in Python.")
