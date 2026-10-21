// Mirrors backend/app/cleaning/ (pipeline.py, router.py and the three models' reports)

export interface Quality {
  segments_raw: number;
  segments_kept: number;
  removed: Record<string, number>;
  redundant_sentences_removed: number;
  error_words_removed: number;
  words_before: number;
  words_after: number;
  words_removed_pct: number;
  avg_confidence: number | null;
  low_confidence_segments: number;
}

export interface CleaningSummary {
  generated_at: string;
  cleaning: { trained_models_in_use: ModelsInUse };
  reasons: Record<string, string>;
  summary: Quality & { videos: number };
  videos: { source_id: string; title?: string | null; duration_sec?: number | null; quality: Quality }[];
  removed_examples: {
    source_id: string;
    id: number;
    start: number;
    reason: string;
    text: string;
    duplicate_of?: { source_id: string; start: number };
  }[];
}

export interface ModelsInUse {
  sentences: boolean;
  words: boolean;
  duplicates: boolean;
}

interface Scores {
  caught: number;
  wrongly_flagged: number;
  precision: number;
  f1: number;
}

export interface SentenceReport {
  examples: { redundant: number; kinds: string[]; real_sentences: number; tricky_content: number };
  model: Scores;
  never_seen_kind: { caught: number; wrongly_flagged: number; per_kind: { kind: string; caught: number; sentences: number }[] };
  rules: Scores;
  activated: boolean;
  on_your_videos: { sentences_checked: number; flagged: number; examples: string[] };
}

export interface WordReport {
  examples: { clean_sentences: number; noisy_versions: number; filler_kinds: number };
  model: {
    threshold: number;
    restored_exactly: number;
    false_edit_rate: number;
    error_words_caught: number;
    error_words_precision: number;
  };
  rules: { restored_exactly: number; false_edit_rate: number };
  test_sentences: number;
  activated: boolean;
}

export interface DuplicateReport {
  examples: { clean_sentences: number; pairs: number };
  model: Scores;
  rules: Scores & { threshold: number };
  learned_weights: Record<string, number>;
  test_pairs: number;
  activated: boolean;
}

export interface CleaningReport {
  trained_at: string;
  real_sentences: number;
  sentences: SentenceReport;
  words: WordReport;
  duplicates: DuplicateReport;
}

export interface CleaningModelInfo {
  report: CleaningReport | null;
  in_use: ModelsInUse;
}
