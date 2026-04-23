# CSEN 174 — GitMap

**GitMap** turns any GitHub repository URL into an interactive visual map of its architecture, so developers new to a codebase can understand how everything connects at a glance.

## Team

- Sally Kim
- Jesse
- Daniela

## About

GitMap addresses the onboarding problem every developer faces when joining an existing project: large codebases are overwhelming, documentation is often missing or stale, and there's no quick way to see how components relate to each other. GitMap lets you paste a GitHub URL and get an AI-generated, interactive graph of the codebase's architecture in seconds.

See [`product-vision.md`](./product-vision.md) for the full product vision and problem framing.

## Prototypes

Each team member's prototype lives in their own directory under `prototypes/`:

| Directory            | Stack                        |
|----------------------|------------------------------|
| `prototypes/sally/`  | Python (FastAPI) + Vanilla JS |

To run a prototype, see the `README.md` inside its directory.

## Repo Structure

```
prototypes/          # Individual prototypes (one per team member)
architecture/        # C4 diagrams and design decisions
product-vision.md    # Shared product vision, HMW statement, and problem framing
.cursorrules         # AI tool context for the project (Cursor, etc.)
.gitignore           # Excludes secrets (.env) and build artifacts everywhere
```

## Backend Module Ownership

The backend is split into modules so teammates can work independently without merge conflicts:

| Module | Owner | Responsibility |
|---|---|---|
| `prototypes/sally/backend/analyzer/` | Sally | AI pipeline, graph builder |
| `prototypes/sally/backend/fetcher/` | Jesse | GitHub API fetching, SQLite cache |
| `prototypes/sally/backend/chat/` | Daniela | Q&A chatbot on top of cached analysis |
| `prototypes/sally/frontend/` | Sally | Interactive graph UI |

**Rule:** only edit your own module. If you need something from another module, import it — don't rewrite it. Coordinate in the group chat if an interface needs to change.

## Git Workflow

Each person works on their own branch and opens a pull request into `main` when something is ready. No one commits directly to `main`.

```
main                  ← stable, always working
├── sally-working     ← Sally  (analyzer/, frontend/)
├── jesse-working     ← Jesse  (fetcher/)
└── daniela-working   ← Daniela (chat/)
```

Daily workflow:

```bash
git checkout <your-branch>
git pull origin main          # stay up to date before starting
# ... edit only your module ...
git add <your-directory>/
git commit -m "feat: short description"
git push origin <your-branch>
# → open a PR on GitHub → teammate reviews → merge to main
```
