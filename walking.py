"""Walk-time estimates from where the user is to each food spot.

Where the user is (the "origin") comes from, in order:
  1. Their phone/laptop GPS ("📍 Use my location" button on the Search page)
  2. A campus building they picked from the "Walking from" dropdown
  3. A building mentioned in their search, e.g. "15 min between classes near Reitz"

Every spot in foodspots.json has approximate "lat"/"lng" fields (within ~100 m),
so walk times are estimates; fix any spot by editing its lat/lng.
"""
import math
import re
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).parent

# Common starting points on campus (approximate coordinates).
CAMPUS_PLACES = {
    "Marston Science Library": (29.6480, -82.3440),
    "Library West": (29.6511, -82.3429),
    "Reitz Union": (29.6461, -82.3478),
    "Turlington Hall": (29.6489, -82.3440),
    "Plaza of the Americas": (29.6494, -82.3432),
    "Century Tower": (29.6487, -82.3424),
    "The Hub": (29.6481, -82.3457),
    "Ben Hill Griffin Stadium": (29.6500, -82.3487),
    "O'Connell Center": (29.6494, -82.3509),
    "Broward Hall": (29.6457, -82.3391),
    "Hume Hall": (29.6441, -82.3508),
    "UF Health Shands Hospital": (29.6402, -82.3437),
    "Southwest Rec Center": (29.6386, -82.3690),
    "Midtown (University Ave & 17th St)": (29.6521, -82.3452),
}

# Words people type in a search -> the campus place they mean
_PLACE_ALIASES = {
    "marston": "Marston Science Library",
    "library west": "Library West",
    "lib west": "Library West",
    "libwest": "Library West",
    "reitz": "Reitz Union",
    "turlington": "Turlington Hall",
    "plaza of the americas": "Plaza of the Americas",
    "century tower": "Century Tower",
    "the hub": "The Hub",
    "stadium": "Ben Hill Griffin Stadium",
    "o'connell": "O'Connell Center",
    "oconnell": "O'Connell Center",
    "o'dome": "O'Connell Center",
    "odome": "O'Connell Center",
    "broward": "Broward Hall",
    "hume": "Hume Hall",
    "shands": "UF Health Shands Hospital",
    "southwest rec": "Southwest Rec Center",
    "sw rec": "Southwest Rec Center",
    "midtown": "Midtown (University Ave & 17th St)",
}

UF_CENTER = (29.6480, -82.3440)
WALK_METERS_PER_MIN = 80   # about 3 mph, an average walking pace
DETOUR_FACTOR = 1.25       # sidewalks aren't a straight line
TOO_FAR_TO_WALK_MIN = 35   # past this we suggest a bus or a ride instead
FAR_FROM_UF_KM = 15        # a GPS fix farther than this probably isn't a student on campus


# ---------- math ----------

def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Straight-line distance in meters between two (lat, lng) points (haversine formula)."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def walk_estimate(origin: dict | None, spot: dict) -> tuple[int, float] | None:
    """(minutes on foot, miles) from the origin to the spot, or None if either location is unknown."""
    if not origin or "lat" not in spot or "lng" not in spot:
        return None
    meters = distance_m((origin["lat"], origin["lng"]), (spot["lat"], spot["lng"])) * DETOUR_FACTOR
    return max(1, round(meters / WALK_METERS_PER_MIN)), meters / 1609.34


def walk_label(origin: dict | None, spot: dict) -> str | None:
    """'🚶 6 min walk · 0.3 mi', or a too-far note. None when there's no origin."""
    est = walk_estimate(origin, spot)
    if est is None:
        return None
    minutes, miles = est
    if minutes > TOO_FAR_TO_WALK_MIN:
        return f"🚌 {miles:.1f} mi away (about {minutes} min on foot, so grab a bus or a ride)"
    distance = "right next door" if miles < 0.1 else f"{miles:.1f} mi"
    return f"🚶 {minutes} min walk · {distance}"


def directions_url(origin: dict | None, spot: dict) -> str | None:
    """Google Maps directions from the origin to the spot (walking when it's close enough)."""
    if not origin or "google_maps_url" not in spot:
        return None
    # Reuse the place search text already in foodspots.json, e.g. "Panda+Express+Reitz+Union+Gainesville+FL"
    query = parse_qs(urlparse(spot["google_maps_url"]).query).get("query", [spot["name"] + " Gainesville FL"])[0]
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin['lat']},{origin['lng']}"
        f"&destination={quote_plus(query)}"
    )
    est = walk_estimate(origin, spot)
    if est and est[0] <= TOO_FAR_TO_WALK_MIN:
        url += "&travelmode=walking"
    return url


# ---------- where is the user? ----------

def place_in_text(text: str) -> dict | None:
    """Spot a campus building in a search like 'near Reitz' and return it as an origin."""
    lowered = (text or "").lower()
    for alias, place in _PLACE_ALIASES.items():
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", lowered):
            lat, lng = CAMPUS_PLACES[place]
            return {"label": place, "lat": lat, "lng": lng, "source": "search"}
    return None


def current_origin(query: str | None = None) -> dict | None:
    """GPS or picked building first; otherwise a building named in the search; otherwise None."""
    return st.session_state.get("origin") or place_in_text(query or "")


def origin_description(origin: dict | None) -> str | None:
    if not origin:
        return None
    if origin["source"] == "gps":
        return "your current location"
    if origin["source"] == "search":
        return f"{origin['label']} (from your search)"
    return origin["label"]


