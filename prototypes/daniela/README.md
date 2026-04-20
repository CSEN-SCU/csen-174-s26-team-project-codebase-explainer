# Daniela prototype — GitMap

**Gallery-walk goal:** A visitor can read the intro, paste a public GitHub URL, see an architecture graph, and ask questions—without prior context.

**Stack:** **React (Vite)** in `frontend/` · **FastAPI** in `backend/` · **SQLite** cache · **GitHub GraphQL** for repo data · **Google Gemini** for graph JSON + chat answers.

---

## 1. Backend (terminal 1)

```bash
cd prototypes/daniela/backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY and preferably GITHUB_TOKEN
uvicorn main:app --reload --port 8001
```

Health check: `curl http://127.0.0.1:8001/api/health`

---

## 2. Frontend (terminal 2)

```bash
cd prototypes/daniela/frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api/*` to the backend on **8001**, so keep both processes running.

**Production-style preview (optional):** build the SPA and serve it while pointing API calls at the backend:

```bash
npm run build
npm run preview
# Set VITE_API_BASE=http://127.0.0.1:8001 if the preview host is not using the proxy
```

---

## What the UI does

1. **Intro** — Explains what GitMap is, who it is for, the problem (large repos hide structure), and how to run the demo (backend + URL).
2. **Workspace** — After analysis: **Cytoscape** graph (modules + edges), tech stack chips, optional node detail, and a **chat** panel that calls `POST /api/chat` using the cached architecture.

---

## Layout

```
prototypes/daniela/
  README.md
  backend/
    main.py
    database.py
    github_fetcher.py
    ai_analyzer.py
    requirements.txt
    .env.example
  frontend/
    package.json
    vite.config.js
    index.html
    src/
      main.jsx
      App.jsx
      api.js
      index.css
      components/
        IntroScreen.jsx
        Workspace.jsx
        ArchitectureGraph.jsx
        ChatPanel.jsx
```

SQLite database file `backend/gitmap.db` is ignored by git (see repo `.gitignore`).
