import { useState } from "react";
import { postJSON } from "../api";
import Consistency from "./Consistency";

const OUTPUT_TYPES = [
  {
    value: "summary",
    label: "Summary",
    description: "A concise overview of the key ideas.",
  },
  {
    value: "notes",
    label: "Study notes",
    description: "Organized topics with headings and key points.",
  },
  {
    value: "quiz",
    label: "Quiz",
    description: "Five multiple-choice questions with answers.",
  },
];

const LANGUAGES = [
  { value: "en", label: "English", nativeLabel: "English" },
  { value: "si", label: "Sinhala", nativeLabel: "සිංහල" },
];

export default function Generate() {
  const [type, setType] = useState("summary");
  const [lang, setLang] = useState("en");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function run(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await postJSON("/generate", { output_type: type, language: lang }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const selectedOutput = OUTPUT_TYPES.find((output) => output.value === type);
  const resultOutput = result
    ? OUTPUT_TYPES.find((output) => output.value === result.output_type)
    : null;

  return (
    <div className="generator">
      <div className="generator-heading">
        <span className="generator-eyebrow">LEARNING MATERIALS</span>
        <h2>Generate from your knowledge base</h2>
        <p>Choose a format and language. Every result is grounded in your fused knowledge.</p>
      </div>

      <form className="generator-form" onSubmit={run}>
        <fieldset className="generator-fieldset">
          <legend>1. Choose an output</legend>
          <div className="generator-options">
            {OUTPUT_TYPES.map((output) => (
              <label
                className={"generator-option" + (type === output.value ? " selected" : "")}
                key={output.value}
              >
                <input
                  type="radio"
                  name="output-type"
                  value={output.value}
                  checked={type === output.value}
                  onChange={() => setType(output.value)}
                />
                <span className="generator-option-copy">
                  <strong>{output.label}</strong>
                  <span>{output.description}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="generator-fieldset">
          <legend>2. Choose a language</legend>
          <div className="generator-languages">
            {LANGUAGES.map((language) => (
              <label
                className={"generator-language" + (lang === language.value ? " selected" : "")}
                key={language.value}
              >
                <input
                  type="radio"
                  name="output-language"
                  value={language.value}
                  checked={lang === language.value}
                  onChange={() => setLang(language.value)}
                />
                <span>{language.nativeLabel}</span>
                {language.nativeLabel !== language.label && (
                  <span className="language-english">{language.label}</span>
                )}
              </label>
            ))}
          </div>
        </fieldset>

        <button className="generator-submit" type="submit" disabled={loading}>
          {loading ? "Generating…" : `Generate ${selectedOutput.label.toLowerCase()}`}
        </button>
        {lang === "si" && (
          <p className="generator-note">
            Sinhala translation may take longer the first time while the translation model loads.
          </p>
        )}
      </form>

      {loading && (
        <div className="generator-status" role="status" aria-live="polite">
          Creating your {selectedOutput.label.toLowerCase()}…
        </div>
      )}
      {error && <div className="generator-error" role="alert">{error}</div>}

      {result && (
        <section
          className="generator-result"
          aria-labelledby="generated-result-title"
          aria-live="polite"
        >
          <div className="generator-result-heading">
            <div>
              <span className="generator-eyebrow">YOUR GENERATED CONTENT</span>
              <h3 id="generated-result-title">
                {resultOutput?.label ?? "Generated content"} ·{" "}
                {result.language === "si" ? "සිංහල" : "English"}
              </h3>
            </div>
            <span className="generator-source-count">
              {result.kb_ids?.length ?? 0} source items
            </span>
          </div>

          <pre className={"generator-output" + (result.language === "si" ? " sinhala" : "")}>
            {result.content}
          </pre>

          {result.language === "si" && (
            <>
              <details className="generator-original">
                <summary>View English original</summary>
                <pre className="generator-output">{result.content_en}</pre>
              </details>
              <Consistency data={result.consistency} />
            </>
          )}
          <p className="generator-footnote">
            Source citations such as [kb_00001] identify the knowledge items used.
          </p>
        </section>
      )}
    </div>
  );
}
