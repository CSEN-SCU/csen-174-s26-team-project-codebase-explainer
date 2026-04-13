import json
from openai import AsyncOpenAI

client = AsyncOpenAI()

SYSTEM_PROMPT = """You are an expert software architect. Your job is to analyze a GitHub repository
and produce a structured JSON description of its architecture for visualization as an interactive graph.

Always respond with valid JSON only — no markdown, no explanation outside the JSON.
"""

ANALYSIS_PROMPT = """Analyze this repository and return a JSON object with the following structure:

{{
  "summary": "2-3 sentence plain-English overview of what this project does",
  "tech_stack": ["list", "of", "main", "technologies"],
  "nodes": [
    {{
      "id": "unique_id",
      "label": "Display Name",
      "type": "module|service|config|entrypoint|external|database|test",
      "description": "1 sentence description",
      "files": ["path/to/file.py"]
    }}
  ],
  "edges": [
    {{
      "source": "node_id",
      "target": "node_id",
      "label": "imports|calls|extends|configures|stores"
    }}
  ]
}}

Rules:
- Create one node per logical module or component (not one per file)
- Group related files into a single node when they form a logical unit
- Only include edges that represent real relationships visible in the code
- Keep it to 5-15 nodes max — focus on the important structure
- node `type` values: module, service, config, entrypoint, external, database, test

Repository: {owner}/{repo}

File tree:
{file_tree}

File contents:
{file_contents}
"""


def build_prompt(repo_data: dict) -> str:
    file_tree_str = "\n".join(repo_data["file_tree"][:200])

    file_contents_parts = []
    for path, content in repo_data["files"].items():
        file_contents_parts.append(f"=== {path} ===\n{content}")
    file_contents_str = "\n\n".join(file_contents_parts)

    return ANALYSIS_PROMPT.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        file_tree=file_tree_str,
        file_contents=file_contents_str,
    )


async def analyze_repo(repo_data: dict) -> dict:
    """
    Send repo data to OpenAI and return parsed graph JSON.
    Returns: { summary, tech_stack, nodes, edges }
    """
    prompt = build_prompt(repo_data)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        raise ValueError(f"OpenAI API error: {type(e).__name__}: {e}")

    text = response.choices[0].message.content or ""
    text = text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```", 1)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()

    # Find the outermost JSON object in case there's leading/trailing text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response. Raw response:\n{text[:500]}")
    text = text[start:end]

    return json.loads(text)
