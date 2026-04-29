import os
import csv
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Client setup
# ---------------------------------------------------------------------------

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL      = "meta/llama-3.3-70b-instruct"
OUTPUT_CSV = "outputs/triage_results.csv"
EMAILS_DIR = "sample_emails"

CSV_COLUMNS = [
    "timestamp",
    "project",
    "category",
    "priority",
    "blocker",
    "deadline_risk",
    "action_needed",
    "responsible_party",
    "summary",
    "tags",
    "sender_intent",
    "confidence",
    "needs_review",
]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an intelligent email triage assistant.

Your job is to read incoming business emails and extract key information from them regardless of industry — construction, legal, logistics, finance, healthcare, or any other domain.

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
# Load emails from files
# ---------------------------------------------------------------------------

def load_emails(directory: str) -> list[tuple[str, str]]:
    """
    Load all .txt files from the given directory.
    Returns a list of (filename, content) tuples, sorted by filename.
    """
    folder = Path(directory)

    if not folder.exists():
        print(f"❌  Folder '{directory}' not found.")
        return []

    files = sorted(folder.glob("*.txt"))

    if not files:
        print(f"❌  No .txt files found in '{directory}'.")
        return []

    emails = []
    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        emails.append((f.name, content))

    return emails


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def analyze_email(email_text: str) -> dict:
    """
    Send an email to the LLM and return extracted fields as a dict.
    Raises json.JSONDecodeError if the model returns unexpected output.
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


def save_to_csv(results: list[dict]) -> None:
    """
    Append a list of triage results to the CSV file.
    Creates the file with headers if it doesn't exist yet.
    """
    file_exists = os.path.isfile(OUTPUT_CSV)

    with open(OUTPUT_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")

        if not file_exists:
            writer.writeheader()

        for row in results:
            row["tags"] = ", ".join(row.get("tags", []))
            writer.writerow(row)


def print_result(i: int, filename: str, result: dict, timestamp: str) -> None:
    """Print a single triage result in a readable format."""

    priority_icon   = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(result["priority"], "⚪")
    confidence_icon = {"High": "✅", "Medium": "⚠️ ", "Low": "❓"}.get(result.get("confidence", ""), "")
    blocker_text    = "YES ⚠️ " if result["blocker"] else "no"
    deadline_text   = "YES ⚠️ " if result["deadline_risk"] else "no"
    review_text     = "  👁  NEEDS REVIEW" if result.get("needs_review") else ""

    print(f"\n📧  {filename}  |  {timestamp}{review_text}")
    print(f"    Project    : {result['project']}")
    print(f"    Category   : {result['category']}")
    print(f"    {priority_icon} Priority  : {result['priority']}  |  Blocker: {blocker_text}  |  Deadline Risk: {deadline_text}")
    print(f"    {confidence_icon} Confidence: {result.get('confidence')} — {result.get('confidence_reason')}")
    print(f"    Summary    : {result['summary']}")
    if result.get("action_needed"):
        print(f"    Action     : {result['action_needed']}")


def print_summary(results: list[dict]) -> None:
    """Print a final summary after all emails are processed."""

    high         = sum(1 for r in results if r["priority"] == "High")
    medium       = sum(1 for r in results if r["priority"] == "Medium")
    low          = sum(1 for r in results if r["priority"] == "Low")
    blockers     = sum(1 for r in results if r["blocker"])
    needs_review = sum(1 for r in results if r.get("needs_review"))

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print(f"  Processed     : {len(results)} emails")
    print(f"  🔴 High       : {high}")
    print(f"  🟡 Medium     : {medium}")
    print(f"  🟢 Low        : {low}")
    print(f"  🚨 Blockers   : {blockers}")
    print(f"  👁  Need Review: {needs_review}")
    print(f"  💾 Saved to   : {OUTPUT_CSV}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  EMAIL TRIAGE SYSTEM — Extraction Test")
    print("=" * 60)

    emails  = load_emails(EMAILS_DIR)
    results = []

    for i, (filename, email_text) in enumerate(emails, start=1):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result    = analyze_email(email_text)

            result["timestamp"] = timestamp
            results.append(result)

            print_result(i, filename, result, timestamp)

        except json.JSONDecodeError as e:
            print(f"\n❌  {filename} — could not parse JSON: {e}")

        except Exception as e:
            print(f"\n❌  {filename} — unexpected error: {e}")

        print("\n" + "-" * 60)

    if results:
        save_to_csv(results)

    print_summary(results)