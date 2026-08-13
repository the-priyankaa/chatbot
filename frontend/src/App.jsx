import { useEffect, useState } from "react";
import { useAuth } from "./context/AuthContext.jsx";
import { ChatProvider } from "./context/ChatContext.jsx";
import AuthForms from "./components/AuthForms.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import Sidebar from "./components/Sidebar.jsx";

function Shell() {
  const { user, loading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("menu-open", sidebarOpen);
    return () => document.body.classList.remove("menu-open");
  }, [sidebarOpen]);

  if (loading) return <div className="boot">Loading...</div>;

  if (!user) return <AuthForms />;

  const layoutClass = [
    "layout",
    sidebarOpen ? "sidebar-open" : "",
    sidebarCollapsed ? "sidebar-collapsed" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <ChatProvider>
      <div className={layoutClass}>
        {sidebarOpen && <div className="backdrop" onClick={() => setSidebarOpen(false)} />}
        <Sidebar
          onNavigate={() => setSidebarOpen(false)}
          onToggle={() => setSidebarOpen((v) => !v)}
        />
        <ChatWindow
          onToggleSidebar={() => {
            if (window.innerWidth <= 860) setSidebarOpen((v) => !v);
            else setSidebarCollapsed((v) => !v);
          }}
        />
      </div>
    </ChatProvider>
  );
}

export default function App() {
  return <Shell />;
}
