// Mirrors backend/app/selection/schemas.py

export interface RankRequest {
  query: string;
  audience?: string;
  source_ids?: string[];
  top_k: number;
  window_sec: number;
  per_video_max: number;
  ranker: "auto" | "fixed";
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
  features: Record<string, number>;
}

export interface RankResponse {
  query: string;
  audience?: string | null;
  method: "learned" | "hybrid" | "bm25";
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

export interface LabelRequest {
  query: string;
  audience?: string;
  source_id: string;
  start: number;
  end: number;
  label: 0 | 1 | null;
  features: Record<string, number>;
}

export interface LabelStats {
  labels: number;
  positives: number;
  negatives: number;
  queries: number;
  ready_to_train: boolean;
  needs?: string | null;
}

export interface MetricPair {
  "ndcg@10": number | null;
  "p@5": number | null;
}

export interface ModelReport {
  n_labels: number;
  n_queries: number;
  positives: number;
  negatives: number;
  evaluated_queries: number;
  metrics: Record<"bm25" | "semantic" | "fixed_hybrid" | "learned", MetricPair>;
  weights: Record<string, number>;
}

export interface ModelInfo {
  trained: boolean;
  trained_at?: string | null;
  report?: ModelReport | null;
}
