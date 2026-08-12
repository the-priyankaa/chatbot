import { useRef } from "react";
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { useChat } from "../context/ChatContext.jsx";
import MessageBubble from "./MessageBubble.jsx";
import MessageInput from "./MessageInput.jsx";
import TypingIndicator from "./TypingIndicator.jsx";

export default function ChatWindow({ onToggleSidebar }) {
  const { user, logout } = useAuth();
  const { messages, loading, streaming, error, activeId, setError } = useChat();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming]);

  return (
    <main className="chat">
      <header className="chat-header">
        <div className="chat-header-left">
          <button
            className="sidebar-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle conversation list"
          >
            &#9776;
          </button>
          <div className="chat-title">
            {activeId ? "Conversation" : "New chat"}
          </div>
        </div>
        <div className="user-menu">
          <span className="user-name">{user?.username}</span>
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
        {messages.length === 0 && !loading && (
          <div className="welcome">
            <h2>Welcome{user ? `, ${user.username}` : ""}!</h2>
            <p>
              Ask me anything. Upload documents in the knowledge base to get
              answers grounded in your own content.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={m.id || `${m.role}-${i}`}
            message={m}
            isLast={i === messages.length - 1 && !streaming}
          />
        ))}
        {streaming && <TypingIndicator />}
      </div>

      <MessageInput />
    </main>
  );
}
