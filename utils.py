import base64
import json
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel

from walking import origin_description, walk_estimate

ROOT = Path(__file__).parent

# Browser-tab icon for every page: st.set_page_config(..., page_icon=PAGE_ICON)
PAGE_ICON = str(ROOT / "gator_icon.png")

# Keep the model names in ONE place so app.py / web_app.py / utils.py never drift apart.
# Flash-Lite goes first: Python already works out open/closed times, so Gemini only has to
# match a request to a list of 50 spots, a small job that the fast model handles.
# Run compare_models.py to check it against 3.8 Flash on real searches; swap these two lines if 3.8 wins.
MODEL = "gemini-3.5-flash-lite"
# Smarter but slower model, used only when MODEL errors, is overloaded (503) or times out.
FALLBACK_MODEL = "gemini-3.8-flash"
# gemini-3.8-flash "thinks" at medium by default, which adds seconds to every call.
# Low is plenty for picking restaurants. (Models not listed here use their own default.)
THINKING_LEVELS = {"gemini-3.8-flash": "low"}
# Give up on a model after this long instead of letting the spinner hang. (milliseconds)
TIMEOUT_MS = 12_000

# Always use Gainesville time. datetime.now() alone uses the *server's* clock,
# which is UTC on Streamlit Cloud (4-5 hours off).
try:
    UF_TZ = ZoneInfo("America/New_York")
except Exception:  # Windows without the `tzdata` package -> fall back to the computer's clock
    UF_TZ = None

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

@st.cache_data(show_spinner=False)  # no "Running img_to_base64()" message on first load
def img_to_base64(path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data(show_spinner=False)  # no "Running load_spots()" message on the first search
def load_spots():
    with open(ROOT / "foodspots.json") as f:
        return json.load(f)

DEFAULT_IMAGE = str(ROOT / "gator_logo.png")  # shown when a spot has no photo


def get_image(spot: dict) -> str:
    """Path to the spot's photo (the "image" field in foodspots.json), or the gator logo if it's missing."""
    rel = spot.get("image")
    if not rel:  # results saved before images existed: look the spot up in the current JSON
        rel = next((s.get("image") for s in load_spots() if s["id"] == spot.get("id")), None)
    if rel and (ROOT / rel).exists():
        return str(ROOT / rel)
    return DEFAULT_IMAGE


def show_spot_image(spot: dict):
    """The photo on a result/review card. Spots without a photo get the gator logo on a light panel."""
    path = get_image(spot)
    # The "noimg_" key lets card_styles() show the logo whole instead of cropping it like a photo
    box = st.container(key=f"noimg_{spot['id']}") if path == DEFAULT_IMAGE else st.container()
    with box:
        try:
            st.image(path, width="stretch")
        except Exception:  # older Streamlit versions
            st.image(path, use_container_width=True)


@st.cache_resource(show_spinner=False)  # no "Running get_client()" message on the first search
def get_client():
    """Create the Gemini client once (not on every rerun), with a clear error if the key is missing."""
    try:
        api_key = st.secrets["API_KEY"]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        raise RuntimeError(
            'No API_KEY found. Create .streamlit/secrets.toml next to FrontPage.py '
            'containing:  API_KEY = "your-gemini-key"'
        )
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))


def make_config(model: str, system_instruction: str, **config) -> types.GenerateContentConfig:
    """Shared Gemini settings; adds the thinking level only for models that need one."""
    if model in THINKING_LEVELS:
        config["thinking_config"] = types.ThinkingConfig(thinking_level=THINKING_LEVELS[model])
    return types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.0, **config)


def ask_gemini(contents: str, system_instruction: str, models=None, **config):
    """Call MODEL; if it errors or times out (e.g. 503 high demand), retry once on FALLBACK_MODEL.

    Prints how long each attempt took, so the terminal shows where the wait comes from.
    `models` lets compare_models.py force one specific model.
    """
    last_error = None
    for model in models or (MODEL, FALLBACK_MODEL):
        start = time.perf_counter()
        try:
            response = get_client().models.generate_content(
                model=model, contents=contents, config=make_config(model, system_instruction, **config)
            )
            print(f"[SwampSnacks] {model} answered in {time.perf_counter() - start:.1f}s")
            return response
        except RuntimeError:
            raise
        except Exception as e:
            print(f"[SwampSnacks] {model} failed after {time.perf_counter() - start:.1f}s: {e!r}")
            last_error = e
    raise last_error


