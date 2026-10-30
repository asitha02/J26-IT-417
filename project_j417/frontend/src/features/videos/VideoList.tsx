import { useCleaningSummary } from "../cleaning/hooks";
import { formatTime } from "../transcription/format";
import { useDeleteVideo, useVideos } from "./hooks";

export default function VideoList() {
  const { data: videos, isLoading, error } = useVideos();
  const quality = new Map(useCleaningSummary().data?.videos.map((v) => [v.source_id, v.quality]));
  const remove = useDeleteVideo();

  const confirmDelete = (id: string, title: string) => {
    if (!window.confirm(`Delete “${title}”?\n\nIts transcript is removed from your JSON files. This cannot be undone.`)) return;
    remove.mutate(id);
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <h2 className="text-lg font-semibold">2. Your videos{videos ? ` (${videos.length})` : ""}</h2>
          <p className="mt-1 text-sm text-slate-600">Each video has a cleaned JSON: duplicates and error words removed, timestamps kept.</p>
        </div>
        {videos && videos.length > 0 && (
          <a
            href="/api/cleaning/download"
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            Download all as one JSON
          </a>
        )}
      </header>

      {isLoading && <p className="px-5 py-4 text-sm text-slate-500">Loading…</p>}
      {error && <p className="px-5 py-4 text-sm text-red-700">{error.message}</p>}
      {remove.error && (
        <p role="alert" className="mx-5 mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {remove.error.message}
        </p>
      )}
      {videos && videos.length === 0 && <p className="px-5 py-6 text-sm text-slate-500">No videos yet. Add a YouTube link above.</p>}

      <ul className="divide-y divide-slate-100">
        {videos?.map((v) => {
          const title = v.title ?? v.source_id;
          const q = quality.get(v.source_id);
          const dupes = q ? (q.removed.duplicate_in_video ?? 0) + (q.removed.duplicate_across_videos ?? 0) : 0;
          const busy = remove.isPending && remove.variables === v.source_id;
          return (
            <li key={v.source_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 text-sm">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{title}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {v.duration_sec ? `${formatTime(v.duration_sec)} · ` : ""}
                  {q
                    ? `${q.segments_raw} → ${q.segments_kept} segments · ${q.error_words_removed} error words · ${q.redundant_sentences_removed} redundant sentences · ${dupes} duplicates removed`
                    : `${v.segments} segments`}
                </p>
              </div>
              <a
                href={`/api/videos/${encodeURIComponent(v.source_id)}/download`}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
              >
                Cleaned JSON
              </a>
              <button
                onClick={() => confirmDelete(v.source_id, title)}
                disabled={busy}
                className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {busy ? "Deleting…" : "Delete"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
