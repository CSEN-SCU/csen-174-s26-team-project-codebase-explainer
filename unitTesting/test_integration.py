"""
Integration tests — seam between FastAPI API and SQLite cache.
Exercises the full POST /analyze → DB write → GET /recent read path
without hitting real external APIs (GitHub and OpenAI are mocked).
"""


import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fetcher import database


MOCK_REPO_DATA = {
    "owner": "tiangolo",
    "repo": "fastapi",
    "file_tree": ["main.py", "routers/items.py", "README.md"],
    "files": {"README.md": "# FastAPI\nA modern web framework."},
}

MOCK_GRAPH = {
    "summary": "A modern, fast web framework for building APIs with Python.",
    "tech_stack": ["Python", "FastAPI", "Starlette"],
    "nodes": [
        {"id": "root", "label": "fastapi", "type": "entrypoint",
         "depth": 0, "parent_id": None, "has_children": True,
         "description": "Root of fastapi", "files": ["README.md"]},
    ],
    "edges": [],
    "tree": "fastapi/\n└── main.py",
}


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    return db_file


@pytest.fixture
def app(tmp_db):
    """Return the FastAPI app with DB redirected to temp file."""
    import main as m
    # Reinitialise DB so it points to the temp file
    database.init_db()
    return m.app


@pytest.mark.asyncio
async def test_analyze_saves_result_to_db(app, tmp_db):
    # As a user, after analyzing a repo the result is cached so my next request returns instantly.
    # Arrange
    with patch("main.get_repo_data", new=AsyncMock(return_value=MOCK_REPO_DATA)), \
         patch("main.analyze_repo", new=AsyncMock(return_value=MOCK_GRAPH)):

        # Action
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/analyze", json={"github_url": "https://github.com/tiangolo/fastapi"})

    # Assert — endpoint returned 200 and the result is now in the DB
    assert response.status_code == 200
    cached = database.get_cached("tiangolo", "fastapi")
    assert cached is not None
    assert cached["summary"] == MOCK_GRAPH["summary"]


@pytest.mark.asyncio
async def test_analyze_returns_cached_on_second_request(app, tmp_db):
    # As a user, the second request for the same repo skips the AI pipeline and returns cached data.
    # Arrange — seed the cache directly
    database.save_analysis("tiangolo", "fastapi", "https://github.com/tiangolo/fastapi", MOCK_GRAPH)

    with patch("main.get_repo_data", new=AsyncMock(return_value=MOCK_REPO_DATA)) as mock_fetch, \
         patch("main.analyze_repo", new=AsyncMock(return_value=MOCK_GRAPH)) as mock_analyze:

        # Action
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/analyze", json={"github_url": "https://github.com/tiangolo/fastapi"})

    # Assert — cache was hit, external APIs were never called
    assert response.status_code == 200
    assert response.json()["cached"] is True
    mock_fetch.assert_not_called()
    mock_analyze.assert_not_called()


@pytest.mark.asyncio
async def test_recent_endpoint_returns_list(app, tmp_db):
    # As a user, the landing page history list shows previously analyzed repos.
    # Arrange — seed two analyses
    database.save_analysis("owner1", "repo1", "https://github.com/owner1/repo1",
                           {"summary": "Repo 1", "tech_stack": [], "nodes": [], "edges": []})
    database.save_analysis("owner2", "repo2", "https://github.com/owner2/repo2",
                           {"summary": "Repo 2", "tech_stack": [], "nodes": [], "edges": []})
    # Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/recent")
    # Assert
    assert response.status_code == 200
    analyses = response.json()["analyses"]
    assert len(analyses) >= 2


@pytest.mark.asyncio
async def test_analyze_invalid_url_returns_400(app, tmp_db):
    # As a user, submitting a non-GitHub URL shows a clear 400 error rather than crashing.
    # Arrange / Action
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/analyze", json={"github_url": "https://notgithub.com/owner/repo"})
    # Assert
    assert response.status_code == 400
