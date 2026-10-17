"""Flask version of SwampSnacks that uses the browser's GPS location.

Run from the project folder:   python web_app.py
Needs:  templates/index.html   (Flask only looks for templates in a folder called "templates")
        .streamlit/secrets.toml with API_KEY = "..."
"""
import json
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from utils import ask_gemini, now_at_uf, spots_for_prompt

app = Flask(__name__)

# foodspots.json is the single source of truth (database.py was an exact copy of it)
with open(Path(__file__).parent / "foodspots.json") as f:
    SPOTS = json.load(f)

SYSTEM_PROMPT = """
You are an expert UF campus dining assistant chatbot.
Answer using ONLY the restaurant database the user message gives you.
Do not assume or invent information not found in the database. If a match isn't found, say so politely.
Each spot has "open_now" and "status" fields that were calculated for the current time; trust them.
Reply in plain text (no Markdown, no asterisks), because the web page shows it as plain text.
"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask-gemini", methods=["POST"])
def ask_gemini():
    data = request.get_json(silent=True) or {}
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")
    if user_lat is None or user_lon is None:
        return jsonify({"reply": "Missing location. Please allow location access and try again."}), 400

    now = now_at_uf()
    user_message = (
        f"Current time in Gainesville: {now:%A, %I:%M %p}\n"
        f"User location: latitude {user_lat}, longitude {user_lon} (near the UF campus)\n\n"
        "Using ONLY the database below, find the 3 closest dining spots that are open now "
        "and give a brief recommendation for each.\n\n"
        f"DATABASE:\n{spots_for_prompt(SPOTS, now)}"  # trimmed: no weekly hours/links = faster
    )

    try:
        # One independent request per click (low thinking, 12 s timeout, backup model).
        response = ask_gemini(user_message, SYSTEM_PROMPT)
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"[SwampSnacks] Gemini error: {e!r}")
        return jsonify({"reply": f"Error communicating with AI: {e}"}), 502


if __name__ == "__main__":
    app.run(debug=True)