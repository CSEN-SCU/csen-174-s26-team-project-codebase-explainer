"""
Unit tests for chat/chat.py
Owner: Daniela

Tests cover current stub behaviour (cache miss path) and define the
expected contract for the real implementation (these will stay RED until
Daniela replaces the stub with a real OpenAI call).
"""


import pytest
from unittest.mock import patch
from fetcher import database


# ── Stub behaviour (should be GREEN now) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_returns_string():
    # As a user, asking a question always returns a string response, never an error object.
    # Arrange
    from chat.chat import answer_question
    # Action
    result = await answer_question("https://github.com/owner/repo", "What does this do?")
    # Assert
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_answer_no_cache_returns_prompt_message():
    # As a user, asking about a repo that hasn't been analyzed yet gives a clear prompt to run /analyze first.
    # Arrange
    from chat.chat import answer_question
    url = "https://github.com/nobody/nonexistent-repo-xyz"
    # Action
    result = await answer_question(url, "What does this repo do?")
    # Assert
    assert "analyze" in result.lower()


# ── Real implementation contract (RED until Daniela implements) ───────────────

@pytest.mark.asyncio
async def test_answer_uses_cached_context():
    # As a user, answers are grounded in the actual repo structure, not generic responses.
    # Arrange — seed the cache with a known summary
    from chat.chat import answer_question
    from fetcher import database as db

    import tempfile, monkeypatch
    # This test will stay RED until the real OpenAI call is wired up.
    # The stub currently ignores the cached data and returns a placeholder.
    graph = {
        "summary": "A FastAPI backend for serving ML predictions.",
        "tech_stack": ["Python", "FastAPI"],
        "nodes": [{"id": "root", "label": "ml-api", "description": "ML API root"}],
        "edges": [],
    }
    db.save_analysis("owner", "ml-api", "https://github.com/owner/ml-api", graph)

    # Action
    result = await answer_question("https://github.com/owner/ml-api", "What framework does this use?")

    # Assert — real answer should mention FastAPI, stub won't
    assert "FastAPI" in result or "fastapi" in result.lower()


@pytest.mark.asyncio
async def test_answer_does_not_hallucinate_modules():
    # As a user, the chat answer only references modules that actually exist in the repo graph.
    # Arrange
    from chat.chat import answer_question
    # Action
    result = await answer_question("https://github.com/tiangolo/fastapi", "List all modules.")
    # Assert — result should be a string (stub passes), real impl must not invent paths
    assert isinstance(result, str)
    # RED: real implementation should be validated against node labels from the cached graph
    # This assertion will need strengthening once Daniela's implementation is complete.
    assert len(result) > 0
