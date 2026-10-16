import { useState } from "react";
import { api, postJSON } from "../api";

export default function IngestFuse() {
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState({ msg: "", error: false });
  const [uploading, setUploading] = useState(false);
  const [fusing, setFusing] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  async function doUpload() {
    if (!file) return setUpload({ msg: "Choose a JSON file first.", error: true });
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api("/ingest/file", { method: "POST", body: form });
      setUpload({ msg: `Ingested ${r.videos.length} video(s): ${r.videos.join(", ")}, ${r.items} items.`, error: false });
    } catch (e) {
      setUpload({ msg: e.message, error: true });
    } finally { setUploading(false); }
  }

  async function doFuse() {
    setFusing(true); setError(""); setStats(null);
    try { setStats(await postJSON("/fusion/run", {})); }
    catch (e) { setError(e.message); }
    finally { setFusing(false); }
  }

  return (
    <div className="fusion-workflow">
      <section className="workflow-card">
        <p className="card-eyebrow">01 / Source material</p>
        <h2>Upload Component 1 output</h2>
        <p className="hint">Choose the JSON file produced by Component 1 (one or more videos).</p>
        <div className="row">
          <input
            type="file"
            accept=".json,application/json"
            aria-label="Choose Component 1 JSON file"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <button className="primary-button" onClick={doUpload} disabled={uploading}>
            {uploading ? "Uploading…" : "Upload file"}
          </button>
        </div>
        {upload.msg && <div className={upload.error ? "error" : "result"} role={upload.error ? "alert" : "status"}>{upload.msg}</div>}
      </section>

      <section className="workflow-card fusion-card">
        <p className="card-eyebrow">02 / Build your knowledge base</p>
        <h2>Run knowledge fusion</h2>
        <p className="hint">Embed ingested knowledge, remove redundancy, and build your unified knowledge base.</p>
        <button className="primary-button" onClick={doFuse} disabled={fusing}>
          {fusing ? "Fusing… (first run loads the model)" : "Run fusion"}
        </button>
        {error && <div className="error" role="alert">{error}</div>}
        {stats && (
          <div className="stats" aria-live="polite">
            <div className="stat"><b>{stats.units_in}</b><span>Knowledge units in</span></div>
            <div className="stat"><b>{stats.kb_items_out}</b><span>Unified KB items</span></div>
            <div className="stat"><b>{stats.reduction_pct}%</b><span>Redundancy removed</span></div>
          </div>
        )}
      </section>
    </div>
  );
}