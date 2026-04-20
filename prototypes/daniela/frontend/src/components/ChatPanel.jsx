import { useRef, useState } from "react";
import { sendChat } from "../api.js";

const DEFAULT_PROMPTS = [
  "What are the main modules in this repo?",
  "What depends on authentication?",
  "Where is the entry point?",
  "Explain this repo in 5 bullet points.",
];

export default function ChatPanel({
  githubUrl,
  title = "Ask the map",
  starterPrompts = DEFAULT_PROMPTS,
}) {
  const [messages, setMessages] = useState(() => [
    {
      role: "assistant",
      text:
        "Ask how modules connect, where configuration lives, or what an area of the graph is responsible for. Answers use the architecture snapshot we just built for this repo.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  async function send(explicitText) {
    const text = (explicitText ?? input).trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const { answer } = await sendChat(githubUrl, text);
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Could not get an answer: ${e.message}` },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
        background: "rgba(255, 252, 247, 0.97)",
        border: "1px solid var(--ridge)",
        borderRadius: "12px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "0.65rem 0.85rem",
          borderBottom: "1px solid var(--ridge)",
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: "0.95rem",
          background: "linear-gradient(90deg, var(--pine-muted), transparent)",
        }}
      >
        {title}
      </div>
      {!!starterPrompts?.length && (
        <div
          style={{
            padding: "0.5rem 0.65rem",
            borderBottom: "1px solid var(--ridge)",
            display: "flex",
            flexWrap: "wrap",
            gap: "0.35rem",
            background: "rgba(255,255,255,0.5)",
          }}
        >
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={sending}
              onClick={() => send(prompt)}
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.75rem",
                padding: "0.28rem 0.5rem",
                borderRadius: "999px",
                border: "1px solid var(--ridge)",
                background: "#fff",
                color: "var(--ink-soft)",
                cursor: sending ? "wait" : "pointer",
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "0.85rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.65rem",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "94%",
              padding: "0.55rem 0.75rem",
              borderRadius: "10px",
              fontSize: "0.86rem",
              lineHeight: 1.45,
              background:
                msg.role === "user" ? "var(--pine)" : "var(--paper-2)",
              color: msg.role === "user" ? "#f0fdf4" : "var(--ink)",
              border:
                msg.role === "user" ? "none" : "1px solid rgba(201, 191, 176, 0.8)",
            }}
          >
            {msg.text}
          </div>
        ))}
        {sending && (
          <div style={{ fontSize: "0.8rem", color: "var(--ink-soft)", fontStyle: "italic" }}>
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div
        style={{
          padding: "0.65rem",
          borderTop: "1px solid var(--ridge)",
          display: "flex",
          gap: "0.45rem",
          alignItems: "flex-end",
          background: "rgba(255,255,255,0.65)",
        }}
      >
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="e.g. Where does the API layer talk to the database?"
          disabled={sending}
          style={{
            flex: 1,
            resize: "none",
            padding: "0.55rem 0.65rem",
            borderRadius: "10px",
            border: "1px solid var(--ridge)",
            fontSize: "0.8rem",
            outline: "none",
          }}
        />
        <button
          type="button"
          onClick={send}
          disabled={sending || !input.trim()}
          style={{
            padding: "0.55rem 0.9rem",
            borderRadius: "10px",
            border: "none",
            fontFamily: "var(--font-display)",
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: sending ? "wait" : "pointer",
            background: "var(--pine)",
            color: "#f0fdf4",
            opacity: sending || !input.trim() ? 0.55 : 1,
            alignSelf: "stretch",
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
