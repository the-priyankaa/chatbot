import { useState } from "react";
import client from "../api/client";
import logo from "../assets/logo.png";

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

export default function MessageBubble({ message, isLast }) {
  const isUser = message.role === "user";
  const [feedback, setFeedback] = useState(null);
  const [comment, setComment] = useState("");
  const [showComment, setShowComment] = useState(false);
  const [copied, setCopied] = useState(false);

  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  const copyText = async () => {
    const text = message.content || "";
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const submitFeedback = async (rating) => {
    setFeedback(rating);
    setShowComment(false);
    try {
      await client.post(`/feedback?message_id=${message.id}`, {
        rating,
        comment: comment.trim() || null,
      });
    } catch {
      /* ignore */
    }
  };

  return (
    <div className={`msg-row ${isUser ? "user" : "assistant"}`}>
      {!isUser && <img className="assistant-avatar" src={logo} alt="AI" />}
      <div className="msg-content">
        <div className="msg-text">{message.content}</div>
        <div className="msg-meta">
          {!isUser && message.content && (
            <button
              className={`copy-btn ${copied ? "copied" : ""}`}
              onClick={copyText}
              title={copied ? "Copied!" : "Copy response"}
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
              <span>{copied ? "Copied!" : ""}</span>
            </button>
          )}
          {!isUser && message.id && (
            <span className="feedback">
              {feedback === null ? (
                <>
                  <button title="Good response" onClick={() => submitFeedback(2)}>
                    &#128077;
                  </button>
                  <button title="Bad response" onClick={() => submitFeedback(1)}>
                    &#128078;
                  </button>
                </>
              ) : (
                <span className="feedback-saved">
                  {feedback === 2 ? "Thanks!" : "Noted"}
                </span>
              )}
              {feedback === 1 && !showComment && (
                <button
                  className="link-btn"
                  onClick={() => setShowComment(true)}
                >
                  add comment
                </button>
              )}
              {showComment && (
                <span className="feedback-comment">
                  <input
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="What went wrong?"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        submitFeedback(1);
                      }
                    }}
                  />
                </span>
              )}
            </span>
          )}
          <span className="time">{time}</span>
        </div>
      </div>
    </div>
  );
}
