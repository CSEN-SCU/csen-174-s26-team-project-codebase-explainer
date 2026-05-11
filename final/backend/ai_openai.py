import json
from openai import AsyncOpenAI

from analyzer.ai_analyzer import format_tree, _should_ignore


def _client() -> AsyncOpenAI:
    return AsyncOpenAI()

SYSTEM_ANALYSIS = (
    "You are an expert software architect explaining a codebase to a new developer. "
    "Focus on DATA FLOW and BEHAVIOR, not file lists. Return valid JSON only."
)

ANALYSIS_USER = """Analyze this repository and return a JSON object with this structure:
{{
  "summary": "2-3 sentence plain-English overview of what this project does and why it exists",
  "tech_stack": ["main technologies"],
  "modules": [
    {{
      "path": "exact/directory/path OR file path from the tree (must match exactly)",
      "description": "Explain the WORKFLOW: what input does this module receive, what does it do with it, and what does it return or trigger next? Name specific functions, classes, or APIs if visible in the file contents.",
      "type": "module|service|config|entrypoint|external|database|test",
      "depends_on": ["other/path"]
    }}
  ]
}}

Rules:
- `path` must exactly match a directory OR important file shown in the tree — no inventing paths
- Include key individual files (entry points, core logic, database files, config files) as their own modules
- Description must answer: WHAT comes in → WHAT happens → WHAT goes out
- Mention real function names, class names, or API endpoints you can see in the file contents
- Do NOT say "this directory contains X files" — explain behavior instead
- `depends_on` lists paths this module calls or imports from

Repository: {owner}/{repo}

Directory structure:
{file_tree}

Key file contents (read carefully — use these to write specific, accurate descriptions):
{file_contents}
"""

WORKFLOW_PROMPT = """Analyze this repository and return a JSON object describing the RUNTIME DATA FLOW as a series of numbered execution steps.

{{
  "workflow_nodes": [
    {{
      "id": "step_1",
      "label": "Short step name (3-5 words)",
      "description": "What data comes IN, what this step does, what goes OUT. Be specific — name real functions, endpoints, or data structures.",
      "type": "entrypoint|service|external|database|module",
      "step": 1,
      "files": ["path/to/key/file.py"]
    }}
  ],
  "workflow_edges": [
    {{
      "source": "step_1",
      "target": "step_2",
      "label": "what is passed (e.g. repo_data, graph JSON, cached result)"
    }}
  ]
}}

Rules:
- 6-12 steps max — cover the full request lifecycle from user input to rendered output
- Each step label is 3-5 words (e.g. "Validate GitHub URL", "Fetch File Tree", "Run AI Analysis")
- `files` lists 1-3 real file paths from the tree that are most central to this step (must exist in the tree)
- Edges label the actual data being passed between steps
- Include both the cache-hit path and the full analysis path
- Do NOT describe file structure — describe RUNTIME BEHAVIOR

Repository: {owner}/{repo}

Directory structure:
{file_tree}

Key file contents:
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


def _modules_to_graph(repo_name: str, summary: str, ai_result: dict) -> dict:
    """
    Build the architecture graph directly from the AI's identified modules.
    Only architecturally meaningful nodes appear — no directory-tree crawling.
    Edges come from each module's depends_on list with fuzzy path matching.
    """
    _EXTS = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java", ".cpp", ".c")

    def _norm(p: str) -> str:
        """Strip file extension for fuzzy matching of depends_on paths."""
        for ext in _EXTS:
            if p.endswith(ext):
                return p[:-len(ext)]
        return p

    modules = [m for m in ai_result.get("modules", []) if (m.get("path") or "").strip()]
    module_paths = {m["path"].strip("/") for m in modules}
    # Build a normalized → actual-path lookup for fuzzy resolution
    norm_to_actual: dict[str, str] = {}
    for p in module_paths:
        norm_to_actual.setdefault(_norm(p), p)

    def _resolve(dep: str) -> str | None:
        dep = dep.strip("/")
        if dep in module_paths:
            return dep
        return norm_to_actual.get(_norm(dep))

    # Pre-count base filenames so we can disambiguate duplicates (e.g. three main.py files)
    _fname_count: dict[str, int] = {}
    for m in modules:
        fname = m["path"].strip("/").split("/")[-1] or m["path"].strip("/")
        _fname_count[fname] = _fname_count.get(fname, 0) + 1

    def _make_label(path: str) -> str:
        parts = path.split("/")
        fname = parts[-1] or path
        # Prefix parent directory when the filename is shared by multiple modules
        if _fname_count.get(fname, 0) > 1 and len(parts) >= 2:
            return f"{parts[-2]}/{fname}"
        return fname

    nodes: list[dict] = []
    edges: list[dict] = []

    # Root / entrypoint node represents the repo itself
    nodes.append({
        "id":          "root",
        "label":       repo_name,
        "description": summary or f"Root of {repo_name}",
        "type":        "entrypoint",
        "files":       [],
    })

    # One node per AI-identified module
    for m in modules:
        path  = m["path"].strip("/")
        nodes.append({
            "id":          path,
            "label":       _make_label(path),
            "description": m.get("description", ""),
            "type":        m.get("type") or "module",
            "files":       [],
        })

    # Dependency edges with fuzzy matching
    has_incoming: set[str] = set()
    for m in modules:
        src = m["path"].strip("/")
        for dep in m.get("depends_on", []):
            tgt = _resolve(dep)
            if tgt and tgt != src:
                edges.append({"source": src, "target": tgt, "label": "uses", "edge_type": "imports"})
                has_incoming.add(tgt)

    # Connect root → modules that nothing else points to (true top-level components)
    for m in modules:
        path = m["path"].strip("/")
        if path not in has_incoming:
            edges.append({"source": "root", "target": path, "label": "", "edge_type": "contains"})

    return {"nodes": nodes, "edges": edges}


async def analyze_repo(repo_data: dict) -> dict:
    full_tree = repo_data.get("file_tree") or []

    # 1. Format the real file tree (filters noise, formats like `tree` command)
    tree_str = format_tree(full_tree, repo_data["repo"])

    # 2. Build file content snippets
    snippets = []
    for path, content in list((repo_data.get("files") or {}).items())[:16]:
        snippets.append(f"=== {path} ===\n{content[:2500]}")
    file_contents = "\n\n".join(snippets)

    prompt = ANALYSIS_USER.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        file_tree=tree_str,
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
    ai_result = _parse_json_object(resp.choices[0].message.content or "{}")

    # 3. Build architecture graph from AI modules — no directory crawling
    graph = _modules_to_graph(repo_data["repo"], ai_result.get("summary", ""), ai_result)

    # 4. Second AI call — workflow/data-flow graph (runs in parallel conceptually)
    workflow_prompt = WORKFLOW_PROMPT.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        file_tree=tree_str,
        file_contents=file_contents,
    )
    wf_resp = await _client().chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_ANALYSIS},
            {"role": "user", "content": workflow_prompt},
        ],
    )
    wf_result = _parse_json_object(wf_resp.choices[0].message.content or "{}")

    return {
        "summary":        ai_result.get("summary", ""),
        "tech_stack":     list(ai_result.get("tech_stack") or [])[:10],
        "nodes":          graph["nodes"],
        "edges":          graph["edges"],
        "tree":           tree_str,
        "workflow_nodes": wf_result.get("workflow_nodes", []),
        "workflow_edges": wf_result.get("workflow_edges", []),
    }


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
