# AI Email Triage System

An end-to-end AI-powered email triage system that automatically reads incoming emails, classifies them, logs results to Google Sheets, and sends Slack alerts for blockers and high-priority issues, with zero manual intervention.

Built as a portfolio project to demonstrate real-world automation skills across LLM integration, workflow orchestration, and API development.

---

## What It Does

When an email arrives in Gmail, the system:

1. Detects it via n8n Gmail Trigger (polls every minute)
2. Sends the email content to a Flask API
3. An LLM reads and extracts structured information
4. Results are logged to Google Sheets automatically
5. If the email is a blocker or high priority, a Slack alert fires instantly

No manual work. No checking inboxes. No missed critical issues.

---

## System Architecture

```
Gmail Inbox
    │
    ▼
n8n Gmail Trigger (every minute)
    │
    ▼
HTTP Request → Flask API (server.py)
    │
    ▼
LLM Analysis (NVIDIA NIM / Llama 3.3 70B)
    │
    ▼
Structured JSON Output
    │
    ├──▶ Google Sheets (every email)
    │
    └──▶ Slack Alert (blockers + high priority only)
```

---

## Extracted Fields

Every email is analyzed and the following fields are extracted:

| Field | Description |
|---|---|
| `project` | Project name mentioned in the email |
| `category` | Delay, Blocker, Payment, Risk, Info Only, etc. |
| `priority` | High, Medium, or Low |
| `blocker` | true if something is stopping work |
| `deadline_risk` | true if a timeline is at risk |
| `action_needed` | What needs to happen next |
| `responsible_party` | Who should act |
| `summary` | One sentence summary |
| `confidence` | How confident the LLM is in its classification |
| `needs_review` | Flagged true if confidence is Low or Medium |
| `tags` | Relevant keywords |

---

## Example Output

**Input email:**
```
Subject: Concrete Delivery Delay - Block B

The concrete supplier informed us that delivery scheduled for Friday
will be delayed by 2 weeks. This will impact foundation work for Block B
and could push our handover date.
```

**Extracted JSON:**
```json
{
  "project": "Block B",
  "category": "Delay",
  "priority": "High",
  "blocker": true,
  "deadline_risk": true,
  "action_needed": "Find alternative supplier or negotiate new delivery date",
  "responsible_party": "Project Manager",
  "summary": "Concrete delivery for Block B delayed by 2 weeks",
  "confidence": "High",
  "needs_review": false,
  "tags": ["concrete", "delay", "Block B", "foundation"]
}
```

**Slack alert:**
```
🚨 Delay DETECTED

Project:       Block B
Priority:      High
Blocker:       true
Deadline Risk: true
Confidence:    High

Summary: Concrete delivery for Block B delayed by 2 weeks
Action:  Find alternative supplier or negotiate new delivery date

From:    Markus <markus@company.com>
Subject: Concrete Delivery Delay - Block B

✅ Logged to Google Sheets
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| n8n (Docker) | Workflow orchestration and Gmail trigger |
| Flask | REST API wrapping the LLM logic |
| NVIDIA NIM | LLM API endpoint |
| Llama 3.3 70B | Email classification and extraction |
| Gmail API | Email trigger via Google OAuth |
| Google Sheets | Structured output and logging |
| Slack | Real-time alerts for blockers |

---

## Project Structure

```
email-triage-ai/
├── email_triage.py        # Standalone extraction script with CSV output
├── server.py              # Flask API server for n8n integration
├── sample_emails/         # Test emails as .txt files
│   ├── delay_concrete.txt
│   ├── invoice_overdue.txt
│   ├── permit_approved.txt
│   └── vague_checkin.txt
├── outputs/               # CSV results (gitignored)
├── .env                   # API keys (gitignored)
├── .gitignore
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/email-triage-ai.git
cd email-triage-ai
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install openai flask python-dotenv
```

### 4. Set up environment variables

Create a `.env` file:

```
NVIDIA_API_KEY=your_nvidia_api_key_here
```

### 5. Run the standalone extraction test

```bash
python email_triage.py
```

### 6. Run the Flask API server

```bash
python server.py
```

### 7. Set up n8n

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  n8nio/n8n
```

Open `http://localhost:5678` and import the workflow.

---

## How to Add New Test Emails

Drop any `.txt` file into the `sample_emails/` folder and run:

```bash
python email_triage.py
```

No code changes needed.

---

## Confidence and Human Review

The system includes a confidence scoring mechanism:

- **High confidence** — email is clear and unambiguous, logged silently
- **Medium confidence** — some details missing, flagged for review
- **Low confidence** — vague or off-topic email, flagged for review

Emails flagged for review have `needs_review: true` in Google Sheets so a human can spot check them without reading every single email.

---

## Adapting to Other Stacks

This system is designed to be stack-agnostic:

| Component | Current | Alternative |
|---|---|---|
| Orchestration | n8n | Power Automate, Make |
| Email trigger | Gmail | Outlook via Graph API |
| LLM | Llama 3.3 70B | GPT-4, Azure OpenAI, Groq |
| Output | Google Sheets | SharePoint Lists, Airtable |
| Alerts | Slack | Microsoft Teams |

---

## Production Deployment

Currently runs locally. For production:

- Deploy `server.py` to a cloud provider (Railway, Render, AWS)
- Move n8n to n8n.cloud or a VPS
- System runs 24/7 without a local machine

---

## Use Cases

This system is applicable to any industry that processes high volumes of emails:

- Construction and real estate project management
- Legal firms tracking case communications
- Logistics and supply chain exception handling
- Finance teams processing invoices and approvals
- Healthcare admin routing patient communications