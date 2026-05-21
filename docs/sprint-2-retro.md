# Sprint 2 Retrospective — GitMap

## Celebrate

Sprint 2 was the sprint where the product started feeling real. **Sally** drove the largest single change of the project — a full UI/UX overhaul of the frontend that introduced resizable panels, draggable overlays, collapsible sidebar sections, smart node-label wrapping, and a zoom-fit button, while simultaneously fixing the backend workflow persistence bug that had been silently dropping `workflow_nodes` and `workflow_edges` from SQLite on every cached result. **Daniela** shipped the chat history and message-waiting indicator feature and carried the remediation work across the finish line — authoring both security PRs and navigating the merge process solo. **Jesse** contributed the zoom-fit feature and kept the team's progress visible through consistent reporting and diagram updates throughout the sprint.

## Red Team Response

The team received a peer red team report in W7 identifying eight findings. Two were acted on immediately and merged before the W8 deadline. Finding #6 (prompt injection via the chat endpoint) and Finding #8 (no in-product safety layer for sensitive user disclosures) were addressed together in [PR #28](https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/pull/28): the OpenAI system prompts in `ai_openai.py` were updated to explicitly treat all repository content and user messages as untrusted input, and a pattern-matching safety layer was added to intercept crisis language and prompt-override attempts before they reach the model. Finding #1 (permissive wildcard CORS) was addressed in [PR #29](https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/pull/29), replacing `allow_origins=["*"]` with an explicit allowlist of trusted origins. Two findings were deferred: the lack of authentication and rate limiting on `/api/analyze` was acknowledged but set aside because adding an auth system is out of scope for the remaining sprint. One finding — a suggestion to add per-user session isolation — was rejected as premature given the single-tenant demo context.

## Sprint 3 Commitments

**Profile the analysis pipeline to identify and resolve bottlenecks causing slow responses.** Fresh analysis currently blocks the HTTP connection for 10–20 seconds while the backend makes two sequential GPT-4o calls plus a GitHub file tree fetch. The team will instrument timing across each stage — GitHub fetch, first AI call, second AI call — identify where the majority of latency lives, and address the highest-impact bottleneck before demo night. This work is tracked on the Sprint 3 board: [GitHub Issue #34](https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/issues/34).

This is the team's only Sprint 3 commitment. With one sprint remaining and a demo deadline at W9, the team is scoping tightly to ship one meaningful improvement rather than spread across several and finish none.
