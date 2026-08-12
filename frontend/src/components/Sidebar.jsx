import { useState } from "react";
import { useChat } from "../context/ChatContext.jsx";

export default function Sidebar({ onNavigate }) {
  const {
    conversations,
    activeId,
    selectConversation,
    newChat,
    deleteConversation,
    exportConversation,
  } = useChat();
  const [confirmDelete, setConfirmDelete] = useState(null);

  const formatDate = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  const handleNewChat = () => {
    newChat();
    onNavigate?.();
  };

  const handleSelect = (id) => {
    selectConversation(id);
    onNavigate?.();
  };

  return (
    <aside className="sidebar">
      <button className="new-chat-btn" onClick={handleNewChat}>
        + New chat
      </button>

      <div className="convo-list">
        {conversations.length === 0 && (
          <p className="empty-hint">No conversations yet</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`convo-item ${c.id === activeId ? "active" : ""}`}
            onClick={() => handleSelect(c.id)}
          >
            <div className="convo-main">
              <div className="convo-title">{c.title}</div>
              <div className="convo-meta">
                {formatDate(c.updated_at)}
                {c.id === activeId && (
                  <span className="convo-actions">
                    <button
                      title="Export conversation"
                      onClick={(e) => {
                        e.stopPropagation();
                        exportConversation(c.id);
                      }}
                    >
                      &#8615;
                    </button>
                    <button
                      title="Delete conversation"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirmDelete === c.id) {
                          deleteConversation(c.id);
                          setConfirmDelete(null);
                        } else {
                          setConfirmDelete(c.id);
                          setTimeout(() => setConfirmDelete(null), 3000);
                        }
                      }}
                    >
                      {confirmDelete === c.id ? "Sure?" : "\u2715"}
                    </button>
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
