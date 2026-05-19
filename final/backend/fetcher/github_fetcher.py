import re
import httpx
from typing import Optional

GITHUB_API = "https://api.github.com"

# File extensions worth reading for analysis
READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs",
    ".cpp", ".c", ".h", ".cs", ".php", ".swift", ".kt", ".md",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
}

# Files that are high-value for architecture understanding
PRIORITY_FILES = {
    "readme.md", "readme.txt", "readme.rst",
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "go.mod", "cargo.toml", "pom.xml", "build.gradle",
    "docker-compose.yml", "dockerfile",
    "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs",
    "manage.py", "server.js", "server.ts",
}

MAX_FILE_SIZE = 6_000    # chars per file
MAX_FILES_TO_READ = 25


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL."""
    url = url.strip().rstrip("/")
    pattern = r"(?<![a-zA-Z0-9])github\.com[/:]([^/]+)/([^/\s\.]+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse GitHub URL: {url}")
    owner, repo = match.group(1), match.group(2)
    repo = repo.removesuffix(".git")
    return owner, repo


def _check_github_response(resp: httpx.Response) -> None:
    """Raise a clear, human-readable ValueError for known GitHub API error codes."""
    if resp.status_code == 401:
        raise ValueError(
            "GitHub token is invalid or expired (401 Unauthorized). "
            "Generate a new one at https://github.com/settings/tokens "
            "and update GITHUB_TOKEN in final/backend/.env"
        )
    if resp.status_code == 403:
        remaining = resp.headers.get("x-ratelimit-remaining", "?")
        if remaining == "0" or "rate limit" in (resp.text or "").lower():
            raise ValueError(
                "GitHub API rate limit exceeded. Add or refresh GITHUB_TOKEN in "
                "final/backend/.env — create one at https://github.com/settings/tokens"
            )
        raise ValueError(f"GitHub API returned 403 Forbidden: {resp.text[:200]}")
    if resp.status_code == 404:
        raise ValueError("Repository not found — check the URL and make sure it's public.")
    if resp.status_code == 422:
        raise ValueError(
            "Repository tree is too large for the GitHub API. "
            "Try a smaller repo, or ensure GITHUB_TOKEN is set."
        )
    resp.raise_for_status()


async def fetch_repo_tree(owner: str, repo: str, token: Optional[str] = None) -> list[dict]:
    """Fetch the full recursive file tree from the GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        repo_resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
        _check_github_response(repo_resp)
        default_branch = repo_resp.json().get("default_branch", "main")

        tree_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}",
            params={"recursive": "1"},
            headers=headers,
        )
        _check_github_response(tree_resp)
        data = tree_resp.json()

    if data.get("truncated"):
        # Still usable — just warn by continuing with partial tree
        pass

    return [item for item in data.get("tree", []) if item.get("type") == "blob"]


async def fetch_file_content(owner: str, repo: str, path: str, token: Optional[str] = None) -> Optional[str]:
    """Fetch raw content of a single file. Returns None on any error."""
    headers = {"Accept": "application/vnd.github.raw+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            content = resp.text
            if len(content) > MAX_FILE_SIZE:
                return content[:MAX_FILE_SIZE] + "\n... [truncated]"
            return content
    except Exception:
        return None


def select_files_to_read(tree: list[dict]) -> list[str]:
    """
    Pick the most relevant files to send to the AI.
    Priority: known entry-point / config files first, then source files by depth.
    """
    priority = []
    secondary = []

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
    Main entry point. Returns owner, repo, full file_tree paths, and selected file contents.
    Raises ValueError with a human-readable message on GitHub API errors.
    """
    owner, repo = parse_github_url(github_url)

    try:
        tree = await fetch_repo_tree(owner, repo, token)
    except ValueError:
        raise  # already human-readable
    except httpx.TimeoutException:
        raise ValueError(
            "GitHub API timed out. The repository may be very large. Try again, "
            "or add a GITHUB_TOKEN to your .env to improve reliability."
        )
    except Exception as e:
        raise ValueError(f"Could not fetch repository from GitHub: {e}")

    all_paths = [item["path"] for item in tree]
    paths_to_read = select_files_to_read(tree)

    import asyncio
    contents = await asyncio.gather(
        *[fetch_file_content(owner, repo, p, token) for p in paths_to_read],
        return_exceptions=False,
    )

    files = {path: content for path, content in zip(paths_to_read, contents) if content}

    return {
        "owner": owner,
        "repo": repo,
        "file_tree": all_paths,
        "files": files,
    }
