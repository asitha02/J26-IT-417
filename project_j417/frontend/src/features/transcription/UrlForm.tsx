import { FormEvent, useState } from "react";

interface Props {
  busy: boolean;
  error?: string | null;
  onSubmit: (v: { url: string; language?: string; word_timestamps: boolean }) => void;
}

export default function UrlForm({ busy, error, onSubmit }: Props) {
  const [url, setUrl] = useState("");
  const [words, setWords] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit({ url: url.trim(), word_timestamps: words });
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <label htmlFor="url" className="mb-2 block text-sm font-medium text-slate-700">
        YouTube or podcast URL
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="url"
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
        <button
          type="submit"
          disabled={busy || !url.trim()}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Working…" : "Transcribe"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-slate-600">
        <span>English only</span>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={words}
            onChange={(e) => setWords(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-indigo-600"
          />
          Word-level timestamps
        </label>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}
