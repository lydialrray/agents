#!/usr/bin/env python3
"""
Marketing Campaign Assistant (Ollama-powered)

What this file provides:
1) campaign_planner_agent(...) -> creates a simple campaign brief JSON
   - fields: messaging, creative_hooks (3), personas (<=3)
2) brand_consistency_agent(...) -> polishes that brief using brand guidelines
   - reads optional text file for guidelines
   - fields: messaging, creative_hooks (3), visuals {fonts, colors, imagery}, tagline

How to run a quick demo:
    python main.py

"""

import json
import os
from typing import List, Dict, Any, Optional

# --- Settings you can change without touching the rest of the code ---
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# ---------------------------------------------------------------------

# Ensure we look for brand_guideline.txt in the SAME folder as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BRAND_GUIDE_PATH_DEFAULT = os.path.join(SCRIPT_DIR, "brand_guideline.txt")

# ========== Small, readable helpers ==================================

def _read_text_file(path: str) -> str:
    """Read a text file if it exists; otherwise return empty string."""
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Safely parse JSON. If the model includes extra text,
    grab the first {...} block and parse that.
    """
    try:
        return json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("Could not parse model output as JSON.")

def _call_ollama(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calls Ollama. Tries the official client; falls back to plain HTTP.
    """
    # A) Try official client first
    try:
        from ollama import Client  # pip install ollama
        client = Client(host=HOST)
        resp = client.chat(model=MODEL, messages=messages, format="json")
        content = resp.get("message", {}).get("content", resp)
        return content if isinstance(content, dict) else _extract_json(content)
    except Exception:
        # B) Fallback to HTTP
        import requests  # pip install requests
        r = requests.post(
            f"{HOST}/api/chat",
            json={"model": MODEL, "messages": messages, "stream": False, "format": "json"},
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", data)
        return content if isinstance(content, dict) else _extract_json(content)


# ========== Agent 1: Campaign Planner (plain brief) ===================

SYSTEM_PROMPT_PLANNER = """
You are the Campaign Planner Agent for Voyager Shoes. 
Your task is turn inputs (goal, audience, football_moment, draft_ideas) into a campaign brief.
Return ONLY valid JSON (no markdown, no extra text) with this exact structure:
{
  "campaign_brief": {
    "messaging": "string",
    "creative_hooks": ["string", "string", "string"],
    "personas": [{"name": "string", "description": "string"}]
  }
}

Rules:
- "messaging" should be between 100 and 200 characters.
- "creative_hooks" must have exactly 3 items, which one is represent emotional, one represent aspirational, one represent fun/sporty.
- "personas" up to 3 maximum; include motivations inside "description".
"""

def _build_planner_user_prompt(goal: str, audience: str, football_moment: str, draft_ideas: List[str]) -> str:
    """
    Turn the raw inputs into a clear prompt for the model.
    """
    ideas = draft_ideas or []
    ideas_text = "\n".join(f"- {i}" for i in ideas) if ideas else "- (none provided)"

    return f"""
Inputs:
- goal: {goal}
- audience: {audience}
- football_moment: {football_moment}
- draft_ideas:
{ideas_text}

Return only the JSON object described above. No extra text.
""".strip()

def campaign_planner_agent(
    goal: str,
    audience: str,
    football_moment: str,
    draft_ideas: List[str],
) -> Dict[str, Any]:
    """
    Build a simple campaign brief JSON.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_PLANNER},
        {"role": "user",   "content": _build_planner_user_prompt(goal, audience, football_moment, draft_ideas)},
    ]
    result = _call_ollama(messages)

    # Light validation (kept easy to read)
    brief = result.get("campaign_brief", {})
    if not isinstance(brief, dict):
        raise ValueError("Missing 'campaign_brief' object.")

    if "messaging" not in brief:
        raise ValueError("Missing 'messaging' in campaign_brief.")

    hooks = brief.get("creative_hooks", [])
    if not isinstance(hooks, list) or len(hooks) != 3:
        raise ValueError("'creative_hooks' must be a list with exactly 3 items.")

    personas = brief.get("personas", [])
    if not isinstance(personas, list):
        raise ValueError("'personas' must be a list (up to 3 recommended).")

    return result


# ========== Agent 2: Brand Consistency (uses ONLY the file) ==========

SYSTEM_PROMPT_BRAND = """
You are the Brand Consistency Agent, acting as Voyager’s Brand Manager. Your goal is to review and refine campaign briefs so they align with Voyager’s brand voice and visual identity as written in the provided brand_guideline.txt.

Return ONLY valid JSON (no markdown, no extra text) with this exact structure:
{
  "polished_campaign_brief": {
    "messaging": "string",
    "creative_hooks": ["string", "string", "string"],
    "visuals": {"fonts": "string", "colors": "string", "imagery": "string"},
    "tagline": "string"
  }
}

Rules:
- "messaging" should be between 100 and 200 characters.
- "creative_hooks" must have exactly 3 items, which one is represent emotional, one represent aspirational, one represent fun/sporty.
- "personas" up to 3 maximum; include motivations inside "description".
- "tagline" should be short (3–6 words), memorable, and reflect the brand’s adventurous and empowering spirit.

Instructions:
- Use ONLY the provided brand guideline text (from the file in the same folder).
- Align with the guideline's: tone of voice and storytelling themes.
- Strengthen messaging and hooks to reflect the brand (adventurous, empowering, authentic, confident).
- Suggest visual style guidance (magery, color palette with hex codes, typography families,
  visual mood) drawn directly from the guideline.
- Ensure a unified tagline and consistent storytelling across personas.
- Keep hooks at exactly 3 items.
"""

def _build_brand_user_prompt(
    draft_campaign_brief: Dict[str, Any],
    guideline_text_from_file: str
) -> str:
    """
    Combine the draft brief + the brand guideline text (from file)
    into a simple prompt for the brand agent.
    """
    draft_json = json.dumps(draft_campaign_brief, ensure_ascii=False, indent=2)
    file_text = guideline_text_from_file.strip() if guideline_text_from_file else "(file missing or empty)"

    return f"""
DRAFT CAMPAIGN BRIEF (JSON):
{draft_json}

BRAND GUIDELINE (from file in same folder):
{file_text}

Return only the JSON object described above. No extra text.
""".strip()

def brand_consistency_agent(
    draft_campaign_brief: Dict[str, Any],
    guideline_path: Optional[str] = BRAND_GUIDE_PATH_DEFAULT
) -> Dict[str, Any]:
    """
    Produce a polished, on-brand version using ONLY the guideline file.
    """
    guideline_text = _read_text_file(guideline_path or "")
    if not guideline_text:
        raise ValueError(
            f"Brand guideline file not found or empty at: {guideline_path}\n"
            "Please create 'brand_guideline.txt' next to main.py."
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_BRAND},
        {"role": "user",   "content": _build_brand_user_prompt(draft_campaign_brief, guideline_text)},
    ]
    result = _call_ollama(messages)

    # Light validation
    polished = result.get("polished_campaign_brief", {})
    if not isinstance(polished, dict):
        raise ValueError("Missing 'polished_campaign_brief' object.")

    if "messaging" not in polished:
        raise ValueError("Missing 'messaging' in polished_campaign_brief.")

    hooks = polished.get("creative_hooks", [])
    if not isinstance(hooks, list) or len(hooks) != 3:
        raise ValueError("'creative_hooks' must be a list with exactly 3 items.")

    visuals = polished.get("visuals", {})
    if not isinstance(visuals, dict) or not all(k in visuals for k in ["fonts", "colors", "imagery"]):
        raise ValueError("Missing visuals details (fonts, colors, imagery).")

    if "tagline" not in polished:
        raise ValueError("Missing 'tagline' in polished_campaign_brief.")

    return result


# ========== Agent 3: Instagram Creator (IG-ready post) ===============

SYSTEM_PROMPT_IG = """
Role: You are the Instagram Creator Agent for Voyager Shoes.
Goal: Turn a polished campaign brief + brand guideline into an Instagram-ready post.

Return ONLY valid JSON (no markdown, no extra text) with this exact structure:
{
  "instagram_post": {
    "caption": "string",
    "image_prompt": "string"
  }
}

Rules for CAPTION:
- Instagram-ready and on-brand.
- Structure:
  1) Hero line: 3–6 words, emotional and strong (brand tone).
  2) Subtext: 1–2 short lines that reflect the polished messaging + tagline.
  3) Soft CTA: motivational (no salesy language).
  4) Hashtags: exactly 2 at the end — 1 brand hashtag and 1 thematic hashtag from the guideline.
