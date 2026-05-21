انا فاطمة بحاول اتواصل مع حد من التيم لان الواتس فيه مشكلة انه عمال يتحظر بدون اي سبب فاحتاج من حد يتواصل معايا علي رقمي التاني 201000327015 او علي ايميلي 
# n8n — Workflow Automation

This folder contains all n8n workflow configurations for the AI Chemistry Tutor project.

## What n8n is Used For

| Purpose | Description |
|---|---|
| **AI Model Integration** | Connect the backend to OpenAI / Gemini / local LLM via HTTP nodes |
| **Webhook Triggers** | Receive events from the FastAPI backend and trigger automated workflows |
| **Notifications** | Send email, push, or messaging notifications to users |
| **Workflow Automation** | Orchestrate multi-step processes without writing custom glue code |

---

## Folder Structure

```
n8n/
├── workflows/          ← Exported n8n workflow JSON files
│   ├── ai_pipeline.json          ← AI model request/response workflow
│   ├── webhook_triggers.json     ← Incoming webhook handlers
│   └── notifications.json        ← Email / push notification workflows
└── README.md
```

---

## Setup

### 1. Run n8n locally

```bash
# Using npx (no install needed)
npx n8n

# Or with Docker
docker run -it --rm \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

n8n will be available at `http://localhost:5678`.

### 2. Import a workflow

1. Open `http://localhost:5678`
2. Go to **Workflows → Import from file**
3. Select any `.json` file from the `workflows/` folder

### 3. Export a workflow

1. Open the workflow in the n8n editor
2. Go to **⋮ menu → Download**
3. Save the `.json` file into `workflows/`

---

## Workflows

### AI Pipeline (`ai_pipeline.json`)
Handles the connection between the FastAPI backend and the AI model provider.

**Flow:**
```
FastAPI backend → HTTP Request → AI Provider (OpenAI / Gemini) → Format Response → Return to backend
```

**Key nodes:**
- `Webhook` — receives requests from FastAPI
- `HTTP Request` — calls the AI provider API
- `Function` — formats and sanitizes the response

---

### Webhook Triggers (`webhook_triggers.json`)
Listens for events from the FastAPI backend (e.g., new user registered, session started).

**Flow:**
```
FastAPI event → n8n Webhook → Route by event type → Trigger downstream workflow
```

**Trigger events:**
- `user.registered` — new user signs up
- `session.started` — user starts a tutoring session
- `session.ended` — user ends a session

---

### Notifications (`notifications.json`)
Sends notifications to users based on workflow events.

**Flow:**
```
Trigger event → Build message → Send via Email / Push / Slack
```

**Channels (configure credentials in n8n):**
- Email — via SMTP or SendGrid node
- Push notifications — via Firebase or OneSignal node
- Slack / Teams — via built-in messaging nodes

---

## Environment Variables

Set these in your n8n instance under **Settings → Environment Variables** or via a `.env` file when self-hosting:

```env
# AI Provider
OPENAI_API_KEY=your-key-here
# or
GEMINI_API_KEY=your-key-here

# Backend webhook secret (to validate requests from FastAPI)
WEBHOOK_SECRET=change-me

# Notification channels (fill in when decided)
# SMTP_HOST=
# SMTP_USER=
# SMTP_PASSWORD=
# FIREBASE_SERVER_KEY=
```

---

## Connecting n8n to the FastAPI Backend

In `backend/.env`, add:

```env
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
```

The backend will POST events to n8n webhook URLs. n8n handles the rest.

---

## Notes

- Workflow JSON files are version-controlled here so the whole team can share and sync automations
- Never commit real API keys — use n8n's built-in **Credentials** system or environment variables
- n8n community nodes can be installed for additional integrations (Firebase, WhatsApp, etc.)
