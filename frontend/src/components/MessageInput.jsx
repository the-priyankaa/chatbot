import { useEffect, useRef, useState } from "react";
import { useChat } from "../context/ChatContext.jsx";

export default function MessageInput() {
  const { sendMessage, loading } = useChat();
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

  return (
    <form className="input-bar" onSubmit={submit}>
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a message..."
        rows={1}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit(e);
          }
        }}
      />
      <button type="submit" disabled={loading || !text.trim()}>
        Send
      </button>
    </form>
  );
}
