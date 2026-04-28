import json

from ai_openai import _parse_json_object, build_chat_code_context


def test_parse_json_object_extracts_from_wrapped_text():
    # As a user, wrapped model output still parses into valid JSON.
    # Arrange
    text = "preface\n{\"summary\":\"ok\",\"tech_stack\":[],\"nodes\":[],\"edges\":[]}\npost"
    # Action
    out = _parse_json_object(text)
    # Assert
    assert out["summary"] == "ok"


def test_parse_json_object_raises_when_missing_object():
    # As a user, invalid model output fails loudly instead of silently returning bad data.
    # Arrange / Action
    try:
        _parse_json_object("no braces here")
        raised = False
    except ValueError:
        raised = True
    # Assert
    assert raised is True


def test_build_chat_code_context_has_expected_keys():
    # As a developer, chat context always includes file tree and code excerpts keys.
    # Arrange
    tree = ["a.py", "b.py"]
    files = {"a.py": "print(1)"}
    # Action
    ctx = build_chat_code_context(tree, files)
    # Assert
    assert "file_tree_sample" in ctx
    assert "code_excerpts" in ctx


def test_build_chat_code_context_limits_file_count():
    # As a developer, chat context limits included files to stay within model bounds.
    # Arrange
    files = {f"f{i}.py": "x" for i in range(100)}
    # Action
    ctx = build_chat_code_context([], files)
    # Assert
    assert len(ctx["code_excerpts"]) <= 32


def test_build_chat_code_context_truncates_long_file():
    # As a developer, large file excerpts are truncated to safe size.
    # Arrange
    long_body = "a" * 6001
    # Action
    ctx = build_chat_code_context([], {"big.py": long_body})
    # Assert
    assert "[truncated]" in ctx["code_excerpts"]["big.py"]


def test_build_chat_code_context_output_is_json_serializable():
    # As a developer, returned context is JSON-serializable for DB/cache storage.
    # Arrange
    ctx = build_chat_code_context(["x.py"], {"x.py": "print('x')"})
    # Action
    encoded = json.dumps(ctx)
    # Assert
    assert isinstance(encoded, str)
