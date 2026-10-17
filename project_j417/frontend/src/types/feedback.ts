/** Number of 100-comment pages to fetch from YouTube, or every page. */
export type CommentLimit = number | 'all';

export interface VideoSummary {
  videoId: string;
  title: string;
  durationSec?: number;
  views?: number;
  commentCount: number;
  topics?: { name: string; startSec: number }[];
}

export interface ImportResult {
  video: VideoSummary;
  comments: { received: number; inserted: number; duplicatesOrEmpty: number };
  chaptersFound: number;
}

export interface AnalyticsSummary {
  total_comments_analyzed: number;
  overall_sentiment_distribution: { positive: number; negative: number; neutral: number };
  dominant_emotions: string[];
}

export interface ContentInsight {
  topic_or_timestamp: string;
  detected_issue_or_interest: string;
  supporting_evidence: string;
}

export type RecommendationType =
  | 'Content Expansion'
  | 'Clarification'
  | 'Content Structuring'
  | 'Audio Alignment';

export interface Recommendation {
  recommendation_type: RecommendationType;
  action_item: string;
  rationale: string;
}

export interface ViewerGuide {
  overview: string;
  before_you_watch: string[];
  watch_out_for: { topic: string; tip: string }[];
  highlights: { topic: string; why: string }[];
  common_questions: string[];
}

export interface FeedbackResult {
  analytics_summary: AnalyticsSummary;
  content_gaps_and_insights: ContentInsight[];
  actionable_recommendations: Recommendation[];
  viewer_guide?: ViewerGuide | null;
}

export interface AnalysisResponse extends FeedbackResult {
  id: string;
  analyzer: 'llm' | 'lexicon';
  model?: string | null;
}
