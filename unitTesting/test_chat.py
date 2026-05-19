# Unit tests for chat/chat.py — Owner: Daniela
# Tests the /chat endpoint behavior end-to-end with the FastAPI app.

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
import database
import main
from ai_openai import chat_about_repo


@pytest.fixture
def app():
    return main.app


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "chat.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    return db_file


@pytest.mark.asyncio
async def test_chat_requires_analysis_first(app):
    # As a user, asking chat before analysis returns a clear message to run /api/analyze first.
    # Arrange / Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"github_url": "https://github.com/owner/repo", "message": "What does this do?"},
        )
    # Assert
    assert response.status_code == 400
    assert "analyze" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_returns_answer_with_cache(app, tmp_db):
    # As a user, chat returns an answer grounded in the cached analysis.
    # Arrange
    graph = {
        "summary": "A FastAPI backend for ML predictions.",
        "tech_stack": ["Python", "FastAPI"],
        "nodes": [{"id": "root", "label": "ml-api", "description": "ML API root", "type": "module"}],
        "edges": [],
    }
    database.save_analysis("owner", "ml-api", "https://github.com/owner/ml-api", graph)
    with patch(
        "main.chat_about_repo",
        new=AsyncMock(return_value="This project uses FastAPI for its HTTP API."),
    ):
        # Action
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={
                    "github_url": "https://github.com/owner/ml-api",
                    "message": "What framework?",
                },
            )
    # Assert
    assert response.status_code == 200
    assert "FastAPI" in response.json()["answer"]


@pytest.mark.asyncio
async def test_chat_returns_crisis_safe_response_without_openai(app, tmp_db):
    graph = {
        "summary": "A sample repo.",
        "tech_stack": ["Python"],
        "nodes": [],
        "edges": [],
    }
    database.save_analysis("owner", "repo", "https://github.com/owner/repo", graph)
    with patch("main.chat_about_repo", wraps=chat_about_repo) as chat_fn:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={
                    "github_url": "https://github.com/owner/repo",
                    "message": "I want to hurt myself.",
                },
            )
    chat_fn.assert_awaited_once()
    assert response.status_code == 200
    assert "988" in response.json()["answer"]


@pytest.mark.asyncio
async def test_chat_passes_conversation_history_to_model(app, tmp_db):
    graph = {
        "summary": "A sample repo.",
        "tech_stack": ["Python"],
        "nodes": [],
        "edges": [],
    }
    database.save_analysis("owner", "repo", "https://github.com/owner/repo", graph)
    prior = [
        {"role": "user", "content": "What framework is used?"},
        {"role": "assistant", "content": "It uses FastAPI."},
    ]
    with patch("main.chat_about_repo", new=AsyncMock(return_value="The API layer is in main.py.")) as chat_fn:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={
                    "github_url": "https://github.com/owner/repo",
                    "message": "Where is the entry point?",
                    "history": prior,
                },
            )
    assert response.status_code == 200
    chat_fn.assert_awaited_once()
    assert chat_fn.await_args.kwargs["history"] == prior
