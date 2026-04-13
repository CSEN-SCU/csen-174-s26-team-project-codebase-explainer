# GitMap Backend — Workflow

## Overview

The backend is a Python FastAPI service. It accepts a GitHub URL, fetches the
repository structure, sends it to an AI model for analysis, and returns a
structured graph (nodes + edges) that the frontend renders as an interactive diagram.

---

## Request Flow

```
Client
  │
  │  POST /analyze  { "github_url": "https://github.com/tiangolo/fastapi" }
  ▼
main.py  (FastAPI)
  │
  ├──▶ github_fetcher.py
  │       1. Parse owner/repo from URL
  │       2. Fetch full file tree via GitHub API (recursive)
  │       3. Select most relevant files (entry points, configs, source)
  │       4. Fetch file contents concurrently
  │
  └──▶ ai_analyzer.py
          5. Build prompt with file tree + contents
          6. Send to OpenAI (gpt-4o) with JSON response format
          7. Parse and return structured JSON
  │
  ▼
Response: { repo, summary, tech_stack, nodes, edges }
```

---

## File Structure

```
backend/
├── main.py             # FastAPI app — defines /analyze and /health endpoints
├── github_fetcher.py   # GitHub API calls — fetch tree and file contents
├── ai_analyzer.py      # AI prompt + response parsing
├── test.py             # Quick test script against tiangolo/fastapi
├── requirements.txt    # Python dependencies
├── .env.example        # Template for environment variables (safe to commit)
├── .env                # Your actual keys — DO NOT commit this file
├── .gitignore
├── HowTo.md            # Run commands and links
└── Workflow.md         # This file
```

---

## API Endpoints

### `GET /health`
Returns `{ "status": "ok" }`. Used to verify the server is running.

### `POST /analyze`
**Request body:**
```json
{ "github_url": "https://github.com/tiangolo/fastapi" }
```

**Response:**
```json
{
  "repo": "tiangolo/fastapi",
  "summary": "Plain-English overview of the project.",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
  "nodes": [
    {
      "id": "auth",
      "label": "Auth Module",
      "type": "module",
      "description": "Handles user login and JWT tokens.",
      "files": ["auth/routes.py", "auth/models.py"]
    }
  ],
  "edges": [
    { "source": "main", "target": "auth", "label": "imports" }
  ]
}
```

**Node types:** `module`, `service`, `config`, `entrypoint`, `external`, `database`, `test`

**Edge labels:** `imports`, `calls`, `extends`, `configures`, `stores`

---

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in your real keys
python3 -m uvicorn main:app --reload
```

Server runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `GITHUB_TOKEN` | No | GitHub personal access token — raises rate limit from 60 to 5000 req/hr |

---

## Switching from OpenAI to Claude

Only `ai_analyzer.py` needs to change. The prompt format and response shape
are identical — swap the client and model, and the rest of the app is unaffected.

```python
# Replace OpenAI client:
from openai import AsyncOpenAI
client = AsyncOpenAI()

# With Anthropic client:
import anthropic
client = anthropic.Anthropic()
```

Also update `requirements.txt`: `openai` → `anthropic`
and `.env`: `OPENAI_API_KEY` → `ANTHROPIC_API_KEY`.
