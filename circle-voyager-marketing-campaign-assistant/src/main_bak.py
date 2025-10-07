#!/usr/bin/env python3
"""
Marketing Campaign Assistant

An AI agent that:
1. Generate marketing campaign brief.
2. Adjusts the brief with brand guidelines.
3. Create Instagram posts based on the brief and brand guidelines.
4. Create X (Twitter) posts based on the brief and brand guidelines.
5. Create LinkedIn posts based on the brief and brand guidelines.
6. Create Facebook posts based on the brief and brand guidelines.

Usage: 
    python main.py                                      # Run the agent
    python main.py --evaluate all                       # Run full evaluation
    python main.py --evaluate accuracy,bias_detection   # Run specific evaluators
"""

# Requirements: pip install openai
# env: export OPENAI_API_KEY="sk-..."

from typing import List, Dict
import re
import json
from typing import Dict, List, Optional
import os
from openai import OpenAI

# ---------------- OpenAI API Key Configuration ----------------
# ⚠️ NOTE: This is for local testing ONLY. Do not commit or share this file with the key inside.
OPENAI_API_KEY = ""

# Make sure the key is visible to the OpenAI client
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# ---------------- campaign_planner_agent (brand-agnostic) ----------------

def campaign_planner_agent(goal: str, audience: str, football_moment: str, draft_ideas: List[str]) -> Dict:
   
    """
    Turn inputs into a minimal strategic campaign brief (brand-neutral).

    Input:
        goal (str): campaign goal
        audience (str): target audience
        football_moment (str): football-related context or timing
        draft_ideas (list[str]): list of creative idea drafts
    Output:
        dict: structured campaign brief
    """

    # Derive objective and KPI in the simplest way
    g = (goal or "").lower()

    if any(k in g for k in ["awareness", "reach", "launch"]):
        objective = "Increase brand awareness and reach."
        kpi = "Impressions, Reach, Video Views"
    elif any(k in g for k in ["engagement", "community", "ugc"]):
        objective = "Boost engagement and user participation."
        kpi = "Engagement Rate, UGC Volume, Shares"
    elif any(k in g for k in ["conversion", "sale", "purchase"]):
        objective = "Drive conversions and sales."
        kpi = "Conversion Rate, Sales Volume"
    else:
        objective = "Strengthen brand connection and affinity."
        kpi = "Positive Sentiment, Brand Mentions"

    # Basic messaging logic
    messaging = (
        f"Goal: {goal}. Audience: {audience}. Context: {football_moment}. "
        f"Core Message: Football is more than a game — it’s a journey."
    )

    # Create quick hooks, personas, and channels
    creative_hooks = draft_ideas[:3] if draft_ideas else [
        "Show the journey.",
        "Highlight passion.",
        "Celebrate every step."
    ]
    
    personas = [{
        "name": "Football Enthusiast",
        "description": "Active players and fans who see football as a path to growth and achievement."
    }]

    # Final structured brief
    return {
        "campaign_brief": {
            "messaging": messaging,
            "creative_hooks": creative_hooks,
            "personas": personas,
            "objective": objective,
            "kpi": kpi
        }
    }

# ---------------- brand_consistency_agent ----------------

