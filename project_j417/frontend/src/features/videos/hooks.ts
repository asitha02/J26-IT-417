import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "../../lib/request";

export interface Video {
  source_id: string;
  title?: string | null;
  source_url: string;
  uploader?: string | null;
  duration_sec?: number | null;
  language?: string | null;
  asr_model?: string | null;
  segments: number;
}

export const useVideos = () => useQuery({ queryKey: ["videos"], queryFn: () => request<Video[]>("/api/videos") });

export function useDeleteVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => request<unknown>(`/api/videos/${encodeURIComponent(sourceId)}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["videos"] });
      qc.invalidateQueries({ queryKey: ["cleaning-summary"] });
    },
  });
}
