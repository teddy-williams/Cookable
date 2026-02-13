from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json

# =================== Config ===================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    raise Exception("Missing OPENROUTER_API_KEY. Add it in Render Environment Variables.")

app = Flask(__name__)
CORS(app)

# =================== AI Logic ===================
def analyze_recipe_video(video_url: str, pantry: list[str]) -> dict:
    """
    Analyze a recipe video link and return structured ingredient data.
    NOTE: The model cannot truly 'watch' the video from a link.
    It will infer from whatever metadata is available.
    """

    system_prompt = """
You are a highly accurate cooking assistant.

The user provides a recipe video link. You must infer the dish and ingredients.

Rules:
- Extract the dish name if possible.
- Infer ingredients from the URL text and likely recipe patterns.
- Cross-check ingredients against the user's pantry.
- If unsure, assume the ingredient is required.
- Return ONLY valid JSON. No explanations. No markdown.

Output JSON format:
{
  "dish_name": "string",
  "have": ["ingredient1", "ingredient2"],
  "need_to_buy": ["ingredient3", "ingredient4"],
  "confidence": number
}
"""

    user_prompt = f"""
Video URL:
{video_url}

User pantry:
{", ".join(pantry)}

Return JSON only.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # OpenRouter recommends these:
        "HTTP-Referer": "https://cookable.onrender.com",
        "X-Title": "Cookable (FridgeToFork)"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        "temperature": 0.2,
        "max_tokens": 600
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=45
    )

    response.raise_for_status()
    data = response.json()

    raw_content = data["choices"][0]["message"]["content"].strip()

    # Sometimes models wrap JSON in ```json ... ```
    raw_content = raw_content.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw_content)

        # Defensive cleanup (avoid crashes)
        return {
            "dish_name": parsed.get("dish_name", "Unknown recipe"),
            "have": parsed.get("have", []),
            "need_to_buy": parsed.get("need_to_buy", []),
            "confidence": parsed.get("confidence", 0)
        }

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

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Cookable API is running. Use POST /analyze"
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}

    video_url = data.get("video_url", "").strip()
    pantry = data.get("pantry", [])

    if not video_url:
        return jsonify({"error": "Missing video_url"}), 400

    if not isinstance(pantry, list):
        return jsonify({"error": "pantry must be a list"}), 400

    try:
        result = analyze_recipe_video(video_url, pantry)
        return jsonify({"result": result})
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"OpenRouter HTTP error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =================== Local Run ===================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
