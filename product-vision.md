# Product Vision — GitMap

---

## Moore's Template

**FOR**
Developers — including CS students and professional engineers — who have just joined a GitHub project that already has a large, implemented codebase.

**WHO**
Struggle to understand the overall structure, component relationships, and architecture of an unfamiliar repository, making it hard to contribute effectively or even know where to start.

**THE**
GitMap is a visual mapping assistant web application for GitHub

**THAT**
Automatically analyzes a repository and generates an interactive, explorable graph of its architecture — showing modules, services, dependencies, and how they connect — so developers can get oriented quickly without reading thousands of lines of code.

**UNLIKE**
Text-based tools (documentation, inline comments, AI chat assistants like Claude or ChatGPT) that explain individual code snippets, or static diagram generators that produce overwhelming, non-interactive output.

**OUR PRODUCT**
Explains codebase structure as a dynamic, interactive graph that users can explore — zooming into relevant modules, filtering components, and clicking nodes for plain-English explanations — making architecture understanding intuitive rather than overwhelming.

**POWERED BY**
OpenAI API (GPT-4o) for AI-driven codebase analysis, and web-based graph visualization libraries for interactive rendering.

---

## How Might We Statement

**HMW** help developers who are new to a codebase quickly understand its structure and component relationships, so they can start contributing confidently without needing a senior engineer to walk them through the entire system?

---

## Key Insights from Problem Framing

- **The onboarding gap is real and recurring.** Every developer who joins an existing project faces this problem. It's not just students — engineers at companies spend significant time just figuring out "where things live" before they can be productive.

- **Text explanations don't scale to architecture.** Reading a README or asking an AI chatbot about the code gives you fragments, not a mental model. Humans understand systems spatially and relationally — a graph matches how we actually think about architecture.

- **Static diagrams fail too.** UML and architecture diagrams created manually go stale, are often missing, or are so detailed they become unreadable. The key insight is that the diagram should be *generated on demand from the actual code*, not maintained separately.

- **Interactivity is the differentiator.** A static graph is still overwhelming if the repo is large. The ability to click a node, see what it does, and see only its connections transforms a wall of information into a navigable exploration.

- **The entry point is frictionless.** Paste a URL — that's it. No install, no configuration, no uploading files. The lower the barrier, the more likely someone actually uses it in the moment they need it.
