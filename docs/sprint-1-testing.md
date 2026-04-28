# Sprint 1 Testing — GitMap

## Part 1: Test Inventory

All tests live in `unitTesting/` and run with one command from the repo root:

```bash
source prototypes/sally/backend/venv/bin/activate
pip install -r unitTesting/requirements-test.txt
pytest unitTesting/ -v
```

### Unit Tests

| Test file | Owner | Functions under test | Expected status |
|---|---|---|---|
| `test_analyzer.py` | Sally | `_should_ignore`, `format_tree`, `build_graph` | GREEN |
| `test_fetcher.py` | Jesse | `parse_github_url`, `select_files_to_read`, DB cache | GREEN |
| `test_chat.py` | Daniela | `answer_question` | 2 GREEN, 1 RED |

**`test_analyzer.py`** (7 tests, all GREEN)

Sally's module is fully implemented. The tests verify that `_should_ignore` correctly hides `__pycache__` and `node_modules`, that `format_tree` produces a tree rooted at the repo name with real directory names and no cache clutter, and that `build_graph` produces nodes and edges, merges AI descriptions into real nodes, and never lets the AI invent nodes that don't exist in the actual file tree.

**`test_fetcher.py`** (8 tests, all GREEN)

Jesse's fetcher is also implemented. Tests cover four URL formats (standard HTTPS, `.git` suffix, trailing slash, invalid domain that must raise `ValueError`), file selection logic (README prioritised, images/binaries excluded, 25-file cap), and the full SQLite cache lifecycle (miss returns `None`, save+retrieve, delete, overwrite).

**`test_chat.py`** (3 tests — 2 GREEN, 1 RED)

Daniela's module is currently a stub. The two stub-behaviour tests pass: `answer_question` always returns a string, and it tells the user to run `/analyze` when the repo hasn't been analyzed yet. The third test (`test_answer_uses_cached_context`) is intentionally RED — it asserts that the answer references the repo's actual tech stack ("FastAPI"), which requires the real OpenAI call Daniela will implement in Sprint 2.

### Integration Test

| Test file | What it exercises | Expected status |
|---|---|---|
| `test_integration.py` | POST `/analyze` → DB write → GET `/recent` | GREEN |

`test_integration.py` exercises the seam between the FastAPI endpoint and the SQLite cache. GitHub and OpenAI are mocked, so the tests run offline and deterministically. Four scenarios are covered: the result is saved to the DB after a successful analyze call, a second request for the same URL hits the cache and skips the AI pipeline, the `/recent` endpoint returns a list of prior analyses, and a non-GitHub URL returns a 400 error. These tests start GREEN because the endpoint logic and DB wiring are already in place.

### AI Behavior Test

| Test file | What it asserts | Expected status |
|---|---|---|
| `test_ai_behavior.py` | Response structure, type safety, grounding, graceful failure | GREEN |

