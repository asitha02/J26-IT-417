import { api } from './api';
import type { AnalysisResponse } from '@/types/feedback';

export const feedbackService = {
  // LLM analysis of many comments can take a while
  analyze: (videoId: string, force = false) =>
    api.post<AnalysisResponse, { videoId: string; force: boolean }>(
      '/feedback/analyze',
      { videoId, force },
      { timeout: 300_000 }
    ),
};
