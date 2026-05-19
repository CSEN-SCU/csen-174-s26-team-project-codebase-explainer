import importlib.util
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

from pydantic import BaseModel, Field

from ai_openai import analyze_repo, build_chat_code_context, chat_about_repo
from fetcher.github_fetcher import get_repo_data, parse_github_url
from database import delete_cache, get_cached, init_db, list_recent, save_analysis

# Load this backend's local .env
load_dotenv(Path(__file__).resolve().parent / ".env")

REPO_ROOT = Path(__file__).resolve().parents[2]

# Trusted browser origins for local dev (static server on 5173, API/UI on 8001).
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
)


def get_cors_origins() -> list[str]:
    """Explicit allowlist; extend via comma-separated CORS_ORIGINS in .env for deployment."""
    origins: list[str] = []
    for origin in DEFAULT_CORS_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    extra = os.getenv("CORS_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


init_db()
app = FastAPI(title="GitMap API — Final (OpenAI)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class AnalyzeRequest(BaseModel):
    github_url: str
    refresh: bool = False


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    github_url: str
    message: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


def _is_github_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower()
    return host in {"github.com", "www.github.com"}


def _load_example_questions() -> list[str]:
    module_path = REPO_ROOT / "final" / "example_questions.py"
    spec = importlib.util.spec_from_file_location("example_questions", module_path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    getter = getattr(module, "get_example_questions", None)
    if not callable(getter):
        return []
    out = getter({})
    if not isinstance(out, list):
        return []
    return [str(x).strip() for x in out if str(x).strip()]


@app.get("/api/health")
def health():
    return {"status": "ok", "prototype": "final", "ai": "openai"}


@app.get("/api/example-questions")
def example_questions():
    return {"questions": _load_example_questions()}


@app.get("/api/recent")
def recent(limit: int = Query(default=8, le=50)):
    return {"analyses": list_recent(limit)}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    if not _is_github_url(request.github_url):
        raise HTTPException(status_code=400, detail="Could not parse GitHub URL")
    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not request.refresh:
        cached = get_cached(owner, repo_name)
        if cached:
            safe = dict(cached)
            safe.pop("code_context", None)
            return {"repo": f"{owner}/{repo_name}", **safe}

    try:
        repo_data = await get_repo_data(request.github_url, token=os.getenv("GITHUB_TOKEN"))
    except ValueError as e:
        print(f"[analyze] GitHub fetch ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[analyze] GitHub fetch Exception ({type(e).__name__}): {e}")
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {type(e).__name__}: {e}")

    try:
        graph = await analyze_repo(repo_data)
    except Exception as e:
        print(f"[analyze] OpenAI analysis Exception ({type(e).__name__}): {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {type(e).__name__}: {e}")

    code_context = build_chat_code_context(
        repo_data.get("file_tree") or [], repo_data.get("files") or {}
    )
    save_analysis(
        owner,
        repo_name,
        request.github_url,
        graph,
        source="openai",
        code_context=code_context,
    )

    return {"repo": f"{owner}/{repo_name}", "cached": False, "source": "openai", **graph}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    msg = (request.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")
    if not _is_github_url(request.github_url):
        raise HTTPException(status_code=400, detail="Could not parse GitHub URL")

    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cached = get_cached(owner, repo_name)
    if not cached:
        raise HTTPException(status_code=400, detail="Analyze this repository first.")

    history = [
        {"role": turn.role, "content": (turn.content or "").strip()}
        for turn in request.history
        if (turn.content or "").strip()
    ]

    try:
        answer = await chat_about_repo(
            msg,
            cached.get("summary") or "",
            cached.get("tech_stack") or [],
            cached.get("nodes") or [],
            cached.get("edges") or [],
            code_context=cached.get("code_context"),
            history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"answer": answer, "repo": f"{owner}/{repo_name}"}


@app.delete("/api/cache")
def clear_cache(github_url: str = Query(...)):
    try:
        owner, repo_name = parse_github_url(github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    deleted = delete_cache(owner, repo_name)
    return {"deleted": deleted, "repo": f"{owner}/{repo_name}"}
