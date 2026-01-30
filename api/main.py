import json
import os
import requests

def handler(request):
    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Only POST allowed"})
        }

    try:
        body = json.loads(request.body)
        video_url = body.get("url")

        if not video_url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing video URL"})
            }

        response = requests.post(
            "https://flavorfetch.dev/api/v1/extract",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.environ.get("FLAVORFETCH_API_KEY")
            },
            json={"url": video_url},
            timeout=30
        )

        if response.status_code != 200:
            return {
                "statusCode": response.status_code,
                "body": json.dumps({
                    "error": "FlavorFetch API error",
                    "details": response.text
                })
            }

        return {
            "statusCode": 200,
            "body": json.dumps(response.json())
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
