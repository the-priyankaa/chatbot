import { useState } from "react";
import { useChat } from "../context/ChatContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import KnowledgePanel from "./KnowledgePanel.jsx";

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4l1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Sidebar({ onNavigate }) {
  const {
    conversations,
    activeId,
    selectConversation,
    newChat,
    deleteConversation,
    exportConversation,
  } = useChat();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [kbOpen, setKbOpen] = useState(false);

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

  const initial = (user?.username?.[0] || "U").toUpperCase();

  return (
    <aside className="sidebar">
      <button className="new-chat-btn" onClick={handleNewChat}>
        <PlusIcon /> New chat
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
        ))}
      </div>

      <div className={`kb-section ${kbOpen ? "open" : ""}`}>
        <button className="kb-section-toggle" onClick={() => setKbOpen((v) => !v)}>
          <span>Knowledge base</span>
          <span className="chevron">&#9654;</span>
        </button>
        {kbOpen && (
          <div className="kb-section-body">
            <KnowledgePanel />
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <div className="user-avatar">{initial}</div>
        <div className="sidebar-user">
          <div className="sidebar-username">{user?.username}</div>
        </div>
        <div className="sidebar-actions">
          <button className="icon-btn" onClick={toggleTheme} title="Toggle theme">
            {theme === "light" ? <MoonIcon /> : <SunIcon />}
          </button>
          <button className="icon-btn" onClick={logout} title="Sign out">
            <LogoutIcon />
          </button>
        </div>
      </div>
    </aside>
  );
}
