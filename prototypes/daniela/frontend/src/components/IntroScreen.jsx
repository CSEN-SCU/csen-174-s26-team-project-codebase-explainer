import { useEffect, useState } from "react";
import { fetchRecent } from "../api.js";

const cardStyle = {
  background: "rgba(255, 252, 247, 0.92)",
  border: "1px solid var(--ridge)",
  borderRadius: "var(--radius)",
  padding: "1rem 1.15rem",
  boxShadow: "var(--shadow)",
};

export default function IntroScreen({ onAnalyze, loading, error }) {
  const [url, setUrl] = useState("");
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    fetchRecent(8)
      .then((d) => setRecent(d.analyses || []))
      .catch(() => {});
  }, []);

  function submit(e) {
    e.preventDefault();
    const u = url.trim();
    if (!u) return;
    onAnalyze(u);
  }

  return (
    <div
      style={{
        minHeight: "100%",
        padding: "clamp(1.25rem, 4vw, 3rem)",
        maxWidth: "1080px",
        margin: "0 auto",
      }}
    >
      <header className="animate-in" style={{ marginBottom: "2rem" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontFamily: "var(--font-display)",
            fontSize: "0.72rem",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--ember)",
            border: "1px solid rgba(194, 65, 12, 0.35)",
            padding: "0.35rem 0.75rem",
            borderRadius: "999px",
            marginBottom: "0.85rem",
            background: "rgba(255,255,255,0.55)",
          }}
        >
          Gallery walk · GitMap prototype
        </div>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "clamp(2rem, 4.5vw, 2.85rem)",
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            margin: "0 0 0.75rem",
            maxWidth: "18ch",
          }}
        >
          Map a GitHub repo as a living architecture graph.
        </h1>
        <p
          style={{
            fontSize: "1.05rem",
            color: "var(--ink-soft)",
            maxWidth: "42ch",
            margin: 0,
          }}
        >
          Paste a public repository URL. Gemini reads what we pull via GitHub GraphQL; you
          explore the layout visually and ask questions in plain language.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gap: "0.85rem",
          marginBottom: "1.75rem",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        }}
      >
        <article className="animate-in stagger-1" style={cardStyle}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.78rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--pine)",
              margin: "0 0 0.45rem",
            }}
          >
            What it is
          </h2>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--ink-soft)" }}>
            <strong style={{ color: "var(--ink)" }}>GitMap</strong> is a small web tool that
            turns repository structure into an interactive node graph plus a chat that reasons
            over the same architecture snapshot we cached for that repo.
          </p>
        </article>
        <article className="animate-in stagger-2" style={cardStyle}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.78rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--pine)",
              margin: "0 0 0.45rem",
            }}
          >
            Who it is for
          </h2>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--ink-soft)" }}>
            Students on group projects, new developers onboarding, open-source contributors, and
            teammates who need orientation without reading every file first.
          </p>
        </article>
        <article className="animate-in stagger-3" style={cardStyle}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.78rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--pine)",
              margin: "0 0 0.45rem",
            }}
          >
            Problem it solves
          </h2>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--ink-soft)" }}>
            Large repos hide how modules connect. Text-only browsing is slow and easy to
            misread. GitMap foregrounds relationships so you build a mental model before you
            ship changes.
          </p>
        </article>
        <article className="animate-in stagger-4" style={cardStyle}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.78rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--pine)",
              margin: "0 0 0.45rem",
            }}
          >
            How to use it
          </h2>
          <ol style={{ margin: 0, paddingLeft: "1.1rem", color: "var(--ink-soft)", fontSize: "0.92rem" }}>
            <li>Ensure the backend is running on port 8001 and your keys are in <code style={{ fontSize: "0.8em" }}>.env</code>.</li>
            <li>Paste a <strong>public</strong> GitHub URL below and submit.</li>
            <li>Explore the graph; use the chat to ask how pieces relate.</li>
          </ol>
        </article>
      </div>

      <section
        className="animate-in stagger-5"
        style={{
          position: "relative",
          background: "rgba(255, 253, 249, 0.96)",
          border: "1px solid var(--ridge)",
          borderRadius: "calc(var(--radius) + 4px)",
          padding: "1.35rem 1.4rem 1.2rem",
          boxShadow: "var(--shadow)",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: "12px",
            border: "1px dashed rgba(201, 191, 176, 0.65)",
            borderRadius: "var(--radius)",
            pointerEvents: "none",
          }}
        />
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.2rem",
            margin: "0 0 0.35rem",
            position: "relative",
          }}
        >
          Try it
        </h2>
        <p style={{ margin: "0 0 1rem", color: "var(--ink-soft)", fontSize: "0.9rem", position: "relative" }}>
          First analysis may take 20–40 seconds. Repeating the same repo uses the SQLite cache
          unless you re-analyze from the workspace.
        </p>
        <form onSubmit={submit} style={{ display: "flex", gap: "0.55rem", flexWrap: "wrap", position: "relative" }}>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            disabled={loading}
            autoComplete="off"
            spellCheck={false}
            style={{
              flex: "1 1 220px",
              minWidth: 0,
              padding: "0.75rem 1rem",
              borderRadius: "10px",
              border: "1px solid var(--ridge)",
              fontSize: "0.82rem",
              outline: "none",
              background: "#fff",
            }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: "0.75rem 1.35rem",
              borderRadius: "10px",
              border: "none",
              cursor: loading ? "wait" : "pointer",
              fontWeight: 600,
              fontSize: "0.95rem",
              color: "#fffaf5",
              background: "linear-gradient(165deg, #c2410c, #9a3412)",
              boxShadow: "0 10px 24px rgba(154, 52, 18, 0.28)",
              opacity: loading ? 0.65 : 1,
            }}
          >
            {loading ? "Mapping…" : "Map repository"}
          </button>
        </form>
        {error && (
          <p style={{ color: "#b91c1c", fontSize: "0.88rem", margin: "0.75rem 0 0", position: "relative" }} role="alert">
            {error}
          </p>
        )}

        {recent.length > 0 && (
          <div style={{ marginTop: "1.15rem", position: "relative" }}>
            <h3
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "0.72rem",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--ink-soft)",
                margin: "0 0 0.5rem",
              }}
            >
              Recent (cached)
            </h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.45rem" }}>
              {recent.map((a) => (
                <button
                  key={a.github_url}
                  type="button"
                  onClick={() => {
                    setUrl(a.github_url);
                    onAnalyze(a.github_url);
                  }}
                  disabled={loading}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    padding: "0.35rem 0.65rem",
                    borderRadius: "999px",
                    border: "1px solid var(--ridge)",
                    background: "#fff",
                    cursor: loading ? "wait" : "pointer",
                    color: "var(--ink)",
                  }}
                >
                  {a.owner}/{a.repo}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
