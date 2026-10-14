import type { Job, Transcript, TranscriptRequest } from "./types";

const BASE = "/api/transcripts";

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const createJob = (body: TranscriptRequest) =>
  request<Job>(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getJob = (jobId: string) => request<Job>(`${BASE}/${jobId}`);

export const getTranscript = (jobId: string) => request<Transcript>(`${BASE}/${jobId}/result`);

export const downloadUrl = (jobId: string) => `${BASE}/${jobId}/download`;
