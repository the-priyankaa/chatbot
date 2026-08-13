import { useRef, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useChat } from "../context/ChatContext.jsx";
import MessageBubble from "./MessageBubble.jsx";
import MessageInput from "./MessageInput.jsx";
import TypingIndicator from "./TypingIndicator.jsx";

const SUGGESTIONS = [
  "What can you help me with?",
  "Explain a concept in simple terms",
  "Help me write something",
  "What do my knowledge base documents cover?",
];

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ChatWindow({ onToggleSidebar }) {
  const { user, logout } = useAuth();
  const { messages, loading, streaming, error, activeId, setError, sendMessage } =
    useChat();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming]);

  const initial = (user?.username?.[0] || "U").toUpperCase();

  return (
    <main className="chat">
      <header className="chat-header">
        <div className="chat-header-left">
          <button
            className="sidebar-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle conversation list"
            title="Toggle sidebar"
          >
            <ChevronIcon />
          </button>
        </div>
        <div className="chat-title">
          {activeId ? "Conversation" : "New chat"}
        </div>
        <div className="user-menu">
          <span className="user-avatar">{initial}</span>
          <button className="link-btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      {error && (
        <div className="banner banner-error chat-banner">
          {error}
          <button className="link-btn" onClick={() => setError(null)}>
            dismiss
          </button>
        </div>
      )}

      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && !loading ? (
          <div className="welcome">
            <div className="welcome-brand">AI</div>
            <h1>How can I help you today?</h1>
            <p>Ask anything, or get answers grounded in your knowledge base.</p>
            <div className="suggestion-grid">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion-card"
                  onClick={() => sendMessage(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-inner">
            {messages.map((m, i) => (
              <MessageBubble
                key={m.id || `${m.role}-${i}`}
                message={m}
                isLast={i === messages.length - 1 && !streaming}
              />
            ))}
            {streaming && <TypingIndicator />}
          </div>
        )}
      </div>

      <MessageInput />
    </main>
  );
}
