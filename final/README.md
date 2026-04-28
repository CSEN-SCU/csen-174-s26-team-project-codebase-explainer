# Final (Daniela + Sally merge)

This folder is the current final prototype:

- **Frontend:** Sally-style single-file UI with onboarding and chat elements.
- **Backend AI:** OpenAI (`gpt-4o`) only (no Gemini).
- **GitHub fetch:** REST API flow (no GraphQL).

## Folder contents

- `backend/main.py` - FastAPI app exposing `/api/health`, `/api/analyze`, `/api/chat`, `/api/recent`, `/api/cache`, and `/api/example-questions`.
- `backend/ai_openai.py` - OpenAI analyze/chat logic.
- `backend/database.py` - SQLite cache used by final backend.
- `backend/.env.example` - required environment variables.
- `frontend/index.html` - final frontend (served statically).
- `example_questions.py` - single source of example prompt strings for final.
- `test_final_prompts.py` - unit tests for final prompt function.

## Run final app

### 1) Start backend

```bash
cd final/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill OPENAI_API_KEY and optionally GITHUB_TOKEN
python3 -m uvicorn main:app --reload --port 8001
```

### 2) Start frontend

```bash
cd final/frontend
python3 -m http.server 5173
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Testing

- Final prompt tests:

```bash
python3 -m pytest final/test_final_prompts.py -v
```

- unitTesting suite (now wired to final backend):

```bash
cd unitTesting
python3 -m pytest -v
```
