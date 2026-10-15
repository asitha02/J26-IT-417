import type { AnalysisResponse, RecommendationType } from '@/types/feedback';

const TYPE_CLASS: Record<RecommendationType, string> = {
  'Content Expansion': 'tag-expansion',
  Clarification: 'tag-clarification',
  'Content Structuring': 'tag-structuring',
  'Audio Alignment': 'tag-audio',
};

export function ResultView({ result }: { result: AnalysisResponse }) {
  const { analytics_summary: s } = result;
  const dist = s.overall_sentiment_distribution;

  return (
    <div className="result">
      <section className="card">
        <h2>Audience summary</h2>
        <p className="muted">
          {s.total_comments_analyzed} comments analysed · analyzer:{' '}
          <strong>{result.analyzer === 'llm' ? 'Claude' : 'keyword rules (offline)'}</strong>
        </p>
        <div className="bar" role="img" aria-label="Sentiment distribution">
          <span className="seg pos" style={{ width: `${dist.positive}%` }} />
          <span className="seg neu" style={{ width: `${dist.neutral}%` }} />
          <span className="seg neg" style={{ width: `${dist.negative}%` }} />
        </div>
        <div className="legend">
          <span><i className="dot pos" /> Positive {dist.positive}%</span>
          <span><i className="dot neu" /> Neutral {dist.neutral}%</span>
          <span><i className="dot neg" /> Negative {dist.negative}%</span>
        </div>
        <p>
          Dominant emotions:{' '}
          {s.dominant_emotions.length ? s.dominant_emotions.map((e) => <span key={e} className="chip">{e}</span>) : '—'}
        </p>
      </section>

      <section className="card">
        <h2>Content gaps &amp; insights</h2>
        {result.content_gaps_and_insights.length === 0 && <p className="muted">No significant gaps detected.</p>}
        <ul className="list">
          {result.content_gaps_and_insights.map((i, idx) => (
            <li key={idx}>
              <strong>{i.topic_or_timestamp}</strong>
              <div>{i.detected_issue_or_interest}</div>
              <div className="muted">{i.supporting_evidence}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Recommendations</h2>
        {result.actionable_recommendations.length === 0 && <p className="muted">Nothing to recommend yet.</p>}
        <ul className="list">
          {result.actionable_recommendations.map((r, idx) => (
            <li key={idx}>
              <span className={`tag ${TYPE_CLASS[r.recommendation_type]}`}>{r.recommendation_type}</span>
              <div>{r.action_item}</div>
              <div className="muted">Why: {r.rationale}</div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
