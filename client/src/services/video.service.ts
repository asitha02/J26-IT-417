import { api } from './api';
import type { CommentLimit, ImportResult, VideoSummary } from '@/types/feedback';

const SLOW = { timeout: 900_000 }; // fetching every comment of a popular video can take minutes

export const videoService = {
  list: () => api.get<VideoSummary[]>('/videos'),
  importFromUrl: (url: string, maxPages: CommentLimit) =>
    api.post<ImportResult, { url: string; maxPages: CommentLimit }>('/videos/import', { url, maxPages }, SLOW),
};
