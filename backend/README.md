# AI Chemistry Tutor — Backend

FastAPI backend that powers the AI Chemistry Tutor with OpenAI GPT.

## Requirements
- Python 3.10+
- OpenAI API key

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your OPENAI_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Send a message, receive AI response |
| GET | `/health` | Health check |

### Chat request body
```json
{
  "message": "What is the atomic number of carbon?",
  "conversation_history": []
}
```
