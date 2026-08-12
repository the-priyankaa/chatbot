import { useEffect, useState } from "react";
import { useAuth } from "./context/AuthContext.jsx";
import { ChatProvider } from "./context/ChatContext.jsx";
import AuthForms from "./components/AuthForms.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import KnowledgePanel from "./components/KnowledgePanel.jsx";
import Sidebar from "./components/Sidebar.jsx";

function Shell() {
  const { user, loading } = useAuth();
  const [showKb, setShowKb] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("menu-open", sidebarOpen || showKb);
    return () => document.body.classList.remove("menu-open");
  }, [sidebarOpen, showKb]);

  if (loading) return <div className="boot">Loading...</div>;

  if (!user) return <AuthForms />;

  return (
    <ChatProvider>
      <div className={`layout ${sidebarOpen ? "sidebar-open" : ""}`}>
        {sidebarOpen && <div className="backdrop" onClick={() => setSidebarOpen(false)} />}
        <Sidebar
          onNavigate={() => setSidebarOpen(false)}
          onToggle={() => setSidebarOpen((v) => !v)}
        />
        <ChatWindow onToggleSidebar={() => setSidebarOpen((v) => !v)} />
        {showKb ? <KnowledgePanel onClose={() => setShowKb(false)} /> : null}
        <button
          className="kb-toggle"
          onClick={() => setShowKb((v) => !v)}
          title="Toggle knowledge base"
        >
          {showKb ? "Hide KB" : "KB"}
        </button>
      </div>
    </ChatProvider>
  );
}

export default function App() {
  return <Shell />;
}
