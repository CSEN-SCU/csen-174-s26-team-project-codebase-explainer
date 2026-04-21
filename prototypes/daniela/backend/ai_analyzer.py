"""
Architecture analysis and Q&A using Google Gemini.
Optional heuristic-only mode when GITMAP_SKIP_GEMINI=1 (no API key / quota needed).
"""

from __future__ import annotations

import json
import os
import re
from google import genai
from google.genai import types

# Default model id (AI Studio; override with GEMINI_MODEL). Matches current Gemini API samples.
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"

# Chat: enough room for a few complete sentences before optional sentence-boundary trim.
_DEFAULT_CHAT_MAX_OUT = 1024


def skip_gemini_enabled() -> bool:
    return os.getenv("GITMAP_SKIP_GEMINI", "").strip().lower() in ("1", "true", "yes", "on")


def analysis_is_heuristic_preview(graph: dict) -> bool:
    """Detect tree-only / mock analyses (including rows saved before we persisted `source`)."""
    s = (graph.get("summary") or "")
    if "Heuristic preview only" in s:
        return True
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        desc = (node.get("description") or "").lower()
        if "mock mode" in desc:
            return True
    return False


def _slug_id(name: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "folder"
    nid = base
    n = 2
    while nid in used:
        nid = f"{base}_{n}"
        n += 1
    used.add(nid)
    return nid


def _infer_tech_stack(paths: list[str], file_contents: dict[str, str]) -> list[str]:
    hints: list[str] = []
    low = [p.lower() for p in paths]

    def any_path(sub: str) -> bool:
        return any(sub in p for p in low)

    pkg_blob = ""
    for rel, text in file_contents.items():
        if rel.lower().endswith("package.json") and text:
            pkg_blob = text.lower()
            break

    if any_path("package.json") or pkg_blob:
        hints.append("Node.js")
    if pkg_blob and "next" in pkg_blob:
        hints.append("Next.js")
    if pkg_blob and "react" in pkg_blob:
        hints.append("React")
    if any_path("tailwind") or "tailwind" in pkg_blob:
        hints.append("Tailwind CSS")
    if any_path("vite.config"):
        hints.append("Vite")
    if any_path("requirements.txt") or any_path("pyproject.toml"):
        hints.append("Python")
    if any_path("go.mod"):
        hints.append("Go")
    if any_path("cargo.toml"):
        hints.append("Rust")

    return hints or ["(add GEMINI_API_KEY for AI-inferred stack)"]


def mock_analysis_from_tree(repo_data: dict) -> dict:
    """Build a small graph from folder structure only — for local testing without Gemini."""
    owner = repo_data["owner"]
    repo = repo_data["repo"]
    paths: list[str] = list(repo_data.get("file_tree") or [])
    files_read: dict[str, str] = repo_data.get("files") or {}
    n = len(paths)

    buckets: dict[str, list[str]] = {}
    root_files: list[str] = []
    for p in paths:
        if "/" not in p:
            root_files.append(p)
        else:
            top = p.split("/")[0]
            buckets.setdefault(top, []).append(p)

    tech_stack = _infer_tech_stack(paths, files_read)
    top_names = sorted(buckets.keys())
    max_dirs = 13
    merged_label = "Other top-level folders"
    if len(top_names) > max_dirs:
        keep = top_names[: max_dirs - 1]
        drop = top_names[max_dirs - 1 :]
        merged: list[str] = []
        for d in drop:
            merged.extend(buckets.pop(d, []))
        buckets[merged_label] = merged
        top_names = sorted(buckets.keys())

    nodes: list[dict] = []
    edges: list[dict] = []
    used_ids: set[str] = set()

    nodes.append(
        {
            "id": "root",
            "label": f"{repo} (root)",
            "type": "entrypoint",
            "description": f"Top-level files in {owner}/{repo} (folder layout preview).",
            "files": sorted(root_files)[:30],
        }
    )
    used_ids.add("root")

    for d in top_names:
        nid = _slug_id(d, used_ids)
        bucket = buckets.get(d, [])
        nodes.append(
            {
                "id": nid,
                "label": d,
                "type": "config" if d in (".github", ".vscode", "ci") else "module",
                "description": f"{len(bucket)} file(s) under {d}/",
                "files": sorted(bucket)[:25],
            }
        )
        edges.append({"source": "root", "target": nid, "label": "contains"})

    summary = (
        f"Heuristic preview only: {owner}/{repo} has {n} tracked file(s) in "
        f"{len(top_names)} top-level folder group(s). "
        "This graph mirrors the repo tree only, not inferred architecture."
    )

    return {
        "summary": summary,
        "tech_stack": tech_stack,
        "nodes": nodes,
        "edges": edges,
    }

SYSTEM_ANALYSIS = """You are an expert software architect. Analyze a GitHub repository from file paths and excerpts.
Respond with valid JSON only — no markdown fences, no commentary outside the JSON object."""

ANALYSIS_USER = """Analyze this repository and return a JSON object with this structure:

{{
  "summary": "2-3 sentence plain-English overview of what this project does",
  "tech_stack": ["list", "of", "main", "technologies"],
  "nodes": [
    {{
      "id": "unique_id",
      "label": "Display Name",
      "type": "module|service|config|entrypoint|external|database|test",
      "description": "1 sentence description",
      "files": ["path/to/file.py"]
    }}
  ],
  "edges": [
    {{
      "source": "node_id",
      "target": "node_id",
      "label": "imports|calls|extends|configures|stores"
    }}
  ]
}}

Rules:
- One node per logical module or component (not one per file)
- Group related files into a single node when they form a logical unit
- Only include edges for relationships you can infer from the code or structure
- 5-15 nodes max
- node type values: module, service, config, entrypoint, external, database, test

Repository: {owner}/{repo}

File tree (sample):
{file_tree}

File contents:
{file_contents}
"""


def _chat_max_output_tokens() -> int:
    """Upper bound on raw model output before sentence trim (tokens ≈ words for English)."""
    raw = os.getenv("GEMINI_CHAT_MAX_OUTPUT_TOKENS", "").strip()
    if raw.isdigit():
        return max(400, min(4096, int(raw)))
    return _DEFAULT_CHAT_MAX_OUT


def _require_genai_api_key() -> None:
    """Same resolution as google-genai Client(): GOOGLE_API_KEY, else GEMINI_API_KEY."""
    key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "No API key in the environment. Set GEMINI_API_KEY (or GOOGLE_API_KEY), "
            "same as the official Gemini samples."
        )


