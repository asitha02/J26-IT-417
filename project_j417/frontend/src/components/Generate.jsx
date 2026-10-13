import { useState } from "react";
import { postJSON } from "../api";
import Consistency from "./Consistency";

export default function Generate() {
  const [type, setType] = useState("summary");
  const [lang, setLang] = useState("en");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await postJSON("/generate", { output_type: type, language: lang })); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <>
      <h2>Generate learning content from the knowledge base</h2>
      <div className="row">
        <label>Output
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="summary">Summary</option>
            <option value="notes">Study notes</option>
            <option value="quiz">Quiz</option>
          </select>
        </label>
        <label>Language
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="en">English</option>
            <option value="si">සිංහල (Sinhala)</option>
          </select>
        </label>
        <button onClick={run} disabled={loading}>{loading ? "Generating…" : "Generate"}</button>
      </div>
      <p className="hint">Sinhala output is translated with NLLB-200 and may take a while the first time.</p>
      {error && <div className="error">{error}</div>}
      {result && (
        <div>
          <div className={"output" + (result.language === "si" ? " si" : "")}>{result.content}</div>
          {result.language === "si" && (
            <>
              <details>
                <summary>English original</summary>
                <div className="output">{result.content_en}</div>
              </details>
              <Consistency data={result.consistency} />
            </>
          )}
          <p className="hint">Built from {result.kb_ids.length} knowledge item(s). [kb_id] tags show the source item.</p>
        </div>
      )}
    </>
  );
}