import { useMemo, useState } from "react";

function sample(arr, n) {
  return [...arr].sort(() => Math.random() - 0.5).slice(0, n);
}

function buildQuestions(analysis) {
  const nodes = analysis.nodes || [];
  const edges = analysis.edges || [];
  if (!nodes.length) return [];

  const questions = [];
  const labels = nodes.map((n) => n.label);

  const byType = {};
  for (const n of nodes) {
    const t = String(n.type || "module").toLowerCase();
    byType[t] = byType[t] || [];
    byType[t].push(n);
  }

  const types = Object.keys(byType).filter((t) => byType[t].length > 0);
  if (types.length >= 2) {
    const targetType = types.sort((a, b) => byType[b].length - byType[a].length)[0];
    const correctNode = byType[targetType][0];
    const distractors = sample(nodes.filter((n) => n.id !== correctNode.id), 3).map((n) => n.label);
    questions.push({
      id: "q-type",
      question: `Which component is classified as a "${targetType}" node?`,
      options: sample([correctNode.label, ...distractors], 4),
      answer: correctNode.label,
      explanation: `${correctNode.label} was tagged as ${targetType} by the architecture analysis.`,
    });
  }

  if (edges.length > 0) {
    const e = edges[0];
    const src = nodes.find((n) => n.id === e.source)?.label || e.source;
    const tgt = nodes.find((n) => n.id === e.target)?.label || e.target;
    const wrongs = sample(nodes.filter((n) => n.label !== tgt), 3).map((n) => n.label);
    questions.push({
      id: "q-edge",
      question: `According to the graph, ${src} has a "${e.label}" relationship with which component?`,
      options: sample([tgt, ...wrongs], 4),
      answer: tgt,
      explanation: `The edge ${src} -> ${tgt} is labeled "${e.label}".`,
    });
  }

  if (analysis.tech_stack?.length) {
    const correct = analysis.tech_stack[0];
    const extras = ["Django", "Redis", "TensorFlow", "Kubernetes", "Laravel", "Spring Boot"];
    const wrong = sample(extras.filter((x) => x !== correct), 3);
    questions.push({
      id: "q-stack",
      question: "Which technology is identified in this repository's tech stack?",
      options: sample([correct, ...wrong], 4),
      answer: correct,
      explanation: `${correct} appears in the generated tech stack summary.`,
    });
  }

  const withFiles = nodes.find((n) => (n.files || []).length > 0);
  if (withFiles) {
    const correctFile = withFiles.files[0];
    const wrongFiles = sample(
      nodes
        .flatMap((n) => n.files || [])
        .filter((f) => f !== correctFile),
      3
    );
    questions.push({
      id: "q-file",
      question: `Which file is grouped under "${withFiles.label}"?`,
      options: sample([correctFile, ...wrongFiles], 4),
      answer: correctFile,
      explanation: `"${withFiles.label}" includes ${correctFile} in its mapped file list.`,
    });
  }

  if (labels.length >= 4) {
    const target = nodes.sort((a, b) => (b.files?.length || 0) - (a.files?.length || 0))[0];
    const count = target.files?.length || 0;
    const wrongLabels = sample(labels.filter((l) => l !== target.label), 3);
    questions.push({
      id: "q-size",
      question: `Which node appears to cover the broadest file group (${count} files)?`,
      options: sample([target.label, ...wrongLabels], 4),
      answer: target.label,
      explanation: `${target.label} has ${count} mapped files in this analysis.`,
    });
  }

  return questions.slice(0, 5);
}

export default function QuizPanel({ analysis }) {
  const questions = useMemo(() => buildQuestions(analysis), [analysis]);
  const [step, setStep] = useState(0);
  const [picked, setPicked] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const current = questions[step];
  const total = questions.length;
  const answered = Object.keys(picked).length;
  const score = questions.reduce((acc, q) => (picked[q.id] === q.answer ? acc + 1 : acc), 0);

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
        No quiz questions available for this analysis.
      </section>
    );
  }

  const reveal = submitted || picked[current.id] != null;
  const reviewItems = submitted
    ? questions.map((q) => ({
        ...q,
        chosen: picked[q.id] ?? "(no answer)",
        correct: picked[q.id] === q.answer,
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
      </div>

      <div style={{ padding: "1rem" }}>
        <h3 style={{ margin: "0 0 0.8rem", fontFamily: "var(--font-display)" }}>{current.question}</h3>

        <div style={{ display: "grid", gap: "0.5rem" }}>
          {current.options.map((opt) => {
            const isChosen = picked[current.id] === opt;
            const isCorrect = current.answer === opt;
            const showCorrect = reveal && isCorrect;
            const showWrongChosen = reveal && isChosen && !isCorrect;
            return (
              <button
                key={opt}
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
