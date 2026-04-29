import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL = "meta/llama-3.3-70b-instruct"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a project management assistant for a construction company.

Your job is to read incoming emails and extract key information from them.

Always reply with a single valid JSON object. No explanation. No markdown. No extra text.

JSON structure:

{
  "project":           "Project name, or 'Unknown' if not mentioned",
  "sender_intent":     "What the sender is trying to communicate or request",
  "category":          "Delay | Blocker | Action Required | Approval Needed | Info Only | Payment | Risk | Other",
  "priority":          "High | Medium | Low",
  "blocker":           true or false,
  "deadline_risk":     true or false,
  "action_needed":     "What needs to happen next, or null",
  "responsible_party": "Who should act on this, or null",
  "summary":           "One clear sentence describing the email",
  "tags":              ["relevant", "keywords"],
  "confidence":        "High | Medium | Low",
  "confidence_reason": "One sentence explaining why you are or are not confident"
}

Guidelines:
- Set blocker to true if something is actively preventing work from continuing
- Set deadline_risk to true if a date or delivery window is at risk
- Set confidence to High if the email is clear and unambiguous
- Set confidence to Medium if some details are missing or unclear
- Set confidence to Low if the email is vague, off-topic, or hard to classify
- Keep everything concise — no padding, no repetition
"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def analyze_email(email_text: str) -> dict:
    """
    Send email text to the LLM and return extracted fields as a dict.
    """
    chunks = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this email:\n\n{email_text.strip()}"},
        ],
        temperature=0.2,
        top_p=0.95,
        max_tokens=1024,
        stream=True,
    )

    raw = ""
    for chunk in chunks:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            raw += delta

    raw = raw.strip()

    # Strip markdown code fences if the model adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)

    # Flag for human review if confidence is not High
    result["needs_review"] = result.get("confidence") in ("Low", "Medium")

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Simple health check to confirm the server is running."""
    return jsonify({"status": "ok", "model": MODEL})


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Accepts a POST request with email text and returns structured JSON.

    Expected request body:
    {
        "email": "raw email text here"
    }
    """
    data = request.get_json()

    if not data or "email" not in data:
        return jsonify({"error": "Missing 'email' field in request body"}), 400

    email_text = data["email"]

    if not email_text.strip():
        return jsonify({"error": "Email text is empty"}), 400

    try:
        result = analyze_email(email_text)
        return jsonify(result)

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Could not parse LLM response as JSON: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  EMAIL TRIAGE API SERVER")
    print("  Running on http://localhost:8001")
    print("  POST /analyze  — analyze an email")
    print("  GET  /health   — check server status")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8001, debug=False)