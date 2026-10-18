import streamlit as st
from utils import PAGE_ICON, page_transition, set_background, show_banner, show_nav, load_spots, get_recommendations
from walking import current_origin, location_picker

st.set_page_config(page_title="Search", page_icon=PAGE_ICON, layout="wide")  # match the other pages
set_background()
show_banner()
page_transition("Search")
show_nav("Search")

st.markdown("<h2 style='text-align: center; color: white;'>What are your cravings? 🐊</h2>", unsafe_allow_html=True)

# "Walking from" bar: campus dropdown + GPS button, used for walk times on the Results page
location_picker()

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
    /* "Gator Chef is cooking..." loading message: centered white pill */
    .st-key-cooking { align-items: center; }
    .st-key-cooking [data-testid="stSpinner"] {
        display: flex;
        justify-content: center;
        margin: 1.5rem auto 0;
    }
    .st-key-cooking [data-testid="stSpinner"] > div {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #FA4616;
        border-radius: 999px;
        padding: 0.7rem 1.6rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
        align-items: center;
        gap: 0.6rem;
    }
    .st-key-cooking [data-testid="stSpinner"] p {
        color: #0021A5 !important;
        font-weight: 700;
        font-size: 1.05rem;
    }
    .st-key-cooking [data-testid="stSpinnerIcon"],
    .st-key-cooking [data-testid="stSpinner"] i {
        border-color: rgba(250, 70, 22, 0.25) !important;
        border-top-color: #FA4616 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

prompt = st.chat_input("e.g. 15 min between classes near Reitz, I'm broke, need vegan")

if prompt:
    with st.container(key="cooking"):  # centered loading message (styled above)
        with st.spinner("🐊 Gator Chef is cooking up recommendations..."):
            results, error = get_recommendations(prompt, load_spots(), origin=current_origin(prompt))
            st.session_state.last_query = prompt
            st.session_state.last_results = results
            st.session_state.last_error = error  # shown on the Results page

    st.switch_page("pages/Results.py")
