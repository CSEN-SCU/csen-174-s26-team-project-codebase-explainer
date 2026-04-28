"""
Unit tests for analyzer/ai_analyzer.py
Owner: Sally

Tests cover the two pure functions that don't touch external APIs:
  - format_tree(): converts flat file paths into a tree-command string
  - build_graph(): merges AI descriptions onto the real file tree to produce nodes/edges
  - _should_ignore(): filters out noise files (pycache, node_modules, etc.)
"""


import pytest
from analyzer.ai_analyzer import format_tree, build_graph, _should_ignore


# ── _should_ignore ─────────────────────────────────────────────────────────────

def test_should_ignore_pycache():
    # As a user, I expect compiled Python cache files to be hidden from the graph.
    # Arrange
    path = "backend/__pycache__/main.cpython-311.pyc"
    # Action
    result = _should_ignore(path)
    # Assert
    assert result is True


def test_should_ignore_node_modules():
    # As a user, I expect node_modules to be hidden so the graph shows app code only.
    # Arrange
    path = "frontend/node_modules/react/index.js"
    # Action
    result = _should_ignore(path)
    # Assert
    assert result is True


def test_should_ignore_lock_files():
    # As a user, I expect lockfiles to be hidden since they carry no architectural meaning.
    # Arrange
    path = "package-lock.json"
    # Action
    result = _should_ignore(path)
    # Assert
    assert result is True


def test_should_not_ignore_source_files():
    # As a user, I expect real source files to appear in the graph.
    # Arrange
    path = "backend/main.py"
    # Action
    result = _should_ignore(path)
    # Assert
    assert result is False


def test_should_not_ignore_readme():
    # As a user, I expect README files to appear since they explain the project.
    # Arrange
    path = ".env.example"
    # Action
    result = _should_ignore(path)
    # Assert
    assert result is False


# ── format_tree ────────────────────────────────────────────────────────────────

def test_format_tree_contains_repo_name():
    # As a user, I see the repo name as the root of the tree so I know which project I'm viewing.
    # Arrange
    paths = ["backend/main.py", "frontend/index.html"]
    # Action
    result = format_tree(paths, "my-repo")
    # Assert
    assert result.startswith("my-repo/")


def test_format_tree_shows_directories():
    # As a user, I see directory names in the tree so I can understand the folder structure.
    # Arrange
    paths = ["backend/main.py", "backend/ai_analyzer.py", "frontend/index.html"]
    # Action
    result = format_tree(paths, "gitmap")
    # Assert
    assert "backend/" in result
    assert "frontend/" in result


def test_format_tree_filters_noise():
    # As a user, noise directories like __pycache__ are hidden so the tree stays readable.
    # Arrange
    paths = ["backend/main.py", "backend/__pycache__/main.cpython-311.pyc"]
    # Action
    result = format_tree(paths, "gitmap")
    # Assert
    assert "__pycache__" not in result


def test_format_tree_empty_paths():
    # As a user, an empty repo still shows a root node without crashing.
    # Arrange
    paths = []
    # Action
    result = format_tree(paths, "empty-repo")
    # Assert
    assert "empty-repo/" in result


# ── build_graph ────────────────────────────────────────────────────────────────

SAMPLE_REPO = {
    "owner": "testuser",
    "repo": "testrepo",
    "file_tree": [
        "backend/main.py",
        "backend/utils.py",
        "frontend/index.html",
        "README.md",
    ],
    "files": {},
}

SAMPLE_AI_RESULT = {
    "summary": "A test repository.",
    "tech_stack": ["Python", "HTML"],
    "modules": [
        {
            "path": "backend",
            "description": "The backend module handles API requests.",
            "type": "service",
            "depends_on": [],
        },
        {
            "path": "frontend",
            "description": "The frontend renders the UI.",
            "type": "module",
            "depends_on": ["backend"],
        },
    ],
}


def test_build_graph_returns_nodes_and_edges():
    # As a user, I receive a graph with nodes and edges so the UI can render it.
    # Arrange / Action
    graph = build_graph(SAMPLE_REPO, SAMPLE_AI_RESULT)
    # Assert
    assert "nodes" in graph
    assert "edges" in graph


def test_build_graph_nodes_come_from_real_tree():
    # As a user, every node in the graph corresponds to a real directory so the AI cannot invent structure.
    # Arrange / Action
    graph = build_graph(SAMPLE_REPO, SAMPLE_AI_RESULT)
    node_labels = [n["label"] for n in graph["nodes"]]
    # Assert — backend and frontend exist in the tree
    assert "backend" in node_labels
    assert "frontend" in node_labels


def test_build_graph_no_hallucinated_nodes():
    # As a user, directories the AI invented but that don't exist never appear in the graph.
    # Arrange
    ai_with_fake = {
        **SAMPLE_AI_RESULT,
        "modules": SAMPLE_AI_RESULT["modules"] + [
            {"path": "nonexistent_module", "description": "Fake.", "type": "module", "depends_on": []}
        ],
    }
    # Action
    graph = build_graph(SAMPLE_REPO, ai_with_fake)
    node_labels = [n["label"] for n in graph["nodes"]]
    # Assert
    assert "nonexistent_module" not in node_labels


def test_build_graph_root_node_has_summary():
    # As a user, the root node shows the AI summary so I get a one-sentence overview immediately.
    # Arrange / Action
    graph = build_graph(SAMPLE_REPO, SAMPLE_AI_RESULT)
    root = next(n for n in graph["nodes"] if n["id"] == "root")
    # Assert
    assert root["description"] == "A test repository."


def test_build_graph_merges_ai_description():
    # As a user, directory nodes show AI-generated descriptions instead of placeholder text.
    # Arrange / Action
    graph = build_graph(SAMPLE_REPO, SAMPLE_AI_RESULT)
    backend_node = next((n for n in graph["nodes"] if n["label"] == "backend"), None)
    # Assert
    assert backend_node is not None
    assert "API requests" in backend_node["description"]


def test_build_graph_containment_edges_exist():
    # As a user, containment edges connect parent directories to children so the tree renders correctly.
    # Arrange / Action
    graph = build_graph(SAMPLE_REPO, SAMPLE_AI_RESULT)
    edge_types = [e["edge_type"] for e in graph["edges"]]
    # Assert
    assert "contains" in edge_types
