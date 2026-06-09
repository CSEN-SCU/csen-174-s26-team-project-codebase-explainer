GitMap — Final Technical Report

CSEN 174 · Spring 2026 Team: Sally Kim · Jesse · Daniela Casillas Repository: csen-174-s26-team-project-codebase-explainer Code freeze (demo night): commit `49bf927` Live deployment: https://csen-174-s26-team-project-codebase-zufu.onrender.com Demo video: linked from README.md (team recording for W9)

1. Product vision and evolution

W2 summary (before)

In Week 2 we framed GitMap for coders joining a GitHub project with an already-large codebase who struggle to see how parts connect outside their assigned slice. The product would be a visual mapping assistant that turns a repo into interactive graphs, unlike text-only explainers (`docs/product-vision.md`). Input was loosely described as “upload repo”; interaction included zooming and filtering cluttered diagrams. Current summary (after)

Today GitMap is for developers and CS students onboarding to unfamiliar public repos: paste a URL, receive an AI-generated architecture graph (6–14 logical modules), an animated runtime workflow, and a chat panel grounded in cached analysis (`product-vision.md`). Input is GitHub URL only (no upload). We traded generic “filter components” for two dedicated views—structure vs. execution flow. Before / after at a glance

Originally GitMap focused on helping developers navigate large codebases through interactive repository graphs. By code freeze, the product evolved into a GitHub URL–based architecture and workflow visualization tool for developers and CS students onboarding to unfamiliar repositories.

The largest change was replacing filtering/full-map interactions with separate architecture and workflow views.

Decisions that bent the vision

Architecture + Workflow tabs replaced the original filtering/full-map concept after user feedback showed that users cared more about understanding system structure and execution flow than manipulating graph controls.

Persona / storyboard artifact

W2 narrative in `docs/product-vision.md` centers the student or new hire assigned a ticket without system context—still our primary user. The W3 gallery-walk intro screen in Daniela’s React prototype (`prototypes/daniela/frontend/src/components/IntroScreen.jsx`, `prototypes/daniela/README.md`) storyboarded the same journey: read the problem → paste URL → see graph → ask questions. We still serve that user; we dropped Daniela’s quiz panel and Gemini stack as out of scope (`docs/architecture/architecture.md` consolidation plan).

Repo reference: `product-vision.md` (current Moore’s template), `docs/product-vision.md` (W2 draft).

2. Architecture evolution (W4 → W8 → code freeze)

W4 — intended architecture (Week 4)

Single-file HTML (Cytoscape + Mermaid), FastAPI with three owner modules (fetcher / analyzer / chat), one GPT-4o call per analysis, graph structure from real file tree with AI descriptions only.
![W4 Architecture](docs/images/w4.png)

Repo reference: `docs/architecture/architecture.md` (Level 1–2 diagrams, “file tree drives graph structure”). W8 — revised architecture (after consolidation + red team)

