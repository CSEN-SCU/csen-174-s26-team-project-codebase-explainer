try:
    # Works when running pytest from the repository root.
    from prototypes.final.example_questions import get_example_questions
except ModuleNotFoundError:
    # Works when running pytest from inside prototypes/final.
    from example_questions import get_example_questions


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
