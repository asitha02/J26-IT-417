// Mirrors backend/app/transcription/schemas.py

export type JobState = "queued" | "downloading" | "transcribing" | "done" | "failed";

export interface Job {
  job_id: string;
  status: JobState;
  progress: number;
  source_url: string;
  source_id?: string | null;
  title?: string | null;
  duration_sec?: number | null;
  transcript_id?: string | null;
  cached: boolean;
  processing_time_sec?: number | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}