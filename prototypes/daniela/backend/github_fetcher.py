"""
Fetch repository structure and file text via the GitHub GraphQL API (v4).
https://docs.github.com/en/graphql
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urlparse
import httpx

GITHUB_GRAPHQL = "https://api.github.com/graphql"

READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs",
    ".cpp", ".c", ".h", ".cs", ".php", ".swift", ".kt", ".md",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
}

PRIORITY_FILES = {
    "readme.md", "readme.txt", "readme.rst",
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "go.mod", "cargo.toml", "pom.xml", "build.gradle",
    "docker-compose.yml", "dockerfile",
    "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs",
    "manage.py", "server.js", "server.ts",
}

MAX_FILE_SIZE = 8_000
MAX_FILES_TO_READ = 15


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Accepts https URLs (with optional /tree/...), git@github.com:owner/repo.git, or owner/repo.
    Repo names may contain dots (e.g. my.repo).
    """
    raw = url.strip().rstrip("/")
    if not raw:
        raise ValueError("GitHub URL is empty")

    # git@github.com:owner/repo
    if raw.startswith("git@"):
        m = re.match(
            r"git@github\.com:([^/]+)/([^/\s]+?)(?:\.git)?(?:/|$)",
            raw,
            re.IGNORECASE,
        )
        if not m:
            raise ValueError(f"Could not parse Git SSH URL: {url}")
        return m.group(1), m.group(2)

    if "://" not in raw:
        raw = "https://" + raw.lstrip("/")

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if "github.com" not in host:
        raise ValueError(f"Not a github.com URL: {url}")

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(
            f"Expected https://github.com/owner/repository — could not parse: {url}"
        )
    owner, repo = parts[0], parts[1]
    return owner, repo.removesuffix(".git")


def _headers(token: Optional[str]) -> dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _graphql(
    client: httpx.AsyncClient,
    query: str,
    variables: dict[str, Any],
    token: Optional[str],
) -> dict[str, Any]:
    try:
        r = await client.post(
            GITHUB_GRAPHQL,
            json={"query": query, "variables": variables},
            headers=_headers(token),
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (401, 403):
            raise ValueError(
                "GitHub API rejected the request (often rate limits without a token). "
                "Set GITHUB_TOKEN in backend/.env (see .env.example), restart the server, and try again."
            ) from e
        raise ValueError(f"GitHub API HTTP error {status}.") from e
    body = r.json()
    if body.get("errors"):
        msgs = "; ".join(e.get("message", "?") for e in body["errors"])
        raise ValueError(f"GitHub GraphQL: {msgs}")
    return body["data"]


QUERY_REPO_LOOKUP = """
query RepoLookup($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
  }
}
"""

QUERY_TREE = """
query TreeEntries($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Tree {
        oid
        entries {
          oid
          name
          type
        }
      }
    }
  }
}
"""

QUERY_BLOB = """
query BlobText($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Blob {
        text
        isBinary
      }
    }
  }
}
"""


def _path_expression(dir_path: str) -> str:
    """Build Git object expression for the tree at dir_path (default branch = HEAD)."""
    if not dir_path:
        return "HEAD:"
    return f"HEAD:{dir_path}"


async def _require_repository(
    owner: str,
    repo: str,
    token: Optional[str],
    client: httpx.AsyncClient,
) -> None:
    data = await _graphql(
        client,
        QUERY_REPO_LOOKUP,
        {"owner": owner, "name": repo},
        token,
    )
    if data.get("repository") is None:
        raise ValueError(
            "Repository not found or not accessible. "
            "Check the URL; for private repositories add GITHUB_TOKEN to .env."
        )


async def _list_all_blob_paths(
    owner: str,
    repo: str,
    token: Optional[str],
    client: httpx.AsyncClient,
) -> list[str]:
    """Walk the repo tree using GraphQL only; collect every blob path."""
    paths: list[str] = []
    queue: list[str] = [""]

    while queue:
        dir_path = queue.pop(0)
        expr = _path_expression(dir_path)
        data = await _graphql(
            client,
            QUERY_TREE,
            {"owner": owner, "name": repo, "expression": expr},
            token,
        )
        obj = (data.get("repository") or {}).get("object")
        if not obj or not obj.get("entries"):
            continue
        for ent in obj["entries"]:
            name = ent["name"]
            typ = (ent.get("type") or "").lower()
            full = f"{dir_path}/{name}" if dir_path else name
            if typ == "blob":
                paths.append(full)
            elif typ == "tree":
                queue.append(full)

    return paths


async def _fetch_blob_text(
    owner: str,
    repo: str,
    path: str,
    token: Optional[str],
    client: httpx.AsyncClient,
) -> Optional[str]:
    expr = f"HEAD:{path}" if path else "HEAD:"
    data = await _graphql(
        client,
        QUERY_BLOB,
        {"owner": owner, "name": repo, "expression": expr},
        token,
    )
    blob = (data.get("repository") or {}).get("object")
    if not blob:
        return None
    if blob.get("isBinary"):
        return None
    text = blob.get("text")
    if text is None:
        return None
    if len(text) > MAX_FILE_SIZE:
        return text[:MAX_FILE_SIZE] + "\n... [truncated]"
    return text


def select_files_to_read(tree: list[dict]) -> list[str]:
    priority: list[str] = []
    secondary: list[str] = []

    for item in tree:
        path: str = item["path"]
        filename = path.split("/")[-1].lower()
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""

        if filename in PRIORITY_FILES:
            priority.append(path)
        elif ext in READABLE_EXTENSIONS:
            secondary.append(path)

    secondary.sort(key=lambda p: (p.count("/"), p))

    selected = priority + secondary
    return selected[:MAX_FILES_TO_READ]


async def get_repo_data(github_url: str, token: Optional[str] = None) -> dict:
    """
    Returns owner, repo, file_tree (all blob paths), files (selected path -> content).
    Uses GitHub GraphQL only (no REST).
    """
    owner, repo = parse_github_url(github_url)

    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        await _require_repository(owner, repo, token, client)
        blob_paths = await _list_all_blob_paths(owner, repo, token, client)
        tree_items = [{"path": p} for p in blob_paths]
        paths_to_read = select_files_to_read(tree_items)

        contents = await asyncio.gather(
            *[_fetch_blob_text(owner, repo, p, token, client) for p in paths_to_read]
        )

    files = {path: content for path, content in zip(paths_to_read, contents) if content}

    return {
        "owner": owner,
        "repo": repo,
        "file_tree": blob_paths,
        "files": files,
    }
