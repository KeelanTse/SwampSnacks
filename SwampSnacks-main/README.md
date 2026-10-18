# 🐊 SwampSnacks

**An AI dining assistant for UF students. Tell it your time, budget, diet and where you are, and it finds food around campus and Gainesville that actually fits.**

> "I have 12 minutes between classes, $7 in my bank account, and I'm stuck near the Reitz Union."

---

## 💡 Inspiration

Life at UF can get overwhelming fast, with students and faculty alike struggling to find eateries that fit their day-to-day preferences and needs.

Standard map apps like Google Maps or Yelp fail to take campus life into consideration. They can't answer hyper-specific student queries like: *"I have 12 minutes between classes, $7 in my bank account, and I'm stuck near the Reitz Union."*

To combat this, we developed **SwampSnacks**: an AI assistant that recommends restaurants around Gainesville and campus, regardless of how specific the constraints may be!

## 🍽️ What it does

SwampSnacks is an **AI-powered dining recommender** designed specifically for the UF and Gainesville community.

- **Natural Language Queries:** Students can type exactly what they're feeling or experiencing (e.g., *"Need vegan options near Midtown before game day starts"*).
- **Context-Aware Recommendations:** SwampSnacks cross-references student prompts with a curated local database of Gainesville eateries, campus dining, and classic staples. Every pick comes with short "why we picked it" reasons.
- **Campus-Smart Logistics:** It provides not just restaurant names, but realistic walking times from major UF landmarks (or your phone's GPS), estimated prices, open/closed status, and campus-specific vibes.
- **Walking Directions:** One click opens Google Maps walking directions from where you are.
- **Gator Reviews:** Search every spot in the database, read what other students thought, and leave your own 1–5 star review.

## 🛠️ How we built it

As this was the first hackathon for our entire team, we aimed to use a familiar tech stack that we could all contribute towards. We chose to hardcode our dataset in a JSON file (`foodspots.json`) that features dining locations, price tiers, hours, proximity tags, and coordinates.

| Layer | Technology |
| --- | --- |
| Frontend & UI | Python, Streamlit |
| Backend | Python, Flask API |
| AI & Intelligence | Gemini API, Claude |
| Data | JSON restaurant database (`foodspots.json`) |
| Reviews storage | SQLite locally, Supabase (Postgres) on the live site |

---

## ✅ Prerequisites

| You need | Why | Where to get it |
| --- | --- | --- |
| **Python 3.10 or newer** | Runs the app | [python.org/downloads](https://www.python.org/downloads/) (check "Add Python to PATH" on Windows) |
| **pip** | Installs the packages in `requirements.txt` | Comes with Python |
| **A Gemini API key** | Powers the recommendations | Free from [Google AI Studio](https://aistudio.google.com/apikey) |
| **Git** *(optional)* | Clones the repo | [git-scm.com](https://git-scm.com/downloads), or use GitHub's **Code → Download ZIP** |
| **A Supabase account** *(optional)* | Keeps reviews saved on the deployed site | Free at [supabase.com](https://supabase.com) (see [Reviews on the live site](#-reviews-on-the-live-site)) |
| **A modern browser** | Chrome, Edge, Firefox or Safari | For the "📍 Use my location" button, the site must be on `https://` or `localhost` |

Python packages (installed in step 3 below): `streamlit`, `google-genai`, `flask`, `requests`, and `tzdata` (time zones on Windows).

> **No API key?** The app still runs. It falls back to simple keyword matching and shows a yellow notice on the Results page.

## 🚀 Getting started

**1. Get the code**

```bash
git clone https://github.com/KeelanTse/SwampSnacks.git
cd SwampSnacks
```

**2. (Recommended) Create a virtual environment**

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

**3. Install the packages**

```bash
pip install -r requirements.txt
```

**4. Add your Gemini API key**

Create a file called `.streamlit/secrets.toml` (next to `.streamlit/config.toml`) containing:

```toml
API_KEY = "your-gemini-api-key"
```

This file is in `.gitignore`. Never commit your key.

**5. Run it**

```bash
streamlit run FrontPage.py
```

Your browser opens at <http://localhost:8501>. Click **Find my food 🐊**, set where you're walking from, and describe what you want.

**Other ways to run it**

- **GitHub Codespaces:** open the repo in a Codespace. The included dev container installs everything and starts the app automatically (you still need to add `secrets.toml`).
- **Terminal chatbot:** `python app.py` gives a text-only version that's handy for testing prompts.

## ☁️ Deploying to Streamlit Community Cloud

1. Push the repo to GitHub.
2. At [share.streamlit.io](https://share.streamlit.io), click **Create app**, pick the repo, and set the main file to **`FrontPage.py`**.
3. In the app's **Settings → Secrets**, paste the contents of your `secrets.toml` (the Gemini key, plus the `[supabase]` section if you set it up).
4. Every push to the main branch redeploys the app automatically.

## ⭐ Reviews on the live site

With no extra setup, reviews are saved to a local `reviews.db` file. That's fine on your laptop, but **Streamlit Cloud deletes local files whenever the app restarts or redeploys**, so reviews on the live site would disappear. A free Supabase database fixes that (about 5 minutes):

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor**, paste this, and click **Run**:

   ```sql
   create table reviews (
     id bigint generated always as identity primary key,
     spot_id text not null,
     name text not null default 'Anonymous Gator',
     rating int not null check (rating between 1 and 5),
     text text not null check (char_length(text) <= 500),
     created_at timestamptz not null default now()
   );
   alter table reviews enable row level security;
   create policy "Anyone can read reviews" on reviews for select using (true);
   create policy "Anyone can add reviews" on reviews for insert with check (true);
   grant select, insert on table reviews to anon, authenticated;
   ```

3. Copy your **Project URL** and **publishable key** (older projects call it the **anon public** key). Both are in **Project Settings** (under API / API Keys), or click **Connect** at the top of the dashboard.
4. Add them to `.streamlit/secrets.toml` **and** to Streamlit Cloud's **Settings → Secrets**:

   ```toml
   [supabase]
   url = "https://YOUR-PROJECT.supabase.co"
   key = "YOUR-PUBLISHABLE-OR-ANON-KEY"
   ```

The app switches to Supabase automatically once those secrets exist. The policies only allow reading and adding reviews, so nobody can edit or delete them through the site. To remove spam, delete the row in Supabase's **Table Editor**.

## 📁 Project structure

```
FrontPage.py            Home page (run this with streamlit run)
pages/
  Search.py             "What are your cravings?" chat box + "Walking from" location picker
  Results.py            Recommendation cards: walk time, open status, ratings, directions
  Reviews.py            Search the database, read and post reviews
utils.py                Gemini calls, prompt, open/closed hours, shared page styling
walking.py              Walk-time estimates, campus starting points, GPS button
reviews.py              Saves and loads reviews (SQLite or Supabase)
components/
  location_button/      Small HTML component that asks the browser for GPS
foodspots.json          The restaurant database (hours, tags, prices, lat/lng, photos)
compressedImages/       Restaurant photos
app.py                  Terminal version of the chatbot
web_app.py              Experimental Flask API version (needs a templates/index.html page)
.streamlit/config.toml  Theme and layout settings
requirements.txt        Python packages
```

**Editing the database:** each spot in `foodspots.json` has an `id`, `name`, `zone`, `nearest_landmark`, `lat`/`lng`, `price_range`, `tags`, weekly `hours` (24-hour `"HH:MM-HH:MM"`, `"closed"` or `"unknown"`), `google_maps_url`, `speed`, and an optional `image`. Walk times use the `lat`/`lng` (accurate to about 100 m), so fix a spot's coordinates if its walk time looks off. Campus starting points are in `CAMPUS_PLACES` in `walking.py`.

## 🧭 What's next for SwampSnacks

- **Live Campus Crowding Integration:** Adding real-time crowd metrics/wait times.
- **Interactive Map Integration:** Embedding live Google Maps route visualizers into our Streamlit interface to provide directions.
- **Mobile Integration:** Transition from a Streamlit interface to a mobile-friendly application.
- **Improving Gemini:** Improving the accuracy and consistency of AI responses upon user inputs.
- **More User Interaction:** Building on Gator Reviews so students can rate individual dishes and submit feedback suggesting new restaurants or features to add.
