import streamlit as st
from utils import PAGE_ICON, set_background, show_banner, show_nav, load_spots, get_recommendations

st.set_page_config(page_title="Search", page_icon=PAGE_ICON, layout="wide")  # match the other pages
set_background()
show_banner()
show_nav("Search")

st.markdown("<h2 style='text-align: center; color: white;'>What are your cravings? 🐊</h2>", unsafe_allow_html=True)

# Chat box in SwampSnacks colors: white panel, UF orange border, UF blue text, orange send button
st.markdown(
    """
    <style>
    [data-testid="stChatInput"] {
        max-width: 900px;
        margin: 0 auto;
    }
    [data-testid="stChatInput"] > div {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid #FA4616 !important;
        border-radius: 999px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
        padding: 0.2rem 0.4rem 0.2rem 0.8rem;
    }
    [data-testid="stChatInput"] > div:focus-within {
        border-color: #0021A5 !important;   /* blue outline while typing */
        box-shadow: 0 0 0 3px rgba(250, 70, 22, 0.35);
    }
    [data-testid="stChatInput"] > div div {
        background: transparent !important;  /* remove Streamlit's gray inner layers */
    }
    [data-testid="stChatInputTextArea"] {
        color: #0021A5 !important;
        caret-color: #FA4616;
        font-size: 1.05rem !important;
    }
    [data-testid="stChatInputTextArea"]::placeholder {
        color: #5a6b8c !important;
        opacity: 1;
    }
    [data-testid="stChatInputSubmitButton"] {
        background: #FA4616 !important;
        border-radius: 999px !important;
    }
    [data-testid="stChatInputSubmitButton"] svg {
        fill: white !important;
        color: white !important;
    }
    [data-testid="stChatInputSubmitButton"]:hover {
        background: #d93a0f !important;
    }
    [data-testid="stChatInputSubmitButton"]:disabled {
        background: #fbb59f !important;     /* faded orange until something is typed */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

prompt = st.chat_input("e.g. 15 min between classes near Reitz, I'm broke, need vegan")

if prompt:
    with st.spinner("🐊 Gator Chef is cooking up recommendations..."):
        results, error = get_recommendations(prompt, load_spots())
        st.session_state.last_query = prompt
        st.session_state.last_results = results
        st.session_state.last_error = error  # shown on the Results page

    st.switch_page("pages/Results.py")
