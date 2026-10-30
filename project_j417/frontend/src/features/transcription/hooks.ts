import { useMutation, useQuery } from "@tanstack/react-query";
import { createJob, getJob } from "./api";

export const useCreateJob = () => useMutation({ mutationFn: createJob });

/** Polls the job every 1.5 s until it is done or failed. */
export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 1500;
    },
  });
}