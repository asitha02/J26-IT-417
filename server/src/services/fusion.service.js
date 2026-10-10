const { tokenize } = require('../utils/text');
const { EMOTIONS } = require('./analyzers/constants');

const MIN_COMMENTS = 2; // ignore topics with less feedback than this
const CONFUSION_RATIO = 0.25;
const INTEREST_RATIO = 0.4;
const NEGATIVE_RATIO = 0.4;
const RETENTION_DROP_PTS = 10;
const AUDIO_INTENSITY = 0.6;

const pct = (n, d) => (d ? Math.round((n / d) * 1000) / 10 : 0);
const quote = (c) => `"${c.cleanText.length > 90 ? `${c.cleanText.slice(0, 87)}...` : c.cleanText}"`;

function normaliseTopics(video) {
  const topics = [...(video.topics || [])].sort((a, b) => a.startSec - b.startSec);
  return topics.map((t, i) => ({
    ...t,
    endSec: t.endSec ?? topics[i + 1]?.startSec ?? video.durationSec ?? Infinity,
  }));
}

/** Link a comment to a topic by its timestamp reference, else by keyword overlap. */
function topicFor(comment, topics) {
  if (comment.timestampSec != null) {
    const t = topics.find((x) => comment.timestampSec >= x.startSec && comment.timestampSec < x.endSec);
    if (t) return t;
  }
  const tokens = new Set(tokenize(comment.cleanText));
  let best = null;
  let bestScore = 0;
  for (const t of topics) {
    const keys = [...tokenize(t.name), ...(t.keywords || []).flatMap(tokenize)].filter((k) => k.length > 2);
    const score = keys.filter((k) => tokens.has(k)).length;
    if (score > bestScore) {
      best = t;
      bestScore = score;
    }
  }
  return best;
}

function retentionDrop(video, t) {
  const pts = (video.retention || [])
    .filter((p) => p.second >= t.startSec && p.second < t.endSec)
    .sort((a, b) => a.second - b.second);
  return pts.length >= 2 ? pts[0].pct - pts[pts.length - 1].pct : null;
}

function audioFor(video, t) {
  const overlap = (video.audioSignals || [])
    .filter((a) => a.startSec < t.endSec && (a.endSec ?? Infinity) > t.startSec)
    .sort((a, b) => (b.intensity || 0) - (a.intensity || 0));
  return overlap[0] || null;
}

/** Aggregate analysed comments per topic of one video. */
function buildTopicStats(video, comments) {
  const topics = normaliseTopics(video);
  const general = { name: 'General discussion', startSec: null, endSec: null };
  const stats = new Map();
  const slot = (t) => {
    if (!stats.has(t.name)) {
      stats.set(t.name, {
        topic: t, comments: [], sentiment: { positive: 0, negative: 0, neutral: 0 },
        emotions: Object.fromEntries(EMOTIONS.map((e) => [e, 0])), questions: [],
      });
    }
    return stats.get(t.name);
  };

  for (const c of comments) {
    const s = slot(topicFor(c, topics) || general);
    s.comments.push(c);
    s.sentiment[c.sentiment || 'neutral'] += 1;
    (c.emotions || []).forEach((e) => { if (e in s.emotions) s.emotions[e] += 1; });
    if (c.isQuestion) s.questions.push(c);
  }
  for (const s of stats.values()) {
    s.total = s.comments.length;
    s.retentionDrop = s.topic.startSec == null ? null : retentionDrop(video, s.topic);
    s.audio = s.topic.startSec == null ? null : audioFor(video, s.topic);
  }
  return [...stats.values()];
}

const label = (video, s, multi) =>
  `${multi ? `${video.title || video.videoId} › ` : ''}${s.topic.name}${
    s.topic.startSec != null ? ` (${Math.floor(s.topic.startSec / 60)}:${String(Math.floor(s.topic.startSec % 60)).padStart(2, '0')})` : ''
  }`;

const sampleOf = (s, pick) => s.comments.filter(pick).sort((a, b) => b.likeCount - a.likeCount).slice(0, 2).map(quote).join(' / ');

/** Detect gaps/interests. `kind` drives the recommendation type downstream. */
function findInsights(video, stats, multi) {
  const out = [];
  for (const s of stats) {
    if (s.total < MIN_COMMENTS) continue;
    const where = label(video, s, multi);
    const neg = s.sentiment.negative / s.total;
    const confusion = s.emotions.Confusion;

    if (confusion >= 2 && confusion / s.total >= CONFUSION_RATIO) {
      out.push({
        kind: 'confusion', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: 'Unclear explanation - viewers are confused',
        supporting_evidence: `${confusion}/${s.total} comments (${pct(confusion, s.total)}%) express confusion, e.g. ${sampleOf(s, (c) => c.emotions.includes('Confusion'))}`,
      });
    }
    if (s.questions.length >= 2) {
      out.push({
        kind: 'questions', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: 'Unaddressed audience questions / knowledge gap',
        supporting_evidence: `${s.questions.length} viewer questions, e.g. ${s.questions.slice(0, 2).map(quote).join(' / ')}`,
      });
    }
    const interest = s.emotions.Curiosity + s.emotions.Enthusiasm; // 'General' has no topic to expand on
    if (s.topic.startSec != null && interest / s.total >= INTEREST_RATIO && s.sentiment.positive / s.total >= 0.5) {
      out.push({
        kind: 'interest', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: 'High audience interest',
        supporting_evidence: `${pct(s.sentiment.positive, s.total)}% positive, ${s.emotions.Enthusiasm} enthusiastic and ${s.emotions.Curiosity} curious comments out of ${s.total}`,
      });
    }
    if (neg >= NEGATIVE_RATIO && confusion / s.total < CONFUSION_RATIO) {
      out.push({
        kind: 'negative', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: 'Negative reception',
        supporting_evidence: `${pct(s.sentiment.negative, s.total)}% negative (${s.emotions.Frustration} frustration, ${s.emotions.Disagreement} disagreement), e.g. ${sampleOf(s, (c) => c.sentiment === 'negative')}`,
      });
    }
    if (s.retentionDrop != null && s.retentionDrop >= RETENTION_DROP_PTS) {
      out.push({
        kind: 'retention', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: 'Viewer retention drops in this segment',
        supporting_evidence: `Retention falls ${Math.round(s.retentionDrop)} percentage points across the segment; ${s.total} comments, ${pct(s.sentiment.negative, s.total)}% negative`,
      });
    }
    if (s.audio && (s.audio.intensity || 0) >= AUDIO_INTENSITY && (neg >= 0.3 || confusion >= 2)) {
      out.push({
        kind: 'audio', topic: s.topic.name, topic_or_timestamp: where,
        detected_issue_or_interest: `Audio mood ("${s.audio.emotion}", intensity ${s.audio.intensity}) may not suit the content`,
        supporting_evidence: `Strong "${s.audio.emotion}" audio overlaps a segment with ${pct(s.sentiment.negative, s.total)}% negative sentiment and ${confusion} confusion comments`,
      });
    }
  }
  return out;
}

/** Fuse analysed comments with each video's knowledge topics, retention and audio signals. */
exports.fuse = (videos, commentsByVideo) => {
  const multi = videos.length > 1;
  const insights = [];
  for (const video of videos) {
    const stats = buildTopicStats(video, commentsByVideo.get(video.videoId) || []);
    insights.push(...findInsights(video, stats, multi));
  }
  return insights;
};