`test_ai_behavior.py` patches the OpenAI client with a controlled mock response and then calls `analyze_repo` directly. Tests assert on structure and categories, never on exact text (since LLM output is non-deterministic). Six assertions are checked: the result has all required keys (`summary`, `tech_stack`, `nodes`, `edges`), the summary is a non-empty string, `tech_stack` is a list, every node has the required shape (`id`, `label`, `type`, `depth`, `description`), hallucinated nodes (paths the AI invented that don't appear in the file tree) are filtered out, and tech stacks are capped at 10 items. A final test asserts that an OpenAI timeout returns a safe empty graph rather than an unhandled exception.

---

## Part 2: Testing Strategy Write-up

### Why these tests, why in this order

GitMap's core risk is a bad separation of concerns: if the AI is allowed to invent structure, the graph misleads rather than clarifies. Every test suite was therefore designed around one invariant — **the graph must be grounded in the real file tree**. `test_build_graph_no_hallucinated_nodes` in `test_analyzer.py` and `test_ai_cannot_invent_nodes_not_in_tree` in `test_ai_behavior.py` both assert this property from different angles.

We started with unit tests because the three backend modules (`analyzer/`, `fetcher/`, `chat/`) are independently owned. Having each owner write tests for their own module means tests document intent, not just implementation, and catch regressions without requiring the whole stack to be running.

The integration test was scoped deliberately narrow: it covers the one seam that all three modules share — the SQLite cache. Rather than spinning up a real server against real external APIs, we mock GitHub and OpenAI and verify the cache round-trip in isolation. This keeps the test fast, offline, and deterministic.

### TDD red-green cycle

We followed a strict RED-first discipline for the one genuinely unimplemented feature: Daniela's chat module. `test_answer_uses_cached_context` was written before the real OpenAI call exists, so it fails today. This is intentional — the failing test is the specification Daniela will implement against in Sprint 2. All other tests were written against existing code to establish a baseline and to document behaviour that must not regress.

### AAA structure

Every test follows Arrange-Action-Assert with a plain-language comment at the top explaining the user story the test protects. This makes it possible for any team member — including non-owners — to read a failing test and immediately understand what broke and why it matters to the user, without having to trace through the implementation.

### What stays RED and why

`test_answer_uses_cached_context` (in `test_chat.py`) is the only test that is intentionally and permanently RED for this sprint. It represents the contract the chat module must fulfil: given a cached graph with a known `tech_stack`, the answer to "What framework does this use?" must mention that framework. The stub returns a placeholder string, so the test fails. It will turn GREEN when Daniela wires up the real OpenAI call using the cached context as the system prompt.

### Bug found and fixed during the RED run

Running the initial suite (`initial_test.out`) revealed a real bug alongside the intentional RED: `test_analyze_invalid_url_returns_400` was failing with a 502 instead of 400 when given `https://notgithub.com/owner/repo`. The root cause was a regex too permissive in `fetcher/github_fetcher.py` — the pattern `github\.com[/:]` matched `notgithub.com` because `github.com` appears as a substring of it. The fix was a one-character negative lookbehind: `(?<![a-zA-Z0-9])github\.com[/:]`, which requires `github.com` to not be preceded by any alphanumeric character. After the fix the full suite reads **39 passed, 1 failed** (the intentional RED only).

# Sprint 1 Testing

## Overview

In this sprint, our team focused on applying test-driven development (TDD) to define and validate key behaviors of our system. We created initial failing tests, implemented partial functionality to pass some tests, and used an AI testing skill to expand our test coverage. We also critically evaluated AI-generated tests to improve their quality.

---

## Part 3: Testing Skill Installed and Used

We selected the TDD skill from the obra/superpowers repository because it aligns with our Python-based project and emphasizes a test-first development approach.

After installing the skill in the `.cursor/skills` directory, we used it to generate additional tests for our `get_example_questions` functionality. Compared to the default AI behavior, the generated tests were more structured and focused on meaningful behaviors such as edge cases and input validation.

Using this skill improved our workflow by encouraging us to think about test design before implementation and helped us identify scenarios that we had not initially considered. For example, the AI generated tests for handling unknown node types and duplicate prompts, which helped us cover important edge cases in our system.

---

## Part 4: AI Critique

### Test 1: test_returns_no_duplicate_prompts_when_node_types_repeat

This test partially reflects user needs, since users expect to see clean and non-redundant questions. However, it mainly focuses on internal implementation by checking that the output contains no duplicates using a set comparison (`len(examples) == len(set(examples))`).

If the internal implementation changes, the test would still pass as long as no duplicates appear. But it does not verify whether the generated questions are actually meaningful or relevant to the user.

Additionally, the test does not consider whether the questions themselves are useful or appropriate for the architecture. A better test would also validate that the generated prompts are relevant and informative, not just unique.

---

### Test 2: test_unknown_node_types_do_not_add_custom_prompts

This test captures an important edge case by ensuring that unknown node types do not introduce irrelevant prompts. It reflects user needs to some extent, as users expect clean and understandable outputs.

However, the test checks for the absence of the string "widget" in the output, which is a potential weak spot for correctness. The system might still generate irrelevant or low-quality prompts that do not explicitly include the word “widget,” and this test would still pass.

If the implementation changes (e.g., different wording or filtering strategy), this test might not effectively detect incorrect behavior. A stronger version of this test would explicitly assert what valid output should look like, rather than only checking for the absence of a specific term.

---

### Diff (Improved Version)

```diff
def test_unknown_node_types_do_not_add_custom_prompts():
    repo_data = {"nodes": [{"type": "widget", "label": "Unknown"}]}

    examples = get_example_questions(repo_data)

-    assert all("widget" not in prompt.lower() for prompt in examples)
+    # Ensure no irrelevant prompts are generated for unknown types
+    assert isinstance(examples, list)
+    assert all(isinstance(prompt, str) for prompt in examples)
+    assert all("widget" not in prompt.lower() for prompt in examples)
```

In the improved version, I added assertions to verify that the output is a list and that every element in the list is a string. This strengthens the test by ensuring the response has a valid and consistent structure, not just the absence of a specific keyword.

These changes make the test more robust and less dependent on specific wording. As a result, the test is more resilient to refactoring and better aligned with user expectations, since users care about receiving well-formed and readable outputs rather than simply avoiding a particular word.

---


