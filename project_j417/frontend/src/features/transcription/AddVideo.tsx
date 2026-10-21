import { FormEvent, useState } from "react";
import { useCreateJob } from "./hooks";
import type { Job } from "./types";

interface Props {
  busy: boolean;
  onJob: (job: Job) => void;
}

/** Paste a YouTube link: it is downloaded, turned into text, and stored as a JSON file. */
export default function AddVideo({ busy, onJob }: Props) {
  const [url, setUrl] = useState("");
  const create = useCreateJob();
  const working = busy || create.isPending;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    create.mutate(url.trim(), {
      onSuccess: (job) => {
        onJob(job);
        setUrl("");
      },
    });
  };

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">1. Add a YouTube video</h2>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          aria-label="YouTube link"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
        <button
          type="submit"
          disabled={working || !url.trim()}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {working ? "Working…" : "Get JSON"}
        </button>
      </div>
      <p className="text-xs text-slate-500">English speech only. Each transcript keeps the video ID and the timestamp of every segment.</p>
      {create.error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {create.error.message}
        </p>
      )}
    </form>
  );
}