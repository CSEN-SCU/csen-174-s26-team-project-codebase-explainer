const base = () => import.meta.env.VITE_API_BASE ?? "";

async function parseError(res) {
  try {
    const j = await res.json();
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || x).join("; ");
    return JSON.stringify(j);
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function analyzeRepo(githubUrl, refresh = false) {
  const res = await fetch(`${base}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, refresh }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchRecent(limit = 8) {
  const res = await fetch(`${base}/api/recent?limit=${limit}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function sendChat(githubUrl, message) {
  const res = await fetch(`${base}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, message }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
