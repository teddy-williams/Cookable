from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json
import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

# =================== Config ===================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    raise Exception("Missing OPENROUTER_API_KEY. Add it in Render Environment Variables.")

app = Flask(__name__)
CORS(app)


# =================== Helpers ===================

def is_youtube_url(url: str) -> bool:
    return ("youtube.com" in url) or ("youtu.be" in url)


def extract_youtube_video_id(url: str) -> str | None:
    """
    Supports:
    - https://www.youtube.com/watch?v=VIDEOID
    - https://youtu.be/VIDEOID
    - https://www.youtube.com/shorts/VIDEOID
    """

    url = url.strip()

    # youtu.be/<id>
    m = re.search(r"youtu\.be\/([a-zA-Z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    # youtube.com/watch?v=<id>
    m = re.search(r"v=([a-zA-Z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    # youtube.com/shorts/<id>
    m = re.search(r"youtube\.com\/shorts\/([a-zA-Z0-9_-]{6,})", url)
    if m:
        return m.group(1)

    return None


def fetch_youtube_transcript(video_id: str) -> str:
    """
    Fetch transcript text. Tries English first, then any available.
    Returns a big text block.
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # Try English first
    try:
        transcript = transcript_list.find_transcript(["en"])
    except:
        # fallback: first transcript available
        transcript = transcript_list.find_generated_transcript(transcript_list._manually_created_transcripts.keys()) \
            if transcript_list._manually_created_transcripts else transcript_list.find_generated_transcript(
                transcript_list._generated_transcripts.keys()
            )

    lines = transcript.fetch()
    text = " ".join([x["text"] for x in lines])

    # Cleanup
    text = text.replace("\n", " ").strip()
    return text


def call_openrouter(system_prompt: str, user_prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
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
        "max_tokens": 800
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()
    data = response.json()
    raw_content = data["choices"][0]["message"]["content"].strip()

    # Remove markdown fences if model adds them
    raw_content = raw_content.replace("```json", "").replace("```", "").strip()

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


# =================== Core AI ===================

def analyze_recipe_video(video_url: str, pantry: list[str]) -> dict:
    """
    For YouTube links:
      - fetch transcript and feed it to LLM
    For non-YouTube:
      - fallback to link-only inference (for now)
    """

    system_prompt = """
You are a highly accurate cooking assistant.

You will be given:
- A recipe video URL
- The user's pantry list
- Sometimes a transcript of the recipe video

Your job:
1) Identify the dish name.
2) Extract a realistic full ingredient list.
3) Compare it to pantry.
4) Output ONLY valid JSON.

Rules:
- Prefer transcript content over guessing.
- Ingredients should be normalized (e.g., "olive oil" not "oil").
- If transcript mentions optional ingredients, include them as optional only if clearly stated.
- If unsure, assume the ingredient is required.
- No markdown. No explanations. JSON only.

Return JSON exactly:
{
  "dish_name": "string",
  "have": ["ingredient1", "ingredient2"],
  "need_to_buy": ["ingredient3", "ingredient4"],
  "confidence": number
}
"""

    transcript_text = ""
    transcript_status = "not_attempted"

    if is_youtube_url(video_url):
        video_id = extract_youtube_video_id(video_url)

        if video_id:
            try:
                transcript_text = fetch_youtube_transcript(video_id)
                transcript_status = "success"
            except (TranscriptsDisabled, NoTranscriptFound):
                transcript_status = "no_transcript"
            except VideoUnavailable:
                transcript_status = "unavailable"
            except Exception:
                transcript_status = "error"
        else:
            transcript_status = "bad_video_id"

    user_prompt = f"""
Video URL:
{video_url}

User pantry:
{", ".join(pantry)}

Transcript status:
{transcript_status}

Transcript text (if available):
{transcript_text[:12000]}

Now return JSON only.
"""

    result = call_openrouter(system_prompt, user_prompt)

    # Attach transcript status (useful for debugging)
    result["_debug"] = {
        "transcript_status": transcript_status,
        "transcript_length": len(transcript_text)
    }

    return result


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
