"""
chat.py — Daniela owns this file

Handles Q&A on top of a cached architecture snapshot.
POST /chat  →  { github_url, question }  →  { answer }

TODO (Daniela):
- Load the cached analysis for the given github_url from the database
- Build a system prompt that includes the repo summary, tech stack, and node descriptions
- Send the user's question + context to the AI
- Return a grounded answer (no hallucinating nodes that aren't in the graph)
"""

from fetcher.database import get_cached


async def answer_question(github_url: str, question: str) -> str:
    """
    Placeholder — returns a stub until Daniela implements the real chat logic.
    """
    cached = get_cached(*_parse(github_url))
    if not cached:
        return "This repo hasn't been analyzed yet. Please run /analyze first."

    # TODO: replace this with a real OpenAI call using the cached architecture as context
    return f"[Chat coming soon] You asked: '{question}' about {github_url}"


def _parse(url: str):
    """Extract (owner, repo) from a GitHub URL."""
    import re
    m = re.search(r"github\.com[/:]([^/]+)/([^/\s\.]+)", url)
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return m.group(1), m.group(2).removesuffix(".git")
