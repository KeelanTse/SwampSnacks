import streamlit as st
from utils import PAGE_ICON, set_background, show_banner

st.set_page_config(page_title="SwampSnacks", page_icon=PAGE_ICON, layout="wide")
set_background()
show_banner()

st.markdown(
    """
    <style>
    .intro {
        background: rgba(255, 255, 255, 0.92);
        border-radius: 24px;
        padding: 2rem 2.5rem;
        margin: 2rem auto 1.5rem;
        max-width: 900px;
        color: #1a1a1a;
        text-align: center;
    }
    .intro h2 { color: #0021A5; margin-top: 0; }
    .steps {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
        text-align: left;
    }
    .step {
        flex: 1;
        background: #f2f5ff;
        border-left: 4px solid #FA4616;
        border-radius: 12px;
        padding: 1rem;
    }
    .step b { color: #0021A5; }
    .stButton > button[kind="primary"] {
    background-color: #FA4616;
    border: none;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 0.6rem 0;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #d93a0f;
    }
    </style>

    <div class="intro">
        <h2>Find food that fits your day, not just your cravings.</h2>
        <p>
            Tell SwampSnacks what you're working with (time between classes,
            budget, diet, where you are on campus, who you're with) and we'll
            match you with spots on and around UF that actually fit.
        </p>
        <div class="steps">
            <div class="step"><b>1. Describe your situation</b><br>
                "20 minutes near Marston, under $10, vegetarian."</div>
            <div class="step"><b>2. We match your constraints</b><br>
                Location, price, speed, diet, and vibe, all at once.</div>
            <div class="step"><b>3. Pick a spot and go</b><br>
                One tap opens directions in Google Maps.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Center the button using columns
left, middle, right = st.columns([2, 1, 2])
with middle:
    if st.button("Find my food 🐊", width="stretch", type="primary"):
        st.switch_page("pages/Search.py")