"""
SQLite caching layer for GitMap.
Stores analysis results so repeated requests for the same repo skip the AI call.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "gitmap.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                owner       TEXT NOT NULL,
                repo        TEXT NOT NULL,
                github_url  TEXT NOT NULL,
                summary     TEXT,
                tech_stack  TEXT,   -- JSON array
                nodes       TEXT,   -- JSON array
                edges       TEXT,   -- JSON array
                created_at  TEXT NOT NULL,
                UNIQUE(owner, repo)
            )
        """)
        conn.commit()


def get_cached(owner: str, repo: str) -> Optional[dict]:
    """Return cached analysis for owner/repo, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE owner=? AND repo=?",
            (owner, repo)
        ).fetchone()
    if not row:
        return None
    return {
        "owner": row["owner"],
        "repo": row["repo"],
        "github_url": row["github_url"],
        "summary": row["summary"],
        "tech_stack": json.loads(row["tech_stack"] or "[]"),
        "nodes": json.loads(row["nodes"] or "[]"),
        "edges": json.loads(row["edges"] or "[]"),
        "created_at": row["created_at"],
        "cached": True,
    }


def save_analysis(owner: str, repo: str, github_url: str, graph: dict):
    """Upsert an analysis result into the DB."""
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO analyses (owner, repo, github_url, summary, tech_stack, nodes, edges, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(owner, repo) DO UPDATE SET
                github_url  = excluded.github_url,
                summary     = excluded.summary,
                tech_stack  = excluded.tech_stack,
                nodes       = excluded.nodes,
                edges       = excluded.edges,
                created_at  = excluded.created_at
        """, (
            owner,
            repo,
            github_url,
            graph.get("summary", ""),
            json.dumps(graph.get("tech_stack", [])),
            json.dumps(graph.get("nodes", [])),
            json.dumps(graph.get("edges", [])),
            now,
        ))
        conn.commit()


def list_recent(limit: int = 10) -> list[dict]:
    """Return the most recently analyzed repos."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT owner, repo, github_url, summary, tech_stack, created_at "
            "FROM analyses ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [
        {
            "owner": r["owner"],
            "repo": r["repo"],
            "github_url": r["github_url"],
            "summary": r["summary"],
            "tech_stack": json.loads(r["tech_stack"] or "[]"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def delete_cache(owner: str, repo: str) -> bool:
    """Delete a cached analysis so it gets re-analyzed next time."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM analyses WHERE owner=? AND repo=?", (owner, repo)
        )
        conn.commit()
    return cursor.rowcount > 0
