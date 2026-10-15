import type { AnalysisResponse, RecommendationType } from '@/types/feedback';

const TYPE_CLASS: Record<RecommendationType, string> = {
  'Content Expansion': 'tag-expansion',
  Clarification: 'tag-clarification',
  'Content Structuring': 'tag-structuring',
  'Audio Alignment': 'tag-audio',
};

const ANALYZER_LABELS: Record<string, string> = {
  llm: 'Claude',
  lexicon: 'Keyword rules (offline)',
};

export function ResultView({ result, title }: { result: AnalysisResponse; title?: string }) {
  const { analytics_summary: s } = result;
  const dist = s.overall_sentiment_distribution;

  return (
    <>
      <section className="card">
        <div className="result-head">
          <div>
            <h2>{title || 'Audience summary'}</h2>
            <p className="muted">Audience summary</p>
          </div>
          <span className="badge">Analyzer: {ANALYZER_LABELS[result.analyzer] ?? result.analyzer}</span>
        </div>

        <div className="tiles">
          <div className="tile">
            <div className="tile-label">Comments</div>
            <div className="tile-value">{s.total_comments_analyzed.toLocaleString()}</div>
          </div>
          <div className="tile">
            <div className="tile-label">Positive</div>
            <div className="tile-value pos">{dist.positive}%</div>
          </div>
          <div className="tile">
            <div className="tile-label">Neutral</div>
            <div className="tile-value">{dist.neutral}%</div>
          </div>
          <div className="tile">
            <div className="tile-label">Negative</div>
            <div className="tile-value neg">{dist.negative}%</div>
          </div>
        </div>

        <div className="bar" role="img" aria-label="Sentiment distribution">
          <span className="seg pos" style={{ width: `${dist.positive}%` }} />
          <span className="seg neu" style={{ width: `${dist.neutral}%` }} />
          <span className="seg neg" style={{ width: `${dist.negative}%` }} />
        </div>
        <div className="legend">
          <span><i className="dot pos" />Positive</span>
          <span><i className="dot neu" />Neutral</span>
          <span><i className="dot neg" />Negative</span>
        </div>

        <div className="emotions">
          <span>Dominant emotions</span>
          {s.dominant_emotions.length ? s.dominant_emotions.map((e) => <span key={e} className="chip">{e}</span>) : '—'}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h3 className="card-title">Content gaps &amp; insights</h3>
          <span className="badge">{result.content_gaps_and_insights.length}</span>
        </div>
        {result.content_gaps_and_insights.length === 0 && <p className="muted">No significant gaps detected.</p>}
        <ul className="items">
          {result.content_gaps_and_insights.map((i, idx) => (
            <li key={idx} className="item insight">
              <div className="item-title">{i.topic_or_timestamp}</div>
              <div className="item-body">{i.detected_issue_or_interest}</div>
              <div className="muted">{i.supporting_evidence}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <div className="card-head">
          <h3 className="card-title">Recommendations</h3>
          <span className="badge">{result.actionable_recommendations.length}</span>
        </div>
        {result.actionable_recommendations.length === 0 && <p className="muted">Nothing to recommend yet.</p>}
        <ul className="items">
          {result.actionable_recommendations.map((r, idx) => (
            <li key={idx} className={`item ${TYPE_CLASS[r.recommendation_type]}`}>
              <span className="tag">{r.recommendation_type}</span>
              <div className="item-body">{r.action_item}</div>
              <div className="muted">Why: {r.rationale}</div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
