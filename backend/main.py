import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github_fetcher import get_repo_data
from ai_analyzer import analyze_repo

app = FastAPI(title="GitMap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    github_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Accepts a GitHub URL, fetches the repo, runs Claude analysis,
    and returns graph data + summary.

    Response shape:
    {
      "repo": "owner/repo",
      "summary": "...",
      "tech_stack": [...],
      "nodes": [...],
      "edges": [...]
    }
    """
    github_token = os.getenv("GITHUB_TOKEN")  # optional — increases rate limit

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

    return {
        "repo": f"{repo_data['owner']}/{repo_data['repo']}",
        **graph,
    }