def _gemini_model_id() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def build_analysis_prompt(repo_data: dict) -> str:
    ft = repo_data["file_tree"]
    file_tree_str = "\n".join(ft[:400] if len(ft) > 400 else ft)

    parts = []
    for path, content in repo_data["files"].items():
        parts.append(f"=== {path} ===\n{content}")
    file_contents_str = "\n\n".join(parts)

    return ANALYSIS_USER.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        file_tree=file_tree_str,
        file_contents=file_contents_str,
    )


def _parse_json_object(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError(f"No JSON object in model output: {text[:400]}")
    return json.loads(text[start:end])


async def analyze_repo(repo_data: dict) -> dict:
    if skip_gemini_enabled():
        return mock_analysis_from_tree(repo_data)

    prompt = build_analysis_prompt(repo_data)
    _require_genai_api_key()
    try:
        async with genai.Client().aio as aclient:
            response = await aclient.models.generate_content(
                model=_gemini_model_id(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_ANALYSIS,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
    except Exception as e:
        raise ValueError(f"Gemini API error: {type(e).__name__}: {e}") from e

    raw = response.text or ""
    data = _parse_json_object(raw)
    for key in ("summary", "tech_stack", "nodes", "edges"):
        if key not in data:
            raise ValueError(f"Missing key in analysis JSON: {key}")
    return data


def build_chat_code_context(file_tree: list[str], files: dict[str, str]) -> dict:
    """
    Pack a bounded file tree sample plus code excerpts for chat.
    Shrinks until the JSON is under a safe size for the model context.
    """
    paths = sorted(set(file_tree or []))
    ft_sample = paths[:450]
    keys = sorted((files or {}).keys())
    per_file_cap = 5_500
    max_files = 36
    excerpts: dict[str, str] = {}
    for k in keys[:max_files]:
        body = (files or {}).get(k) or ""
        if len(body) > per_file_cap:
            body = body[:per_file_cap] + "\n... [truncated]"
        excerpts[k] = body

    payload: dict = {
        "file_tree_sample": ft_sample,
        "code_excerpts": excerpts,
        "note": "code_excerpts are partial GitHub file contents; file_tree_sample is a path subset.",
    }
    raw = json.dumps(payload, indent=2)
    while len(raw) > 95_000 and len(excerpts) > 10:
        drop = max(excerpts, key=lambda p: len(excerpts[p]))
        del excerpts[drop]
        payload["code_excerpts"] = dict(excerpts)
        raw = json.dumps(payload, indent=2)
    while len(raw) > 95_000 and len(ft_sample) > 120:
        ft_sample = ft_sample[:-80]
        payload["file_tree_sample"] = ft_sample
        raw = json.dumps(payload, indent=2)
    return payload


CHAT_SYSTEM = """You are the Q&A layer for a single repository. The user sends JSON that may include:

- summary, tech_stack, nodes, edges: architecture snapshot (how pieces relate).
- file_tree_sample: a subset of repo paths.
- code_excerpts: path → partial file text from GitHub (what the code actually does in those files).

Evidence rules:
- Use code_excerpts to infer behavior, imports, frameworks, and what major folders do. Use nodes/edges to relate components. Use file_tree_sample to see layout when excerpts are thin.
- Still do not invent files or behavior that are nowhere in the JSON. If excerpts do not cover an area, say what is missing instead of guessing from general knowledge.
- Read the question literally. The first sentence must directly answer it.

Presentation (plain-text chat bubble; not Markdown):
- Write two or three complete sentences (each should end with proper punctuation). The first sentence must answer the question; the others may add brief supporting detail or note what the snapshot does not show—then stop.
- Do not cut off mid-thought: finish each sentence you start.
- No lists, no numbered lines, no headings. No **bold**; at most one short `path` in backticks if essential.
- No lines starting with * or -."""


def _flatten_md_double_asterisk(text: str) -> str:
    """Remove `**bold**` wrappers — models often emit Markdown even when asked not to."""
    if not text:
        return text
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text


def _compact_graph_for_chat(
    nodes: list[dict],
    edges: list[dict],
    *,
    max_files_per_node: int = 12,
) -> tuple[list[dict], list[dict]]:
    """Trim long per-node file lists so chat context emphasizes roles and relationships."""
    out_nodes: list[dict] = []
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        slim = {k: v for k, v in n.items() if k != "files"}
        files = n.get("files")
        if isinstance(files, list) and files:
            slim["files"] = files[:max_files_per_node]
            rest = len(files) - max_files_per_node
            if rest > 0:
                slim["files_truncated"] = rest
        out_nodes.append(slim)
    return out_nodes, [e for e in (edges or []) if isinstance(e, dict)]


def _format_chat_for_plain_ui(text: str) -> str:
    """Strip Markdown bold; turn line-leading bullets into plain arrows for plain-text bubbles."""
    text = _flatten_md_double_asterisk(text)
    # Lines that look like Markdown / unicode bullets → single visible prefix
    text = re.sub(r"(?m)^\s*[-*•]\s+", "→ ", text)
    return text.strip()


def _truncate_chat_to_sentences(text: str, max_sentences: int = 3) -> str:
    """If the model returns a long essay, keep only the first few sentence-sized segments (split on . ? !)."""
    t = (text or "").strip()
    if not t or max_sentences <= 0:
        return t
    parts = re.split(r"(?<=[.!?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return t
    # Single unpunctuated paragraph: do not chop mid-sentence—return as-is so one thought can finish.
    if len(parts) == 1:
        return parts[0]
    if len(parts) <= max_sentences:
        return " ".join(parts)
    return " ".join(parts[:max_sentences]).strip()


async def chat_about_repo(
    user_message: str,
    summary: str,
    tech_stack: list[str],
    nodes: list[dict],
    edges: list[dict],
    *,
    code_context: dict | None = None,
) -> str:
    if skip_gemini_enabled():
        return (
            "Chat uses Gemini, which is turned off (`GITMAP_SKIP_GEMINI=1`). "
            "Remove that line from `.env` and set `GEMINI_API_KEY` to get answers here. "
            "The graph is still a real folder-structure preview from GitHub."
        )

    chat_nodes, chat_edges = _compact_graph_for_chat(nodes, edges)
    context: dict = {
        "summary": summary,
        "tech_stack": tech_stack,
        "nodes": chat_nodes,
        "edges": chat_edges,
    }
    if code_context:
        if code_context.get("file_tree_sample"):
            context["file_tree_sample"] = code_context["file_tree_sample"]
        if code_context.get("code_excerpts"):
            context["code_excerpts"] = code_context["code_excerpts"]
        if code_context.get("note"):
            context["note"] = code_context["note"]

    payload = json.dumps(context, indent=2)[:200_000]
    prompt = (
        "Repository evidence (JSON). Use architecture fields plus code_excerpts to describe what the code does.\n\n"
        f"{payload}\n\n"
        f"Question:\n{user_message}\n\n"
        "Answer directly first. If excerpts or graph omit something the question needs, say what is not covered."
    )

    _require_genai_api_key()
    try:
        async with genai.Client().aio as aclient:
            response = await aclient.models.generate_content(
                model=_gemini_model_id(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=CHAT_SYSTEM,
                    temperature=0.28,
                    max_output_tokens=_chat_max_output_tokens(),
                ),
            )
    except Exception as e:
        raise ValueError(f"Gemini API error: {type(e).__name__}: {e}") from e

    raw = _format_chat_for_plain_ui((response.text or "").strip())
    clipped = _truncate_chat_to_sentences(raw, max_sentences=3)
    return clipped or "(No response)"
