# GitMap — Architecture Documentation

## Consolidation Plan

The team is building on **Sally's prototype** as the foundation. The core pipeline — GitHub URL → file tree → AI analysis → interactive graph — is already working end-to-end. We are adding Daniela's chat panel concept (ask questions about the repo after analysis) and keeping Jesse's simpler scoping (focus on explaining structure, not raw code).

**What we're keeping from each prototype:**
- Sally: FastAPI backend, OpenAI GPT-4o, SQLite caching, Cytoscape.js graph, progressive disclosure tree, walkthrough view
- Daniela: chat panel UX pattern (ask the architecture questions after analysis)
- Jesse: nothing technical, but the principle of keeping AI explanations plain and short

**What we're leaving behind:**
- Daniela's React/Vite frontend (adds build complexity for no gain at this stage), Gemini API, quiz panel
- Jesse's C++ backend, raw code paste input, no-graph approach

**Tech stack:**
- Frontend: Single-file HTML + Cytoscape.js + Mermaid.js (no build step, opens in browser directly)
- Backend: Python + FastAPI + uvicorn
- Database: SQLite (zero-config, single file, sufficient for prototype scale)
- AI: OpenAI GPT-4o via the OpenAI Python SDK
- GitHub data: GitHub REST API via httpx

**Ownership:**
- Sally — AI analyzer, graph engine, frontend views (interactive + walkthrough)
- Daniela — chat integration (POST /chat endpoint + chat UI panel)
- Jesse — GitHub fetcher, SQLite cache layer

---

## Level 1 — System Context

GitMap sits between one type of user and two external systems. A developer or student who needs to understand an unfamiliar codebase pastes a GitHub URL and receives an interactive architecture map within seconds — no cloning, no reading, no guessing. GitMap calls GitHub to get the raw repository contents and OpenAI to interpret them. Nothing else crosses the system boundary.

```mermaid
graph TD
    User(["👤 Developer / Student\nPastes a GitHub URL,\nexplores architecture"])
    GitMap["🗺️ GitMap\nTurns any public GitHub URL\ninto an interactive architecture map"]
    GitHub(["⚙️ GitHub REST API\nProvides file tree\nand raw file contents"])
    OpenAI(["🤖 OpenAI API - GPT-4o\nGenerates module descriptions,\ntech stack and dependency edges"])

    User -->|"paste URL, explore graph, ask questions"| GitMap
    GitMap -->|"GET file tree + file contents / HTTPS"| GitHub
    GitMap -->|"POST tree + snippets, receive JSON analysis / HTTPS"| OpenAI

    style User fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style GitMap fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style GitHub fill:#fef3c7,stroke:#f59e0b,color:#451a03
    style OpenAI fill:#dcfce7,stroke:#16a34a,color:#14532d
```

---

## Level 2 — Component Diagram (FastAPI API)

The FastAPI backend is the orchestration layer. It exposes four endpoints, each owned by a distinct Python module. The `/analyze` route is the most complex — it is the only one that calls external services, and only when the SQLite cache has no stored result for the requested repo. All other routes are thin wrappers that read from or write to the local cache with no external calls.

```mermaid
graph TD
    User(["👤 User"])
    FE["🖥️ Frontend\nHTML, Cytoscape.js, Mermaid.js\nInteractive graph, Walkthrough, Chat panel"]
    DB[("🗄️ SQLite Cache\nAnalyses stored by owner/repo")]
    GitHub(["⚙️ GitHub REST API"])
    OpenAI(["🤖 OpenAI API - GPT-4o"])

    subgraph API ["⚡ FastAPI Backend"]
        Analyze["POST /analyze\nCache-first: check DB, fetch repo,\nrun AI, save, return graph"]
        Chat["POST /chat\nQ&A on cached analysis"]
        Recent["GET /recent\nLanding page history"]
        Clear["DELETE /cache\nInvalidate cached result"]
        Fetcher["📡 GitHub Fetcher - Jesse\nFetches file tree and file contents"]
        Analyzer["🧠 AI Analyzer - Sally\nBuilds graph from real file tree via GPT-4o"]
        ChatMod["💬 Chat Module - Daniela\nAnswers questions using cached graph"]
    end

    User -->|"browser"| FE
    FE -->|"POST /analyze"| Analyze
    FE -->|"POST /chat"| Chat
    FE -->|"GET /recent"| Recent
    FE -->|"DELETE /cache"| Clear
    Analyze -->|"cache hit: read / miss: write"| DB
    Analyze -->|"on cache miss"| Fetcher
    Analyze -->|"after fetch"| Analyzer
    Chat --> ChatMod
    ChatMod -->|"reads cached graph"| DB
    Recent -->|"read"| DB
    Clear -->|"delete"| DB
    Fetcher -->|"HTTPS"| GitHub
    Analyzer -->|"HTTPS"| OpenAI
    ChatMod -->|"HTTPS"| OpenAI

    style FE fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style Analyze fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style Chat fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style Recent fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style Clear fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    style Fetcher fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style Analyzer fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style ChatMod fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style DB fill:#fef3c7,stroke:#f59e0b,color:#451a03
    style GitHub fill:#f1f5f9,stroke:#94a3b8,color:#334155
    style OpenAI fill:#dcfce7,stroke:#16a34a,color:#14532d
```

---

## Key Design Decisions

**Why does the file tree drive graph structure, not the AI?**
Early versions let GPT-4o decide which nodes to create. It hallucinated directories that didn't exist and missed real ones. The fix: graph structure is built algorithmically from the real GitHub file tree. AI only fills in descriptions and suggests dependency edges. The graph is always grounded in reality.

**Why SQLite instead of Postgres?**
SQLite has zero setup — no separate server process, no connection string, no migrations tool. It lives in a single file and handles our read-heavy workload (most requests are cache hits) without connection pooling. If the product scaled to many concurrent users we'd add a job queue and switch to Postgres, but that's premature at prototype stage.

**Why a single HTML file for the frontend instead of React?**
A single HTML file means anyone on the team (or a gallery walk visitor) can open it directly in a browser with no npm install, no build step, no tooling. The tradeoff is harder component reuse — acceptable for a prototype. The standalone `demo.html` takes this further and needs no backend at all, making it useful for offline demos.

**Why separate modules for fetcher, analyzer, and chat?**
Each module has a distinct external dependency (GitHub API, OpenAI for analysis, OpenAI for chat) and a distinct owner. Keeping them in separate directories means teammates can develop and test independently with no merge conflicts. `main.py` only imports and wires them together — it has no business logic of its own.

**What would break at scale?**
The main bottleneck is holding an HTTP connection open while GitMap calls two external APIs sequentially. For large repos this can take 10–15 seconds. At scale we'd make analysis async: the frontend submits a job, the backend returns a job ID immediately, and the frontend polls for the result. We'd also add a job queue (Celery + Redis) so multiple analyses can run in parallel without blocking each other.