def brand_consistency_agent(raw_brief: Dict, brand_guideline_path: str) -> Dict:
    """
    Align a raw campaign brief with a brand guideline text file and return a polished brief containing ONLY the requested fields.
    
    Input:
        raw_brief (dict): raw campaign brief from campaign_planner_agent
        brand_guideline_path (str): path to brand guideline text file
    Output:
        dict: polished campaign brief with brand-aligned messaging, hooks, visuals, and tagline
    """
    
    # Load guideline text (if not found, proceed with sensible defaults)
    try:
        with open(brand_guideline_path, "r", encoding="utf-8") as f:
            guide = f.read()
    except FileNotFoundError:
        guide = ""

    # Extract brand cues (very lightweight parsing)
    # Colors (HEX)
    hex_colors = list(dict.fromkeys(re.findall(r"#(?:[0-9A-Fa-f]{3}){1,2}\b", guide)))
    colors = ", ".join(hex_colors[:5]) if hex_colors else "#0B1E40, #F5B500, #FFFFFF"

    # Fonts (common families)
    font_families = ["Montserrat", "Bebas Neue", "Oswald", "Open Sans", "Lato", "Roboto", "Raleway", "Playfair", "Playfair Display"]
    found_fonts = [fam for fam in font_families if re.search(rf"\b{re.escape(fam)}\b", guide, re.IGNORECASE)]
    fonts = ", ".join(dict.fromkeys(found_fonts)) if found_fonts else "Bold Sans-Serif (headline), Clean Sans-Serif (body)"

    # Tagline
    tagline = ""
    m = re.search(r"Tagline:\s*[“\"']?(.+?)[”\"']?\s*(?:\n|$)", guide, re.IGNORECASE)
    if m:
        tagline = m.group(1).strip()
    if not tagline:
        # Fallback: look for a quoted journey/exploration line
        m2 = re.search(r"[“\"'](.+?(exploration|journey).+?)[”\"']", guide, re.IGNORECASE)
        if m2:
            tagline = m2.group(1).strip()

    # Imagery keywords
    imagery_vocab = [
        "cinematic", "sunrise", "sunset", "golden", "motion", "movement", "horizon",
        "turf", "grass", "dust", "light", "silhouette", "close-up", "low-angle",
        "grit", "authentic", "dynamic", "exploration", "journey"
    ]
    imagery_found = [w for w in imagery_vocab if re.search(rf"\b{w}\b", guide, re.IGNORECASE)]
    imagery = ", ".join(imagery_found[:6]) if imagery_found else "cinematic, motion, horizon"

    # Raw inputs
    cb = raw_brief.get("campaign_brief", {})
    raw_msg = cb.get("messaging", "")
    raw_hooks = cb.get("creative_hooks", []) or []

    # Messaging (append tagline if not present)
    messaging = raw_msg or "Football is a journey—show progress, grit, and milestone moments."
    if tagline and tagline not in messaging:
        messaging = f"{messaging} Tagline: {tagline}"

    # Top 3 hooks, deduped
    cleaned = []
    for h in raw_hooks:
        h_clean = re.sub(r"\s+", " ", str(h)).strip()
        if h_clean and h_clean not in cleaned:
            cleaned.append(h_clean)
    creative_hooks = cleaned[:3] if cleaned else ["Show the journey.", "Highlight passion.", "Celebrate every step."]

    # Build final polished brief (ONLY requested fields)
    return {
        "polished_campaign_brief": {
            "messaging": messaging,
            "creative_hooks": creative_hooks,
            "visuals": {
                "fonts": fonts,
                "colors": colors,
                "imagery": imagery
            },
            "tagline": tagline or ""
        }
    }

# ---------- Helpers for post generation (OpenAI) ----------
def _compose_prompt(channel: str, polished_campaign_brief: Dict) -> str:
    pcb = polished_campaign_brief.get("polished_campaign_brief", {})
    messaging = pcb.get("messaging", "")
    tagline = pcb.get("tagline", "")
    hooks = pcb.get("creative_hooks", []) or []
    visuals = pcb.get("visuals", {})
    tone = pcb.get("tone", [])
    hashtags = pcb.get("hashtags", [])

    # Channel-specific guidance
    if channel == "instagram":
        platform_rules = (
            "Cinematic, inspiring caption (<= 150 words). Short lines, tasteful emojis OK. "
            "Soft nudge, no hard sell. Hashtags: 3–6, relevant and on-brand."
        )
    elif channel == "x":
        platform_rules = (
            "High-impact concise post (<= 250 characters). One strong line + short kicker. "
            "Emojis minimal. Hashtags: 1–3 only."
        )
    elif channel == "linkedin":
        platform_rules = (
            "Professional, inspirational caption (2–4 short paragraphs, <= 120 words). "
            "Focus on craft, mindset, learning. Emojis rare/subtle. Hashtags: 2–4 thoughtful tags."
        )
    elif channel == "facebook":
        platform_rules = (
            "Warm, community-forward caption (1–3 short paragraphs, <= 100 words). "
            "Invite comments or stories; no hard sell. Hashtags: 2–4 relevant."
        )
    else:
        platform_rules = "Concise, on-brand caption with 2–4 relevant hashtags."

    visual_guide = (
        "Also provide one sentence 'Visual Idea' to brief an image generator using imagery/color cues. "
        "No camera tech jargon."
    )

    return f"""
You are a social copywriter creating a post for: {channel.upper()}.

Inputs:
- Messaging: {messaging}
- Tagline: {tagline}
- Creative Hooks: {", ".join(hooks[:5])}
- Visuals: fonts={visuals.get("fonts","")}; colors={visuals.get("colors","")}; imagery={visuals.get("imagery","")}
- Tone: {", ".join(tone) if tone else "adventurous, empowering, authentic, confident"}
- Suggested Hashtags: {", ".join(hashtags[:8]) if hashtags else "(none provided)"}

Rules:
{platform_rules}
{visual_guide}

Task:
Return JSON ONLY with:
{{
  "post_caption": "string",
  "post_visual_idea": "string",
  "hashtags": ["string", "string"]
}}
""".strip()

