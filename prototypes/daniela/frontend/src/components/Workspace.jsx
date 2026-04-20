import { useCallback, useEffect, useMemo, useState } from "react";
import ArchitectureGraph from "./ArchitectureGraph.jsx";
import ChatPanel from "./ChatPanel.jsx";
import QuizPanel from "./QuizPanel.jsx";

const TYPE_COLORS = {
  entrypoint: "#1d4ed8",
  module: "#15803d",
  service: "#7c3aed",
  config: "#b45309",
  external: "#be123c",
  database: "#0369a1",
  test: "#4d7c0f",
};

function buildOnboardingGuide(analysis) {
  const nodes = analysis.nodes || [];
  const edges = analysis.edges || [];
  const findByType = (type) => nodes.find((n) => String(n.type || "").toLowerCase() === type);

  const entry = findByType("entrypoint") || nodes[0];
  const service = findByType("service") || findByType("module");
  const db = findByType("database") || findByType("external");

  const startHere = [];
  if (entry) startHere.push(`Open ${entry.label} first to see where execution starts.`);
  if (service && service !== entry) startHere.push(`Then read ${service.label} to understand the main behavior layer.`);
  if (db) startHere.push(`Finally inspect ${db.label} to understand persistence/integrations.`);

  const path = [entry?.label, service?.label, db?.label].filter(Boolean);
  const core = edges.slice(0, 3).map((e) => {
    const src = nodes.find((n) => n.id === e.source)?.label || e.source;
    const tgt = nodes.find((n) => n.id === e.target)?.label || e.target;
    return `${src} -> ${tgt} (${e.label || "relates"})`;
  });

  return {
    startHere: startHere.length ? startHere : ["Start with the summary and top-level nodes on the graph."],
    path: path.length ? path : nodes.slice(0, 3).map((n) => n.label),
    core: core.length ? core : ["No explicit edges were generated; inspect node descriptions for flow clues."],
  };
}

