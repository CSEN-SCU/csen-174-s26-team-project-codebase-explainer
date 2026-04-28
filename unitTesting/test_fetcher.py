"""
Unit tests for fetcher/github_fetcher.py and fetcher/database.py
Owner: Jesse

Tests cover:
  - parse_github_url(): extracts (owner, repo) from various GitHub URL formats
  - select_files_to_read(): prioritises entry-point and config files
  - Database cache: save, retrieve, delete, and cache-miss behaviour
"""


import pytest
import tempfile
from unittest.mock import patch
from fetcher.github_fetcher import parse_github_url, select_files_to_read
from fetcher import database


# ── parse_github_url ───────────────────────────────────────────────────────────

def test_parse_github_url_https():
    # As a user, pasting a standard HTTPS GitHub URL correctly identifies the owner and repo.
    # Arrange
    url = "https://github.com/tiangolo/fastapi"
    # Action
    owner, repo = parse_github_url(url)
    # Assert
    assert owner == "tiangolo"
    assert repo == "fastapi"


def test_parse_github_url_with_git_suffix():
    # As a user, pasting a .git URL still resolves to the correct repo name.
    # Arrange
    url = "https://github.com/owner/my-repo.git"
    # Action
    owner, repo = parse_github_url(url)
    # Assert
    assert owner == "owner"
    assert repo == "my-repo"


def test_parse_github_url_with_trailing_slash():
    # As a user, URLs with trailing slashes are handled without errors.
    # Arrange
    url = "https://github.com/owner/repo/"
    # Action
    owner, repo = parse_github_url(url)
    # Assert
    assert owner == "owner"
    assert repo == "repo"


def test_parse_github_url_invalid_raises():
    # As a user, submitting a non-GitHub URL shows a clear error rather than silently failing.
    # Arrange
    url = "https://gitlab.com/owner/repo"
    # Action / Assert
    with pytest.raises(ValueError):
        parse_github_url(url)


# ── select_files_to_read ───────────────────────────────────────────────────────

def test_select_files_prioritises_readme():
    # As a user, README is always included and appears before generic source files
    # so the AI receives project context before implementation details.
    # Arrange — use a non-priority source file to test ordering clearly
    # (Note: app.py is itself in PRIORITY_FILES, so we compare against a plain module)
    tree = [
        {"path": "src/models.py", "type": "blob"},
        {"path": "README.md", "type": "blob"},
        {"path": "src/utils.py", "type": "blob"},
    ]
    # Action
    selected = select_files_to_read(tree)
    # Assert
    assert "README.md" in selected
    assert selected.index("README.md") < selected.index("src/models.py")


def test_select_files_respects_max_limit():
    # As a user, the AI never receives more files than the limit so requests stay within token bounds.
    # Arrange — generate 50 fake Python files
    tree = [{"path": f"src/module_{i}.py", "type": "blob"} for i in range(50)]
    # Action
    selected = select_files_to_read(tree)
    # Assert
    assert len(selected) <= 25


def test_select_files_excludes_non_readable():
    # As a user, binary and compiled files are excluded so the AI only sees meaningful text.
    # Arrange
    tree = [
        {"path": "app.py", "type": "blob"},
        {"path": "image.png", "type": "blob"},
        {"path": "binary.exe", "type": "blob"},
    ]
    # Action
    selected = select_files_to_read(tree)
    # Assert
    assert "image.png" not in selected
    assert "binary.exe" not in selected
    assert "app.py" in selected


# ── Database cache ─────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file so tests don't touch the real database."""
    db_file = str(tmp_path / "test_gitmap.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    return db_file


def test_cache_miss_returns_none(tmp_db):
    # As a user, requesting a repo that has never been analyzed returns nothing rather than crashing.
    # Arrange / Action
    result = database.get_cached("unknown", "repo")
    # Assert
    assert result is None


def test_save_and_retrieve_cached(tmp_db):
    # As a user, a previously analyzed repo loads instantly from cache on the next request.
    # Arrange
    graph = {
        "summary": "A test repo.",
        "tech_stack": ["Python"],
        "nodes": [{"id": "root", "label": "testrepo"}],
        "edges": [],
    }
    # Action
    database.save_analysis("owner", "testrepo", "https://github.com/owner/testrepo", graph)
    result = database.get_cached("owner", "testrepo")
    # Assert
    assert result is not None
    assert result["summary"] == "A test repo."
    assert result["cached"] is True


def test_delete_cache_removes_entry(tmp_db):
    # As a user, clearing a repo's cache means the next analyze call re-fetches fresh data.
    # Arrange
    graph = {"summary": "Old data.", "tech_stack": [], "nodes": [], "edges": []}
    database.save_analysis("owner", "repo", "https://github.com/owner/repo", graph)
    # Action
    deleted = database.delete_cache("owner", "repo")
    result = database.get_cached("owner", "repo")
    # Assert
    assert deleted is True
    assert result is None


def test_save_overwrites_existing(tmp_db):
    # As a user, re-analyzing a repo updates the cached result rather than creating a duplicate.
    # Arrange
    graph_v1 = {"summary": "Version 1.", "tech_stack": [], "nodes": [], "edges": []}
    graph_v2 = {"summary": "Version 2.", "tech_stack": ["Go"], "nodes": [], "edges": []}
    database.save_analysis("owner", "repo", "https://github.com/owner/repo", graph_v1)
    # Action
    database.save_analysis("owner", "repo", "https://github.com/owner/repo", graph_v2)
    result = database.get_cached("owner", "repo")
    # Assert
    assert result["summary"] == "Version 2."