After merging Sally’s prototype into final/ and W7 security remediations: Mermaid removed, two sequential GPT-4o calls (architecture + workflow), module-driven graph in one `ai_openai.py`, CORS allowlist (PR #29), prompt-injection + crisis guards (PR #28). Documented at merge `6340e06`.
![W8 Architecture](docs/images/w8.png)

Repo reference: `docs/architecture-retrospective.md` (W8-era container diagram), `docs/sprint-2-retro.md` (red team response). Code freeze — current architecture (Week 10)

![Final Architecture](docs/images/final.png)
Sprint 3 added parallel GPT-4o calls (asyncio.gather), pipeline profiling logs, ethics disclaimer in UI, and parallelized per-file GitHub reads (`e096843`, `49bf927`). What changed between stages (triggers + traceability)

TransitiWhat changed Trigger Repo trace on

W4 →File-tree graph → AI80+ unreadable nodes on`ai_openai.py`, W8module graphreal repos`docs/architecture-retrospectiv e.md` §2

W4 →1 → 2 analyzeSprint 2 demo feedback `453389d` UI/UX + workflow W8prompts + workflowpersistence columns

W4 →Wildcard CORS →Peer red team finding #1 PR #29, W8allowlist`unitTesting/test_cors.py`

W8 →Sequential →Sprint 3 commitment`e096843` freezeparallel AI callsIssue #34

W8 →Consolidated final/ +Prototype phase end `final/backend/app.py`, freezeRender entry`docs/sprint-1-cicd.md`

3. Current state of the prototype

What it does today

GitMap analyzes public GitHub repositories through POST /api/analyze in `final/backend/main.py`, generating both an architecture graph and runtime workflow using `ai_openai.py`. Results are cached in SQLite and visualized in `final/frontend/index.html`. Users can ask grounded questions through /api/chat, browse recently analyzed repositories, and receive example questions generated from graph node types.

Links: Live — Render URL · Code freeze — `49bf927` · Demo video — see README.md.

What it does not do yet (seams)

No auth or rate limiting on /api/analyze (accepted debt after W7 red team; `docs/ethics-reflection.md` §3).

No validation that AI module paths exist in the fetched tree (`docs/architecture-retrospective.md` tech debt).

Private repos unsupported (public GitHub only).

Frontend untested — single 900+ line HTML file; all automated tests target backend (`unitTesting/`). Repo reference: `final/README.md`, `README.md`.

4. Engineering process: testing, security, deployment

Testing

Planned (W5) Implemented

Scope Per-owner unit tests + narrow`docs/sprint-1-testing.md` integration on cache seam; RED test for chat contract

Run pytest unitTesting/ -v on every PR `.github/workflows/ci.yml`

AI in loop TDD skill generated edge-case tests;`docs/sprint-1-testing.md` Part 4–5 team critiqued weak AI tests

Methodical example: test_analyze_invalid_url_returns_400 in `unitTesting/test_integration.py` — written when the suite returned 502 for https://notgithub.com/owner/repo because github.com matched inside notgithub.com. Fix: negative lookbehind in `final/backend/fetcher/github_fetcher.py` (documented in `docs/sprint-1-testing.md`). This encodes a user-visible failure mode, not an implementation detail. What we chose not to test: Live OpenAI/GitHub in CI (mocked via unittest.mock); frontend rendering; end-to-end browser flows. Why: determinism and cost; prototype velocity. Repo reference: `unitTesting/test_ai_safety.py` (post–PR #28), CI run example.

Security

Our Week 7 security plan combined a self-audit with a peer red-team review. The review focused on prompt injection, CORS configuration, SSRF risks, abuse prevention, and Responsible AI concerns (`potential_security_problems.txt`, `docs/sprint-2-retro.md`).

The team implemented the highest-priority fixes identified during the review, including prompt hardening, a chat safety layer, and a restricted CORS allowlist (PR #28, PR #29; `docs/sprint-2-remediations.md`).

Finding → Fix: Peer finding #6 identified a prompt-injection vulnerability in the chat feature. The fix introduced check_user_message_safety in `final/backend/ai_openai.py `to block override attempts before requests reach OpenAI, with regression tests added in `unitTesting/test_ai_safety.py`.

AI vs. Human Judgment: AI assisted in drafting guard logic, but the team made the final policy decisions, including crisis-response behavior and Responsible AI boundaries (`docs/ethics-reflection.md`).

Deferred Work: Authentication, rate limiting, and validation of AI-generated module paths against the repository file tree remained open technical debt at code freeze.

Repo reference: `final/backend/ai_openai.py` (check_user_message_safety), `final/backend/main.py` (get_cors_origins).

Deployment

Planned (W6) Implemented

Host Render from main branch `docs/sprint-1-cicd.md`

Pipeline PR + push to main → pytest `.github/workflows/ci.yml` jobs: checkout, Python 3.12, install unitTesting/requirements-test.txt, pytest unitTesting/ -v

Secrets OPENAI_API_KEY,`docs/sprint-1-cicd.md` GITHUB_TOKEN in GitHub Actions + Render env Repo reference: `.github/workflows/ci.yml`, `final/backend/app.py`.

5. Successes, setbacks, and AI across the quarter

Sources: `docs/sprint-1-retro.md`, `docs/sprint-2-retro.md`, Sprint 3 work in git history. Successes (practices to keep)

1. RED-first chat contract (Sprint 1) — test_answer_uses_cached_context specified chat behavior before implementation; forced explicit Sprint 2 delivery (`docs/sprint-1-testing.md`, `unitTesting/test_chat.py`).
2. Peer red team → shipped PRs (Sprint 2) — Daniela landed PR #28 and PR #29 before W8 deadline (`docs/sprint-2-retro.md`).
3. Sprint 3 scope discipline — One commitment (pipeline latency, Issue #34) → parallel AI + profiling in `e096843` instead of unfinished feature sprawl.

Setbacks (signals missed, lessons)

1. Merge conflicts on `main` (Sprint 1) — Multiple teammates pushed to main simultaneously; AI resolved syntax but not whose logic was correct (`docs/sprint-1-retro.md`).
2. Workflow data silently dropped (Sprint 2) — Cached analyses returned empty workflow until SQLite write path fixed in `453389d`.
3. Vision/architecture drift (W4 → product) — W4 promised tree-grounded graphs; we inverted to AI modules after user testing (`docs/architecture/architecture.md` vs. `docs/architecture-retrospective.md` §2). AI tools — specific moments

Deployment: AI corrected dependencies and production API base URL (`docs/sprint-1-retro.md`) — high leverage.

Testing: TDD skill generated tests we partially rejected after human critique (`docs/sprint-1-testing.md`).

Architecture: We unwound file-tree-as-graph after seeing AI-only module graphs worked better — human judgment over initial AI-friendly W4 design. Repo reference: `docs/sprint-1-retro.md`, `docs/sprint-2-retro.md`.

6. Future work

- Auth + rate limiting on `/api/analyze` — Prevent API budget abuse and excessive automated usage (see `docs/ethics-reflection.md`). (Sprint-sized task)
- Validate AI-generated module paths against the fetched file tree — Reduce hallucination-related errors and improve trustworthiness of generated explanations. (~1 week)
- Async analyze workflow (submit → poll) — Eliminate 10–20 second blocking HTTP requests and improve scalability (see `docs/architecture/architecture.md`). (Sprint-sized task)
- Frontend refactoring and smoke tests — Split the current 900-line HTML file into maintainable components and add basic regression coverage (see `docs/architecture-retrospective.md`). (Sprint-sized task)
- Research improved graph grounding without per-file nodes — Investigate hybrid static-analysis and LLM approaches for more reliable repository structure inference. (Long-term research problem)

Repo reference: Issue #34 (latency — partially done), open issues on team board.
7. Advice to future CSEN 174 teams

1. Write the failing integration test the moment you add a SQLite column — we lost workflow data in cache until Sprint 2 because the cache seam test did not assert new fields (see §5 setback 2).
2. Branch and PR before you “just push to main” for a week — merge conflicts cost more than review overhead (see `docs/sprint-1-retro.md`).
3. Run one large real repo through your analyzer in Week 5 — it would have exposed the 80-node graph failure before architecture docs were frozen (see `docs/architecture-retrospective.md` §2)
