#!/usr/bin/env python3
# Streamlit front end for Voyager Shoes agents

import json
import os
import time
import streamlit as st

# Import your agents from main.py (must be in the same folder)
from main import (
    campaign_planner_agent,
    brand_consistency_agent,
    instagram_creator_agent,
    BRAND_GUIDE_PATH_DEFAULT,  # path to ./brand_guideline.txt (resolved in main.py)
)

st.set_page_config(page_title="Voyager Campaign Assistant", page_icon="🟦", layout="wide")

# --- Sidebar: Environment / status -------------------------------------------------
st.sidebar.title("⚙️ Settings")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
st.sidebar.write(f"**Model:** `{MODEL}`")
st.sidebar.write(f"**Ollama host:** `{HOST}`")

# Brand guideline preview
with st.sidebar.expander("📘 brand_guideline.txt (preview)"):
    try:
        with open(BRAND_GUIDE_PATH_DEFAULT, "r", encoding="utf-8") as f:
            st.code(f.read(), language="markdown")
    except FileNotFoundError:
        st.warning("brand_guideline.txt not found next to main.py")

st.sidebar.info("Make sure Ollama is running and the model is pulled (e.g., `ollama pull llama3.1`).")

# --- Main header -------------------------------------------------------------------
st.title("🟦 Voyager Shoes — Campaign Assistant")
st.caption("Campaign Planner → Brand Consistency → Instagram Creator")

# --- Inputs ------------------------------------------------------------------------
with st.form("inputs"):
    st.subheader("Inputs")
    goal = st.text_input("Goal", value="Grow email signups ahead of the derby weekend.")
    audience = st.text_input("Audience", value="Urban 18–34 sneaker fans who watch Premier League highlights on mobile.")
    football_moment = st.text_input("Football moment", value="Derby weekend buildup (Fri–Sun) and matchday rituals.")
    draft_ideas_text = st.text_area(
        "Draft ideas (one per line)",
        value="UGC challenge: 'matchday steps' to the stadium\n"
              "Limited-time colorway inspired by home/away kits\n"
              "Fan podcast mini-segment about pre-match routines",
        height=120,
    )
    submitted = st.form_submit_button("▶️ Run Agents")

# Helper to split draft ideas safely
def _to_list(multiline: str):
    lines = [ln.strip() for ln in (multiline or "").splitlines()]
    return [ln for ln in lines if ln]

# --- Run the pipeline --------------------------------------------------------------
if submitted:
    draft_ideas = _to_list(draft_ideas_text)
    progress = st.progress(0)
    timings = []

    # ---------- Agent 1: Campaign Planner ----------
    st.subheader("1) Campaign Planner Agent")
    st.write("**What it does:**")
    st.markdown(
        "- Creates concise **messaging** aligned to your inputs\n"
        "- Generates **exactly 3 creative hooks** (emotional, aspirational, fun/sporty)\n"
        "- Defines up to **3 personas** (with motivations)\n"
    )

    t0 = time.perf_counter()
    with st.spinner("Running Campaign Planner Agent…"):
        try:
            draft = campaign_planner_agent(goal, audience, football_moment, draft_ideas)
            dur = time.perf_counter() - t0
            timings.append({"Agent": "Campaign Planner", "Duration (s)": round(dur, 2)})
            st.success(f"Done in {dur:.2f} seconds")
            with st.expander("🔎 Draft Campaign Brief (JSON)"):
                st.json(draft)
        except Exception as e:
            st.error(f"Campaign Planner Agent failed: {e}")
            st.stop()
    progress.progress(33)

    # ---------- Agent 2: Brand Consistency ----------
    st.subheader("2) Brand Consistency Agent")
    st.write("**What it does:**")
    st.markdown(
        "- Aligns draft with **brand guideline** (tone, palette, typography, visual mood)\n"
        "- Strengthens **messaging** and **hooks** to match brand voice\n"
        "- Produces **visuals** (fonts, colors, imagery) and a unified **tagline**\n"
    )

    t1 = time.perf_counter()
    with st.spinner("Running Brand Consistency Agent…"):
        try:
            polished = brand_consistency_agent(draft_campaign_brief=draft, guideline_path=BRAND_GUIDE_PATH_DEFAULT)
            dur = time.perf_counter() - t1
            timings.append({"Agent": "Brand Consistency", "Duration (s)": round(dur, 2)})
            st.success(f"Done in {dur:.2f} seconds")
            with st.expander("🔎 Polished Campaign Brief (JSON)"):
                st.json(polished)
        except Exception as e:
            st.error(f"Brand Consistency Agent failed: {e}")
            st.stop()
    progress.progress(66)

    # ---------- Agent 3: Instagram Creator ----------
    st.subheader("3) Instagram Creator Agent")
    st.write("**What it does:**")
    st.markdown(
        "- Crafts an **Instagram-ready caption**:\n"
        "  - Hero line (3–6 words)\n"
        "  - 1–2 short subtext lines + soft CTA\n"
        "  - **Exactly 2 hashtags** (1 brand + 1 thematic)\n"
        "- Generates a single **image prompt** that matches the caption and brand visuals\n"
    )

    t2 = time.perf_counter()
    with st.spinner("Running Instagram Creator Agent…"):
        try:
            instagram = instagram_creator_agent(polished_campaign_brief=polished, guideline_path=BRAND_GUIDE_PATH_DEFAULT)
            dur = time.perf_counter() - t2
            timings.append({"Agent": "Instagram Creator", "Duration (s)": round(dur, 2)})
            st.success(f"Done in {dur:.2f} seconds")
            with st.expander("🔎 Instagram Output (JSON)"):
                st.json(instagram)
        except Exception as e:
            st.error(f"Instagram Creator Agent failed: {e}")
            st.stop()
    progress.progress(100)

    # ---------- Final Output + Timings ----------
    st.markdown("---")
    st.header("✅ Final Instagram Post")
    caption = instagram.get("instagram_post", {}).get("caption", "").strip()
    image_prompt = instagram.get("instagram_post", {}).get("image_prompt", "").strip()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Caption")
        st.text_area("Instagram Caption", caption, height=220)
    with col2:
        st.subheader("Image Prompt")
        st.text_area("Image Generation Prompt", image_prompt, height=220)

    st.download_button(
        label="💾 Download instagram_post.json",
        data=json.dumps(instagram, indent=2, ensure_ascii=False),
        file_name="instagram_post.json",
        mime="application/json",
    )

    st.subheader("⏱️ Agent Timings")
    st.table(timings)
else:
    st.info("Fill the inputs above and click **Run Agents** to generate your campaign!")
