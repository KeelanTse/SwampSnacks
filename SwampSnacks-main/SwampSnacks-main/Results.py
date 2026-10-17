import html

import streamlit as st
from utils import set_background, show_banner, show_nav, open_status, now_at_uf

st.set_page_config(page_title="Results", page_icon="🐊", layout="wide")
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
        padding: 0.5rem 1rem;
        color: #1a1a1a;
        animation: fadeUp 0.5s ease-out both;
    }
    [class*="st-key-card_"] h4 { color: #0021A5 !important; }
    .results-heading { color: white !important; text-align: center; }
    [data-testid="stAlert"] { background: rgba(255, 255, 255, 0.92); border-radius: 12px; }
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
        st.markdown(f"#### {spot['name']}")
        st.write(f"📍 {spot['nearest_landmark']}  ·  {spot['price_range']}  ·  {spot['speed'].replace('_', ' ')}")
        st.write(f"{'🟢' if is_open else '🔴'} {status}")

        st.write(" ".join(f"`{t}`" for t in spot.get("tags", [])[:6]))

        if "google_maps_url" in spot:
            st.link_button("Open in Google Maps", spot["google_maps_url"])
