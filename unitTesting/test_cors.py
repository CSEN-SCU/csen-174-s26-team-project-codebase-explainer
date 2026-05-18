"""CORS allowlist for final/backend/main.py."""

from fastapi.testclient import TestClient

import main


def test_get_cors_origins_includes_local_dev_defaults():
    origins = main.get_cors_origins()
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:5173" in origins
    assert "*" not in origins


def test_get_cors_origins_merges_env_allowlist(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://gitmap.example.com, https://staging.example.com/")
    origins = main.get_cors_origins()
    assert "https://gitmap.example.com" in origins
    assert "https://staging.example.com" in origins


def test_cors_allows_trusted_origin_preflight():
    client = TestClient(main.app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_blocks_untrusted_origin():
    client = TestClient(main.app)
    response = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"
