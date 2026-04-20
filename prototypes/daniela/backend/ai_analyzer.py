"""
Architecture analysis and Q&A using Google Gemini.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai

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