function timedPathSteps(path) {
  if (!path.length) return [];
  const n = path.length;
  let elapsed = 0;
  return path.map((p, i) => {
    // Evenly distribute across 10 minutes and ensure we end exactly at 10.
    const isLast = i === n - 1;
    const segment = isLast ? 10 - elapsed : Math.max(1, Math.round(10 / n));
    const start = elapsed;
    const end = isLast ? 10 : Math.min(10, elapsed + segment);
    elapsed = end;
    return {
      label: p,
      startMin: start,
      endMin: end,
      time: `${start}-${end} min`,
    };
  });
}

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
  const [activePanel, setActivePanel] = useState("guide");
  const [pathRunning, setPathRunning] = useState(false);
  const [pathStep, setPathStep] = useState(0);
  const [stepElapsedSec, setStepElapsedSec] = useState(0);

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
  const guide = buildOnboardingGuide(analysis);
  const timedPath = timedPathSteps(guide.path);
  const totalPathSteps = timedPath.length;
  const totalSec = 10 * 60;

  const currentStep = timedPath[pathStep];
  const currentStepSec = useMemo(() => {
    if (!currentStep) return 0;
    return Math.max(1, (currentStep.endMin - currentStep.startMin) * 60);
  }, [currentStep]);

  useEffect(() => {
    if (!pathRunning || !currentStepSec || !totalPathSteps) return undefined;

    const id = setInterval(() => {
      setStepElapsedSec((prev) => {
        const next = prev + 1;
        if (next < currentStepSec) return next;

        // Step completed: advance or stop at end.
        setPathStep((s) => {
          if (s >= totalPathSteps - 1) {
            setPathRunning(false);
            return s;
          }
          return s + 1;
        });
        return 0;
      });
    }, 1000);

    return () => clearInterval(id);
  }, [pathRunning, currentStepSec, totalPathSteps]);

  useEffect(() => {
    // Reset per-step elapsed when user manually changes step.
    setStepElapsedSec(0);
  }, [pathStep]);

  const completedSec = useMemo(() => {
    if (!timedPath.length) return 0;
    const previous = timedPath
      .slice(0, pathStep)
      .reduce((acc, step) => acc + (step.endMin - step.startMin) * 60, 0);
    return Math.min(totalSec, previous + stepElapsedSec);
  }, [timedPath, pathStep, stepElapsedSec, totalSec]);

  const progressPct = Math.round((completedSec / totalSec) * 100);
  const currentRemainingSec = Math.max(0, currentStepSec - stepElapsedSec);
  const remMin = String(Math.floor(currentRemainingSec / 60)).padStart(2, "0");
  const remSec = String(currentRemainingSec % 60).padStart(2, "0");

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
          display: "flex",
          flexDirection: "column",
          minHeight: 0,
          padding: "0.85rem clamp(1rem, 2vw, 1.25rem) 0.85rem",
          gap: "0.85rem",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", alignItems: "center" }}>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.72rem",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--pine)",
            }}
          >
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

        <div
          style={{
            width: "min(1120px, 100%)",
            display: "flex",
            flexDirection: "column",
            gap: "0.85rem",
            minHeight: 0,
            flex: 1,
          }}
        >
        <div
          style={{
            minHeight: 48,
            overflowY: "auto",
            paddingRight: "0.2rem",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.4rem",
              marginBottom: "0.7rem",
              justifyContent: "center",
            }}
          >
            {[
              ["guide", "Guide"],
              ["ask", "Ask AI"],
              ["quiz", "Quiz"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setActivePanel(id)}
                style={{
                  padding: "0.65rem 1.15rem",
                  borderRadius: "999px",
                  border: activePanel === id ? "1px solid var(--pine)" : "1px solid var(--ridge)",
                  background: activePanel === id ? "#ecfdf5" : "#fff",
                  color: activePanel === id ? "var(--pine)" : "var(--ink-soft)",
                  fontSize: "1rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {activePanel === "guide" && (
          <section
            style={{
              marginBottom: "0.75rem",
              border: "1px solid var(--ridge)",
              borderRadius: "12px",
              background: "rgba(255,252,247,0.94)",
              boxShadow: "var(--shadow)",
              padding: "0.9rem 1rem",
              maxWidth: "860px",
              marginInline: "auto",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "1.2rem",
                marginBottom: "0.2rem",
              }}
            >
              New-to-repo guide
            </div>
            <p style={{ margin: "0 0 0.8rem", fontSize: "0.95rem", color: "var(--ink-soft)" }}>
              Fast orientation for onboarding and group projects.
            </p>
            <div
              style={{
                display: "grid",
                gap: "0.55rem",
                gridTemplateColumns: "minmax(0, 1fr)",
              }}
            >
              <article
                style={{
                  border: "1px solid var(--ridge)",
                  borderRadius: "10px",
                  background: "#fff",
                  padding: "0.7rem 0.8rem",
                }}
              >
                <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", marginBottom: "0.35rem" }}>
                  1) Start here if you're new
                </div>
                <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.92rem", color: "var(--ink-soft)" }}>
                  {guide.startHere.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </article>
              <article
                style={{
                  border: "1px solid var(--ridge)",
                  borderRadius: "10px",
                  background: "#fff",
                  padding: "0.9rem 1rem",
                }}
              >
                <div style={{ fontFamily: "var(--font-display)", fontSize: "0.95rem", marginBottom: "0.35rem" }}>
                  2) Follow this path in ~10 minutes
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "0.5rem",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setPathRunning(true);
                      setPathStep(0);
                      setStepElapsedSec(0);
                    }}
                    style={{
                      padding: "0.35rem 0.7rem",
                      borderRadius: "999px",
                      border: "1px solid var(--pine)",
                      background: "#ecfdf5",
                      color: "var(--pine)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Start 10-minute path
                  </button>
                  <button
                    type="button"
                    onClick={() => setPathRunning((r) => !r)}
                    disabled={!totalPathSteps}
                    style={{
                      padding: "0.35rem 0.65rem",
                      borderRadius: "999px",
                      border: "1px solid var(--ridge)",
                      background: "#fff",
                      color: "var(--ink-soft)",
                      fontSize: "0.8rem",
                      cursor: !totalPathSteps ? "not-allowed" : "pointer",
                      opacity: !totalPathSteps ? 0.6 : 1,
                    }}
                  >
                    {pathRunning ? "Pause" : "Resume"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPathRunning(false);
                      setPathStep(0);
                      setStepElapsedSec(0);
                    }}
                    style={{
                      padding: "0.35rem 0.65rem",
                      borderRadius: "999px",
                      border: "1px solid var(--ridge)",
                      background: "#fff",
                      color: "var(--ink-soft)",
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    Reset
                  </button>
                  <span style={{ fontSize: "0.8rem", color: "var(--ink-soft)" }}>
                    {progressPct}% complete
                  </span>
                  <span style={{ fontSize: "0.8rem", color: "var(--ink-soft)" }}>
                    Step {Math.min(pathStep + 1, totalPathSteps)}/{Math.max(totalPathSteps, 1)} · {remMin}:{remSec} left
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: "9px",
                    borderRadius: "999px",
                    border: "1px solid var(--ridge)",
                    background: "#f5f5f4",
                    overflow: "hidden",
                    marginBottom: "0.55rem",
                  }}
                >
                  <div
                    style={{
                      width: `${progressPct}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, #16a34a, #22c55e)",
                      transition: "width 220ms ease",
                    }}
                  />
                </div>
                <ol style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.86rem", color: "var(--ink-soft)" }}>
                  {timedPath.map((step, idx) => (
                    <li
                      key={step.label}
                      style={{
                        fontWeight: idx === pathStep ? 700 : 400,
                        color: idx === pathStep ? "var(--ink)" : "var(--ink-soft)",
                      }}
                    >
                      <strong>{step.time}</strong>: {step.label}
                    </li>
                  ))}
                </ol>
              </article>
              <article
                style={{
                  border: "1px solid var(--ridge)",
                  borderRadius: "10px",
                  background: "#fff",
                  padding: "0.7rem 0.8rem",
                }}
              >
                <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", marginBottom: "0.35rem" }}>
                  3) Core flow of the application
                </div>
                <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.92rem", color: "var(--ink-soft)" }}>
                  {guide.core.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </article>
            </div>
          </section>
          )}

          {activePanel === "ask" && (
          <section
            style={{
              marginBottom: "0.75rem",
              border: "1px solid var(--ridge)",
              borderRadius: "12px",
              background: "rgba(255,252,247,0.94)",
              boxShadow: "var(--shadow)",
              padding: "0.8rem",
              maxWidth: "860px",
              marginInline: "auto",
            }}
          >
            <ChatPanel
              githubUrl={githubUrl}
              title="Ask AI about this repo"
              starterPrompts={[
                "What are the main modules in this repo?",
                "What depends on authentication?",
                "Where is the entry point?",
                "Explain this repo in 5 bullet points.",
              ]}
            />
          </section>
          )}

          {activePanel === "quiz" && <QuizPanel analysis={analysis} />}
          {selected && (
            <aside
              style={{
                marginTop: "0.75rem",
                padding: "0.85rem 1rem",
                borderRadius: "12px",
                border: "1px solid var(--ridge)",
                background: "#fff",
                fontSize: "0.86rem",
              }}
            >
              <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, marginBottom: "0.25rem" }}>
                Selected on graph: {selected.label}
              </div>
              <div
                style={{
                  fontSize: "0.68rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--pine)",
                  marginBottom: "0.35rem",
                }}
              >
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

        <div
          className="graph-dock"
          style={{
            borderTop: "1px solid var(--ridge)",
            paddingTop: "0.6rem",
            width: "100%",
          }}
        >
          <div
            style={{
              marginBottom: "0.45rem",
              display: "flex",
              flexWrap: "wrap",
              gap: "0.55rem 0.85rem",
              alignItems: "center",
              fontSize: "0.95rem",
              color: "var(--ink-soft)",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-display)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                fontSize: "1rem",
                fontWeight: 700,
              }}
            >
              Graph Key
            </span>
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <span key={type} style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem" }}>
                <span
                  style={{
                    width: "14px",
                    height: "14px",
                    borderRadius: "2px",
                    background: color,
                    border: "1px solid #0002",
                  }}
                />
                {type}
              </span>
            ))}
          </div>
          <div
            style={{
              width: "100%",
              aspectRatio: "16 / 6",
              minHeight: "180px",
            }}
          >
            <ArchitectureGraph
              nodes={nodes}
              edges={edges}
              onSelectNode={handleNode}
              allowPanZoom={false}
              minHeight={0}
            />
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
