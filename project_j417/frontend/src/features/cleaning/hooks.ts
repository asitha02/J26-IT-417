import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "../../lib/request";
import type { CleaningModelInfo, CleaningSummary } from "./types";

/** What cleaning did to every video (updates when a video is added or removed, or the models are trained). */
export const useCleaningSummary = () =>
  useQuery({
    queryKey: ["cleaning-summary"],
    queryFn: () => request<CleaningSummary>("/api/cleaning/summary"),
    retry: false, // "no videos yet" is an expected answer, not an error to retry
  });

export const useCleaningModels = () =>
  useQuery({ queryKey: ["cleaning-models"], queryFn: () => request<CleaningModelInfo>("/api/cleaning/model") });

export function useTrainCleaning() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => request<CleaningModelInfo>("/api/cleaning/train", { method: "POST" }),
    onSuccess: (info) => {
      qc.setQueryData(["cleaning-models"], info);
      qc.invalidateQueries({ queryKey: ["cleaning-summary"] }); // every JSON is rebuilt with the models that passed
    },
  });
}
