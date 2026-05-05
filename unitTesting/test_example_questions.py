from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_QUESTIONS_PATH = REPO_ROOT / "final" / "example_questions.py"

_spec = spec_from_file_location("example_questions", EXAMPLE_QUESTIONS_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load module at {EXAMPLE_QUESTIONS_PATH}")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
get_example_questions = _module.get_example_questions


def test_includes_node_type_specific_questions():
    repo_data = {
        "nodes": [
            {"type": "service", "label": "API"},
            {"type": "database", "label": "Postgres"},
        ]
    }

    examples = get_example_questions(repo_data)

    assert "Which services are core to this architecture?" in examples
    assert "How does data flow into and out of the database layer?" in examples


def test_unknown_node_types_do_not_add_custom_prompts():
    repo_data = {"nodes": [{"type": "widget", "label": "Unknown"}]}

    examples = get_example_questions(repo_data)

    assert all("widget" not in prompt.lower() for prompt in examples)


def test_returns_no_duplicate_prompts_when_node_types_repeat():
    repo_data = {
        "nodes": [
            {"type": "service", "label": "Auth"},
            {"type": "service", "label": "Billing"},
            {"type": "database", "label": "Primary DB"},
            {"type": "database", "label": "Replica DB"},
        ]
    }

    examples = get_example_questions(repo_data)

    assert len(examples) == len(set(examples))


@pytest.mark.skip(
    reason="Deferred to a later sprint: normalize node type matching to be case-insensitive."
)
def test_node_types_are_handled_case_insensitively():
    repo_data = {"nodes": [{"type": "Service", "label": "API"}]}

    examples = get_example_questions(repo_data)

    assert "Which services are core to this architecture?" in examples


@pytest.mark.skip(
    reason="Deferred to a later sprint: add auth-specific example prompts from node labels."
)
def test_auth_related_nodes_add_security_question():
    repo_data = {"nodes": [{"type": "module", "label": "Authentication Module"}]}

    examples = get_example_questions(repo_data)

    assert "How is authentication and authorization handled in this repo?" in examples


@pytest.mark.skip(
    reason="Deferred to a later sprint: cap example question list length (e.g. max 10 prompts)."
)
def test_example_questions_are_capped_to_ten():
    repo_data = {
        "nodes": [
            {"type": "service"},
            {"type": "database"},
            {"type": "config"},
            {"type": "test"},
            {"type": "external"},
            {"type": "entrypoint"},
            {"type": "module"},
        ]
    }

    examples = get_example_questions(repo_data)

    assert len(examples) <= 10
