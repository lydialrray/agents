import json, os, requests
from datetime import datetime
import time

# ---------- BASIC CONFIG ----------
USE_OLLAMA = True
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
TOKENS = {"input": 0, "output": 0}

# use host-only; the helper will pick the endpoint
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
CHAT_URL = f"{OLLAMA_HOST}/api/chat"
GEN_URL  = f"{OLLAMA_HOST}/api/generate"

# ---------- PROMPTS (one string each) ----------
# PROMPT_AUDIENCE_PROFILER = """You are an audience profiler.
# Return ONLY valid JSON with:
# key_insight, desired_emotions[], voice_tone, literacy_level, taboo_list[]."""

# PROMPT_CAMPAIGN_PLANNER = """You are a campaign planner for Instagram.
# Return ONLY:
# comms_objective, single_minded_proposition, reasons_to_believe[], CTA, success_signal."""

# PROMPT_CAPTION_GENERATOR = """You are an Instagram caption writer.
# Write 3–5 captions based on the plan and trends.
# Rules: hook<125, total<2200, soft CTA, exactly 2 hashtags (1 brand + 1 theme), no salesy language.
# Return ONLY JSON with captions[]: id, hook, body, CTA, hashtags[2], est_chars, used_trends."""

# PROMPT_IMAGE_PROMPT_ENGINEER = """You are an AI image prompt engineer.
# Make ONE cinematic prompt + negatives + short alt_text + metadata ratio.
# Return ONLY JSON with: image_prompt, negative_prompts[], alt_text, metadata{ratio}."""

PROMPT_AUDIENCE_PROFILER = """You are an audience profiler.
READ the JSON immediately after the line 'Audience:'.
Write ONLY a JSON object with the following keys:
- key_insight: 1 sentence, plain language.
- desired_emotions: array of 2–4 lowercase words.
- voice_tone: short, comma-separated style (≤6 words), e.g., "adventurous, empowering, authentic".
- literacy_level: one of ["general","youth","expert","casual"] (pick best fit).
- taboo_list: array of 3–6 short phrases to avoid (lowercase, no punctuation).

Rules:
- UK spelling.
- No marketing puffery.
- No extra keys, no comments, no markdown, no prose outside JSON.
"""

PROMPT_CAMPAIGN_PLANNER = """You are a campaign planner for Instagram.
Input sections appear after 'Draft:' and 'Audience voice:'.
Write ONLY a JSON object with:
- comms_objective: 1 sentence outcome (not a tactic).
- single_minded_proposition: ≤10 words, memorable, brand-ownable.
- reasons_to_believe: array of 2–4 short, concrete reasons (no fluff).
- CTA: soft, motivational (no salesy verbs, no 'buy', no prices).
- success_signal: one measurable signal, e.g., "Saves rate ≥ 1.5%" or "Shares per 1k impressions ≥ 25".

Constraints:
- Align tone with Audience voice.
- Avoid absolute claims, avoid endorsements.
- UK spelling. No extra keys or text outside JSON.
"""

PROMPT_CAPTION_GENERATOR = """You are an Instagram caption writer.
You will receive three blocks: Plan:, Trends:, IG Rules: (JSON).
Return ONLY a JSON object:
{
  "captions": [
    {
      "id": "cap_1..n",
      "hook": "≤125 chars, punchy, cinematic",
      "body": "1–2 short lines, emotive, no salesy language",
      "CTA": "soft action line consistent with plan",
      "hashtags": ["#BrandRequired","#OneThemeOnly"],
      "est_chars": 0,
      "used_trends": true
    }
  ]
}

STRICT rules:
- Produce 3–5 captions.
- Total caption length (hook + body + CTA + hashtags) < 2200 chars.
- Exactly 2 hashtags:
  • First MUST be IG Rules.hashtag_policy.required_brand[0]
  • Second MUST be one item from IG Rules.hashtag_policy.theme_pool
- Tone: adventurous, empowering, authentic; UK spelling.
- 0–2 emojis max; never in hashtags.
- No quotes, no markdown, no extra keys, no explanations.

Implementation hint (follow, do not print):
- Read required_brand[0] and theme_pool from IG Rules JSON.
"""

