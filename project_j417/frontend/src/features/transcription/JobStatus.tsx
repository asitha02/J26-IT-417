import type { Job } from "./types";

const LABELS: Record<Job["status"], string> = {
  queued: "Queued",
  downloading: "Extracting audio",
  transcribing: "Transcribing speech",
  done: "Done",
  failed: "Failed",
};

export default function JobStatus({ job }: { job: Job }) {
  const pct = Math.round(job.progress * 100);
  const failed = job.status === "failed";
  const done = job.status === "done";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between text-sm">
        <span className={`font-semibold ${failed ? "text-red-600" : done ? "text-emerald-600" : "text-indigo-600"}`}>
          {LABELS[job.status]}
          {job.cached && done && " (served from cache)"}
        </span>
        <span className="tabular-nums text-slate-500">{pct}%</span>
      </div>

      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            failed ? "bg-red-500" : done ? "bg-emerald-500" : "bg-indigo-500"
          }`}
          style={{ width: `${failed ? 100 : pct}%` }}
        />
      </div>

      {job.title && <p className="mt-3 truncate text-sm text-slate-600">{job.title}</p>}
      {failed && job.error && <p className="mt-3 text-sm text-red-700">{job.error}</p>}
    </div>
  );
}
