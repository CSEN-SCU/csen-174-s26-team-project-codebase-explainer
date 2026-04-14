import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from github_fetcher import get_repo_data, parse_github_url
from ai_analyzer import analyze_repo
from database import init_db, get_cached, save_analysis, list_recent, delete_cache

# Initialize DB on startup
init_db()

app = FastAPI(title="GitMap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class AnalyzeRequest(BaseModel):
    github_url: str
    refresh: bool = False  # set True to bypass cache


@app.get("/")
def root():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "GitMap API — see /docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/recent")
def recent(limit: int = Query(default=8, le=50)):
    """Return the most recently analyzed repos from the DB."""
    return {"analyses": list_recent(limit)}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Accepts a GitHub URL, checks the cache, fetches the repo,
    runs AI analysis, stores the result, and returns graph data + summary.

    Response shape:
    {
      "repo":       "owner/repo",
      "cached":     bool,
      "summary":    "...",
      "tech_stack": [...],
      "nodes":      [...],
      "edges":      [...],
      "created_at": "..."
    }
    """
    # Parse URL early to check cache before any network calls
    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check cache (unless refresh requested)
    if not request.refresh:
        cached = get_cached(owner, repo_name)
        if cached:
            return {
                "repo": f"{owner}/{repo_name}",
                **cached,
            }

    github_token = os.getenv("GITHUB_TOKEN")

    try:
        repo_data = await get_repo_data(request.github_url, token=github_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch repo: {e}")

    try:
        graph = await analyze_repo(repo_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Persist to DB
    save_analysis(owner, repo_name, request.github_url, graph)

    return {
        "repo": f"{owner}/{repo_name}",
        "cached": False,
        **graph,
    }


@app.delete("/cache")
def clear_cache(github_url: str = Query(...)):
    """Delete a cached analysis so the next request re-analyzes from scratch."""
    try:
        owner, repo_name = parse_github_url(github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    deleted = delete_cache(owner, repo_name)
    return {"deleted": deleted, "repo": f"{owner}/{repo_name}"}
