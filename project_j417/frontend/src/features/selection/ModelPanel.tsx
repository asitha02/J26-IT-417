import { labelsExportUrl } from "./api";
import { useLabelStats, useModel, useTrain } from "./hooks";

const METHODS: ["bm25" | "semantic" | "fixed_hybrid" | "learned", string][] = [
  ["bm25", "Keyword only (BM25)"],
  ["semantic", "Meaning only (embeddings)"],
  ["fixed_hybrid", "Fixed blend (35% / 65%)"],
  ["learned", "Trained ranker"],
];

const fmt = (v: number | null | undefined) => (v == null ? "–" : v.toFixed(3));

export default function ModelPanel() {
  const stats = useLabelStats();
  const model = useModel();
  const train = useTrain();
  const report = model.data?.report;
  const best = report
    ? Math.max(...METHODS.map(([k]) => report.metrics[k]["ndcg@10"] ?? -1))
    : null;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Ranking model training</h2>
          <p className="mt-1 text-sm text-slate-600">
            Mark clips above as relevant or not, then train. The model learns how much to trust each signal (keyword
            match, meaning match, speech confidence, position…) from your labels.
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={labelsExportUrl}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
          >
            Export labels
          </a>
          <button
            onClick={() => train.mutate()}
            disabled={train.isPending || !stats.data?.ready_to_train}
            className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {train.isPending ? "Training…" : "Train ranker"}
          </button>
        </div>
      </div>

      {stats.data && (
        <p className="mt-3 text-sm text-slate-600">
          <b>{stats.data.labels}</b> labels ({stats.data.positives} relevant, {stats.data.negatives} not) across{" "}
          <b>{stats.data.queries}</b> queries.
          {stats.data.needs && <span className="text-amber-700"> {stats.data.needs}</span>}
        </p>
      )}
      {train.error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {train.error.message}
        </p>
      )}

      {report ? (
        <div className="mt-5 space-y-4">
          <p className="text-xs text-slate-500">
            Trained {model.data?.trained_at} on {report.n_labels} labels · tested on {report.evaluated_queries} held-out
            queries (each query is left out once, the model is trained on the rest).
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="py-1 font-medium">Method</th>
                <th className="py-1 font-medium">nDCG@10</th>
                <th className="py-1 font-medium">Precision@5</th>
              </tr>
            </thead>
            <tbody>
              {METHODS.map(([key, name]) => {
                const m = report.metrics[key];
                const isBest = best !== null && m["ndcg@10"] === best;
                return (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-1.5">{name}</td>
                    <td className={`py-1.5 font-mono ${isBest ? "font-bold text-indigo-700" : ""}`}>{fmt(m["ndcg@10"])}</td>
                    <td className="py-1.5 font-mono">{fmt(m["p@5"])}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div>
            <h3 className="mb-1 text-xs font-medium text-slate-500">What the model relies on (weight)</h3>
            <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
              {Object.entries(report.weights)
                .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                .map(([name, w]) => (
                  <li key={name} className="flex justify-between border-b border-slate-100 py-0.5">
                    <span>{name}</span>
                    <span className={`font-mono ${w < 0 ? "text-red-600" : "text-emerald-700"}`}>
                      {w > 0 ? "+" : ""}
                      {w.toFixed(2)}
                    </span>
                  </li>
                ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-500">No trained model yet — the fixed keyword/meaning blend is in use.</p>
      )}
    </section>
  );
}
