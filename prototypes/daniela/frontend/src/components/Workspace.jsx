import { useCallback, useState } from "react";
import ArchitectureGraph from "./ArchitectureGraph.jsx";
import ChatPanel from "./ChatPanel.jsx";

export default function Workspace({
  githubUrl,
  analysis,
  onBack,
  onReanalyze,
  analyzeError,
  onDismissError,
}) {
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);

  const handleNode = useCallback((data) => {
    setSelected(data);
  }, []);

  async function reanalyze() {
    setBusy(true);
    try {
      await onReanalyze();
    } finally {
      setBusy(false);
    }
  }

  const nodes = analysis.nodes || [];
  const edges = analysis.edges || [];

  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        flexDirection: "column",
        background: "var(--paper)",
      }}
    >
      {analyzeError && (
        <div
          role="alert"
          style={{
            padding: "0.55rem 1rem",
            background: "#fef2f2",
            borderBottom: "1px solid #fecaca",
            color: "#991b1b",
            fontSize: "0.88rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <span>{analyzeError}</span>
          {onDismissError && (
            <button
              type="button"
              onClick={onDismissError}
              style={{
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontWeight: 600,
                color: "#991b1b",
              }}
            >
              Dismiss
            </button>
          )}
        </div>
      )}
      <header
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.65rem",
          padding: "0.85rem clamp(1rem, 3vw, 1.5rem)",
          borderBottom: "1px solid var(--ridge)",
          background: "rgba(255, 252, 247, 0.95)",
        }}
      >
        <div style={{ flex: "1 1 200px", minWidth: 0 }}>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "1.15rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              flexWrap: "wrap",
            }}
          >
            GitMap
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", fontWeight: 500, color: "var(--ink-soft)" }}>
              {analysis.repo}
            </span>
            {analysis.cached && (
              <span
                style={{
                  fontSize: "0.65rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  padding: "0.2rem 0.45rem",
                  borderRadius: "999px",
                  border: "1px solid var(--ridge)",
                  color: "var(--ink-soft)",
                }}
              >
                Cached
              </span>
            )}
          </div>
          <p style={{ margin: "0.35rem 0 0", fontSize: "0.88rem", color: "var(--ink-soft)", maxWidth: "72ch" }}>
            {analysis.summary}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.45rem", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              padding: "0.45rem 0.85rem",
              borderRadius: "10px",
              border: "1px solid var(--ridge)",
              background: "#fff",
              fontFamily: "var(--font-display)",
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            ← Back
          </button>
          <button
            type="button"
            onClick={reanalyze}
            disabled={busy}
            style={{
              padding: "0.45rem 0.85rem",
              borderRadius: "10px",
              border: "1px solid rgba(194, 65, 12, 0.45)",
              background: "var(--ember-glow)",
              fontFamily: "var(--font-display)",
              fontSize: "0.85rem",
              cursor: busy ? "wait" : "pointer",
              color: "var(--ember)",
            }}
          >
            {busy ? "Re-analyzing…" : "Re-analyze"}
          </button>
        </div>
      </header>

      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(300px, 380px)",
          gap: "0.85rem",
          padding: "0.85rem clamp(1rem, 2vw, 1.25rem) 1rem",
          minHeight: 0,
        }}
        className="workspace-grid"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem", minHeight: 0 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", alignItems: "center" }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--pine)" }}>
              Tech stack
            </span>
            {(analysis.tech_stack || []).map((t) => (
              <span
                key={t}
                style={{
                  fontSize: "0.72rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "999px",
                  border: "1px solid var(--ridge)",
                  background: "#fff",
                  color: "var(--ink-soft)",
                }}
              >
                {t}
              </span>
            ))}
          </div>
          <div style={{ flex: 1, minHeight: "360px" }}>
            <ArchitectureGraph nodes={nodes} edges={edges} onSelectNode={handleNode} />
          </div>
          {selected && (
            <aside
              style={{
                padding: "0.85rem 1rem",
                borderRadius: "12px",
                border: "1px solid var(--ridge)",
                background: "#fff",
                fontSize: "0.86rem",
              }}
            >
              <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, marginBottom: "0.25rem" }}>
                {selected.label}
              </div>
              <div style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--pine)", marginBottom: "0.35rem" }}>
                {selected.type}
              </div>
              <p style={{ margin: "0 0 0.5rem", color: "var(--ink-soft)" }}>{selected.description}</p>
              {(selected.files || []).length > 0 && (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--ink-soft)" }}>
                  {(selected.files || []).map((f) => (
                    <div key={f}>· {f}</div>
                  ))}
                </div>
              )}
            </aside>
          )}
        </div>
        <div style={{ minHeight: "420px", height: "100%" }}>
          <ChatPanel githubUrl={githubUrl} />
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .workspace-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
