/**
 * API origin for fetch(). Prototype default is direct FastAPI so we do not rely on the
 * Vite proxy (it often breaks in embedded browsers, IPv4/IPv6 host mismatch, or preview).
 * Override with VITE_API_BASE (full URL, no trailing slash). Use "same" for same-origin /api.
 */
const base = () => {
  const raw = (import.meta.env.VITE_API_BASE ?? "").trim();
  if (raw === "same" || raw === ".") {
    return "";
  }
  if (raw) {
    return raw.replace(/\/$/, "");
  }
  return "http://127.0.0.1:8001";
};

async function parseError(res) {
  try {
    const j = await res.json();
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || x).join("; ");
    return JSON.stringify(j);
  } catch {
    const hint =
      res.status === 404
        ? " — is the backend running on port 8001? For `npm run preview`, use the same proxy as dev or set VITE_API_BASE."
        : "";
    return `Request failed (${res.status} ${res.statusText || ""})${hint}`.trim();
  }
}

export async function analyzeRepo(githubUrl, refresh = false) {
  const res = await fetch(`${base()}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, refresh }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchRecent(limit = 8) {
  const res = await fetch(`${base()}/api/recent?limit=${limit}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function sendChat(githubUrl, message) {
  const res = await fetch(`${base()}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, message }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