def open_rank(spot: dict, now: datetime) -> int:
    """Sort key: open spots first, then spots with unknown hours, then closed ones."""
    is_open = open_status(spot, now)[0]
    return 0 if is_open else (1 if is_open is None else 2)


def spots_for_prompt(spots: list, now: datetime, origin: dict | None = None) -> str:
    """Compact JSON of only the fields Gemini needs (no weekly hours or map links = fewer tokens).

    With an origin ({"lat", "lng", ...} from walking.py), each spot also gets "walk_min".
    """
    rows = []
    for s in spots:
        is_open, status = open_status(s, now)
        row = {
            "id": s["id"],
            "name": s["name"],
            "zone": s["zone"],
            "landmark": s["nearest_landmark"],
            "price": s["price_range"],
            "speed": s["speed"],
            "tags": s["tags"],
            "open_now": is_open,
            "status": status,
        }
        est = walk_estimate(origin, s)
        if est:
            row["walk_min"] = est[0]
        rows.append(row)
    return json.dumps(rows, separators=(",", ":"))


# ---------- time-of-day helpers ----------

def now_at_uf() -> datetime:
    return datetime.now(UF_TZ)


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def pretty_time(hhmm: str) -> str:
    """'21:30' -> '9:30pm', '00:00' -> '12am'."""
    h, m = map(int, hhmm.split(":"))
    suffix = "am" if h < 12 else "pm"
    h = h % 12 or 12
    return f"{h}{suffix}" if m == 0 else f"{h}:{m:02d}{suffix}"


def open_status(spot: dict, now: datetime | None = None) -> tuple[bool, str]:
    """Return (is_open, label) e.g. (True, 'Open now · until 9pm') or (False, 'Closed · opens 11am').

    Handles hours that run past midnight like "11:00-02:00": at 1am Saturday,
    Friday's hours are the ones that count.
    """
    now = now or now_at_uf()
    if spot["hours"].get(DAYS[now.weekday()]) == "unknown":
        return None, "Hours not listed · check before going"
    t = now.hour * 60 + now.minute
    today = DAYS[now.weekday()]
    yesterday = DAYS[(now.weekday() - 1) % 7]

    # 1) Still open from last night's late shift?
    prev = spot["hours"].get(yesterday, "closed")
    if prev not in ("closed", "unknown"):
        start, end = prev.split("-")
        if _minutes(end) <= _minutes(start) and t < _minutes(end):
            return True, f"Open now · until {pretty_time(end)}"

    # 2) Today's hours
    hours = spot["hours"].get(today, "closed")
    if hours == "closed":
        return False, "Closed today"
    start, end = hours.split("-")
    s, e = _minutes(start), _minutes(end)
    overnight = e <= s
    if (overnight and t >= s) or (not overnight and s <= t < e):
        return True, f"Open now · until {pretty_time(end)}"
    if t < s:
        return False, f"Closed · opens {pretty_time(start)}"
    return False, "Closed for the day"


