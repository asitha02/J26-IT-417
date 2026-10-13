import { useState } from "react";
import { postJSON } from "../api";
import Consistency from "./Consistency";

export default function Translate() {
  const [source, setSource] = useState("en");
  const [target, setTarget] = useState("si");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function run() {
    if (!text.trim()) return setError("Enter some text first.");
    setLoading(true); setError(""); setResult(null);
    try { setResult(await postJSON("/translate", { text, source, target, check: true })); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <>
      <h2>Translate text</h2>
      <div className="row">
        <label>From
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="en">English</option><option value="si">Sinhala</option>
          </select>
        </label>
        <label>To
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="si">Sinhala</option><option value="en">English</option>
          </select>
        </label>
      </div>
      <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} placeholder="Enter text to translate" />
      <button onClick={run} disabled={loading}>{loading ? "Translating…" : "Translate"}</button>
      {error && <div className="error">{error}</div>}
      {result && (
        <>
          <div className={"output" + (target === "si" ? " si" : "")}>{result.translation}</div>
          <Consistency data={result.consistency} />
        </>
      )}
    </>
  );
}