def _call_openai_for_post(prompt: str, model: Optional[str] = None) -> Dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    use_model = model or "gpt-4o-mini"

    resp = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": "You are a precise content generator. Output strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=400,
    )

    content = resp.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        # Fallback if the model returns non-JSON (keeps flow simple)
        return {
            "post_caption": content,
            "post_visual_idea": "Cinematic action image showing movement and exploration in brand colors.",
            "hashtags": [],
        }

def _build_output(channel: str, payload: Dict) -> Dict:
    return {
        "channel": channel,
        "post_content": {
            "post_caption": payload.get("post_caption", ""),
            "post_visual_idea": payload.get("post_visual_idea", ""),
            "hashtags": payload.get("hashtags", [])[:6],
        },
    }

# ---------------- instagram_post_creator_agent ----------------
def instagram_post_creator_agent(polished_campaign_brief: Dict, model: Optional[str] = None) -> Dict:
    prompt = _compose_prompt("instagram", polished_campaign_brief)
    payload = _call_openai_for_post(prompt, model=model)
    # Ensure 3–6 hashtags
    if len(payload.get("hashtags", [])) < 3:
        payload["hashtags"] = (payload.get("hashtags") or []) + ["#FootballJourney", "#EveryStepIsAnExploration", "#VoyagerShoes"]
    payload["hashtags"] = payload["hashtags"][:6]
    return _build_output("instagram", payload)


# ---------------- x_post_creator_agent ----------------
def x_post_creator_agent(polished_campaign_brief: Dict, model: Optional[str] = None) -> Dict:
    prompt = _compose_prompt("x", polished_campaign_brief)
    payload = _call_openai_for_post(prompt, model=model)
    # Max 3 hashtags for X
    payload["hashtags"] = (payload.get("hashtags") or [])[:3]
    return _build_output("x", payload)


# ---------------- linkedin_post_creator_agent ----------------
def linkedin_post_creator_agent(polished_campaign_brief: Dict, model: Optional[str] = None) -> Dict:
    prompt = _compose_prompt("linkedin", polished_campaign_brief)
    payload = _call_openai_for_post(prompt, model=model)
    # Keep hashtags tidy (2–4)
    payload["hashtags"] = (payload.get("hashtags") or [])[:4]
    return _build_output("linkedin", payload)


# ---------------- facebook_post_creator_agent ----------------
def facebook_post_creator_agent(polished_campaign_brief: Dict, model: Optional[str] = None) -> Dict:
    prompt = _compose_prompt("facebook", polished_campaign_brief)
    payload = _call_openai_for_post(prompt, model=model)
    # Keep hashtags tidy (2–4)
    payload["hashtags"] = (payload.get("hashtags") or [])[:4]
    return _build_output("facebook", payload)

# --------------- Demo (runs only when this file is executed directly) ---------------
if __name__ == "__main__":
    raw = campaign_planner_agent(
        goal="Drive awareness for the new football boot launch",
        audience="Young football players aged 16-25",
        football_moment="Start of the league season",
        draft_ideas=[
            "Launch teaser video of players preparing for kickoff.",
            "Fan challenge: show your 'first step' moment.",
            "Behind-the-scenes with team captains."
        ]
    )

    # Replace with your actual guideline path
    guideline_path = "brand_guideline.txt"
    try:
        with open(guideline_path, "r", encoding="utf-8") as _:
            pass
    except FileNotFoundError:
        # Minimal fallback file
        with open(guideline_path, "w", encoding="utf-8") as f:
            f.write("Brand Name: Voyager Shoes\n"
                    "Tagline: \"Every step is an exploration.\"\n"
                    "Colours: #0B1E40, #F5B500, #FFFFFF, #7C8BA1, #3B7D3C\n"
                    "Fonts: Montserrat, Bebas Neue, Oswald, Open Sans, Lato, Roboto, Raleway, Playfair\n"
                    "Imagery: cinematic, sunrise, motion, horizon, turf, light, silhouette\n")

    polished = brand_consistency_agent(raw, guideline_path)

    print("\n--- Example Posts ---")
    ig = instagram_post_creator_agent(polished)
    tw = x_post_creator_agent(polished)
    li = linkedin_post_creator_agent(polished)
    fb = facebook_post_creator_agent(polished)

    print(json.dumps(ig, indent=2, ensure_ascii=False))
    print(json.dumps(tw, indent=2, ensure_ascii=False))
    print(json.dumps(li, indent=2, ensure_ascii=False))
    print(json.dumps(fb, indent=2, ensure_ascii=False))

    #print(json.dumps(raw, indent=2, ensure_ascii=False)) 
    #print("------------------------------")  
    print(json.dumps(polished, indent=2, ensure_ascii=False))