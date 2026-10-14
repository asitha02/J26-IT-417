// Mirrors backend/app/transcription/schemas.py

export type JobState = "queued" | "downloading" | "transcribing" | "done" | "failed";

export interface TranscriptRequest {
  url: string;
  language?: string;
  word_timestamps: boolean;
}

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

export interface Word {
  start: number;
  end: number;
  word: string;
  probability?: number;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
  confidence?: number;
  words?: Word[];
}

export interface Transcript {
  schema_version: string;
  source_id: string;
  source_url: string;
  title?: string;
  uploader?: string;
  duration_sec?: number;
  language: string;
  language_probability?: number;
  asr_model: string;
  device: string;
  created_at: string;
  processing_time_sec: number;
  full_text: string;
  segments: Segment[];
}
