import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github_fetcher import get_repo_data, parse_github_url
from ai_analyzer import analyze_repo, chat_about_repo
from database import init_db, get_cached, save_analysis, list_recent, delete_cache

init_db()

app = FastAPI(title="GitMap API — Daniela (GraphQL + Gemini)")

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
    return {"status": "ok", "prototype": "daniela", "github": "graphql", "ai": "gemini"}


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
            return {"repo": f"{owner}/{repo_name}", **cached}

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

    save_analysis(owner, repo_name, request.github_url, graph)

    return {
        "repo": f"{owner}/{repo_name}",
        "cached": False,
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

    try:
        answer = await chat_about_repo(
            msg,
            cached.get("summary") or "",
            cached.get("tech_stack") or [],
            cached.get("nodes") or [],
            cached.get("edges") or [],
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
