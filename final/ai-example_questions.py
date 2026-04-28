def get_example_questions(repo_data):
    """Return starter prompts a student can ask about a repository."""
    examples = [
        "What are the main modules in this repo?",
        "What depends on authentication?",
        "Where is the entry point?",
        "Explain this repo in five short numbered points (1–5).",
    ]

    type_to_prompt = {
        "service": "Which services are core to this architecture?",
        "database": "How does data flow into and out of the database layer?",
        "config": "Which configuration files are most important to review first?",
        "test": "What parts of the codebase are covered by tests?",
        "external": "Which external APIs or services does this repo rely on?",
        "entrypoint": "What are the main startup paths or entry points?",
        "module": "How do the main modules interact with each other?",
    }

    seen_types = set()
    for node in repo_data.get("nodes", []):
        node_type = node.get("type")
        if node_type in type_to_prompt and node_type not in seen_types:
            examples.append(type_to_prompt[node_type])
            seen_types.add(node_type)

    return list(dict.fromkeys(examples))
