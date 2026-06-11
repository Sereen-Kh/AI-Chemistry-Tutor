# AI Chemistry Tutor

An AI-powered chemistry tutor app built with **Flutter** (frontend) and **FastAPI** (backend).

## Features

- 🧪 Interactive chemistry Q&A powered by Google Gemini
- 💬 Chat interface with full conversation history
- 📝 Markdown rendering for formatted responses (equations, lists, code)
- ✨ Animated typing indicator while the AI responds
- 🌙 Light & dark theme (follows system setting)
- 📱 Cross-platform: iOS, Android, Web, and Desktop

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flutter + Provider (state management) |
| Backend | Python + FastAPI |
| AI | Google Gemini (gemini-2.0-flash by default) |

## Project Structure

```
AI-Chemistry-Tutor/
├── backend/          # Python FastAPI app (Gemini integration)
└── frontend/         # Flutter app (cross-platform UI)
```

## Quick Start

**1. Start the backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY
uvicorn app.main:app --reload
```

**2. Start the frontend**
```bash
cd frontend
flutter pub get
flutter run
```

See each subdirectory's README for detailed setup instructions:
- [Backend Setup](./backend/README.md)
- [Frontend Setup](./frontend/README.md)
