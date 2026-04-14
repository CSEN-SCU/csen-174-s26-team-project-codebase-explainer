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
product-vision.md    # Shared product vision, HMW statement, and problem framing
.cursorrules         # AI tool context for the project (Cursor, etc.)
.gitignore           # Excludes secrets (.env) and build artifacts everywhere
```
