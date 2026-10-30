import { request } from "../../lib/request";
import type { Job } from "./types";

export const createJob = (url: string) =>
  request<Job>("/api/transcripts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

export const getJob = (jobId: string) => request<Job>(`/api/transcripts/${jobId}`);