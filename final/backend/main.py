import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_openai import analyze_repo, build_chat_code_context, chat_about_repo

# Load this backend's local .env
load_dotenv(Path(__file__).resolve().parent / ".env")

# Reuse Daniela's GitHub + DB modules to speed integration.
REPO_ROOT = Path(__file__).resolve().parents[2]
DANIELA_BACKEND = REPO_ROOT / "prototypes" / "daniela" / "backend"
if str(DANIELA_BACKEND) not in sys.path:
    sys.path.append(str(DANIELA_BACKEND))

from database import delete_cache, get_cached, init_db, list_recent, save_analysis  # noqa: E402

# Use Sally's REST GitHub fetcher (not GraphQL).
SALLY_FETCHER_PATH = REPO_ROOT / "prototypes" / "sally" / "backend" / "fetcher" / "github_fetcher.py"
_fetcher_spec = importlib.util.spec_from_file_location("sally_fetcher", SALLY_FETCHER_PATH)
if _fetcher_spec is None or _fetcher_spec.loader is None:
    raise RuntimeError("Could not load Sally REST fetcher.")
_fetcher_module = importlib.util.module_from_spec(_fetcher_spec)
_fetcher_spec.loader.exec_module(_fetcher_module)
get_repo_data = _fetcher_module.get_repo_data
parse_github_url = _fetcher_module.parse_github_url

init_db()
app = FastAPI(title="GitMap API — Final (OpenAI)")

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


def _load_example_questions() -> list[str]:
    module_path = REPO_ROOT / "prototypes" / "final" / "example_questions.py"
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {e}")

    try:
        graph = await analyze_repo(repo_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

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

    try:
        owner, repo_name = parse_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cached = get_cached(owner, repo_name)
    if not cached:
        raise HTTPException(status_code=400, detail="Analyze this repository first.")

    try:
        answer = await chat_about_repo(
            msg,
            cached.get("summary") or "",
            cached.get("tech_stack") or [],
            cached.get("nodes") or [],
            cached.get("edges") or [],
            code_context=cached.get("code_context"),
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
