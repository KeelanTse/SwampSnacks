"""Review storage for the Reviews page.

Two backends, picked automatically:

* Supabase (a free hosted Postgres database). Used when .streamlit/secrets.toml
  (or the Streamlit Cloud "Secrets" box) contains:

      [supabase]
      url = "https://YOUR-PROJECT.supabase.co"
      key = "YOUR-ANON-OR-PUBLISHABLE-KEY"

  Reviews stay up for good, even when Streamlit Cloud restarts or redeploys the app.
  Setup steps are in README.md.

* reviews.db, a SQLite file next to this one. Used when there are no Supabase
  secrets. Works with zero setup on your own computer, but Streamlit Cloud wipes
  local files whenever the app restarts, so use Supabase for the live site.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

DB_PATH = Path(__file__).parent / "reviews.db"
TABLE = "reviews"
MAX_NAME = 40
MAX_TEXT = 500


# ---------- which backend? ----------

def _supabase():
    """(url, key) if Supabase secrets are set, else None."""
    try:
        cfg = st.secrets["supabase"]
        return cfg["url"].rstrip("/"), cfg["key"]
    except Exception:  # no secrets file, no [supabase] section, or a missing field
        return None


def using_supabase() -> bool:
    return _supabase() is not None


def _headers(key: str) -> dict:
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):  # legacy "anon" keys are JWTs and also go in Authorization
        headers["Authorization"] = f"Bearer {key}"
    return headers


# ---------- SQLite ----------

def _sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id TEXT NOT NULL,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    return conn


# ---------- public API ----------

@st.cache_data(ttl=60, show_spinner=False)
def all_reviews() -> list[dict]:
    """Every review, newest first: [{"spot_id", "name", "rating", "text", "created_at"}, ...].

    Cached for a minute so pages don't hit the database on every click;
    add_review() clears the cache so a new review shows up right away.
    """
    sb = _supabase()
    if sb:
        url, key = sb
        resp = requests.get(
            f"{url}/rest/v1/{TABLE}",
            params={"select": "spot_id,name,rating,text,created_at", "order": "created_at.desc"},
            headers=_headers(key),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    with _sqlite() as conn:
        rows = conn.execute(
            f"SELECT spot_id, name, rating, text, created_at FROM {TABLE} ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_review(spot_id: str, name: str, rating: int, text: str) -> None:
    """Save one review. Raises on a database/network error so the page can show a message."""
    row = {
        "spot_id": spot_id,
        "name": (name or "").strip()[:MAX_NAME] or "Anonymous Gator",
        "rating": max(1, min(5, int(rating))),
        "text": text.strip()[:MAX_TEXT],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    sb = _supabase()
    if sb:
        url, key = sb
        resp = requests.post(
            f"{url}/rest/v1/{TABLE}",
            json=row,
            headers={**_headers(key), "Prefer": "return=minimal"},
            timeout=10,
        )
        resp.raise_for_status()
    else:
        with _sqlite() as conn:
            conn.execute(
                f"INSERT INTO {TABLE} (spot_id, name, rating, text, created_at) VALUES (?, ?, ?, ?, ?)",
                (row["spot_id"], row["name"], row["rating"], row["text"], row["created_at"]),
            )
    all_reviews.clear()


def reviews_for(spot_id: str, reviews: list[dict]) -> list[dict]:
    return [r for r in reviews if r["spot_id"] == spot_id]


def summarize(reviews: list[dict]) -> dict[str, tuple[float, int]]:
    """{spot_id: (average rating, number of reviews)}"""
    totals: dict[str, list[int]] = {}
    for r in reviews:
        totals.setdefault(r["spot_id"], []).append(int(r["rating"]))
    return {sid: (sum(v) / len(v), len(v)) for sid, v in totals.items()}


def stars(rating: float) -> str:
    """4.4 -> '★★★★☆'"""
    full = int(round(rating))
    return "★" * full + "☆" * (5 - full)


def nice_date(iso: str) -> str:
    """'2026-10-18T00:31:05+00:00' -> 'Oct 17, 2026' (in Gainesville time)"""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        try:
            d = d.astimezone(ZoneInfo("America/New_York"))
        except Exception:  # Windows without the tzdata package: keep UTC
            pass
        return f"{d:%b} {d.day}, {d.year}"
    except Exception:
        return ""
