# main.py
from flask import Flask, request, jsonify
import os
import requests
import json
from dotenv import load_dotenv

# =================== Load environment ===================
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise Exception("Please set OPENROUTER_API_KEY in your .env file!")

OPENROUTER_URL = "https://api.openrouter.ai/v1/chat/completions"

# =================== Flask App ===================
app = Flask(__name__, static_url_path="", static_folder="pages")

# =================== AI Logic ===================
def analyze_recipe_video(video_url: str, pantry: list[str]) -> dict:
    """
    Analyze a recipe video link (YouTube, Instagram, TikTok, etc.)
    and return structured ingredient data.
    """

    system_prompt = """
You are a highly accurate cooking assistant.

Your task is to analyze a recipe video link from any social media platform
(YouTube, Instagram, TikTok, Facebook, etc.) and determine the ingredients.

Rules:
- Extract the dish name if possible.
- Infer ingredients from the video title, description, transcript, and visuals.
- Cross-check ingredients against the user's pantry.
- If unsure, assume the ingredient is required.
- Return ONLY valid JSON. No explanations. No markdown.
"""

    user_prompt = f"""
Video URL:
{video_url}

User pantry:
{", ".join(pantry)}

Return JSON exactly in this format:
{{
  "dish_name": "string",
  "have": ["ingredient1", "ingredient2"],
  "need_to_buy": ["ingredient3", "ingredient4"],
  "confidence": number
}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "FridgeToFork"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    raw_content = data["choices"][0]["message"]["content"]

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        return {
            "dish_name": "Unknown recipe",
            "have": [],
            "need_to_buy": [],
            "confidence": 0,
            "error": "Invalid JSON from model",
            "raw": raw_content
        }

# =================== Routes ===================
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    video_url = data.get("video_url")
    pantry = data.get("pantry", [])

    if not video_url or not isinstance(pantry, list):
        return jsonify({"error": "Invalid request"}), 400

    try:
        result = analyze_recipe_video(video_url, pantry)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =================== Serve Frontend ===================
@app.route("/")
def index():
    return app.send_static_file("index.html")

# =================== Run ===================
if __name__ == "__main__":
    app.run(debug=True)
