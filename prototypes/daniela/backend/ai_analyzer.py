"""
Architecture analysis and Q&A using Google Gemini.
Optional heuristic-only mode when GITMAP_SKIP_GEMINI=1 (no API key / quota needed).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai


def skip_gemini_enabled() -> bool:
    return os.getenv("GITMAP_SKIP_GEMINI", "").strip().lower() in ("1", "true", "yes", "on")


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
            "description": f"Top-level files in {owner}/{repo} (mock mode — folder layout only).",
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
        f"Heuristic preview only (Gemini off): {owner}/{repo} has {n} tracked file(s) "
        f"in {len(top_names)} top-level folder group(s). "
        "Nodes mirror the repo tree, not inferred architecture. "
        "Unset GITMAP_SKIP_GEMINI and set GEMINI_API_KEY for AI analysis and chat."
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


def _configure() -> None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)


def _model_json() -> Any:
    _configure()
    name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return genai.GenerativeModel(
        name,
        system_instruction=SYSTEM_ANALYSIS,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )


def _model_chat() -> Any:
    _configure()
    name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return genai.GenerativeModel(
        name,
        system_instruction=CHAT_SYSTEM,
        generation_config=genai.GenerationConfig(temperature=0.35),
    )


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
    model = _model_json()
    try:
        response = await model.generate_content_async(prompt)
    except Exception as e:
        raise ValueError(f"Gemini API error: {type(e).__name__}: {e}") from e

    raw = response.text or ""
    data = _parse_json_object(raw)
    for key in ("summary", "tech_stack", "nodes", "edges"):
        if key not in data:
            raise ValueError(f"Missing key in analysis JSON: {key}")
    return data


CHAT_SYSTEM = """You are a helpful assistant explaining a software repository architecture.
Answer using only the provided summary, tech stack, graph nodes/edges, and the user's question.
If you are unsure, say what is unknown. Be concise."""


async def chat_about_repo(
    user_message: str,
    summary: str,
    tech_stack: list[str],
    nodes: list[dict],
    edges: list[dict],
) -> str:
    if skip_gemini_enabled():
        return (
            "Chat uses Gemini, which is turned off (`GITMAP_SKIP_GEMINI=1`). "
            "Remove that line from `.env` and set `GEMINI_API_KEY` to get answers here. "
            "The graph is still a real folder-structure preview from GitHub."
        )

    context = {
        "summary": summary,
        "tech_stack": tech_stack,
        "nodes": nodes,
        "edges": edges,
    }
    payload = json.dumps(context, indent=2)[:120_000]
    prompt = f"""Repository context (JSON):\n{payload}\n\nUser question:\n{user_message}"""

    model = _model_chat()
    try:
        response = await model.generate_content_async(prompt)
    except Exception as e:
        raise ValueError(f"Gemini API error: {type(e).__name__}: {e}") from e

    return (response.text or "").strip() or "(No response)"
