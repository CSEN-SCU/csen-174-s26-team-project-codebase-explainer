"""
Entry point for GitMap final app — works both locally and on Render.

Locally:
    python3 app.py          (keys loaded from .env in this directory)

On Render:
    Build:  pip install -r requirements.txt
    Start:  uvicorn app:app --host 0.0.0.0 --port $PORT
    Set OPENAI_API_KEY and GITHUB_TOKEN in Render's Environment dashboard.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # final/backend/
FRONTEND = HERE.parent / "frontend"             # final/frontend/

# Load .env locally — silently skipped on Render (vars come from dashboard)
from dotenv import load_dotenv
load_dotenv(HERE / ".env")

# OPENAI_API_KEY is required — fail fast with a clear message
if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not set.\n"
        "  Locally: fill in final/backend/.env\n"
        "  Render:  add it under Environment in the Render dashboard"
    )

# GITHUB_TOKEN is optional but recommended
if not os.environ.get("GITHUB_TOKEN"):
    print(
        "Warning: GITHUB_TOKEN is not set. "
        "GitHub API rate limit will be 60 req/hr instead of 5,000."
    )

from main import app
from fastapi.staticfiles import StaticFiles

# Serve the frontend so http://localhost:8001 shows the UI
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    print(f"\n  GitMap running at http://127.0.0.1:{port}\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
