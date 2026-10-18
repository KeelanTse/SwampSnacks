import html
import time

import streamlit as st
from reviews import MAX_NAME, MAX_TEXT, add_review, all_reviews, nice_date, reviews_for, stars, summarize
from utils import page_transition, card_styles, show_spot_image, load_spots, now_at_uf, open_status
from walking import current_origin, directions_url, walk_label

card_styles()

st.markdown(
    """
    <style>
    .reviews-heading { color: white !important; text-align: center; margin-bottom: 0; }
    .reviews-sub { color: #e8ecf8; text-align: center; margin: 0.2rem 0 1rem; }
    .result-count { color: #e8ecf8; max-width: 1100px; margin: 0.25rem auto 0.5rem !important; }

    /* Search box: same white pill with an orange border as the Search page chat box */
    .st-key-review_search { max-width: 900px; margin: 0 auto; }
    .st-key-review_search [data-testid="stTextInputRootElement"] {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid #FA4616 !important;
        border-radius: 999px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
        padding: 0.15rem 0.6rem;
    }
    .st-key-review_search [data-testid="stTextInputRootElement"]:focus-within {
        border-color: #0021A5 !important;
        box-shadow: 0 0 0 3px rgba(250, 70, 22, 0.35);
    }
    .st-key-review_search [data-testid="stTextInputRootElement"] * { background: transparent !important; }
    .st-key-review_search input {
        color: #0021A5 !important;
        caret-color: #FA4616;
        font-size: 1.05rem !important;
    }
    .st-key-review_search input::placeholder { color: #5a6b8c !important; opacity: 1; }
    .st-key-review_search [data-testid="InputInstructions"] { display: none; }
    .st-key-review_search [data-testid="stElementContainer"]:has([data-testid="stRadio"]) {
        display: flex;
        justify-content: center;
    }
    .st-key-review_search [data-testid="stRadio"] label p { color: white !important; font-weight: 600; }

    /* List cards */
    [class*="st-key-card_list_"] h4 { margin-bottom: 0; }
    .snippet { color: #3d4660; font-style: italic; margin: 0.2rem 0 0.4rem; }
    .muted { color: #5a6b8c; }

    /* Review list + rating breakdown */
    .review { border-top: 1px solid #e3e7f2; padding: 0.75rem 0; }
    .review:first-child { border-top: none; padding-top: 0.25rem; }
    .review .who { color: #0021A5; font-weight: 700; }
    .review .when { color: #6b7590; font-size: 0.85rem; }
    .review p { margin: 0.3rem 0 0; color: #1a1a1a; }
    .big-rating { font-size: 2.2rem; font-weight: 700; color: #0021A5; line-height: 1; }
    .bars { margin-top: 0.4rem; }
    .bar-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #3d4660; }
    .bar { flex: 1; height: 8px; background: #e3e7f2; border-radius: 999px; overflow: hidden; }
    .bar > span { display: block; height: 100%; background: #FA4616; }

    /* Post button: UF orange like the home page button */
    [class*="st-key-card_write_"] [data-testid="stFormSubmitButton"] button {
        background-color: #FA4616;
        border: none;
        color: white;
        font-weight: 700;
    }
    [class*="st-key-card_write_"] [data-testid="stFormSubmitButton"] button:hover { background-color: #d93a0f; }
    [class*="st-key-card_write_"] label p { color: #0021A5 !important; font-weight: 600; }
    [class*="st-key-card_write_"] [data-testid="stTextInputRootElement"],
    [class*="st-key-card_write_"] [data-testid="stTextAreaRootElement"] {
        background: white !important;
        border: 2px solid #d5dcf0 !important;
        border-radius: 12px !important;
    }
    [class*="st-key-card_write_"] [data-testid="stTextInputRootElement"]:focus-within,
    [class*="st-key-card_write_"] [data-testid="stTextAreaRootElement"]:focus-within { border-color: #FA4616 !important; }
    [class*="st-key-card_write_"] [data-testid="stTextInputRootElement"] *,
    [class*="st-key-card_write_"] [data-testid="stTextAreaRootElement"] * { background: white !important; }
    [class*="st-key-card_write_"] input, [class*="st-key-card_write_"] textarea {
        color: #1a1a1a !important;
        caret-color: #FA4616;
    }
    [class*="st-key-card_write_"] input::placeholder,
    [class*="st-key-card_write_"] textarea::placeholder { color: #8a93ab !important; opacity: 1; }
    /* Star picker: grey stars, orange up to the one you picked */
    [class*="st-key-card_write_"] [data-testid="stFeedbackButton"] [data-testid="stIconMaterial"] {
        color: #c3cadb !important;
        font-size: 2rem;
    }
    [class*="st-key-card_write_"] [data-testid="stFeedbackButton"][aria-checked="true"] [data-testid="stIconMaterial"],
    [class*="st-key-card_write_"] [data-testid="stFeedbackButton"]:has(~ [aria-checked="true"]) [data-testid="stIconMaterial"],
    [class*="st-key-card_write_"] [data-testid="stFeedbackButton"]:hover [data-testid="stIconMaterial"] { color: #FA4616 !important; }
    [class*="st-key-card_write_"] [data-testid="stForm"] { border: none; padding: 0; }
    [class*="st-key-card_write_"] [data-testid="InputInstructions"] { color: #5a6b8c; }
    [class*="st-key-detail_wrap"] { max-width: 1100px; margin: 0 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

spots = load_spots()
by_id = {s["id"]: s for s in spots}

# Coming from a "⭐ Reviews" button on the Results page: open that spot.
# (Kept in the URL as ?spot=uf-010, so a spot's reviews can be linked to directly.)
if "open_review" in st.session_state:
    st.query_params["spot"] = st.session_state.pop("open_review")

# Smooth fade-in; also replays when you open a spot or go back to the list
page_transition("Reviews", view=st.query_params.get("spot", "list"))

if "review_posted" in st.session_state:
    st.toast(f"Thanks! Your review of {st.session_state.pop('review_posted')} is live 🐊")

try:
    reviews = all_reviews()
    load_error = None
except Exception as e:
    print(f"[SwampSnacks] Couldn't load reviews: {e!r}")
    reviews, load_error = [], "Couldn't reach the review database right now, so reviews aren't showing. Try again in a minute."
ratings = summarize(reviews)


def open_spot(spot_id: str):
    st.query_params["spot"] = spot_id


def back_to_list():
    st.query_params.pop("spot", None)


def rating_html(spot_id: str) -> str:
    if spot_id not in ratings:
        return "<span class='muted'>No reviews yet. Be the first!</span>"
    avg, count = ratings[spot_id]
    return f"<span class='stars'>{stars(avg)}</span> <b>{avg:.1f}</b> ({count} review{'s' if count != 1 else ''})"


def meta_line(spot: dict) -> str:
    return f"📍 {spot['nearest_landmark']}  ·  {spot['price_range']}  ·  {spot['speed'].replace('_', ' ')}"


selected = by_id.get(st.query_params.get("spot", ""))

# ======================= One spot: its reviews + the form to add one =======================
if selected:
    sid = selected["id"]
    spot_reviews = reviews_for(sid, reviews)

    with st.container(key="detail_wrap"):
        st.button("← All spots", on_click=back_to_list)
    if load_error:
        st.warning(load_error, icon="⚠️")

    with st.container(border=True, key=f"card_detail_{sid}"):
        info_col, img_col = st.columns([3, 2], gap="large", vertical_alignment="center")
        with info_col:
            st.markdown(f"#### {selected['name']}")
            st.write(meta_line(selected))
            origin = current_origin()
            walk = walk_label(origin, selected)
            if walk:
                st.write(walk)
            is_open, status = open_status(selected, now_at_uf())
            st.write(f"{'🟢' if is_open else ('⚪' if is_open is None else '🔴')} {status}")

            if spot_reviews:
                avg, count = ratings[sid]
                counts = {n: sum(1 for r in spot_reviews if int(r["rating"]) == n) for n in range(5, 0, -1)}
                bars = "".join(
                    f"<div class='bar-row'>{n}★<div class='bar'><span style='width:{100 * c / count:.0f}%'></span></div>{c}</div>"
                    for n, c in counts.items()
                )
                st.markdown(
                    f"<div class='big-rating'>{avg:.1f} <span class='stars' style='font-size:1.4rem'>{stars(avg)}</span></div>"
                    f"<div class='muted'>{count} review{'s' if count != 1 else ''}</div><div class='bars'>{bars}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(rating_html(sid), unsafe_allow_html=True)

            link = directions_url(origin, selected)
            if link:
                st.link_button("Get directions", link)
            elif "google_maps_url" in selected:
                st.link_button("Open in Google Maps", selected["google_maps_url"])
        with img_col:
            show_spot_image(selected)

    st.write("")
    with st.container(key="detail_wrap_2"):
        list_col, form_col = st.columns([3, 2], gap="medium")

    with form_col:
        with st.container(border=True, key=f"card_write_{sid}"):
            st.markdown("#### Leave a review")
            with st.form(f"review_form_{sid}", clear_on_submit=True):
                rating = st.feedback("stars", key=f"stars_{sid}")
                name = st.text_input("Your name", max_chars=MAX_NAME, placeholder="Anonymous Gator")
                text = st.text_area("Your review", max_chars=MAX_TEXT, height=120,
                                    placeholder="What did you get? Was it worth the walk?")
                submitted = st.form_submit_button("Post review 🐊", width="stretch")

            if submitted:
                last_post = st.session_state.get("last_review_time", 0)
                if rating is None:
                    st.error("Tap the stars to give it a rating.")
                elif len(text.strip()) < 5:
                    st.error("Write at least a few words about it.")
                elif time.time() - last_post < 20:
                    st.error("Slow down there, Gator. Wait a few seconds before posting again.")
                else:
                    try:
                        add_review(sid, name, rating + 1, text)  # st.feedback stars are 0-4
                    except Exception as e:
                        print(f"[SwampSnacks] Couldn't save review: {e!r}")
                        st.error("Couldn't save your review right now. Please try again.")
                    else:
                        st.session_state.last_review_time = time.time()
                        st.session_state.review_posted = selected["name"]
                        st.rerun()

    with list_col:
        with st.container(border=True, key=f"card_reviews_{sid}"):
            st.markdown("#### What Gators are saying")
            if spot_reviews:
                items = "".join(
                    "<div class='review'>"
                    f"<span class='stars'>{stars(int(r['rating']))}</span> "
                    f"<span class='who'>{html.escape(r['name'])}</span> "
                    f"<span class='when'>· {nice_date(r['created_at'])}</span>"
                    f"<p>{html.escape(r['text']).replace(chr(10), '<br>')}</p>"
                    "</div>"
                    for r in spot_reviews
                )
                st.markdown(f"<div>{items}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<p class='muted'>No reviews yet. Be the first to tell other Gators what you thought!</p>",
                            unsafe_allow_html=True)

    st.stop()

# ======================= All spots: search + list =======================
st.markdown("<h2 class='reviews-heading'>Gator Reviews ⭐</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='reviews-sub'>Search every spot in our database, see what other Gators think, and add your own review.</p>",
    unsafe_allow_html=True,
)

with st.container(key="review_search"):
    query = st.text_input(
        "Search spots",
        placeholder="🔍 Search by name, food, or location...",
        label_visibility="collapsed",
        key="review_q",
    )
    sort = st.radio("Sort by", ["Top rated", "Most reviewed", "A–Z"], horizontal=True,
                    label_visibility="collapsed", key="review_sort")

if load_error:
    st.warning(load_error, icon="⚠️")


def searchable(spot: dict) -> str:
    parts = [spot["name"], spot["zone"], spot["nearest_landmark"], spot["speed"], *spot["tags"]]
    return " ".join(parts).lower().replace("_", " ").replace("-", " ")


words = [w for w in query.lower().replace("_", " ").split() if w]
matches = [s for s in spots if all(w in searchable(s) for w in words)]

if sort == "Top rated":
    matches.sort(key=lambda s: (-ratings.get(s["id"], (0, 0))[0], -ratings.get(s["id"], (0, 0))[1], s["name"]))
elif sort == "Most reviewed":
    matches.sort(key=lambda s: (-ratings.get(s["id"], (0, 0))[1], s["name"]))
else:
    matches.sort(key=lambda s: s["name"].lower())

if not matches:
    st.markdown(
        f"<h3 class='reviews-heading'>No spots match “{html.escape(query)}”. Try a different word. 🐊</h3>",
        unsafe_allow_html=True,
    )
    st.stop()

limit = st.session_state.get("review_limit", 12)
shown = matches[:limit]
st.markdown(f"<p class='result-count'>{len(matches)} spot{'s' if len(matches) != 1 else ''}</p>",
            unsafe_allow_html=True)

latest = {}
for r in reviews:  # reviews are newest first
    latest.setdefault(r["spot_id"], r)

with st.container(key="detail_wrap_3"):
    for row_start in range(0, len(shown), 2):
        cols = st.columns(2, gap="medium")
        for col, spot in zip(cols, shown[row_start:row_start + 2]):
            with col:
                with st.container(border=True, key=f"card_list_{spot['id']}"):
                    st.markdown(f"#### {spot['name']}")
                    st.write(meta_line(spot))
                    st.markdown(rating_html(spot["id"]), unsafe_allow_html=True)
                    if spot["id"] in latest:
                        r = latest[spot["id"]]
                        snippet = r["text"] if len(r["text"]) <= 110 else r["text"][:107].rstrip() + "…"
                        st.markdown(
                            f"<p class='snippet'>“{html.escape(snippet)}” · {html.escape(r['name'])}</p>",
                            unsafe_allow_html=True,
                        )
                    st.button("Read & write reviews →", key=f"open_{spot['id']}", on_click=open_spot, args=(spot["id"],))

if len(matches) > limit:
    _, mid, _ = st.columns([2, 1, 2])
    with mid:
        if st.button(f"Show more ({len(matches) - limit} left)", width="stretch"):
            st.session_state.review_limit = limit + 12
            st.rerun()
