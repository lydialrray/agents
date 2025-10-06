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

from typing import List, Dict
from typing import List, Dict
import re
import json

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

# ---------------- instagram_post_creator_agent ----------------

# ---------------- x_post_creator_agent ----------------

# ---------------- linkedin_post_creator_agent ----------------

# ---------------- facebook_post_creator_agent ----------------


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

    #print(json.dumps(raw, indent=2, ensure_ascii=False)) 
    #print("------------------------------")  
    print(json.dumps(polished, indent=2, ensure_ascii=False))