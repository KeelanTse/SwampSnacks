import html

import streamlit as st
from utils import PAGE_ICON, set_background, show_banner, show_nav, open_status, now_at_uf, get_image

st.set_page_config(page_title="Results", page_icon=PAGE_ICON, layout="wide")
set_background()
show_banner()
show_nav("Results")

st.markdown(
    """
    <style>
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    /* Result cards: same white panel as the home page so text is readable over the photo */
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
    .results-heading { color: white !important; text-align: center; }
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

if error:
    st.warning(error, icon="⚠️")

now = now_at_uf()
for spot in results:
    is_open, status = open_status(spot, now)
    with st.container(border=True, key=f"card_{spot['id']}"):
        # Text on the left, photo on the right, both vertically centered in the card
        info_col, img_col = st.columns([3, 2], gap="large", vertical_alignment="center")

        with info_col:
            st.markdown(f"#### {spot['name']}")
            st.write(f"📍 {spot['nearest_landmark']}  ·  {spot['price_range']}  ·  {spot['speed'].replace('_', ' ')}")
            st.write(f"{'🟢' if is_open else '🔴'} {status}")

            reasons = spot.get("reasons")
            if reasons:
                st.markdown("**Why we picked it**")
                st.markdown("\n".join(f"- {r}" for r in reasons))
            else:
                st.write(" ".join(f"`{t}`" for t in spot.get("tags", [])[:6]))

            if "google_maps_url" in spot:
                st.link_button("Open in Google Maps", spot["google_maps_url"])

        with img_col:
            try:
                st.image(get_image(spot), width="stretch")
            except Exception:  # older Streamlit versions
                st.image(get_image(spot), use_container_width=True)
