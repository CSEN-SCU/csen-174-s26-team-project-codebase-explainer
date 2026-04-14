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

MAX_FILE_SIZE = 8_000    # chars per file — keeps total prompt under context limit
MAX_FILES_TO_READ = 15   # cap on how many files we send to the AI


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL."""
    url = url.strip().rstrip("/")
    pattern = r"github\.com[/:]([^/]+)/([^/\s\.]+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse GitHub URL: {url}")
    owner, repo = match.group(1), match.group(2)
    repo = repo.removesuffix(".git")
    return owner, repo


async def fetch_repo_tree(owner: str, repo: str, token: Optional[str] = None) -> list[dict]:
    """Fetch the full recursive file tree from the GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        # Get default branch first
        repo_resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
        repo_resp.raise_for_status()
        default_branch = repo_resp.json().get("default_branch", "main")

        # Fetch recursive tree
        tree_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}",
            params={"recursive": "1"},
            headers=headers,
        )
        tree_resp.raise_for_status()
        data = tree_resp.json()

    return [item for item in data.get("tree", []) if item.get("type") == "blob"]


async def fetch_file_content(owner: str, repo: str, path: str, token: Optional[str] = None) -> Optional[str]:
    """Fetch raw content of a single file."""
    headers = {"Accept": "application/vnd.github.raw+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        content = resp.text
        if len(content) > MAX_FILE_SIZE:
            return content[:MAX_FILE_SIZE] + "\n... [truncated]"
        return content


def select_files_to_read(tree: list[dict]) -> list[str]:
    """
    Pick the most relevant files to send to Claude.
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

    # Sort secondary by depth (shallow first) then alphabetically
    secondary.sort(key=lambda p: (p.count("/"), p))

    selected = priority + secondary
    return selected[:MAX_FILES_TO_READ]


async def get_repo_data(github_url: str, token: Optional[str] = None) -> dict:
    """
    Main entry point. Returns:
      {
        "owner": str,
        "repo": str,
        "file_tree": [str, ...],        # all paths
        "files": {"path": "content"},   # selected files with content
      }
    """
    owner, repo = parse_github_url(github_url)
    tree = await fetch_repo_tree(owner, repo, token)

    all_paths = [item["path"] for item in tree]
    paths_to_read = select_files_to_read(tree)

    # Fetch all selected files concurrently
    import asyncio
    contents = await asyncio.gather(
        *[fetch_file_content(owner, repo, p, token) for p in paths_to_read]
    )

    files = {path: content for path, content in zip(paths_to_read, contents) if content}

    return {
        "owner": owner,
        "repo": repo,
        "file_tree": all_paths,
        "files": files,
    }
