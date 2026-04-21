# GitMap — C4 Architecture Diagrams

## Context Diagram

> **What does our system talk to?**
> GitMap sits between a developer and the complexity of an unfamiliar codebase. It talks to two external systems: GitHub (to get the code) and OpenAI (to understand it).

```mermaid
C4Context
  title System Context — GitMap

  Person(user, "Developer / Student", "Wants to quickly understand the structure of an unfamiliar GitHub repository")

  System(gitmap, "GitMap", "Turns any public GitHub URL into an interactive visual architecture map with AI-generated module descriptions")

  System_Ext(github, "GitHub REST API", "Provides the repository file tree and raw file contents for any public repo")
  System_Ext(openai, "OpenAI API (GPT-4o)", "Generates per-module descriptions, tech stack, and dependency edges from the file tree and code snippets")

  Rel(user, gitmap, "Pastes a GitHub URL, explores the architecture graph")
  Rel(gitmap, github, "Fetches recursive file tree and key file contents", "HTTPS")
  Rel(gitmap, openai, "Sends tree-formatted structure + file snippets, receives module descriptions", "HTTPS")
```

---

## Container Diagram

> **What are the big pieces, and how do they connect?**
> The frontend is a single HTML file served directly by the backend. The backend has three clear responsibilities: fetch (GitHub), analyze (AI), and cache (SQLite). The AI analyzer is the only component that talks to OpenAI — everything else is isolated.

```mermaid
C4Container
  title Container Diagram — GitMap

  Person(user, "Developer / Student", "Opens GitMap in a browser")

  System_Boundary(gitmap, "GitMap") {

    Container(frontend, "Frontend", "HTML · Cytoscape.js · Mermaid.js", "Single-page app: landing form, interactive graph (expandable tree), flowchart view, and step-by-step walkthrough view")

    Container(api, "FastAPI Backend", "Python · FastAPI · uvicorn", "Exposes REST endpoints: POST /analyze, GET /recent, DELETE /cache. Orchestrates fetching, analysis, and caching")

    Container(fetcher, "GitHub Fetcher", "Python · httpx", "Fetches the full recursive file tree and raw content of up to 25 priority files (README, entry points, config files)")

    Container(analyzer, "AI Analyzer", "Python · OpenAI SDK", "Formats file tree as tree-command output, sends to GPT-4o with file snippets, builds graph nodes and edges from real file paths (AI cannot invent structure)")

    ContainerDb(db, "SQLite Cache", "SQLite", "Stores every completed analysis so repeat lookups return instantly without re-calling GitHub or OpenAI")
  }

  System_Ext(github_api, "GitHub REST API", "Returns recursive blob tree and raw file content for any public repository")
  System_Ext(openai_api, "OpenAI API (GPT-4o)", "Returns JSON: summary, tech stack, per-module descriptions, and dependency edges")

  Rel(user, frontend, "Pastes GitHub URL, clicks Analyze, explores graph", "Browser")
  Rel(frontend, api, "POST /analyze · GET /recent", "HTTP/JSON")
  Rel(api, db, "Read cached result / write new result", "SQL")
  Rel(api, fetcher, "Calls get_repo_data(url)", "In-process")
  Rel(api, analyzer, "Calls analyze_repo(repo_data)", "In-process")
  Rel(fetcher, github_api, "GET /repos/:owner/:repo/git/trees (recursive) + /contents/:path", "HTTPS")
  Rel(analyzer, openai_api, "chat.completions.create — json_object mode — GPT-4o", "HTTPS")
  Rel(db, api, "Returns cached nodes, edges, summary", "SQL")
```

---

## Key design decisions

**Why does the file tree drive graph structure, not the AI?**
Early versions let GPT-4o invent the graph. It hallucinated nodes that didn't exist and missed real directories. Now the graph structure comes entirely from the real GitHub file tree — AI only adds descriptions and dependency edges. This makes the output verifiable and reproducible.

**Why SQLite instead of Postgres?**
GitMap is a prototype used by a small team for demos. SQLite has zero setup cost, stores everything in a single file, and handles our read-heavy workload (most analyses are cache hits) without connection pooling. If this scaled to many concurrent users we'd switch to Postgres.

**Why a single HTML file for the frontend instead of React?**
React would add a build step (npm, Vite, bundler) that every teammate needs to run locally. A single HTML file means anyone can open it directly in a browser — including the standalone `demo.html` which needs no backend at all. The tradeoff is that component reuse is harder, but for a prototype with one main view this is acceptable.

**What would break at scale?**
The biggest bottleneck is the sequential dependency on two external APIs (GitHub then OpenAI). For large repos, GitHub's tree API can be slow and OpenAI has rate limits. At scale we'd add a job queue (e.g. Celery + Redis) so analysis runs async and the frontend polls for results, rather than holding the HTTP connection open.
