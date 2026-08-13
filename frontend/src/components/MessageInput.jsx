import { useEffect, useRef, useState } from "react";
import { useChat } from "../context/ChatContext.jsx";

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function PaperclipIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="7" y="7" width="10" height="10" rx="2" />
    </svg>
  );
}

export default function MessageInput() {
  const { sendMessage, loading, stopStreaming } = useChat();
  const [text, setText] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    if (!loading) ref.current?.focus();
  }, [loading]);

  const submit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    sendMessage(trimmed);
    setText("");
  };

  const hasText = text.trim().length > 0;

  return (
    <div className="input-wrap">
      <form className="input-bar" onSubmit={submit}>
        <button type="button" className="input-side-btn" title="Attach file">
          <PlusIcon />
        </button>
        <textarea
          ref={ref}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Message AI Chatbot"
          rows={1}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(e);
            }
          }}
        />
        {loading ? (
          <button
            type="button"
            className="send-btn"
            title="Stop generating"
            onClick={stopStreaming}
          >
            <StopIcon />
          </button>
        ) : (
          <button
            type="submit"
            className="send-btn"
            disabled={!hasText}
            title="Send message"
          >
            <SendIcon />
          </button>
        )}
      </form>
      <p className="input-disclaimer">
        AI Chatbot can make mistakes. Consider checking important information.
      </p>
    </div>
  );
}
