import json
from openai import AsyncOpenAI


def _client() -> AsyncOpenAI:
    return AsyncOpenAI()

SYSTEM_ANALYSIS = (
    "You are an expert software architect. Return valid JSON only."
)

ANALYSIS_USER = """Analyze this repository and return a JSON object with this structure:
{
  "summary": "2-3 sentence plain-English overview",
  "tech_stack": ["main technologies"],
  "nodes": [
    {
      "id": "unique_id",
      "label": "Display Name",
      "type": "module|service|config|entrypoint|external|database|test",
      "description": "1 sentence description",
      "files": ["path/to/file.py"]
    }
  ],
  "edges": [
    {
      "source": "node_id",
      "target": "node_id",
      "label": "imports|calls|extends|configures|stores"
    }
  ]
}

Rules:
- 5-15 nodes max
- group related files by logical component
- do not invent files not present in input

Repository: {owner}/{repo}

File tree:
{file_tree}

File contents:
{file_contents}
"""

CHAT_SYSTEM = (
    "You answer repository questions grounded in provided JSON context. "
    "Be concise, factual, and avoid hallucinations."
)


def _parse_json_object(text: str) -> dict:
    text = (text or "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start:end])


def build_chat_code_context(file_tree: list[str], files: dict[str, str]) -> dict:
    paths = sorted(set(file_tree or []))[:450]
    excerpts = {}
    for path in sorted((files or {}).keys())[:32]:
        body = (files or {}).get(path) or ""
        excerpts[path] = body[:5000] + ("\n... [truncated]" if len(body) > 5000 else "")
    return {"file_tree_sample": paths, "code_excerpts": excerpts}


async def analyze_repo(repo_data: dict) -> dict:
    file_tree_str = "\n".join((repo_data.get("file_tree") or [])[:400])
    snippets = []
    for path, content in list((repo_data.get("files") or {}).items())[:16]:
        snippets.append(f"=== {path} ===\n{content[:2500]}")
    file_contents = "\n\n".join(snippets)
    prompt = ANALYSIS_USER.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        file_tree=file_tree_str,
        file_contents=file_contents,
    )
    resp = await _client().chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_ANALYSIS},
            {"role": "user", "content": prompt},
        ],
    )
    data = _parse_json_object(resp.choices[0].message.content or "{}")
    for key in ("summary", "tech_stack", "nodes", "edges"):
        if key not in data:
            raise ValueError(f"Missing key in analysis JSON: {key}")
    return data


async def chat_about_repo(
    user_message: str,
    summary: str,
    tech_stack: list[str],
    nodes: list[dict],
    edges: list[dict],
    *,
    code_context: dict | None = None,
) -> str:
    context = {
        "summary": summary,
        "tech_stack": tech_stack,
        "nodes": nodes,
        "edges": edges,
    }
    if code_context:
        context.update(code_context)
    payload = json.dumps(context, indent=2)[:180000]
    prompt = (
        "Repository evidence JSON:\n"
        f"{payload}\n\n"
        f"Question: {user_message}\n"
        "Answer in 2-3 complete sentences grounded in the JSON."
    )
    resp = await _client().chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=220,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip() or "(No response)"
