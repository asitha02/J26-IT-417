import { useMutation, useQuery } from "@tanstack/react-query";
import { getLibrary, rankSegments } from "./api";

export const useLibrary = () => useQuery({ queryKey: ["library"], queryFn: getLibrary });

export const useRank = () => useMutation({ mutationFn: rankSegments });
