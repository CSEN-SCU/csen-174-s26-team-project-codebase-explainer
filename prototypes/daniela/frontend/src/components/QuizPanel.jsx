import { useMemo, useState } from "react";

function sample(arr, n) {
  return [...arr].sort(() => Math.random() - 0.5).slice(0, n);
}

/** Trim + collapse spaces + lowercase — labels and tech names. */
function normLabel(s) {
  return String(s ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

/**
 * Scoring runs in the browser only. Quiz uses node/edge labels from the graph JSON.
 */
function isAnswerCorrect(q, chosen) {
  if (chosen == null || chosen === "") return false;
  return normLabel(chosen) === normLabel(q.answer);
}

/** Up to 4 unique labels + correct, shuffled. Returns null if not enough distractors. */
function buildMcqOptions(correct, pool) {
  const out = [];
  const seen = new Set();
  for (const raw of [correct, ...pool]) {
    const s = String(raw);
    const k = normLabel(s);
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(s);
    if (out.length >= 8) break;
  }
  const opts = sample(out, Math.min(4, out.length));
  return opts.length >= 2 ? opts : null;
}

/**
 * Only `nodes` and `edges` (no tech stack, no per-node file lists). Each question is built so
 * exactly one option matches the graph fact described.
 */
function buildQuestions(analysis) {
  const nodes = analysis.nodes || [];
  const edges = analysis.edges || [];
  if (nodes.length < 2) return [];
  if (!edges.length) return [];

  const idTo = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const lab = (id) => idTo[id]?.label || String(id);

  const goodEdges = edges.filter(
    (e) => e && e.source !== e.target && idTo[e.source] && idTo[e.target]
  );
  if (!goodEdges.length) return [];

  const pool = [];

  for (const n of nodes) {
    const outE = edges.filter((e) => e && e.source === n.id && e.target !== e.source);
    if (outE.length !== 1) continue;
    const e = outE[0];
    const tgt = lab(e.target);
    const srcL = lab(n.id);
    const distr = sample(
      nodes.filter((x) => normLabel(x.label) !== normLabel(tgt)).map((x) => x.label),
      14
    );
    const options = buildMcqOptions(tgt, distr);
    if (!options) continue;
    pool.push({
      id: `g-out1-${n.id}`,
      question: `In this graph, "${srcL}" has exactly one outgoing edge. Which node does it point to?`,
      options,
      answer: tgt,
      explanation: `The only edge from ${srcL} goes to ${tgt} (“${e.label || "link"}”).`,
    });
  }

  for (const n of nodes) {
    const inE = edges.filter((e) => e && e.target === n.id && e.source !== e.target);
    if (inE.length !== 1) continue;
    const e = inE[0];
    const src = lab(e.source);
    const tgtL = lab(n.id);
    const distr = sample(
      nodes.filter((x) => normLabel(x.label) !== normLabel(src)).map((x) => x.label),
      14
    );
    const options = buildMcqOptions(src, distr);
    if (!options) continue;
    pool.push({
      id: `g-in1-${n.id}`,
      question: `In this graph, exactly one node links into "${tgtL}". Which node is that?`,
      options,
      answer: src,
      explanation: `Only ${src} → ${tgtL} (“${e.label || "link"}”).`,
    });
  }

  const outCounts = nodes.map((n) => ({
    n,
    c: edges.filter((e) => e && e.source === n.id).length,
  }));
  const maxOut = Math.max(...outCounts.map((x) => x.c), 0);
  if (maxOut > 0) {
    const leaders = outCounts.filter((x) => x.c === maxOut).map((x) => x.n);
    if (leaders.length === 1) {
      const w = leaders[0];
      const distr = sample(
        nodes.filter((x) => normLabel(x.label) !== normLabel(w.label)).map((x) => x.label),
        14
      );
      const options = buildMcqOptions(w.label, distr);
      if (options) {
        pool.push({
          id: `g-outdeg-${w.id}`,
          question: `Which node has the most outgoing edges (${maxOut}) in this graph?`,
          options,
          answer: w.label,
          explanation: `${w.label} is the only node with the highest out-degree (${maxOut}).`,
        });
      }
    }
  }

  const typeGroups = {};
  for (const n of nodes) {
    const t = String(n.type || "module").toLowerCase();
    typeGroups[t] = typeGroups[t] || [];
    typeGroups[t].push(n);
  }
  for (const [t, arr] of Object.entries(typeGroups)) {
    if (arr.length !== 1) continue;
    const sole = arr[0];
    const distr = sample(
      nodes.filter((x) => normLabel(x.label) !== normLabel(sole.label)).map((x) => x.label),
      14
    );
    const options = buildMcqOptions(sole.label, distr);
    if (!options) continue;
    pool.push({
      id: `g-type1-${sole.id}`,
      question: `Only one node has type “${t}” in this graph. Which label is it?`,
      options,
      answer: sole.label,
      explanation: `${sole.label} is the only node tagged “${t}”.`,
    });
  }

  const edgeSample = sample(goodEdges, Math.min(4, goodEdges.length));
  for (let ei = 0; ei < edgeSample.length; ei++) {
    const e = edgeSample[ei];
    const srcL = lab(e.source);
    const tgtL = lab(e.target);
    const distr = sample(
      nodes.filter((x) => normLabel(x.label) !== normLabel(tgtL)).map((x) => x.label),
      14
    );
    const options = buildMcqOptions(tgtL, distr);
    if (!options) continue;
    pool.push({
      id: `g-edge-${e.source}-${e.target}-${ei}`,
      question: `In the graph, “${srcL}” has an edge labeled “${e.label || "link"}” into which node?`,
      options,
      answer: tgtL,
      explanation: `Edge: ${srcL} —[${e.label || "link"}]→ ${tgtL}.`,
    });
  }

  const seen = new Set();
  const uniq = [];
  for (const q of pool) {
    if (seen.has(q.id)) continue;
    seen.add(q.id);
    uniq.push(q);
  }
  return sample(uniq, Math.min(5, uniq.length));
}

export default function QuizPanel({ analysis }) {
  const questions = useMemo(() => buildQuestions(analysis), [analysis]);
  const [step, setStep] = useState(0);
  const [picked, setPicked] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const current = questions[step];
  const total = questions.length;
  const answered = Object.keys(picked).length;
  const score = questions.reduce(
    (acc, q) => acc + (isAnswerCorrect(q, picked[q.id]) ? 1 : 0),
    0
  );

  if (!questions.length) {
    return (
      <section
        style={{
          padding: "1rem",
          border: "1px solid var(--ridge)",
          borderRadius: "12px",
          background: "rgba(255,252,247,0.94)",
        }}
      >
        This graph is too small for the quiz (need at least two nodes and one edge), or none of
        the graph-only question patterns matched. Try re-analyzing a larger repo.
      </section>
    );
  }

  const reveal = submitted || picked[current.id] != null;
  const reviewItems = submitted
    ? questions.map((q) => ({
        ...q,
        chosen: picked[q.id] ?? "(no answer)",
        correct: isAnswerCorrect(q, picked[q.id]),
      }))
    : [];

  return (
    <section
      style={{
        border: "1px solid var(--ridge)",
        borderRadius: "12px",
        background: "rgba(255,252,247,0.94)",
        boxShadow: "var(--shadow)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "0.8rem 1rem",
          borderBottom: "1px solid var(--ridge)",
          background: "linear-gradient(90deg, var(--pine-muted), transparent)",
        }}
      >
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1rem" }}>
          Codebase Quiz
        </div>
        <div style={{ fontSize: "0.82rem", color: "var(--ink-soft)" }}>
          Question {step + 1} / {total} · Answered {answered} · Score {score}
        </div>
        <div style={{ fontSize: "0.74rem", color: "var(--ink-soft)", marginTop: "0.35rem" }}>
          Each question uses only the graph (nodes + edges). Exactly one choice is correct;
          grading is automatic in the browser (not the chat AI).
        </div>
      </div>

      <div style={{ padding: "1rem" }}>
        <h3 style={{ margin: "0 0 0.8rem", fontFamily: "var(--font-display)" }}>{current.question}</h3>

        <div style={{ display: "grid", gap: "0.5rem" }}>
          {current.options.map((opt, i) => {
            const isChosen = picked[current.id] === opt;
            const isCorrectOption = isAnswerCorrect(current, opt);
            const showCorrect = reveal && isCorrectOption;
            const showWrongChosen =
              reveal && isChosen && !isAnswerCorrect(current, picked[current.id]);
            return (
              <button
                key={`${current.id}-${i}`}
                type="button"
                onClick={() => setPicked((prev) => ({ ...prev, [current.id]: opt }))}
                disabled={submitted}
                style={{
                  textAlign: "left",
                  padding: "0.65rem 0.75rem",
                  borderRadius: "10px",
                  border: showCorrect
                    ? "1px solid #16a34a"
                    : showWrongChosen
                    ? "1px solid #dc2626"
                    : isChosen
                    ? "1px solid var(--pine)"
                    : "1px solid var(--ridge)",
                  background: showCorrect
                    ? "#f0fdf4"
                    : showWrongChosen
                    ? "#fef2f2"
                    : isChosen
                    ? "#ecfdf5"
                    : "#fff",
                  cursor: submitted ? "default" : "pointer",
                  fontSize: "0.86rem",
                }}
              >
                {opt}
              </button>
            );
          })}
        </div>

        {reveal && (
          <p style={{ margin: "0.75rem 0 0", fontSize: "0.82rem", color: "var(--ink-soft)" }}>
            {current.explanation}
          </p>
        )}

        <div style={{ marginTop: "0.9rem", display: "flex", gap: "0.45rem", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            style={{
              padding: "0.45rem 0.8rem",
              borderRadius: "10px",
              border: "1px solid var(--ridge)",
              background: "#fff",
              cursor: step === 0 ? "not-allowed" : "pointer",
              opacity: step === 0 ? 0.6 : 1,
            }}
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setStep((s) => Math.min(total - 1, s + 1))}
            disabled={step === total - 1}
            style={{
              padding: "0.45rem 0.8rem",
              borderRadius: "10px",
              border: "1px solid var(--ridge)",
              background: "#fff",
              cursor: step === total - 1 ? "not-allowed" : "pointer",
              opacity: step === total - 1 ? 0.6 : 1,
            }}
          >
            Next
          </button>
          <button
            type="button"
            onClick={() => setSubmitted(true)}
            disabled={submitted || answered < total}
            style={{
              marginLeft: "auto",
              padding: "0.45rem 0.8rem",
              borderRadius: "10px",
              border: "1px solid rgba(20,83,45,0.45)",
              background: "var(--pine)",
              color: "#f0fdf4",
              cursor: submitted || answered < total ? "not-allowed" : "pointer",
              opacity: submitted || answered < total ? 0.6 : 1,
            }}
          >
            Submit quiz
          </button>
          <button
            type="button"
            onClick={() => {
              setPicked({});
              setSubmitted(false);
              setStep(0);
            }}
            style={{
              padding: "0.45rem 0.8rem",
              borderRadius: "10px",
              border: "1px solid rgba(194,65,12,0.45)",
              background: "var(--ember-glow)",
              color: "var(--ember)",
              cursor: "pointer",
            }}
          >
            Reset
          </button>
        </div>

        {submitted && (
          <div
            style={{
              marginTop: "0.8rem",
              padding: "0.65rem",
              borderRadius: "10px",
              border: "1px solid var(--ridge)",
              background: "#fff",
              fontSize: "0.85rem",
            }}
          >
            Final score: <strong>{score}/{total}</strong>
          </div>
        )}

        {submitted && (
          <div
            style={{
              marginTop: "0.75rem",
              border: "1px solid var(--ridge)",
              borderRadius: "10px",
              background: "#fff",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "0.6rem 0.75rem",
                borderBottom: "1px solid var(--ridge)",
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "0.9rem",
              }}
            >
              Review section
            </div>
            <div style={{ maxHeight: "240px", overflowY: "auto", padding: "0.55rem 0.7rem" }}>
              {reviewItems.map((item, i) => (
                <article
                  key={item.id}
                  style={{
                    border: "1px solid var(--ridge)",
                    borderRadius: "8px",
                    padding: "0.5rem 0.6rem",
                    marginBottom: "0.45rem",
                    background: item.correct ? "#f0fdf4" : "#fef2f2",
                  }}
                >
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, marginBottom: "0.2rem" }}>
                    Q{i + 1}: {item.correct ? "Correct" : "Needs review"}
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "var(--ink-soft)" }}>{item.question}</div>
                  <div style={{ marginTop: "0.2rem", fontSize: "0.75rem" }}>
                    Your answer: <strong>{item.chosen}</strong>
                  </div>
                  {!item.correct && (
                    <div style={{ fontSize: "0.75rem" }}>
                      Correct answer: <strong>{item.answer}</strong>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
