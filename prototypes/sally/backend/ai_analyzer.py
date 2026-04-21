"""
ai_analyzer.py

Pipeline:
  1. Format the file tree as a `tree`-command-style string (humans and AI both read this easily)
  2. Send tree + key file snippets to AI → get back per-module descriptions + dependency edges
  3. Build the graph from the real tree structure (AI cannot invent nodes)
  4. Nodes carry depth + parent_id for progressive frontend disclosure (10 shown at first)
"""

import re
import json
from openai import AsyncOpenAI

client = AsyncOpenAI()

# ── Noise filters ──────────────────────────────────────────────────────────────
IGNORE_DIRS = {
    "__pycache__", "node_modules", ".git", "venv", ".venv", "env",
    "dist", "build", ".next", ".nuxt", "out", "target", "vendor",
    ".idea", ".vscode", ".cache", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "eggs", ".eggs", "htmlcov",
    ".gradle", ".mvn", "bin", "obj", ".parcel-cache", "storybook-static",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".class", ".o", ".so", ".dll", ".exe",
    ".map", ".min.js", ".min.css", ".lock", ".log",
    ".jpg", ".jpeg", ".png", ".gif", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
}

IGNORE_FILENAMES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "pipfile.lock",
    "composer.lock", "gemfile.lock", ".ds_store", "thumbs.db",
    ".gitkeep", ".gitmodules",
}

NOTABLE_ROOT_FILES = {
    "readme.md", "readme.txt", "readme.rst",
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "go.mod", "cargo.toml", "dockerfile", "docker-compose.yml",
    "makefile", ".env.example", ".cursorrules",
}

ENTRYPOINT_FILES = {
    "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs",
    "server.js", "server.ts", "manage.py", "wsgi.py", "asgi.py",
}

