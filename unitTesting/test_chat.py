"""Unit tests for final `/api/chat` behavior."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

import database
import main


@pytest.fixture
def app():
    return main.app


@pytest.mark.asyncio
async def test_chat_requires_analysis_first(app):
    # As a user, asking chat before analysis returns a clear message.
    # Arrange / Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"github_url": "https://github.com/owner/repo", "message": "What does this do?"},
        )
    # Assert
    assert response.status_code == 400
    assert "Analyze" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_returns_answer_with_cache(app, tmp_path, monkeypatch):
    # As a user, chat returns an answer when cached analysis exists.
    # Arrange
    db_file = str(tmp_path / "chat.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()

    graph = {
        "summary": "A FastAPI backend for serving ML predictions.",
        "tech_stack": ["Python", "FastAPI"],
        "nodes": [{"id": "root", "label": "ml-api", "description": "ML API root", "type": "module"}],
        "edges": [],
    }
    database.save_analysis("owner", "ml-api", "https://github.com/owner/ml-api", graph, source="openai")

    # Action
    with patch("main.chat_about_repo", new=AsyncMock(return_value="Uses FastAPI.")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={"github_url": "https://github.com/owner/ml-api", "message": "What framework?"},
            )
    # Assert
    assert response.status_code == 200
    assert "FastAPI" in response.json()["answer"]


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(app):
    # As a user, empty chat messages are rejected with 400.
    # Arrange / Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"github_url": "https://github.com/owner/repo", "message": "   "},
        )
    # Assert
    assert response.status_code == 400
