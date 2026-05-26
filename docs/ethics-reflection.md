# Ethics Reflection – GitMap

---

# Product Vision

> FOR developers, CS students, and engineers joining unfamiliar GitHub projects WHO need to understand large codebases, architecture, and component relationships quickly.

GitMap is an AI-powered web application for GitHub repository visualization THAT automatically analyzes repositories and generates interactive architecture maps with explorable modules, dependencies, and plain-English explanations.

UNLIKE static diagrams, documentation, or text-only AI tools that focus on isolated snippets or overwhelming outputs, OUR PRODUCT provides a dynamic, visual, and interactive way to explore and understand how an entire codebase is structured and connected.

**POWERED BY:** OpenAI API (GPT-4o), GitHub GraphQL API, and interactive web-based visualization libraries.

---

# Stakeholders

## User Group

**Developers and CS students onboarding to unfamiliar repositories**

This group pastes a GitHub URL into GitMap and relies on the generated architecture graph and AI chat to orient themselves in a codebase they did not write.

## Non-User Group

**Open-source repository authors and maintainers**

When a user submits any public GitHub URL, GitMap fetches up to 25 source files from that repository and transmits their contents to the OpenAI API for analysis.

The repository's authors did not opt in, are not notified, and receive no attribution in the output—yet their code is the raw material the product depends on.

---

# Potential Harms

## 1. AI Hallucinations Mislead Developers Making Architectural Decisions

### Harm

GitMap presents GPT-4o's output as an authoritative interactive map of the repository.

When GPT-4o hallucinates module paths, invents dependency edges, or mischaracterizes what a component does, developers onboarding to the codebase form incorrect mental models. This may lead to bugs, poor architectural decisions, or modifications to the wrong system component.

### Principle

> **IEEE/ACM SE Code 1.03**
>
> "Approve software only if they have a well-founded belief that it is safe, meets specifications, passes appropriate tests, and does not diminish quality of life."

The product currently has no validation layer that checks AI-generated module paths against the actual repository structure before rendering them.

### Mitigation

Our team identified this issue as deferred technical debt before code freeze.

Before demo night, we will add a visible disclaimer adjacent to the architecture graph stating that the visualization is AI-generated and may not fully reflect the actual codebase.

While this does not eliminate the underlying risk, it improves transparency and encourages users to verify important information against the original source code.

---

## 2. Source Code Transmitted to a Third-Party API Without Repository Owner Consent

### Harm

Every fresh analysis sends up to 25 source files—including business logic, configuration patterns, and design decisions—to OpenAI's API.

Authors of public repositories did not explicitly consent to their code being processed by a commercial AI service. For maintainers of small open-source projects, startup repositories, or projects containing sensitive implementation details, this represents an unannounced secondary use of their work.

### Principle

> **IEEE/ACM SE Code 3.12**
>
> "Be sensitive to the right of others to privacy and work to preserve the privacy of users and third parties."

Repository authors are third parties affected by the product without their knowledge.

### Mitigation

GitMap is restricted to public repositories and cannot access private repositories.

Additionally, OpenAI API submissions are not used for model training unless explicitly opted in.

For this prototype, the team accepts the residual risk because:

- The code analyzed is already publicly accessible.
- Analysis is read-only.
- GitMap does not redistribute repository contents.

A production deployment would require a more explicit disclosure policy and terms of use.

---

## 3. No Rate Limiting Enables Financial Abuse and Denial of Service

### Harm

Any visitor can submit any public GitHub URL and trigger two GPT-4o API calls.

Because there is currently:

- No authentication
- No per-user quota
- No cooldown period

a malicious actor could repeatedly submit unique repositories and rapidly exhaust the project's OpenAI budget.

This creates both financial harm to the operator and service degradation for legitimate users.

### Principle

> **IEEE/ACM SE Code 1.03**
>
> "Approve software only if they have a well-founded belief that it is safe."

A system that allows uncapped financial exploitation does not meet a basic standard of operational safety.

### Mitigation

GitMap currently uses a SQLite cache.

Repositories that have already been analyzed are served from cache, eliminating additional API costs for repeated requests.

The lack of rate limiting was identified during the W7 Red Team Review and formally accepted as technical debt due to project scope constraints.

A production deployment would require:

- User authentication
- Per-IP rate limiting
- Usage quotas
- OpenAI spending limits

---

# One Concrete Change

During the W7 Red Team Review, our team discovered that the `/api/chat` endpoint forwarded all user input directly to GPT-4o without preprocessing.

In response, we implemented a pattern-matching safety layer in `ai_openai.py` (PR #28) that intercepts:

- Crisis-related language (e.g., self-harm references)
- Prompt-injection attempts (e.g., "ignore previous instructions")

before requests reach the model.

Instead, the system returns a predefined safe response.

This change was made because GitMap is a repository visualization tool, not a crisis-support platform, and allowing jailbreak attempts to reach the model created both safety and reliability risks.
