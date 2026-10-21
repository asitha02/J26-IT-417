import { useState } from "react";
import SegmentFinder from "./features/selection/SegmentFinder";
import JobStatus from "./features/transcription/JobStatus";
import TranscriptViewer from "./features/transcription/TranscriptViewer";
import UrlForm from "./features/transcription/UrlForm";
import { useCreateJob, useJob, useTranscript } from "./features/transcription/hooks";

type Tab = "transcribe" | "segments";

const TABS: [Tab, string][] = [
  ["transcribe", "Transcribe"],
  ["segments", "Find best segments"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("transcribe");
  const [jobId, setJobId] = useState<string | null>(null);
  const create = useCreateJob();
  const job = useJob(jobId);
  const transcript = useTranscript(jobId, job.data?.status === "done");

  const active = job.data && job.data.status !== "done" && job.data.status !== "failed";

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Cross-Video Knowledge Extraction</h1>
        <p className="mt-1 text-sm text-slate-600">
          {tab === "transcribe"
            ? "Paste a video or podcast link to get a timestamped transcript as JSON."
            : "Rank the most relevant clips for a topic or audience across all transcribed videos."}
        </p>
        <nav className="mt-4 flex gap-1 border-b border-slate-200" role="tablist">
          {TABS.map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
                tab === id ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      {tab === "transcribe" ? (
        <>
          <UrlForm
            busy={create.isPending || !!active}
            error={create.error?.message}
            onSubmit={(values) =>
              create.mutate(values, {
                onSuccess: (j) => setJobId(j.job_id),
              })
            }
          />

          {job.data && <JobStatus job={job.data} />}
          {job.error && <p className="text-sm text-red-700">{job.error.message}</p>}

          {jobId && transcript.data && <TranscriptViewer jobId={jobId} transcript={transcript.data} />}
        </>
      ) : (
        <SegmentFinder />
      )}
    </main>
  );
}
