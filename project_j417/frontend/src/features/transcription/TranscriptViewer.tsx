import { useMemo, useState } from "react";
import { downloadUrl } from "./api";
import { formatTime, youtubeId } from "./format";
import type { Transcript } from "./types";

interface Props {
  jobId: string;
  transcript: Transcript;
}

export default function TranscriptViewer({ jobId, transcript }: Props) {
  const [query, setQuery] = useState("");
  const [startAt, setStartAt] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  const videoId = youtubeId(transcript.source_url);

  const segments = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? transcript.segments.filter((s) => s.text.toLowerCase().includes(q)) : transcript.segments;
  }, [query, transcript.segments]);

  const copyJson = async () => {
    await navigator.clipboard.writeText(JSON.stringify(transcript, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const speedFactor =
    transcript.duration_sec && transcript.processing_time_sec
      ? (transcript.duration_sec / transcript.processing_time_sec).toFixed(1)
      : null;

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 p-5">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold">{transcript.title ?? transcript.source_id}</h2>
          <p className="mt-1 text-xs text-slate-500">
            {transcript.segments.length} segments · language {transcript.language} · model {transcript.asr_model} (
            {transcript.device}) · {transcript.processing_time_sec}s
            {speedFactor && ` · ${speedFactor}× real time`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyJson}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
          >
            {copied ? "Copied" : "Copy JSON"}
          </button>
          <a
            href={downloadUrl(jobId)}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            Download JSON
          </a>
        </div>
      </header>

      {videoId && (
        <div className="border-b border-slate-200 p-5">
          <iframe
            key={startAt ?? "initial"}
            className="aspect-video w-full max-w-2xl rounded-lg"
            src={`https://www.youtube.com/embed/${videoId}?start=${Math.floor(startAt ?? 0)}${startAt !== null ? "&autoplay=1" : ""}`}
            title="Source video"
            allow="autoplay; encrypted-media"
            allowFullScreen
          />
        </div>
      )}

      <div className="border-b border-slate-200 px-5 py-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search in transcript…"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
      </div>

      <ol className="max-h-[32rem] divide-y divide-slate-100 overflow-y-auto">
        {segments.map((s) => (
          <li key={s.id} className="flex gap-4 px-5 py-3 text-sm hover:bg-slate-50">
            <button
              onClick={() => videoId && setStartAt(s.start)}
              disabled={!videoId}
              className="w-14 shrink-0 text-left font-mono text-xs text-indigo-600 enabled:hover:underline disabled:text-slate-400"
              title={videoId ? "Jump to this moment" : undefined}
            >
              {formatTime(s.start)}
            </button>
            <p className="flex-1 leading-relaxed">{s.text}</p>
          </li>
        ))}
        {segments.length === 0 && <li className="px-5 py-8 text-center text-sm text-slate-500">No matches.</li>}
      </ol>
    </section>
  );
}
