# GitMap — CSEN 174

**GitMap** takes any public GitHub repository URL and turns it into an interactive visual map of its architecture. Paste a URL, get an AI-generated graph of modules, their relationships, and how data flows through the system — no reading source code required.

**Team:** Sally Kim · Jesse · Daniela

🔗 **Live demo:** [https://csen-174-s26-team-project-codebase-zufu.onrender.com](https://csen-174-s26-team-project-codebase-zufu.onrender.com)

---

## What it does

1. You paste a GitHub repo URL into the UI.
2. The backend fetches the repo's file tree and key source files via the GitHub API.
3. OpenAI (`gpt-4o`) analyzes the files and identifies the meaningful modules, their types, and their dependencies.
4. The result is cached in SQLite so repeat visits are instant.
5. The frontend renders two views side by side:
   - **Architecture** — an interactive node graph (Cytoscape.js) showing modules color-coded by type (entrypoint, service, database, config, etc.)
   - **Workflow** — an animated SVG diagram showing how data flows step by step through the system
   - **Full Map** — a Mermaid flowchart of the complete architecture with all edges

You can also ask follow-up questions about the repo in a chat panel powered by the same cached analysis.

---

## Project layout

```
final/                        ← the production app (start here)
  backend/
    main.py                   ← FastAPI app, all API routes
    ai_openai.py              ← OpenAI prompts, graph builder (_modules_to_graph)
    database.py               ← SQLite cache (analyses table)
    fetcher/
      github_fetcher.py       ← GitHub API: fetch tree + file contents
    analyzer/
      ai_analyzer.py          ← Shared utilities (format_tree, _should_ignore)
    requirements.txt
    .env.example              ← copy to .env and fill in keys
  frontend/
    index.html                ← entire frontend (single file, no build step)
  example_questions.py        ← generates suggested prompts based on repo node types

unitTesting/                  ← pytest suite for the final backend
  conftest.py                 ← adds final/backend to sys.path
  test_fetcher.py             ← GitHub fetcher + URL parser tests
  test_analyzer.py            ← AI response parsing + code context builder tests
  test_ai_behavior.py         ← end-to-end analyze_repo() mock tests
  test_chat.py                ← /api/chat endpoint tests
  test_integration.py         ← /api/analyze full-stack integration tests
  test_example_questions.py   ← example_questions.py logic tests

prototypes/                   ← earlier individual prototypes (reference only)
  sally/                      ← Sally's prototype (FastAPI + Vanilla JS)
  jesse/                      ← Jesse's prototype
  daniela/                    ← Daniela's prototype
```

---

## Running the app

### Prerequisites

- Python 3.11+
- An OpenAI API key (`OPENAI_API_KEY`)
- Optionally a GitHub personal access token (`GITHUB_TOKEN`) — avoids rate limiting on public repos

### 1. Start the backend

```bash
cd final/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Open .env and fill in OPENAI_API_KEY (and optionally GITHUB_TOKEN)
python3 -m uvicorn main:app --reload --port 8001
```

Backend runs at `http://localhost:8001`. You can verify it's up at `http://localhost:8001/api/health`.

### 2. Start the frontend

```bash
cd final/frontend
python3 -m http.server 5173
```

Open `http://127.0.0.1:5173` in your browser.

> **Important:** run `http.server` from inside `final/frontend/`, not from `final/`. If you see a directory listing instead of the UI, you're in the wrong folder.

---

## API routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/health` | Liveness check |
| `POST` | `/api/analyze` | Analyze a repo (`{ github_url, refresh? }`) |
| `POST` | `/api/chat` | Ask a question about an analyzed repo |
| `GET` | `/api/recent` | List recently analyzed repos |
| `GET` | `/api/example-questions` | Suggested prompts for the current repo |
| `DELETE` | `/api/cache` | Clear cached analysis for a repo |

The `/api/analyze` response includes `nodes`, `edges`, `summary`, `tech_stack`, and `workflow` fields that the frontend renders directly.

---

## Running tests

```bash
cd unitTesting
python3 -m pytest -v
```

The `conftest.py` adds `final/backend` to the Python path automatically, so the tests import from the real source. Tests use `unittest.mock` — no live API calls are made.

To run a specific file:
```bash
python3 -m pytest test_ai_behavior.py -v
```

Some tests are marked `@pytest.mark.skip` — these document planned features that aren't implemented yet (e.g., case-insensitive node type matching, capped question list length). They're intentionally skipped, not broken.

---

## How the AI analysis works

Two separate OpenAI calls happen per `analyze_repo()`:

1. **Architecture pass** — given the file tree and key file contents, the model returns a list of `modules` (each with a `path`, `type`, `description`, and `depends_on` list). The `_modules_to_graph()` function in `ai_openai.py` converts this into the `nodes`/`edges` graph the frontend renders.

2. **Workflow pass** — the model returns a sequential list of `steps` describing how a typical request flows through the system. Each step includes the files involved and is rendered as the animated SVG workflow panel.

Results are cached in `final/backend/gitmap.db` (SQLite). Re-analyzing the same repo skips the API calls unless you pass `"refresh": true`.

---

## Key design decisions

- **Modules, not directories.** The graph shows AI-identified logical components, not every folder in the repo. This keeps the visualization clean for large repos.
- **Fuzzy dependency resolution.** `depends_on: ["database"]` will match `database.py` even without the extension — handled by `_resolve()` in `ai_openai.py`.
- **Duplicate filename disambiguation.** If multiple modules share the same filename (e.g., three files named `main.py`), the label is prefixed with the parent directory automatically.
- **No build step.** The frontend is a single `index.html` file. Cytoscape.js and Mermaid are loaded from CDN.
- **SQLite cache.** No database server needed. The cache file lives at `final/backend/gitmap.db` and persists across restarts.
