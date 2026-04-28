# Unit tests for chat/chat.py — Owner: Daniela
# Tests the /chat endpoint behavior end-to-end with the FastAPI app.

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
from fetcher import database
import main


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
    # As a user, asking chat before analysis returns a clear message to run /analyze first.
    # Arrange / Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"github_url": "https://github.com/owner/repo", "question": "What does this do?"},
        )
    # Assert
    assert response.status_code == 200
    assert "analyze" in response.json()["answer"].lower()


@pytest.mark.asyncio
async def test_chat_returns_answer_with_cache(app, tmp_db):
    # As a user, chat returns an answer grounded in the cached analysis.
    # RED — stays failing until Daniela implements the real OpenAI call in chat.py.
    # Arrange
    graph = {
        "summary": "A FastAPI backend for ML predictions.",
        "tech_stack": ["Python", "FastAPI"],
        "nodes": [{"id": "root", "label": "ml-api", "description": "ML API root", "type": "module"}],
        "edges": [],
    }
    database.save_analysis("owner", "ml-api", "https://github.com/owner/ml-api", graph)
    # Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"github_url": "https://github.com/owner/ml-api", "question": "What framework?"},
        )
    # Assert
    assert response.status_code == 200
    assert "FastAPI" in response.json()["answer"]
