import os
from pathlib import Path

from dotenv import load_dotenv

# Always load backend/.env even if uvicorn was started from another directory.
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github_fetcher import fetch_extra_repo_files, get_repo_data, parse_github_url
from ai_analyzer import (
    analysis_is_heuristic_preview,
    analyze_repo,
    build_chat_code_context,
    chat_about_repo,
    skip_gemini_enabled,
)
from database import init_db, get_cached, save_analysis, list_recent, delete_cache

init_db()

app = FastAPI(title="GitMap API — Daniela (GraphQL + Gemini / mock)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    github_url: str
    refresh: bool = False


class ChatRequest(BaseModel):
    github_url: str
    message: str


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "prototype": "daniela",
        "github": "graphql",
        "ai": "mock" if skip_gemini_enabled() else "gemini",
    }


@app.get("/api/recent")
def recent(limit: int = Query(default=8, le=50)):
    return {"analyses": list_recent(limit)}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not request.refresh:
        cached = get_cached(owner, repo_name)
        if cached:
            # Do not reuse tree-only / mock cache once Gemini is enabled (avoids stale "preview" text).
            cached_heuristic = cached.get("source") == "mock" or (
                cached.get("source") is None and analysis_is_heuristic_preview(cached)
            )
            if not (not skip_gemini_enabled() and cached_heuristic):
                safe = dict(cached)
                safe.pop("code_context", None)
                return {"repo": f"{owner}/{repo_name}", **safe}

    github_token = os.getenv("GITHUB_TOKEN")

    try:
        repo_data = await get_repo_data(request.github_url, token=github_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub GraphQL failed: {e}")

    try:
        graph = await analyze_repo(repo_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    analysis_source = "mock" if skip_gemini_enabled() else "gemini"
    merged_files = dict(repo_data["files"])
    try:
        extra_files = await fetch_extra_repo_files(
            owner,
            repo_name,
            github_token,
            repo_data["file_tree"],
            set(merged_files.keys()),
            max_additional=24,
        )
        merged_files.update(extra_files)
    except Exception:
        pass
    code_context = build_chat_code_context(repo_data["file_tree"], merged_files)
    save_analysis(
        owner,
        repo_name,
        request.github_url,
        graph,
        source=analysis_source,
        code_context=code_context,
    )

    return {
        "repo": f"{owner}/{repo_name}",
        "cached": False,
        "source": analysis_source,
        **graph,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    msg = (request.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cached = get_cached(owner, repo_name)
    if not cached:
        raise HTTPException(
            status_code=400,
            detail="Analyze this repository first so we have architecture context to answer.",
        )

    code_ctx = cached.get("code_context")
    if not code_ctx or not code_ctx.get("code_excerpts"):
        try:
            rd = await get_repo_data(request.github_url, token=os.getenv("GITHUB_TOKEN"))
            merged = dict(rd["files"])
            extra = await fetch_extra_repo_files(
                owner,
                repo_name,
                os.getenv("GITHUB_TOKEN"),
                rd["file_tree"],
                set(merged.keys()),
                max_additional=24,
            )
            merged.update(extra)
            code_ctx = build_chat_code_context(rd["file_tree"], merged)
        except Exception:
            code_ctx = None

    try:
        answer = await chat_about_repo(
            msg,
            cached.get("summary") or "",
            cached.get("tech_stack") or [],
            cached.get("nodes") or [],
            cached.get("edges") or [],
            code_context=code_ctx,
        )
    except ValueError as e:
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
