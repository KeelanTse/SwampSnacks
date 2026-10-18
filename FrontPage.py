"""Starts SwampSnacks: run with  streamlit run FrontPage.py

This file runs before every page. It draws the background, banner and nav bar once,
then shows the page you're on. Because the top bar is drawn here (not on each page),
it stays perfectly still when you switch pages.
"""
import streamlit as st
from utils import PAGE_ICON, set_background, show_banner, show_nav

st.set_page_config(page_icon=PAGE_ICON, layout="wide")  # each page's browser-tab title comes from st.Page below

# Every page in the app. The nav bar links in utils.show_nav() use these same file paths.
PAGES = {
    "Home": st.Page("app_pages/Home.py", title="SwampSnacks", default=True),
    "Search": st.Page("app_pages/Search.py", title="Search"),
    "Results": st.Page("app_pages/Results.py", title="Results"),
    "Reviews": st.Page("app_pages/Reviews.py", title="Reviews"),
}
current = st.navigation(list(PAGES.values()), position="hidden")  # our own nav bar replaces the sidebar
name = next(n for n, p in PAGES.items() if p.url_path == current.url_path)

set_background()
show_banner()
if name != "Home":  # the home page has its own big button instead of the nav bar
    show_nav(name)

current.run()
