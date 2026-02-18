from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
from dotenv import load_dotenv

# Load .env locally (Render ignores .env, it uses Dashboard env vars)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    raise Exception("OPENROUTER_API_KEY is missing! Set it in Render Environment Variables.")

app = Flask(__name__)
CORS(app)

# =================== AI Logic ===================
def analyze_recipe_video(video_url: str, pantry: list[str]) -> dict:
    system_prompt = """
You are a highly accurate cooking assistant.

Your task is to analyze a recipe video link and determine ingredients.

Rules:
- Extract the dish name if possible.
- Use the URL context (title, description, transcript if available).
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
        # OpenRouter recommends these (they can be anything valid)
        "HTTP-Referer": "https://cookable.onrender.com",
        "X-Title": "Cookable"
    }

    payload = {
        "model": "openai/gpt-4o-mini",
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
        timeout=60
    )

    # If OpenRouter returns an error, show it clearly
    if response.status_code != 200:
        return {
            "error": f"OpenRouter HTTP error: {response.status_code}",
            "raw": response.text
        }

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"]

    try:
        return json.loads(raw_content)
    except:
        return {
            "dish_name": "Unknown recipe",
            "have": [],
            "need_to_buy": [],
            "confidence": 0,
            "error": "Invalid JSON from model",
            "raw": raw_content
        }

# =================== Routes ===================
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "Cookable API is running. Use POST /analyze"
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    video_url = data.get("video_url")
    pantry = data.get("pantry", [])

    if not video_url:
        return jsonify({"error": "video_url is required"}), 400

    if not isinstance(pantry, list):
        return jsonify({"error": "pantry must be a list"}), 400

    result = analyze_recipe_video(video_url, pantry)
    return jsonify({"result": result})

# =================== Run ===================
if __name__ == "__main__":
    app.run(debug=True)
