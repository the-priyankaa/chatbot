import { useEffect, useState } from "react";
import client from "../api/client";

export default function KnowledgePanel({ onClose }) {
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const { data } = await client.get("/knowledge/documents");
      setDocuments(data);
    } catch {
      setDocuments([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setMsg(null);
    const form = new FormData();
    form.append("file", file);
    try {
      await client.post("/knowledge/ingest", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMsg({ type: "ok", text: `Ingested "${file.name}"` });
      await load();
    } catch (err) {
      setMsg({ type: "error", text: err.response?.data?.detail || "Upload failed" });
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  const remove = async (id) => {
    try {
      await client.delete(`/knowledge/documents/${id}`);
      await load();
    } catch {
      /* ignore */
    }
  };

  const search = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    try {
      const { data } = await client.post("/knowledge/search", {
        query: query.trim(),
        top_k: 5,
      });
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="knowledge-panel">
      <div className="kb-header">
        <h3>Knowledge base</h3>
        <button
          className="kb-close"
          onClick={onClose}
          aria-label="Close knowledge base"
        >
          &#215;
        </button>
      </div>
      <p className="kb-hint">
        Upload .txt / .md files. The chatbot retrieves relevant chunks when
        answering.
      </p>

      <label className="upload-btn">
        {busy ? "Processing..." : "Upload document"}
        <input type="file" accept=".txt,.md,.rst,.csv,.json,.html" onChange={upload} hidden />
      </label>

      {msg && <div className={`banner banner-${msg.type}`}>{msg.text}</div>}

      <div className="doc-list">
        {documents.length === 0 && <p className="empty-hint">No documents yet</p>}
        {documents.map((d) => (
          <div className="doc-item" key={d.id}>
            <div className="doc-name" title={d.filename}>
              {d.filename}
            </div>
            <div className="doc-meta">
              {d.chunk_count} chunks
              <button onClick={() => remove(d.id)}>remove</button>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={search} className="kb-search">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Test semantic search..."
        />
        <button type="submit" disabled={!query.trim()}>
          Search
        </button>
      </form>

      {results.length > 0 && (
        <div className="kb-results">
          {results.map((r, i) => (
            <div className="kb-result" key={i}>
              <div className="kb-result-score">
                {r.filename} · {r.score.toFixed(2)}
              </div>
              <p>{r.content}</p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
