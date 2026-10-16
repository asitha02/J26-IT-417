import { useEffect, useState } from "react";
import { api } from "./api";
import IngestFuse from "./components/IngestFuse";
import KnowledgeBase from "./components/KnowledgeBase";
import Generate from "./components/Generate";
import Translate from "./components/Translate";

const TABS = [
  ["fusion", "01", "Ingest & Fuse"],
  ["kb", "02", "Knowledge Base"],
  ["generate", "03", "Generate"],
  ["translate", "04", "Translate"],
];

export default function App() {
  const [tab, setTab] = useState("fusion");
  const [online, setOnline] = useState(null);
  const currentStep = TABS.findIndex(([id]) => id === tab) + 1;

  useEffect(() => {
    api("/health").then(() => setOnline(true)).catch(() => setOnline(false));
  }, []);

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="Knowledge Studio home">
          <span className="brand-mark" aria-hidden="true">KF</span>
          <span className="brand-copy">
            <strong>Knowledge Studio</strong>
            <span>J26-IT-417 &nbsp;·&nbsp; Component 02</span>
          </span>
        </a>
        <span
          className={"pill " + (online === null ? "" : online ? "ok" : "bad")}
          role="status"
          aria-live="polite"
        >
          {online === null ? "Checking connection" : online ? "Backend connected" : "Backend offline"}
        </span>
      </header>

      <main className="workspace">
        <section className="page-intro">
          <div className="intro-copy">
            <p className="eyebrow">Semantic knowledge fusion</p>
            <h1>Knowledge, connected.<br /><span>Ideas, in every language.</span></h1>
            <p className="intro-description">
              Bring your source material together, explore what you know, and create
              thoughtful learning content in multiple languages.
            </p>
          </div>
          <aside className="intro-aside" aria-label="About this workflow">
            <span>{String(currentStep).padStart(2, "0")} / 04</span>
            <p>From raw knowledge to clear, multilingual learning materials.</p>
          </aside>
        </section>

        <nav className="workflow-nav" role="tablist" aria-label="Knowledge workflow">
          {TABS.map(([id, number, label]) => (
            <button
              key={id}
              id={`tab-${id}`}
              className={"tab" + (tab === id ? " active" : "")}
              role="tab"
              aria-selected={tab === id}
              aria-controls="workflow-panel"
              tabIndex={tab === id ? 0 : -1}
              onClick={() => setTab(id)}
            >
              <span className="tab-number">{number}</span>
              <span className="tab-label">{label}</span>
            </button>
          ))}
        </nav>

        <section
          className="panel active"
          id="workflow-panel"
          role="tabpanel"
          aria-labelledby={`tab-${tab}`}
        >
          {tab === "fusion" && <IngestFuse />}
          {tab === "kb" && <KnowledgeBase />}
          {tab === "generate" && <Generate />}
          {tab === "translate" && <Translate />}
        </section>
      </main>
    </div>
  );
}
