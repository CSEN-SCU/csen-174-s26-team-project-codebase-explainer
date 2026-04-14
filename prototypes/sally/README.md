# GitMap — Sally's Prototype

**For:** Developers joining an unfamiliar GitHub codebase  
**Problem:** Large repos are overwhelming — no clear picture of how components connect  
**Solution:** Paste a GitHub URL → AI maps the architecture as an interactive visual graph

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Frontend | HTML / CSS / Vanilla JS + Cytoscape.js |
| Backend  | Python + FastAPI                    |
| Database | SQLite (analysis cache)             |
| AI       | OpenAI GPT-4o                       |

---

## Setup & Run

### 1. Prerequisites

- Python 3.11+
- An OpenAI API key
- (Optional) A GitHub personal access token — raises the API rate limit from 60 → 5,000 req/hr

### 2. Create a virtual environment and install dependencies

> **Mac users (Homebrew Python):** You must use a venv or pip will refuse to install.

```bash
cd prototypes/sally/backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You'll see `(venv)` in your prompt when it's active. Run `source venv/bin/activate` again any time you open a new terminal window before starting the server.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your OPENAI_API_KEY (and optionally GITHUB_TOKEN)
```

### 4. Start the backend

Make sure your venv is active (`source venv/bin/activate`), then:

```bash
uvicorn main:app --reload
```

The API runs at **http://localhost:8000**  
The frontend is served at **http://localhost:8000** (open this in your browser)

---

## How to Demo

1. Open http://localhost:8000 in a browser
2. Paste any public GitHub URL — e.g. `https://github.com/tiangolo/fastapi`
3. Click **Analyze** and wait ~10–20 seconds for the AI to process
4. Explore the interactive graph:
   - **Click a node** to see what that component does and which files belong to it
   - **Scroll** to zoom, **drag** to pan
   - Highlighted edges show how that node connects to the rest of the system
5. Results are cached in SQLite — the second request for the same repo is instant
6. Click **↻ Re-analyze** to force a fresh AI pass

---

## API Endpoints

| Method | Path       | Description                                      |
|--------|------------|--------------------------------------------------|
| GET    | `/`        | Serves the frontend (index.html)                 |
| GET    | `/health`  | Health check                                     |
| POST   | `/analyze` | Analyze a repo (body: `{github_url, refresh?}`)  |
| GET    | `/recent`  | List recently analyzed repos from DB             |
| DELETE | `/cache`   | Clear cached result for a URL                    |

---

## What Satisfies the Requirements

- **Front end** — `frontend/index.html` (landing page + Cytoscape.js graph UI)
- **Back end** — FastAPI in `backend/`
- **Database** — SQLite via `database.py`; caches every analysis result
- **AI API** — OpenAI GPT-4o called in `ai_analyzer.py`
- **Intro screen** — Landing page explains the product, audience, problem, and how to use it
