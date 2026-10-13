import { useEffect, useState } from "react";
import "./App.css";
import { api } from "./api";
import IngestFuse from "./components/IngestFuse";
import KnowledgeBase from "./components/KnowledgeBase";
import Generate from "./components/Generate";
import Translate from "./components/Translate";

const TABS = [
  ["fusion", "1 · Ingest & Fuse"],
  ["kb", "2 · Knowledge Base"],
  ["generate", "3 · Generate"],
  ["translate", "4 · Translate"],
];

export default function App() {
  const [tab, setTab] = useState("fusion");
  const [online, setOnline] = useState(null);

  useEffect(() => {
    api("/health").then(() => setOnline(true)).catch(() => setOnline(false));
  }, []);

  return (
    <>
      <header>
        <div>
          <h1>Semantic Knowledge Fusion &amp; Multilingual Content Generation</h1>
          <p className="sub">J26-IT-417 · Component 2</p>
        </div>
        <span className={"pill " + (online === null ? "" : online ? "ok" : "bad")}>
          {online === null ? "checking…" : online ? "Backend connected" : "Backend offline"}
        </span>
      </header>

      <nav>
        {TABS.map(([id, label]) => (
          <button key={id} className={"tab" + (tab === id ? " active" : "")} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      <main>
        <section className="panel active">
          {tab === "fusion" && <IngestFuse />}
          {tab === "kb" && <KnowledgeBase />}
          {tab === "generate" && <Generate />}
          {tab === "translate" && <Translate />}
        </section>
      </main>
    </>
  );
}
