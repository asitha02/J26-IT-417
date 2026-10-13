import { useEffect, useState } from "react";
import { api } from "../api";

export default function KnowledgeBase() {
  const [type, setType] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError("");
    api(`/kb?limit=200${type ? "&type=" + encodeURIComponent(type) : ""}`)
      .then((r) => !cancelled && setData(r))
      .catch((e) => !cancelled && setError(e.message));
    return () => { cancelled = true; };
  }, [type, nonce]);

  return (
    <>
      <h2>Unified knowledge base</h2>
      <div className="row">
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          {["concept", "definition", "fact", "entity", "relationship"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <button onClick={() => setNonce((n) => n + 1)}>Refresh</button>
        {data && <span className="hint">{data.count} item(s)</span>}
      </div>
      {error && <div className="error">{error}</div>}
      {data && data.items.length === 0 && <p className="hint">No items yet. Upload data and run fusion first.</p>}
      {data && data.items.map((it) => (
        <div className="kb-item" key={it.kb_id}>
          <div className="kb-top">
            <span className="badge">{it.type}</span>
            <span className="kb-id">{it.kb_id}</span>
            {it.merged_from > 1 && <span className="badge merged">merged from {it.merged_from}</span>}
          </div>
          <div>{it.text}</div>
          {it.variants?.length > 0 && (
            <details>
              <summary>{it.variants.length} other wording(s)</summary>
              {it.variants.map((v, i) => <div key={i}>• {v}</div>)}
            </details>
          )}
          <div className="chips">
            {it.sources.map((s, i) => <span className="chip" key={i}>{s.video_id} @ {s.timestamp}</span>)}
          </div>
        </div>
      ))}
    </>
  );
}