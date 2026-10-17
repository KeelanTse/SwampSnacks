import streamlit as st
from utils import set_background, show_banner, show_nav, load_spots, get_recommendations

st.set_page_config(page_title="Search", page_icon="🐊", layout="wide")  # match the other pages
set_background()
show_banner()
show_nav("Search")

st.markdown("<h2 style='text-align: center; color: white;'>What are your cravings? 🐊</h2>", unsafe_allow_html=True)

prompt = st.chat_input("e.g. 15 min between classes near Reitz, I'm broke, need vegan")

if prompt:
    with st.spinner("🐊 Gator Chef is cooking up recommendations..."):
        results, error = get_recommendations(prompt, load_spots())
        st.session_state.last_query = prompt
        st.session_state.last_results = results
        st.session_state.last_error = error  # shown on the Results page

    st.switch_page("pages/Results.py")