# ---------- "Use my location" button (a tiny custom component, no extra packages) ----------

_location_button = components.declare_component(
    "location_button", path=str(ROOT / "components" / "location_button")
)


GPS_OPTION = "📍 Your current location"  # shown in the dropdown while GPS is in use, so ✕ can clear it


def location_button(active: bool, key: str = "gps_button"):
    """Shows the button. When the browser answers, _apply_gps_fix() saves the result.

    `active` just changes the label ("Use my location" vs "Update location").
    """
    return _location_button(active=active, key=key, default=None, on_change=_apply_gps_fix)


def _apply_gps_fix():
    """on_change for the GPS button: the value is {"lat", "lng", "accuracy", "ts"} or {"error", "ts"}."""
    fix = st.session_state.get("gps_button")
    if not fix:
        return
    if "error" in fix:
        st.session_state.gps_error = fix["error"]
    elif distance_m((fix["lat"], fix["lng"]), UF_CENTER) > FAR_FROM_UF_KM * 1000:
        miles = distance_m((fix["lat"], fix["lng"]), UF_CENTER) / 1609.34
        st.session_state.gps_error = (
            f"Your location is about {miles:,.0f} miles from UF, so walk times wouldn't help. "
            "Pick a campus spot instead."
        )
    else:
        st.session_state.origin = {
            "label": "Your location", "lat": fix["lat"], "lng": fix["lng"],
            "accuracy": fix.get("accuracy"), "source": "gps",
        }
        st.session_state.pop("gps_error", None)


def _pick_place():
    """on_change for the 'Walking from' dropdown, including its ✕ (clear) button."""
    place = st.session_state.get("origin_pick")
    if place is None:  # ✕ clicked: stop using a location
        st.session_state.origin = None
        st.session_state.pop("gps_error", None)
    elif place in CAMPUS_PLACES:
        lat, lng = CAMPUS_PLACES[place]
        st.session_state.origin = {"label": place, "lat": lat, "lng": lng, "source": "campus"}
        st.session_state.pop("gps_error", None)


def location_picker():
    """'Walking from' bar for the Search page: campus dropdown + GPS button + a status line."""
    st.markdown(
        """
        <style>
        .st-key-locbar {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 24px;
            padding: 0.9rem 1.5rem 1rem;
            max-width: 900px;
            margin: 0 auto 1rem;
        }
        .st-key-locbar label p { color: #0021A5 !important; font-weight: 700; }
        /* White dropdown with a light border (two selectors: older and newer Streamlit versions) */
        .st-key-locbar [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        .st-key-locbar [data-testid="stSelectbox"] [role="group"] {
            background: white !important;
            border: 2px solid #d5dcf0 !important;
            border-radius: 999px !important;
        }
        .st-key-locbar [data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
        .st-key-locbar [data-testid="stSelectbox"] [role="group"]:hover { border-color: #FA4616 !important; }
        .st-key-locbar [data-testid="stSelectbox"] [data-baseweb="select"] *,
        .st-key-locbar [data-testid="stSelectbox"] input,
        .st-key-locbar [data-testid="stSelectbox"] svg { color: #0021A5 !important; }
        .st-key-locbar [data-testid="stSelectbox"] input::placeholder { color: #5a6b8c !important; opacity: 1; }
        .st-key-locbar iframe { display: block; }
        .loc-status { color: #33415c; font-size: 0.92rem; margin: 0.15rem 0 0.1rem; }
        /* Streamlit pulls markdown up by 1rem; undo that here so the status line stays inside the box */
        .st-key-locbar [data-testid="stMarkdownContainer"]:has(.loc-status) { margin-bottom: 0 !important; }
        .loc-status b { color: #0021A5; }
        .loc-status.warn { color: #8a3a00; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="locbar"):
        pick_col, gps_col = st.columns([3, 1.25], vertical_alignment="bottom")

        origin = st.session_state.get("origin")
        using_gps = bool(origin and origin["source"] == "gps")
        with gps_col:
            location_button(active=using_gps)

        # Keep the dropdown in sync with the saved origin (widgets forget their value when you change pages).
        # While GPS is in use it shows "📍 Your current location", so its ✕ can clear that too.
        options = ([GPS_OPTION] if using_gps else []) + list(CAMPUS_PLACES)
        st.session_state.origin_pick = GPS_OPTION if using_gps else (origin["label"] if origin else None)
        with pick_col:
            st.selectbox(
                "🚶 Walking from",
                options=options,
                index=None,
                key="origin_pick",
                on_change=_pick_place,
                placeholder="Pick where you are on campus",
            )

        if st.session_state.get("gps_error"):
            st.markdown(f"<p class='loc-status warn'>⚠️ {st.session_state.gps_error}</p>", unsafe_allow_html=True)
        elif origin and origin["source"] == "gps":
            acc = origin.get("accuracy")
            acc_note = f" (±{acc:,.0f} m)" if acc else ""
            st.markdown(f"<p class='loc-status'>✅ Walk times from <b>your current location</b>{acc_note}</p>",
                        unsafe_allow_html=True)
        elif origin:
            st.markdown(f"<p class='loc-status'>✅ Walk times from <b>{origin['label']}</b></p>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<p class='loc-status'>Set where you are to see walk times. "
                "We also pick up buildings you mention, like “near Reitz”.</p>",
                unsafe_allow_html=True,
            )
