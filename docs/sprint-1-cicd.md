Merged PR:
https://github.com/CSEN-SCU/csen-174-s26-team-project-codebase-explainer/actions/runs/25405117888

Secrets: 
Our team manages two main secrets: an API key for the AI provider and a GitHub API token for accessing repository data. Both secrets are stored securely in environment variables and are used in both CI and deployment environments. The CI pipeline uses these keys to run integration tests that depend on real API responses, while the deployment environment uses them to enable full application functionality for users. At runtime, the backend reads these secrets from environment variables (e.g., through a .env file locally or CI/deployment settings), ensuring that sensitive data is never hardcoded in the codebase.

url: 
https://csen-174-s26-team-project-codebase-zufu.onrender.com

Screenshot:
<img width="512" height="261" alt="Image" src="https://github.com/user-attachments/assets/81659f9a-b62a-40b1-bcbb-e3d688c6d3f6" />

Why we chose Render: 
We chose Render because it deploys straight from GitHub with no config files — just a build command (`pip install -r requirements.txt`) and a start command (`uvicorn app:app --host 0.0.0.0 --port $PORT`), which matched our FastAPI stack perfectly with Python being our main coding language and all. The first deployment failed because `requirements.txt` still had Flask and gunicorn from an old prototype, so uvicorn was never installed. After fixing the deps and hardcoded `127.0.0.1` API URL in the frontend, it went live.