def set_background():
    # Small web-sized copy: this image is embedded in every page, so its size = page load time
    encoded = img_to_base64(ROOT / "Uf_Reitz_Picture_web.jpg")

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');

        html, body, [class*="css"], .stMarkdown, .stChatMessage, textarea, input, h1, h2, h3, h4 {{
            font-family: 'DM Sans', sans-serif !important;
        }}

        .stApp {{
            background-image:
                linear-gradient(rgba(0, 0, 0, 0.45), rgba(0, 0, 0, 0.45)),
                url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"] {{
            background: transparent !important;
        }}

        /* Hide the sidebar page list so users only navigate through the app */
        [data-testid="stSidebarNav"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}

        /* Hide the heading anchor-link icons */
        [data-testid="stHeaderActionElements"] {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_banner():
    chef_gator = img_to_base64(ROOT / "gator_logo.png")  # logo with transparent background, 160px tall

    st.markdown(
        f"""
        <style>
        .banner {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: #0021A5;
            border: 3px solid #FA4616;
            border-radius: 32px;
            padding: 0.25rem 1.5rem;
            margin-top: -2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }}
        .banner img {{
            height: 60px;
            width: 60px;
            object-fit: contain;
        }}
        .banner img.flip {{
            transform: scaleX(-1);
        }}
        .banner h1 {{
            flex: 1;
            text-align: center;
            color: white !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 700;
            font-size: 2.75rem;
            margin: 0;
            padding: 0;
        }}
        .banner h1 a {{
            display: none !important;
        }}
        .block-container {{
        padding-top: 3rem !important;
        }}
        </style>

        <div class="banner">
            <img src="data:image/png;base64,{chef_gator}">
            <h1>SwampSnacks</h1>
            <img class="flip" src="data:image/png;base64,{chef_gator}">
        </div>
        """,
        unsafe_allow_html=True,
    )

def page_transition(page: str, view: str = ""):
    """Smooth page changes: the page content fades in and grows slightly into place.

    Call it at the top of each page. Each page gets its own animation name, so the animation
    replays when you switch pages but not when you click things on the same page.
    `view` replays it for a different view of the same page (the Reviews page uses it
    when you open a spot or go back to the list). The banner and nav bar don't animate:
    FrontPage.py draws them once, so they stay still.
    """
    anim = "pageIn_" + re.sub(r"[^A-Za-z0-9_-]", "_", f"{page}_{view}")
    top = ('[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]',
           '[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]')  # newer / older Streamlit
    # Page content = everything after the banner except the nav bar
    content = ", ".join(f"{t} > :has(.banner) ~ :not(:has(.st-key-navbar))" for t in top)
    st.markdown(
        f"""
        <style>
        /* Fade in while growing from 98% size. (Sliding up from below would make the page briefly
           taller, and on the Search page Streamlit's chat scrolling would then nudge the top bar.) */
        @keyframes {anim} {{
            from {{ opacity: 0; transform: scale(0.98); }}
            to   {{ opacity: 1; transform: none; }}
        }}
        {content}, [data-testid="stBottom"] {{
            animation: {anim} 0.45s cubic-bezier(0.2, 0.7, 0.2, 1) both;
            transform-origin: top center;
        }}
        @media (prefers-reduced-motion: reduce) {{
            {content}, [data-testid="stBottom"] {{ animation: none; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_nav(current: str):
    """Navigation bar under the banner. `current` is "Home", "Search", "Results", or "Reviews"."""
    pages = [
        ("Home", "app_pages/Home.py", "🏠"),
        ("Search", "app_pages/Search.py", "🔍"),
        ("Results", "app_pages/Results.py", "🍽️"),
        ("Reviews", "app_pages/Reviews.py", "⭐"),
    ]

    st.markdown(
        f"""
        <style>
        .st-key-navbar {{
            margin: 0.75rem auto 0.5rem;
        }}
        .st-key-navbar [data-testid="stPageLink"] a {{
            justify-content: center;
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid transparent;
            border-radius: 999px;
            padding: 0.35rem 1rem;
            transition: background 0.2s, border-color 0.2s;
        }}
        .st-key-navbar [data-testid="stPageLink"] a:hover {{
            background: white;
            border-color: #FA4616;
        }}
        .st-key-navbar [data-testid="stPageLink"] a p {{
            color: #0021A5 !important;
            font-weight: 600;
        }}
        /* Highlight the page you're on */
        .st-key-nav_{current} [data-testid="stPageLink"] a {{
            background: #FA4616 !important;
            border-color: #FA4616 !important;
        }}
        .st-key-nav_{current} [data-testid="stPageLink"] a p {{
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="navbar"):
        cols = st.columns([2.5, 1, 1, 1, 1, 2.5])
        for col, (label, path, icon) in zip(cols[1:-1], pages):
            with col:
                with st.container(key=f"nav_{label}"):
                    st.page_link(path, label=label, icon=icon, width="stretch")


def card_styles():
    """White, rounded card look for any st.container(key="card_...") (used on Results and Reviews)."""
    st.markdown(
        """
        <style>
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(16px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        /* Same white panel as the home page so text is readable over the photo */
        [class*="st-key-card_"] {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
            padding: 1rem 1.5rem;
            max-width: 1100px;     /* narrower card, centered on the page */
            margin: 0 auto;
            color: #1a1a1a;
            animation: fadeUp 0.5s ease-out both;
        }
        [class*="st-key-card_"] h4 { color: #0021A5 !important; }
        [class*="st-key-card_"] li { margin-bottom: 0.15rem; }
        [class*="st-key-card_"] li::marker { color: #FA4616; }
        /* Restaurant photos: same size on every card, cropped to fill, rounded corners */
        [class*="st-key-card_"] [data-testid="stFullScreenFrame"] > div:has([data-testid="stImage"]),
        [class*="st-key-card_"] [data-testid="stImage"],
        [class*="st-key-card_"] [data-testid="stImageContainer"] {
            width: 100% !important;  /* let portrait and landscape photos fill the column the same way */
        }
        [class*="st-key-card_"] [data-testid="stImage"] img {
            width: 100% !important;
            height: 260px;
            object-fit: cover;       /* crop to fill instead of stretching */
            border-radius: 12px;
        }
        /* No photo: show the whole gator logo, centered on a light panel */
        [class*="st-key-card_"] [class*="st-key-noimg_"] [data-testid="stImage"] img {
            object-fit: contain;
            padding: 45px;
            background: #e8edf9;
        }
        /* Turn off the "expand image" (fullscreen) button on card photos */
        [class*="st-key-card_"] [data-testid="stElementToolbar"],
        [class*="st-key-card_"] [data-testid="StyledFullScreenButton"] {
            display: none !important;
        }
        /* Buttons inside cards keep white text (the card's dark text color would hide it) */
        [class*="st-key-card_"] .stButton > button[kind="secondary"],
        [class*="st-key-card_"] .stButton > button[kind="secondary"] p { color: #fafafa !important; }
        .stars { color: #FA4616; letter-spacing: 1px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- recommendations ----------

_STOPWORDS = {"near", "need", "want", "with", "from", "between", "class", "classes",
              "minutes", "under", "something", "food", "place", "places", "good", "have"}


class Pick(BaseModel):
    """One recommendation from Gemini: which spot, and why it fits the user's request."""
    id: str
    reasons: list[str]


_SPEED_LABELS = {
    "grab_and_go": "Grab-and-go, so you're in and out in minutes",
    "quick": "Quick service, usually 10-20 minutes",
    "sit_down": "Sit-down spot if you have time to relax",
}


def _rule_reasons(spot: dict, words: set, now: datetime) -> list[str]:
    """Plain-English reasons built from the data, used when Gemini is unavailable."""
    reasons = []
    hits = [t for t in spot["tags"] if any(w in t for w in words)]
    if hits:
        reasons.append("Matches what you asked for: " + ", ".join(t.replace("_", " ") for t in hits[:3]))
    is_open, status = open_status(spot, now)
    if is_open:
        reasons.append(status)
    if spot["price_range"] == "$":
        reasons.append("Budget-friendly ($)")
    reasons.append(_SPEED_LABELS.get(spot["speed"], spot["speed"].replace("_", " ")))
    return reasons[:3]


def _keyword_fallback(query: str, spots: list, now: datetime, origin: dict | None = None) -> list:
    """Used only when Gemini is unreachable: rank spots by simple keyword overlap, open ones first
    (ties go to the shorter walk when we know where the user is)."""
    words = {w.strip(",.!?$").lower() for w in query.split()}
    words = {w for w in words if len(w) > 3 and w not in _STOPWORDS}

    def score(s):
        text = " ".join([s["name"], s["zone"], s["nearest_landmark"], *s["tags"]]).lower()
        est = walk_estimate(origin, s)
        return sum(w in text for w in words), -(est[0] if est else 0)

    top = sorted(spots, key=score, reverse=True)[:5]
    top.sort(key=lambda s: open_rank(s, now))  # open, then unknown hours, then closed
    return [{**s, "reasons": _rule_reasons(s, words, now)} for s in top]


def get_recommendations(query: str, spots: list, models=None, origin: dict | None = None) -> tuple[list, str | None]:
    """Return (matched_spots, error_message_or_None).

    Each matched spot is a copy of its foodspots.json entry plus a "reasons" list:
    short bullet points explaining why it fits the user's request.

    The error is returned instead of shown with st.error() because Search.py calls
    st.switch_page() right after this, which wiped the error box before you could read it.
    """
    now = now_at_uf()

    if origin:
        walking_rule = f"""
    WALKING RULE: The user is at {origin_description(origin)}. Each restaurant has "walk_min", the
    estimated minutes on foot from there. Prefer short walks, especially when the user is short on
    time; if they give a time limit, the walk there and back has to fit inside it."""
    else:
        walking_rule = ""

    system_prompt = f"""
    You are an expert UF campus dining assistant.
    The user will provide a location, craving, or constraint.
    The current time in Gainesville is {now:%A %I:%M %p}.

    CRITICAL GEOGRAPHY RULE: Use your general knowledge of the University of Florida campus to match
    user locations (like "Turlington", "Lib West", etc.) to the nearest landmarks in our database
    (like "Plaza of the Americas", "The Hub", "Marston", or "Midtown").
    {walking_rule}

    TIME RULE: open_now null means hours are unknown; treat those as possibly open. Being closed does NOT disqualify a spot. Always include every strong match for what
    the user asked (cuisine, food type, location), open or closed. The app shows closed spots at the
    bottom with a red dot. Use the time of day too (breakfast in the morning, late_night spots late).

    MATCHING: Match by meaning, not exact words. "Chinese" matches chinese; "coffee" matches coffee,
    cafe, lattes; "dessert"/"sweet" matches desserts, sweets, ice_cream, pastries, milkshakes;
    "cheap"/"broke" matches "$" and cheap_eats. Location matters: a spot near the user beats a far one.

    BUDGET/SPEED: "$" is cheapest. If the user is short on time, prefer grab_and_go or quick.

    Select up to 5 best matching restaurants, best match first.

    For each pick, give 2-3 short "reasons" explaining why it fits THIS user's request.
    - Tie each reason to something the user said (time, budget, diet, location, group, vibe).
    - Use only facts from the restaurant data (price, speed, landmark, tags, open status, walk_min).
      Never invent menu items, prices in dollars, or ratings. Only mention a walking time if the
      spot has walk_min, and use that number.
    - Keep each reason under 15 words, casual and friendly, no ending period.
    Example: {{"id": "uf-005", "reasons": ["Right at Plaza of the Americas, steps from Turlington",
              "Fully vegan and under $10", "Grab-and-go, fits your 15-minute window"]}}

    RESTAURANTS:
    {spots_for_prompt(spots, now, origin)}
    """

    try:
        response = ask_gemini(
            f"User Query: {query}",
            system_prompt,
            models=models,
            response_mime_type="application/json",
            response_schema=list[Pick],  # forces [{"id": ..., "reasons": [...]}, ...]
        )
        picks = response.parsed
        if picks is None:  # older SDKs: parse the JSON text ourselves
            picks = [Pick(**p) for p in json.loads(response.text)]

        by_id = {s["id"]: s for s in spots}
        # Copy each spot (so the cached database isn't modified) and attach Gemini's reasons.
        # Keeps Gemini's ranking order.
        matched = [{**by_id[p.id], "reasons": p.reasons} for p in picks if p.id in by_id]
        # Open spots first, closed ones at the bottom (Python's sort is stable, so Gemini's order is kept within each group)
        matched.sort(key=lambda s: open_rank(s, now))
        if matched:
            return matched, None
        return _keyword_fallback(query, spots, now, origin), "Gemini didn't find a match, so these are the closest keyword matches."

    except Exception as e:
        print(f"[SwampSnacks] Gemini error: {e!r}")  # full details in your terminal
        return _keyword_fallback(query, spots, now, origin), f"AI is unavailable right now ({e}). Showing keyword matches instead."
