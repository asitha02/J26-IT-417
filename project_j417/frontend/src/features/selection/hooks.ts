import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getLabelStats, getLibrary, getModel, rankSegments, setLabel, trainRanker } from "./api";

export const useLibrary = () => useQuery({ queryKey: ["library"], queryFn: getLibrary });

export const useRank = () => useMutation({ mutationFn: rankSegments });

export const useLabelStats = () => useQuery({ queryKey: ["label-stats"], queryFn: getLabelStats });

export const useModel = () => useQuery({ queryKey: ["ranker-model"], queryFn: getModel });

export function useSetLabel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: setLabel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["label-stats"] }),
  });
}

export function useTrain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: trainRanker,
    onSuccess: (info) => {
      qc.setQueryData(["ranker-model"], info);
      qc.invalidateQueries({ queryKey: ["label-stats"] });
    },
  });
}
