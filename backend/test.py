import httpx
import json

resp = httpx.post(
    "http://localhost:8000/analyze",
    json={"github_url": "https://github.com/tiangolo/fastapi"},
    timeout=60,
)

print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
