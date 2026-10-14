import { useState } from "react";
import JobStatus from "./features/transcription/JobStatus";
import TranscriptViewer from "./features/transcription/TranscriptViewer";
import UrlForm from "./features/transcription/UrlForm";
import { useCreateJob, useJob, useTranscript } from "./features/transcription/hooks";

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const create = useCreateJob();
  const job = useJob(jobId);
  const transcript = useTranscript(jobId, job.data?.status === "done");

  const active = job.data && job.data.status !== "done" && job.data.status !== "failed";

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Transcript Extractor</h1>
        <p className="mt-1 text-sm text-slate-600">
          Paste a video or podcast link to get a timestamped transcript as JSON.
        </p>
      </header>

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
    </main>
  );
}
