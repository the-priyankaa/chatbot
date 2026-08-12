import { createContext, useCallback, useContext, useEffect, useState } from "react";
import client from "../api/client";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(false);

  const loadConversations = useCallback(async () => {
    try {
      const { data } = await client.get("/chat/conversations");
      setConversations(data);
    } catch {
      setConversations([]);
    }
  }, []);

  const loadMessages = useCallback(async (id) => {
    try {
      const { data } = await client.get(`/chat/conversations/${id}/messages`);
      setMessages(data);
    } catch {
      setMessages([]);
    }
  }, []);

  const selectConversation = useCallback(
    async (id) => {
      setActiveId(id);
      setError(null);
      await loadMessages(id);
    },
    [loadMessages]
  );

  const sendMessage = useCallback(
    async (text, title) => {
      setError(null);
      setLoading(true);
      setStreaming(true);

      const userMsg = { role: "user", content: text, created_at: new Date().toISOString() };
      setMessages((prev) => [...prev, userMsg]);

      const assistantMsg = { role: "assistant", content: "", created_at: new Date().toISOString() };
      setMessages((prev) => [...prev, assistantMsg]);

      try {
        const resp = await fetch("/api/chat/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
          body: JSON.stringify({
            message: text,
            conversation_id: activeId || null,
            title: title || null,
          }),
        });

        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let convId = activeId;
        let full = "";

        const updateAssistant = (delta) => {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + delta,
            };
            return next;
          });
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop();
          for (const part of parts) {
            const lines = part.split("\n");
            const event = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
            const dataLine = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
            if (!dataLine) continue;

            if (event === "start") {
              const parsed = JSON.parse(dataLine);
              convId = parsed.conversation_id;
              setActiveId(parsed.conversation_id);
            } else if (event === "token") {
              const parsed = JSON.parse(dataLine);
              full += parsed.text;
              updateAssistant(parsed.text);
            } else if (event === "error") {
              const parsed = JSON.parse(dataLine);
              updateAssistant(parsed.text || dataLine);
              setError(parsed.text || "Request failed");
            }
          }
        }
        if (convId) setActiveId(convId);
        await loadConversations();
      } catch (err) {
        setError(err.message || "Network error while contacting the AI service.");
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1].content += "\n[Error: failed to reach the AI service]";
          return next;
        });
      } finally {
        setLoading(false);
        setStreaming(false);
      }
    },
    [activeId, loadConversations]
  );

  const newChat = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }, []);

  const deleteConversation = useCallback(
    async (id) => {
      await client.delete(`/chat/conversations/${id}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) newChat();
    },
    [activeId, newChat]
  );

  const exportConversation = useCallback(async (id) => {
    const { data } = await client.get(`/chat/conversations/${id}/export`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.title.replace(/[^a-z0-9]+/gi, "_") || "conversation"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeId,
        messages,
        loading,
        error,
        streaming,
        setError,
        selectConversation,
        sendMessage,
        newChat,
        deleteConversation,
        exportConversation,
        loadConversations,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  return useContext(ChatContext);
}