PROMPT_IMAGE_PROMPT_ENGINEER = """You are an AI image prompt engineer for a football brand with a deep-blue & gold palette.
You will receive Inputs: JSON with adjusted_plan, caption, palette, negatives, ratio.
Return ONLY a JSON object with:
- image_prompt: one compact, cinematic prompt for a photoreal image generator. Include:
  • subject: football boots in motion / low-angle action
  • mood: golden hour, explorer journey
  • composition: dynamic, horizon/low angle, motion blur, shallow depth of field
  • palette: use provided hexes (blue/gold) as accents or grading
  • textures: turf, dust, sweat, natural light
- negative_prompts: merge Inputs.negatives and add: ["logos","brand marks","league badges","faces","text overlays","watermarks","celebrity likeness"]
- alt_text: 1 sentence, literal description, no marketing.
- metadata: { "ratio": same string as Inputs.ratio }

Constraints:
- No brand names, no player likeness, no tournament logos, no text-in-image.
- Keep it under 60 words for image_prompt.
- UK spelling, no extra keys or prose outside JSON.
"""

# ---------- Interact with Ollama ----------
def ask_ollama(model, prompt, *, mode="json", schema=None, temperature=0.4):
    import requests, json

    def call_chat():
        body = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": prompt + (
                    f"\n\nReturn ONLY valid JSON matching:\n{schema}" if (mode=="json" and schema) else ""
                )
            }],
            "options": {"temperature": temperature},
            "stream": False  # <<< SINGLE JSON, fixes 'Extra data'
        }
        if mode == "json":
            body["format"] = "json"
        r = requests.post(CHAT_URL, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        TOKENS["input"]  += data.get("prompt_eval_count", 0)
        TOKENS["output"] += data.get("eval_count", 0)
        return data.get("message", {}).get("content", "")

    def call_generate():
        body = {
            "model": model,
            "prompt": prompt + (
                f"\n\nReturn ONLY valid JSON matching:\n{schema}" if (mode=="json" and schema) else ""
            ),
            "options": {"temperature": temperature},
            "stream": False  # <<< SINGLE JSON
        }
        # You can also set body["format"]="json" here, but plain prompt + schema hint is usually enough for phi3:mini
        r = requests.post(GEN_URL, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        TOKENS["input"]  += data.get("prompt_eval_count", 0)
        TOKENS["output"] += data.get("eval_count", 0)
        return data.get("response", "")

    # Prefer chat; on 404/405 or network issues, fall back to generate
    try:
        out = call_chat()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (404, 405):
            out = call_generate()
        else:
            raise
    except requests.RequestException:
        out = call_generate()

    if mode == "text":
        return out

    # JSON mode: parse; if model added extra text, try a stricter second pass via /generate
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        repaired = call_generate()
        return json.loads(repaired)

# ---------- Time logging ----------

def time_step(label, fn, *args, **kwargs):
    from datetime import datetime; import time
    bi, bo = TOKENS["input"], TOKENS["output"]
    s = datetime.now().isoformat(timespec="seconds"); t = time.perf_counter()
    print(f"▶ {label} START {s}")
    out = fn(*args, **kwargs)
    e = datetime.now().isoformat(timespec="seconds"); d = time.perf_counter() - t
    di, do = TOKENS["input"]-bi, TOKENS["output"]-bo
    print(f"✓ {label} END   {e}  ({d:.2f}s)  tokens in/out: {di}/{do}")
    return out

# ---------- Simple web "tool" for trends ----------
def trend_scraper_tool(topic: str, month: str, locale: str) -> dict:
    # super simple RSS/title scraper → keywords
    import re, collections
    cc = (locale.split("-")[-1] or "GB").upper()
    ll = (locale.split("-")[0] or "en").lower()

    feeds = [
        f"https://news.google.com/rss/search?q={requests.utils.quote(topic + ' ' + month)}&hl={ll}-{cc}&gl={cc}&ceid={cc}:{ll}",
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.theguardian.com/football/rss",
    ]

    titles = []
    for url in feeds:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            if r.ok:
                titles += re.findall(r"<title>(.*?)</title>", r.text, flags=re.I)
        except Exception:
            pass

    # clean + dedupe
    titles = [t for t in titles if len(t.split()) > 3]
    titles = list(dict.fromkeys(titles))[:50]

    text = " ".join(titles).lower()
    words = re.findall(r"[a-z]{3,}", text)
    stop = set("""
        the and for with from this that into your have has are was were will they them you our their who why what when
        sport sports football soccer match game games live latest update updates vs cup league premier fa uefa
    """.split())
    words = [w for w in words if w not in stop]

    hot = [w for w,_ in collections.Counter(words).most_common(10)]
    summary  = ", ".join(hot[:5]) if hot else "no strong signals"
    angles   = [f"{w} — pre-match ritual" for w in hot[:3]] or ["golden-hour match prep"]
    snippets = titles[:3]

    return {
        "trend_summary": summary,
        "hot_keywords": hot,
        "example_angles": angles,
        "fact_snippets": snippets,
        "data_confidence": "medium" if len(titles) >= 10 else "low",
        "source": "web" 
    }

# ---------- BRAND (based on brand_guidelin.json) ----------
def load_brand_guidelines(path="brand_guidelines.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return {
      "brand_name":"Voyager Shoes",
      "locale":"en-GB",
      "tone":["adventurous","empowering","authentic","confident"],
      "visual_style":{"palette":{"voyager_blue":"#0B1E40","explorer_gold":"#F5B500"}},
      "platforms":{
        "instagram":{
          "caption_rules":{"hook_max_chars":125,"caption_max_chars":2200},
          "hashtag_policy":{
            "required_brand":["#VoyagerShoes"],
            "theme_pool":["#EveryStepIsAnExploration","#FootballJourney"]
          }
        }
      },
      "ai_image":{"negative_prompts":["club logos","league badges","faces","endorsements"]},
      "taboo_terms":["buy now","miracle","guaranteed"]
    }

def basic_setup(inp: dict) -> dict:
    if "brand_guidelines" not in inp: inp["brand_guidelines"] = load_brand_guidelines()
    inp.setdefault("target_audience", {"label":"generic","locale":"en-GB"})
    inp.setdefault("campaign_draft_paragraph", "Promote Voyager Shoes as the boot for explorers.")
    inp.setdefault("topic", "football")
    inp.setdefault("month", "2025-10")
    return inp

# ---------- AGENTS (each ends with _agent) ----------
def audience_profiler_agent(audience: dict) -> dict:
    if USE_OLLAMA:
        schema = '{"key_insight":"string","desired_emotions":["string"],"voice_tone":"string","literacy_level":"string","taboo_list":["string"]}'
        prompt = f"""{PROMPT_AUDIENCE_PROFILER}

Audience:
{json.dumps(audience)}"""
        return ask_ollama(OLLAMA_MODEL, prompt, mode="json", schema=schema, temperature=0.2)
    return {"key_insight":"Football = identity.","desired_emotions":["amped","proud"],"voice_tone":"adventurous, empowering","literacy_level":"general","taboo_list":["hard sell"]}

def campaign_planner_agent(draft: str, profile: dict) -> dict:
    if USE_OLLAMA:
        schema = '{"comms_objective":"string","single_minded_proposition":"string","reasons_to_believe":["string"],"CTA":"string","success_signal":"string"}'
        prompt = f"""{PROMPT_CAMPAIGN_PLANNER}

Draft: {draft}
Audience voice: {profile.get('voice_tone')}"""
        return ask_ollama(OLLAMA_MODEL, prompt, mode="json", schema=schema, temperature=0.1)
    return {"comms_objective":"Drive consideration","single_minded_proposition":"Every step is an exploration.","reasons_to_believe":["exploration framing"],"CTA":"Keep moving.","success_signal":"Saves >= 1.5%"}

def brand_enforcer_agent(plan: dict, brand: dict, taboo_list: list) -> dict:
    tone = ", ".join(brand.get("tone", [])) or "adventurous, empowering"
    adj = dict(plan); adj["voice_tone"] = tone
    if any(t in adj.get("CTA","").lower() for t in ["buy now","sale"]): adj["CTA"] = "Keep moving."
    return {"adjusted_plan": adj, "violations": [], "alignment_score": 0.95}

# def trend_miner_agent(topic: str, month: str, locale: str) -> dict:
#     return {"trend_summary":"Derby chatter, stoppage-time drama, pre-match rituals.",
#             "hot_keywords":["derby day","stoppage time"],
#             "example_angles":["golden-hour match prep"],
#             "fact_snippets":[f"{month} {locale}"], "data_confidence":"medium"}

def trend_miner_agent(topic: str, month: str, locale: str) -> dict:
    try:
        data = trend_scraper_tool(topic, month, locale)
        if data.get("hot_keywords"):
            return data
    except Exception:
        pass
    # fallback if scraping fails or finds nothing useful
    return {
        "trend_summary":"Derby chatter, stoppage-time drama, pre-match rituals.",
        "hot_keywords":["derby day","stoppage time"],
        "example_angles":["golden-hour match prep"],
        "fact_snippets":[f"{month} {locale}"],
        "data_confidence":"low",
        "source": "local_fallback"
    }

def caption_generator_agent(adjusted_plan: dict, trends: dict, brand: dict) -> dict:
    ig = brand["platforms"]["instagram"]["hashtag_policy"]
    brand_tag, theme_tag = ig["required_brand"][0], ig["theme_pool"][0]

    if USE_OLLAMA:
        schema = '{"captions":[{"id":"string","hook":"string","body":"string","CTA":"string","hashtags":["string","string"],"est_chars":0,"used_trends":true}]}'
        prompt = f"""{PROMPT_CAPTION_GENERATOR}

Plan:
{json.dumps(adjusted_plan)}

Trends:
{json.dumps(trends)}

IG Rules:
{json.dumps(brand["platforms"]["instagram"])}"""
        data = ask_ollama(OLLAMA_MODEL, prompt, mode="json", schema=schema, temperature=0.7)
        caps = data.get("captions", []) if isinstance(data, dict) else []
    else:
        caps = []

    # ultra-simple normalization + tiny fallback
    if not caps:
        base = {"CTA": adjusted_plan.get("CTA","Keep moving."), "hashtags":[brand_tag, theme_tag], "used_trends": True}
        caps = [
            {"id":"cap_1","hook":"Every pitch is a new world.","body":"Boots on. Head clear. Chase the horizon—90+ and beyond.",**base},
            {"id":"cap_2","hook":"Find your next horizon.","body":"From kickoff to stoppage time—keep exploring.",**base}
        ]

    for i, c in enumerate(caps, 1):
        c.setdefault("id", f"cap_{i}")
        c["hook"] = str(c.get("hook",""))
        c["body"] = str(c.get("body",""))
        c["CTA"]  = str(c.get("CTA","Keep moving."))
        hs = c.get("hashtags")
        if not isinstance(hs, list) or len(hs) != 2:
            c["hashtags"] = [brand_tag, theme_tag]
        txt = f"{c['hook']}\n{c['body']}\n\n{c['CTA']}\n{' '.join(c['hashtags'])}"
        c["est_chars"] = len(txt)

    return {"captions": caps}


def image_prompt_engineer_agent(adjusted_plan: dict, chosen_caption: dict, brand: dict, ratio="4:5") -> dict:
    if USE_OLLAMA:
        schema = '{"image_prompt":"string","negative_prompts":["string"],"alt_text":"string","metadata":{"ratio":"string"}}'
        payload = {"adjusted_plan": adjusted_plan, "caption": chosen_caption, "palette": brand.get("visual_style",{}).get("palette",{}),
                   "negatives": brand.get("ai_image",{}).get("negative_prompts",[]), "ratio": ratio}
        prompt = f"""{PROMPT_IMAGE_PROMPT_ENGINEER}

Inputs:
{json.dumps(payload)}"""
        return ask_ollama(OLLAMA_MODEL, prompt, mode="json", schema=schema, temperature=0.6)
    neg = brand.get("ai_image", {}).get("negative_prompts", [])
    return {"image_prompt":"Cinematic scene, Voyager blue & gold, low-angle boots, golden hour, motion blur.",
            "negative_prompts":neg, "alt_text":"Low-angle boots sprinting at golden hour.", "metadata":{"ratio":ratio}}

def qa_and_selector_agent(captions: list, image_json: dict, brand: dict, plan: dict) -> dict:
    ig = brand["platforms"]["instagram"]
    req = ig["hashtag_policy"]["required_brand"][0]
    pool = ig["hashtag_policy"]["theme_pool"]
    hook_max = ig["caption_rules"]["hook_max_chars"]
    cap_max = ig["caption_rules"]["caption_max_chars"]

    passing = []
    for c in captions:
        hook = str(c.get("hook","")).strip()
        body = str(c.get("body","")).strip()
        CTA  = str(c.get("CTA","Keep moving.")).strip()
        hs   = c.get("hashtags", [])
        if not hook or not body: continue
        if len(hook) > hook_max: continue
        if len(" ".join([hook, body, CTA, " ".join(hs)])) > cap_max: continue
        if not isinstance(hs, list) or len(hs) != 2: continue
        if req not in hs: continue
        if not any(h in pool for h in hs if h != req): continue
        text = (hook + " " + body + " " + CTA).lower()
        if any(t in text for t in brand.get("taboo_terms", [])): continue
        passing.append(c)

    if not passing:
        return {"status":"needs_revision","reason":"no passing caption"}

    best = passing[0]
    post = f"{best['hook']}\n{best['body']}\n\n{best['CTA']}\n{' '.join(best['hashtags'])}"
    return {
        "instagram_post_text": post,
        "image_generation_prompt": image_json.get("image_prompt",""),
        "alt_text": image_json.get("alt_text",""),
        "metadata": {
            "objective": plan.get("comms_objective",""),
            "primary_kpi": plan.get("success_signal",""),
            "constraints_applied": True
        }
    }

# ---------- FLOW ----------
def run_pipeline(user_input: dict) -> dict:
    inp = basic_setup(user_input)
    brand = inp["brand_guidelines"]; audience = inp["target_audience"]

    prof     = time_step("audience_profiler_agent", audience_profiler_agent, audience)
    taboos   = prof.get("taboo_list", inp["brand_guidelines"].get("taboo_terms", []))
    plan     = time_step("campaign_planner_agent",  campaign_planner_agent, inp["campaign_draft_paragraph"], prof)
    enforced = time_step("brand_enforcer_agent",    brand_enforcer_agent, plan, brand, taboos)
    trends = time_step("trend_miner_agent", trend_miner_agent, inp["topic"], inp["month"], audience.get("locale","en-GB"))
    print("Trend source:", trends.get("source", "unknown"))
    
    caps     = time_step("caption_generator_agent", caption_generator_agent, enforced["adjusted_plan"], trends, brand)
    img      = time_step("image_prompt_engineer_agent", image_prompt_engineer_agent, enforced["adjusted_plan"], caps["captions"][0], brand)
    final    = time_step("qa_and_selector_agent",   qa_and_selector_agent, caps["captions"], img, brand, plan)
    
    final.setdefault("metadata", {})["trend_source"] = trends.get("source", "unknown")

    return final

# ---------- DEMO ----------
if __name__ == "__main__":
    sample = {
      "target_audience": {"label":"UK football fans 18–24","locale":"en-GB"},
      "campaign_draft_paragraph": "Promote Voyager Shoes as the boot for explorers. Focus on the journey.",
      "topic":"football","month":"2025-10",
      "brand_guidelines": load_brand_guidelines()
    }
    result = run_pipeline(sample)
    print(json.dumps(result, indent=2))
    print(f"Token usage — input: {TOKENS['input']}, output: {TOKENS['output']}")

