import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import CleaningModels from "./features/cleaning/CleaningModels";
import AddVideo from "./features/transcription/AddVideo";
import JobStatus from "./features/transcription/JobStatus";
import { useJob } from "./features/transcription/hooks";
import VideoList from "./features/videos/VideoList";

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const job = useJob(jobId);
  const status = job.data?.status;
  const active = status !== undefined && status !== "done" && status !== "failed";

  // A finished job adds a video to the list and to the cleaned JSON.
  useEffect(() => {
    if (status === "done") {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      queryClient.invalidateQueries({ queryKey: ["cleaning-summary"] });
    }
  }, [status, queryClient]);

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">YouTube transcripts → cleaned JSON</h1>
        <p className="mt-1 text-sm text-slate-600">
          Paste a YouTube link to get its timestamped transcript as JSON. Trained models then remove the duplicates and error
          words.
        </p>
      </header>

      <AddVideo busy={active} onJob={(j) => setJobId(j.job_id)} />
      {job.data && <JobStatus job={job.data} />}
      {job.error && <p className="text-sm text-red-700">{job.error.message}</p>}
      <VideoList />
      <CleaningModels />
    </main>
  );
}
