import json
import os
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

def extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None

def get_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([seg["text"] for seg in transcript])

def extract_recipe_with_llm(transcript):
    prompt = f"""
You are a professional chef.

Extract a cooking recipe from the transcript below.

Return STRICT JSON only. No markdown. No explanations.

Format:
{{
  "title": "Dish name",
  "ingredients": ["ingredient 1", "ingredient 2"],
  "instructions": ["step 1", "step 2"]
}}

Transcript:
\"\"\"
{transcript}
\"\"\"
"""

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You extract structured recipes."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        },
        timeout=40
    )

    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)

def handler(request):
    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "POST only"})
        }

    try:
        body = json.loads(request.body)
        video_url = body.get("url")

        if not video_url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing YouTube URL"})
            }

        video_id = extract_video_id(video_url)
        if not video_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid YouTube URL"})
            }

        transcript = get_transcript(video_id)
        recipe = extract_recipe_with_llm(transcript)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "title": recipe.get("title"),
                "ingredients": recipe.get("ingredients", []),
                "instructions": recipe.get("instructions", [])
            })
        }

    except (TranscriptsDisabled, NoTranscriptFound):
        return {
            "statusCode": 422,
            "body": json.dumps({"error": "No transcript available for this video"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
