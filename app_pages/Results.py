import html

import streamlit as st
from reviews import all_reviews, stars, summarize
from utils import page_transition, card_styles, open_status, now_at_uf, show_spot_image
from walking import current_origin, directions_url, origin_description, walk_label

page_transition("Results")
card_styles()  # white result cards (shared with the Reviews page)

st.markdown(
    """
    <style>
    .results-heading { color: white !important; text-align: center; }
    .walk-note { color: #e8ecf8; text-align: center; margin: -0.4rem 0 1rem; }
    [data-testid="stAlert"] {
        background: rgba(255, 255, 255, 0.92);
        border-radius: 12px;
        max-width: 1100px;
        margin: 0 auto;
    }
    [data-testid="stAlert"] p { color: #6b4e00 !important; }  /* dark amber: readable on the white box */
    </style>
    """,
    unsafe_allow_html=True,
)

query = st.session_state.get("last_query")
results = st.session_state.get("last_results")
error = st.session_state.get("last_error")

if not results:
    st.markdown(
        "<h2 class='results-heading'>No search yet. Head to Search to find some food! 🐊</h2>",
        unsafe_allow_html=True,
    )
    st.stop()

# html.escape so a query like "<b>pizza" can't break the page layout
st.markdown(f"<h3 class='results-heading'>Results for: <i>{html.escape(query)}</i></h3>", unsafe_allow_html=True)

# Where walk times are measured from (GPS, picked building, or a building named in the search)
origin = current_origin(query)
if origin:
    st.markdown(f"<p class='walk-note'>🚶 Walk times from {html.escape(origin_description(origin))}</p>",
                unsafe_allow_html=True)
else:
    st.markdown("<p class='walk-note'>🚶 Want walk times? Set where you are on the Search page.</p>",
                unsafe_allow_html=True)

if error:
    st.warning(error, icon="⚠️")

try:
    ratings = summarize(all_reviews())
except Exception as e:  # review database unreachable: still show results, just without stars
    print(f"[SwampSnacks] Couldn't load reviews: {e!r}")
    ratings = {}

now = now_at_uf()
for spot in results:
    is_open, status = open_status(spot, now)
    with st.container(border=True, key=f"card_{spot['id']}"):
        # Text on the left, photo on the right, both vertically centered in the card
        info_col, img_col = st.columns([3, 2], gap="large", vertical_alignment="center")

        with info_col:
            st.markdown(f"#### {spot['name']}")
            st.write(f"📍 {spot['nearest_landmark']}  ·  {spot['price_range']}  ·  {spot['speed'].replace('_', ' ')}")
            walk = walk_label(origin, spot)
            if walk:
                st.write(walk)

            status_line = f"{'🟢' if is_open else ('⚪' if is_open is None else '🔴')} {status}"
            if spot["id"] in ratings:
                avg, count = ratings[spot["id"]]
                status_line += (f"  ·  <span class='stars'>{stars(avg)}</span> {avg:.1f} "
                                f"({count} review{'s' if count != 1 else ''})")
            st.markdown(status_line, unsafe_allow_html=True)

            reasons = spot.get("reasons")
            if reasons:
                st.markdown("**Why we picked it**")
                st.markdown("\n".join(f"- {r}" for r in reasons))
            else:
                st.write(" ".join(f"`{t}`" for t in spot.get("tags", [])[:6]))

            map_col, review_col, _ = st.columns([1, 1, 2])
            with map_col:
                walk_url = directions_url(origin, spot)
                if walk_url:
                    st.link_button("Get directions", walk_url)
                elif "google_maps_url" in spot:
                    st.link_button("Open in Google Maps", spot["google_maps_url"])
            with review_col:
                if st.button("⭐ Reviews", key=f"reviews_{spot['id']}"):
                    st.session_state.open_review = spot["id"]  # the Reviews page opens this spot
                    st.switch_page("app_pages/Reviews.py")

        with img_col:
            show_spot_image(spot)