- Keep lines short. Avoid corporate or “buy now” tone. Cinematic, empowering, exploratory.

Rules for IMAGE_PROMPT:
- One single prompt string (for an image generator).
- Must reflect the Instagram caption and the brand guideline’s visual identity:
  * Palette (Voyager Blue #0B1E40, Explorer Gold #F5B500, Freedom White #FFFFFF, Journey Grey #7C8BA1, optional Pitch Green #3B7D3C)
  * Visual mood (golden hour lighting, movement, textures like turf/dust)
  * Composition (dynamic/low-angle action, horizon lines, space for hero quote bottom-left)
  * Textures and realism (motion blur, grounded feel)
- Include the scene elements that match the caption (e.g., close-up of boots in motion).
- Do NOT include camera brands; keep it general but vivid and actionable.

Make sure the final JSON includes both fields: 'caption' and 'image_prompt'.
"""

def _build_instagram_user_prompt(
    polished_campaign_brief: Dict[str, Any],
    guideline_text_from_file: str
) -> str:
    """
    Build a simple, self-contained prompt for the Instagram Creator Agent.
    """
    polished_json = json.dumps(polished_campaign_brief, ensure_ascii=False, indent=2)
    file_text = guideline_text_from_file.strip() if guideline_text_from_file else "(file missing or empty)"

    return f"""
POLISHED CAMPAIGN BRIEF (JSON):
{polished_json}

BRAND GUIDELINE (from file in same folder):
{file_text}

Return only the JSON object described above. No extra text.
""".strip()

def instagram_creator_agent(
    polished_campaign_brief: Dict[str, Any],
    guideline_path: Optional[str] = BRAND_GUIDE_PATH_DEFAULT
) -> Dict[str, Any]:
    """
    Create an Instagram-ready post using ONLY the guideline file + polished brief.
    Output shape:
    {
      "instagram_post": {
        "caption": "string",
        "image_prompt": "string"
      }
    }
    """
    guideline_text = _read_text_file(guideline_path or "")
    if not guideline_text:
        raise ValueError(
            f"Brand guideline file not found or empty at: {guideline_path}\n"
            "Please create 'brand_guideline.txt' next to main.py."
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_IG},
        {"role": "user",   "content": _build_instagram_user_prompt(polished_campaign_brief, guideline_text)},
    ]
    result = _call_ollama(messages)

    # Light validation
    ig = result.get("instagram_post", {})
    if not isinstance(ig, dict):
        raise ValueError("Missing 'instagram_post' object.")
    if "caption" not in ig or not isinstance(ig["caption"], str) or not ig["caption"].strip():
        raise ValueError("Missing or empty 'caption' in instagram_post.")
    if "image_prompt" not in ig or not isinstance(ig["image_prompt"], str) or not ig["image_prompt"].strip():
        raise ValueError("Missing or empty 'image_prompt' in instagram_post.")

    # Optional: ensure exactly 2 hashtags in the last line (best-effort check)
    # This keeps things beginner-friendly and not too strict.
    # You can remove this block if it’s too opinionated.
    caption_lines = [ln.strip() for ln in ig["caption"].splitlines() if ln.strip()]
    if caption_lines:
        last_line = caption_lines[-1]
        hashtags = [tok for tok in last_line.split() if tok.startswith("#")]
        if len(hashtags) != 2:
            # Not fatal—just a gentle nudge by appending correct brand + thematic pair.
            # If your guideline uses different tags, update them in brand_guideline.txt.
            if "#VoyagerShoes" not in last_line or "#EveryStepIsAnExploration" not in last_line:
                ig["caption"] = ig["caption"].rstrip() + "\n#VoyagerShoes #EveryStepIsAnExploration"

    return result


# ========== Quick demo (runs if you execute `python main.py`) =========

if __name__ == "__main__":
    # 1) Generate a draft brief
    draft = campaign_planner_agent(
        goal="Grow email signups ahead of the derby weekend.",
        audience="Urban 18–34 sneaker fans who watch Premier League highlights on mobile.",
        football_moment="Derby weekend buildup (Fri–Sun) and matchday rituals.",
        draft_ideas=[
            "UGC challenge: 'matchday steps' to the stadium",
            "Limited-time colorway inspired by home/away kits",
            "Fan podcast mini-segment about pre-match routines",
        ],
    )
    print("\n=== Draft Campaign Brief ===")
    print(json.dumps(draft, indent=2, ensure_ascii=False))

    # 2) Polish the draft using ONLY ./brand_guideline.txt
    polished = brand_consistency_agent(
        draft_campaign_brief=draft,
        guideline_path=BRAND_GUIDE_PATH_DEFAULT,  # ./brand_guideline.txt (same folder)
    )
    print("\n=== Polished Campaign Brief (On-Brand) ===")
    print(json.dumps(polished, indent=2, ensure_ascii=False))

    # 3) Create an Instagram-ready post from the polished brief + guideline
    instagram = instagram_creator_agent(
        polished_campaign_brief=polished,
        guideline_path=BRAND_GUIDE_PATH_DEFAULT,
    )
    print("\n=== Instagram Post (Caption + Image Prompt) ===")
    print(json.dumps(instagram, indent=2, ensure_ascii=False))