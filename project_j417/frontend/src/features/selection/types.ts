// Mirrors backend/app/selection/schemas.py

export interface RankRequest {
  query: string;
  audience?: string;
  source_ids?: string[];
  top_k: number;
  window_sec: number;
  per_video_max: number;
}

export interface Clip {
  rank: number;
  source_id: string;
  title?: string | null;
  source_url: string;
  watch_url: string;
  start: number;
  end: number;
  score: number;
  lexical_score: number;
  semantic_score?: number | null;
  text: string;
}

export interface RankResponse {
  query: string;
  audience?: string | null;
  method: "hybrid" | "bm25";
  embedding_model?: string | null;
  videos_searched: number;
  windows_searched: number;
  elapsed_sec: number;
  clips: Clip[];
}

export interface LibraryItem {
  source_id: string;
  title?: string | null;
  source_url: string;
  duration_sec?: number | null;
  language?: string | null;
  segments: number;
}
