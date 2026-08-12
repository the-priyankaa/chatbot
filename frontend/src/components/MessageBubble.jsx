import { useState } from "react";
import client from "../api/client";

export default function MessageBubble({ message, isLast }) {
  const isUser = message.role === "user";
  const [feedback, setFeedback] = useState(null);
  const [comment, setComment] = useState("");
  const [showComment, setShowComment] = useState(false);

  const time = message.created_at
    ? new Date(message.created_at).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

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
    <div className={`bubble-row ${isUser ? "user" : "assistant"}`}>
      <div className="bubble">
        <div className="bubble-content">{message.content}</div>
        <div className="bubble-meta">
          <span className="time">{time}</span>
          {!isUser && message.id && isLast && (
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
        </div>
      </div>
    </div>
  );
}
