import { FormEvent, useState } from "react";
import { formatTime } from "../transcription/format";
import { useLibrary, useRank } from "./hooks";
import type { Clip } from "./types";

const inputCls =
  "rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200";

function download(clips: Clip[], query: string) {
  const blob = new Blob([JSON.stringify({ query, clips }, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ranked-segments.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function SegmentFinder() {
  const library = useLibrary();
  const rank = useRank();
  const [query, setQuery] = useState("");
  const [audience, setAudience] = useState("");
  const [topK, setTopK] = useState(10);
  const [windowSec, setWindowSec] = useState(30);
  const [perVideo, setPerVideo] = useState(3);
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    rank.mutate({
      query: query.trim(),
      audience: audience.trim() || undefined,
      source_ids: selected.length ? selected : undefined,
      top_k: topK,
      window_sec: windowSec,
      per_video_max: perVideo,
    });
  };

  const videos = library.data ?? [];
  const result = rank.data;

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Topic
            <input
              required
              minLength={2}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. how to keep a sourdough starter alive"
              className={`mt-1 w-full ${inputCls}`}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Audience <span className="font-normal text-slate-400">(optional)</span>
            <input
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="e.g. complete beginners"
              className={`mt-1 w-full ${inputCls}`}
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-slate-600">
          <label className="flex items-center gap-2">
            Clips
            <input type="number" min={1} max={50} value={topK} onChange={(e) => setTopK(+e.target.value || 10)} className={`w-20 ${inputCls} py-1`} />
          </label>
          <label className="flex items-center gap-2">
            Clip length (s)
            <input type="number" min={10} max={120} value={windowSec} onChange={(e) => setWindowSec(+e.target.value || 30)} className={`w-20 ${inputCls} py-1`} />
          </label>
          <label className="flex items-center gap-2">
            Max per video
            <input type="number" min={1} max={50} value={perVideo} onChange={(e) => setPerVideo(+e.target.value || 3)} className={`w-20 ${inputCls} py-1`} />
          </label>
        </div>

        <fieldset>
          <legend className="mb-2 text-sm font-medium text-slate-700">
            Videos to search{" "}
            <span className="font-normal text-slate-400">
              ({selected.length ? `${selected.length} selected` : `all ${videos.length}`})
            </span>
          </legend>
          {library.isLoading && <p className="text-sm text-slate-500">Loading library…</p>}
          {library.error && <p className="text-sm text-red-700">{library.error.message}</p>}
          {!library.isLoading && videos.length === 0 && (
            <p className="text-sm text-slate-500">No transcripts yet — transcribe some videos in the Transcribe tab first.</p>
          )}
          <ul className="max-h-48 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
            {videos.map((v) => (
              <li key={v.source_id}>
                <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selected.includes(v.source_id)}
                    onChange={() => toggle(v.source_id)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                  />
                  <span className="min-w-0 flex-1 truncate">{v.title ?? v.source_id}</span>
                  {v.duration_sec ? <span className="font-mono text-xs text-slate-400">{formatTime(v.duration_sec)}</span> : null}
                </label>
              </li>
            ))}
          </ul>
        </fieldset>

        <button
          type="submit"
          disabled={rank.isPending || query.trim().length < 2 || videos.length === 0}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {rank.isPending ? "Ranking…" : "Find best segments"}
        </button>

        {rank.error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {rank.error.message}
          </p>
        )}
      </form>

      {result && (
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
            <p className="text-xs text-slate-500">
              {result.clips.length} clips from {result.videos_searched} videos · {result.windows_searched} candidates ·{" "}
              {result.method === "hybrid" ? `semantic + keyword (${result.embedding_model})` : "keyword only (BM25)"} ·{" "}
              {result.elapsed_sec}s
            </p>
            {result.clips.length > 0 && (
              <button
                onClick={() => download(result.clips, result.query)}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
              >
                Download JSON
              </button>
            )}
          </header>
          <ol className="divide-y divide-slate-100">
            {result.clips.map((c) => (
              <li key={`${c.source_id}-${c.start}`} className="space-y-2 px-5 py-4 text-sm">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                    {c.rank}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-medium">{c.title ?? c.source_id}</span>
                  <a
                    href={c.watch_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-xs text-indigo-600 hover:underline"
                  >
                    {formatTime(c.start)}–{formatTime(c.end)} ↗
                  </a>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-40 overflow-hidden rounded-full bg-slate-100" title={`Relevance ${c.score}`}>
                    <div className="h-full bg-indigo-500" style={{ width: `${Math.round(c.score * 100)}%` }} />
                  </div>
                  <span className="font-mono text-xs text-slate-500">{c.score.toFixed(2)}</span>
                  <span className="text-xs text-slate-400">
                    keyword {c.lexical_score.toFixed(2)}
                    {c.semantic_score != null && ` · semantic ${c.semantic_score.toFixed(2)}`}
                  </span>
                </div>
                <p className="leading-relaxed text-slate-700">{c.text}</p>
              </li>
            ))}
            {result.clips.length === 0 && (
              <li className="px-5 py-8 text-center text-sm text-slate-500">No relevant segments found.</li>
            )}
          </ol>
        </section>
      )}
    </div>
  );
}
