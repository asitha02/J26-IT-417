import { api } from './api';
import type { ImportResult, VideoSummary } from '@/types/feedback';

const SLOW = { timeout: 120_000 }; // YouTube paging can take a while

export const videoService = {
  list: () => api.get<VideoSummary[]>('/videos'),
  importFromUrl: (url: string, maxPages?: number) =>
    api.post<ImportResult, { url: string; maxPages?: number }>('/videos/import', { url, maxPages }, SLOW),
};