TYPE_RULES = {
    "test":     {"test", "tests", "spec", "specs", "__tests__", "e2e", "fixtures"},
    "config":   {"config", "configs", "configuration", "settings", "env", "environments"},
    "database": {"db", "database", "databases", "migrations", "models", "schemas", "seeds"},
    "service":  {"api", "routes", "endpoints", "controllers", "handlers", "services",
                 "middleware", "graphql", "grpc"},
    "external": {"vendor", "third_party", "external", "integrations"},
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _should_ignore(path: str) -> bool:
    parts = path.split("/")
    for part in parts:
        if part.lower() in IGNORE_DIRS:
            return True
        if part.startswith(".") and part not in {
            ".env.example", ".gitignore", ".cursorrules", ".github", ".env.example"
        }:
            return True
    filename = parts[-1].lower()
    if filename in IGNORE_FILENAMES:
        return True
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return ext in IGNORE_EXTENSIONS


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("-", "_").replace(".", "_").replace(" ", "_")


def _detect_type(name: str, files_in_dir: list[str]) -> str:
    lower = name.lower()
    for f in files_in_dir:
        if f.split("/")[-1].lower() in ENTRYPOINT_FILES:
            return "entrypoint"
    for node_type, keywords in TYPE_RULES.items():
        if lower in keywords or any(kw in lower for kw in keywords):
            return node_type
    return "module"


# ── 1. Format file tree like the `tree` command ────────────────────────────────
def format_tree(paths: list[str], repo_name: str, max_depth: int = 4) -> str:
    """
    Convert a flat list of file paths into a tree-command-style string.

    Example output:
      my-repo/
      ├── backend/
      │   ├── main.py
      │   ├── ai_analyzer.py
      │   └── requirements.txt
      ├── frontend/
      │   └── index.html
      └── README.md
    """
    # Filter noise and build nested dict
    clean = [p for p in paths if not _should_ignore(p)]

    # Build tree dict: nested defaultdicts
    def make_tree():
        return {}

    tree: dict = make_tree()
    for path in clean:
        parts = path.split("/")
        if len(parts) > max_depth:
            # Truncate deep paths but mark that more exists
            parts = parts[:max_depth] + ["..."]
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    # Render to string
    lines = [f"{repo_name}/"]

    def render(node: dict, prefix: str = ""):
        items = sorted(node.keys(), key=lambda k: (k == "...", k))
        for i, key in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            child = node[key]
            is_dir = bool(child) and key != "..."
            label = f"{key}/" if is_dir else key
            lines.append(f"{prefix}{connector}{label}")
            if is_dir:
                extension = "    " if is_last else "│   "
                render(child, prefix + extension)

    render(tree)
    return "\n".join(lines)


# ── 2. AI analysis: tree + file snippets → descriptions + edges ────────────────
SYSTEM_PROMPT = """\
You are an expert software architect analyzing a GitHub repository.
You will be given:
  - A tree-formatted directory structure (like the `tree` command)
  - Key file contents

Respond with valid JSON only — no markdown, no explanation outside the JSON.
"""

ANALYSIS_PROMPT = """\
Analyze this repository and return a JSON object with this exact structure:

{{
  "summary": "2-3 sentence plain-English description of what this project does",
  "tech_stack": ["list", "of", "main", "technologies"],
  "modules": [
    {{
      "path": "exact/directory/path or filename for root-level files",
      "description": "one sentence: what this module does and its role in the system",
      "type": "module|service|config|entrypoint|external|database|test",
      "depends_on": ["other/path", "..."]
    }}
  ]
}}

Rules:
- `path` must exactly match a directory or file from the tree (do not invent paths)
- Only include top-level directories and important root-level files as modules
- `depends_on` lists other paths from the tree that this module imports or calls
- Keep descriptions specific and meaningful (not "contains files")
- `type` values: module, service, config, entrypoint, external, database, test

Repository: {owner}/{repo}

Directory structure:
{tree}

Key file contents:
{file_contents}
"""


async def _ai_analyze(repo_data: dict, tree_str: str) -> dict:
    """
    Call AI with the tree-formatted structure and file snippets.
    Returns: { summary, tech_stack, modules: [{path, description, type, depends_on}] }
    """
    # Build file content snippet (priority files first, truncated)
    snippets = []
    for path, content in list(repo_data["files"].items())[:12]:
        truncated = content[:2000] if len(content) > 2000 else content
        snippets.append(f"=== {path} ===\n{truncated}")
    file_contents = "\n\n".join(snippets)

    prompt = ANALYSIS_PROMPT.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        tree=tree_str,
        file_contents=file_contents,
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        text = response.choices[0].message.content or "{}"
        text = text.strip()
        start, end = text.find("{"), text.rfind("}") + 1
        return json.loads(text[start:end]) if start != -1 else {}
    except Exception as e:
        return {"summary": "", "tech_stack": [], "modules": [], "_error": str(e)}


# ── 3. Build hierarchical graph from tree (AI cannot invent structure) ─────────
def build_graph(repo_data: dict, ai_result: dict) -> dict:
    """
    Nodes come from the real file tree.
    AI-generated descriptions and dependency edges are merged in by path matching.
    """
    raw_tree = repo_data["file_tree"]
    tree = [p for p in raw_tree if not _should_ignore(p)]

    # Index AI module info by path for fast lookup
    ai_modules: dict[str, dict] = {}
    for m in ai_result.get("modules", []):
        path = m.get("path", "").strip("/")
        if path:
            ai_modules[path] = m

    # Collect all directories
    dir_files: dict[str, list[str]] = {}
    root_files: list[str] = []

    for path in tree:
        parts = path.split("/")
        if len(parts) == 1:
            root_files.append(path)
        else:
            for depth in range(1, len(parts)):
                d = "/".join(parts[:depth])
                dir_files.setdefault(d, [])
            parent = "/".join(parts[:-1])
            dir_files[parent].append(path)

    all_dirs = set(dir_files.keys())
    node_ids: set[str] = set()
    nodes: list[dict] = []
    edges: list[dict] = []

    # ── Root node ──────────────────────────────────────────────
    root_id = "root"
    nodes.append({
        "id":          root_id,
        "label":       repo_data["repo"],
        "type":        "entrypoint",
        "depth":       0,
        "parent_id":   None,
        "has_children": bool(dir_files),
        "description": ai_result.get("summary") or f"Root of {repo_data['repo']}",
        "files":       [f for f in root_files if f.lower() in NOTABLE_ROOT_FILES],
    })
    node_ids.add(root_id)

    # ── Directory nodes ────────────────────────────────────────
    for dir_path in sorted(dir_files.keys()):
        parts    = dir_path.split("/")
        depth    = len(parts)
        dir_name = parts[-1]
        nid      = _safe_id(dir_path)

        if nid in node_ids:
            continue

        parent_id    = root_id if len(parts) == 1 else _safe_id("/".join(parts[:-1]))
        all_here     = [p for p in tree if p.startswith(dir_path + "/")]
        direct_files = [p for p in all_here if p.count("/") == depth]
        has_children = any(
            d.startswith(dir_path + "/") and d.count("/") == depth
            for d in all_dirs
        )

        # Merge AI description if available
        ai_info  = ai_modules.get(dir_path, {})
        node_type = ai_info.get("type") or _detect_type(dir_name, all_here)
        description = (
            ai_info.get("description")
            or f"{len(all_here)} file(s) in {dir_name}/"
        )

        nodes.append({
            "id":          nid,
            "label":       dir_name,
            "type":        node_type,
            "depth":       depth,
            "parent_id":   parent_id,
            "has_children": has_children,
            "description": description,
            "files":       direct_files[:8],
        })
        node_ids.add(nid)

        # Containment edge
        edges.append({
            "source":    parent_id,
            "target":    nid,
            "label":     "",
            "edge_type": "contains",
        })

    # ── Dependency edges from AI ───────────────────────────────
    for m in ai_result.get("modules", []):
        src_path = m.get("path", "").strip("/")
        src_id   = _safe_id(src_path) if src_path else root_id
        if src_id not in node_ids:
            continue

        for dep_path in m.get("depends_on", []):
            dep_path = dep_path.strip("/")
            tgt_id   = _safe_id(dep_path)
            if tgt_id not in node_ids or tgt_id == src_id:
                continue
            # Avoid duplicate or redundant containment edges
            edges.append({
                "source":    src_id,
                "target":    tgt_id,
                "label":     "uses",
                "edge_type": "imports",
            })

    return {"nodes": nodes, "edges": edges}


# ── Main entry point ───────────────────────────────────────────────────────────
async def analyze_repo(repo_data: dict) -> dict:
    """
    Returns: { summary, tech_stack, nodes, edges }
    - Nodes: id, label, type, depth, parent_id, has_children, description, files
    - Edges: source, target, label, edge_type ("contains" | "imports")
    """
    # 1. Build tree string from real file paths
    tree_str = format_tree(repo_data["file_tree"], repo_data["repo"])

    # 2. Ask AI to describe modules and identify dependencies (using the tree)
    ai_result = await _ai_analyze(repo_data, tree_str)

    # 3. Build graph — structure from tree, meaning from AI
    graph = build_graph(repo_data, ai_result)

    return {
        "summary":    ai_result.get("summary", ""),
        "tech_stack": ai_result.get("tech_stack", [])[:10],
        "nodes":      graph["nodes"],
        "edges":      graph["edges"],
        "tree":       tree_str,   # send to frontend so it can display it too
    }
