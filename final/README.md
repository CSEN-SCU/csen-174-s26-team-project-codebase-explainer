# Final merge scaffold (Daniela + Sally)

This folder is the merge point for the final prototype:

- **Frontend experience**: Daniela's onboarding + chatbot UI
- **AI provider**: Sally's OpenAI-based API approach (no Gemini)
- **GitHub data fetch**: Sally's REST API fetcher (no GraphQL)

## What is in this folder

- `backend/main.py`: FastAPI backend with `/api/*` routes compatible with Daniela frontend.
- `backend/ai_openai.py`: OpenAI analysis + chat implementation.
- `backend/.env.example`: Environment variables for OpenAI + GitHub.
- `backend/requirements.txt`: Python dependencies for the merged backend.
- `frontend/index.html`: Sally-style single-file frontend with onboarding + chatbot.

The backend intentionally reuses existing repo utilities from `prototypes/daniela/backend`
for SQLite cache, while using Sally's REST fetcher for repository data.

## Run merged setup

### 1) Start merged backend (OpenAI)

```bash
cd prototypes/final/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill OPENAI_API_KEY and optionally GITHUB_TOKEN
uvicorn main:app --reload --port 8001
```

### 2) Run final frontend (Sally UI + onboarding + chatbot)

```bash
cd prototypes/final/frontend
python3 -m http.server 5173
```

Open `http://localhost:5173`.

## Notes

- This merge scaffold removes Gemini usage entirely in the final backend.
- Frontend is based on Sally's style and includes onboarding + chat elements.
