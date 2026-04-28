"""
AI behavior tests for final/backend/ai_openai.py.
"""


import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


MOCK_AI_JSON = {
    "summary": "A modern web framework for building APIs.",
    "tech_stack": ["Python", "FastAPI", "Starlette", "Pydantic"],
    "nodes": [
        {
            "id": "backend",
            "label": "backend",
            "type": "service",
            "description": "Core backend handling HTTP routes and middleware.",
            "files": ["backend/main.py"],
        }
    ],
    "edges": [],
}

SAMPLE_REPO_DATA = {
    "owner": "tiangolo",
    "repo": "fastapi",
    "file_tree": ["backend/main.py", "backend/router.py", "tests/test_main.py", "README.md"],
    "files": {"README.md": "# FastAPI"},
}


def make_mock_openai_response(content: dict):
    """Build a minimal mock that looks like an OpenAI ChatCompletion response."""
    mock_msg = MagicMock()
    mock_msg.content = json.dumps(content)
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


@pytest.mark.asyncio
async def test_ai_response_has_required_fields():
    # As a developer, the AI response always contains summary, tech_stack, and modules
    # so the graph builder never crashes on missing keys.
    # Arrange
    from ai_openai import analyze_repo
    mock_resp = make_mock_openai_response(MOCK_AI_JSON)

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_factory.return_value = mock_client
        # Action
        result = await analyze_repo(SAMPLE_REPO_DATA)

    # Assert — required top-level keys
    assert "summary" in result
    assert "tech_stack" in result
    assert "nodes" in result
    assert "edges" in result


@pytest.mark.asyncio
async def test_ai_response_summary_is_non_empty_string():
    # As a user, the summary is always readable text so the UI has something meaningful to display.
    # Arrange
    from ai_openai import analyze_repo
    mock_resp = make_mock_openai_response(MOCK_AI_JSON)

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_factory.return_value = mock_client
        result = await analyze_repo(SAMPLE_REPO_DATA)

    # Assert
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


@pytest.mark.asyncio
async def test_ai_response_tech_stack_is_list():
    # As a user, the tech stack is always a list so the UI can render chips without type errors.
    # Arrange
    from ai_openai import analyze_repo
    mock_resp = make_mock_openai_response(MOCK_AI_JSON)

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_factory.return_value = mock_client
        result = await analyze_repo(SAMPLE_REPO_DATA)

    # Assert
    assert isinstance(result["tech_stack"], list)


@pytest.mark.asyncio
async def test_ai_response_nodes_have_required_fields():
    # As a developer, every node has id, label, type, depth, and description
    # so the frontend never has to guard against missing properties.
    # Arrange
    from ai_openai import analyze_repo
    mock_resp = make_mock_openai_response(MOCK_AI_JSON)

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_factory.return_value = mock_client
        result = await analyze_repo(SAMPLE_REPO_DATA)

    # Assert — every node has the required shape
    required_keys = {"id", "label", "type", "description"}
    for node in result["nodes"]:
        assert required_keys.issubset(node.keys()), f"Node missing keys: {node}"


@pytest.mark.asyncio
async def test_ai_response_within_tech_stack_limit():
    # As a developer, tech stack is capped at 10 items so the UI chip row never overflows.
    # Arrange — AI returns 15 technologies
    bloated = {**MOCK_AI_JSON, "tech_stack": [f"Tech{i}" for i in range(15)]}
    from ai_openai import analyze_repo
    mock_resp = make_mock_openai_response(bloated)

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_factory.return_value = mock_client
        result = await analyze_repo(SAMPLE_REPO_DATA)

    # Assert
    assert len(result["tech_stack"]) <= 10


@pytest.mark.asyncio
async def test_ai_failure_raises_exception():
    from ai_openai import analyze_repo

    with patch("ai_openai._client") as mock_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API timeout"))
        mock_factory.return_value = mock_client
        with pytest.raises(Exception):
            await analyze_repo(SAMPLE_REPO_DATA)
