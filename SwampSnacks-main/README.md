# SwampSnacks

A chatbot that finds food on and around UF's campus based on your time, budget, diet, and where you are.

## Run it

```
pip install -r requirements.txt
streamlit run FrontPage.py
```

`.streamlit/secrets.toml` needs your Gemini key:

```toml
API_KEY = "your-gemini-key"
```

## Walk times

* On the **Search** page, the "Walking from" bar lets you pick a campus building or tap
  **📍 Use my location** (browser GPS). If you skip it, buildings named in the search
  ("near Reitz", "at Marston") are used instead.
* Result cards show `🚶 6 min walk · 0.3 mi`, and **Get directions** opens Google Maps walking directions.
* Gemini also gets each spot's `walk_min`, so short walks rank higher when you're in a hurry.
* Every spot in `foodspots.json` has approximate `lat`/`lng` (within about 100 m). If a walk time
  looks off, fix that spot's coordinates. Campus starting points live in `walking.py` (`CAMPUS_PLACES`).
* Browsers only share GPS on `https://` sites (Streamlit Cloud is fine) or `http://localhost`.

## Reviews

The **Reviews** page lets anyone search the database, read reviews, and post a 1–5 star review.

**Where reviews are saved:**

* **No setup:** a local `reviews.db` file. Good for testing on your laptop, but Streamlit Cloud
  deletes local files whenever the app restarts or redeploys, so reviews on the live site would disappear.
* **Live site (keeps reviews for good):** a free Supabase database. About 5 minutes of setup:

1. Create a free project at <https://supabase.com>.
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

3. Copy your **Project URL** and **publishable key** (older projects call it the **anon public** key).
   Both are in **Project Settings** (under API / API Keys), or click **Connect** at the top of the dashboard.
4. Add them to `.streamlit/secrets.toml` locally **and** to the app's **Settings → Secrets** on Streamlit Cloud:

   ```toml
   [supabase]
   url = "https://YOUR-PROJECT.supabase.co"
   key = "YOUR-PUBLISHABLE-OR-ANON-KEY"
   ```

The app switches to Supabase automatically once those secrets exist. The policies only allow
reading and adding reviews, so nobody can edit or delete them through the site.
To remove spam, delete the row in Supabase's **Table Editor**.
