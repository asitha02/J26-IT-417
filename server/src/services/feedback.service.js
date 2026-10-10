const Video = require('../models/Video');
const Comment = require('../models/Comment');
const FeedbackAnalysis = require('../models/FeedbackAnalysis');
const analyzer = require('./analyzers');
const { EMOTIONS } = require('./analyzers/constants');
const fusion = require('./fusion.service');
const recommendations = require('./recommendation.service');

const round1 = (n) => Math.round(n * 10) / 10;

async function classifyPending(videoIds, force) {
  const filter = { videoId: { $in: videoIds }, ...(force ? {} : { analyzed: { $ne: true } }) };
  const pending = await Comment.find(filter).select('cleanText').lean();
  if (!pending.length) return 0;

  const results = await analyzer.analyze(pending.map((c) => ({ id: String(c._id), text: c.cleanText })));
  await Comment.bulkWrite(
    results.map((r) => ({
      updateOne: {
        filter: { _id: r.id },
        update: { $set: { analyzed: true, sentiment: r.sentiment, emotions: r.emotions, isQuestion: r.isQuestion } },
      },
    }))
  );
  return pending.length;
}

function summarise(comments) {
  const total = comments.length;
  const sentiments = { positive: 0, negative: 0, neutral: 0 };
  const emotions = Object.fromEntries(EMOTIONS.map((e) => [e, 0]));
  for (const c of comments) {
    sentiments[c.sentiment || 'neutral'] += 1;
    (c.emotions || []).forEach((e) => { if (e in emotions) emotions[e] += 1; });
  }
  const pct = (n) => (total ? round1((n / total) * 100) : 0);
  return {
    total_comments_analyzed: total,
    overall_sentiment_distribution: {
      positive: pct(sentiments.positive), negative: pct(sentiments.negative), neutral: pct(sentiments.neutral),
    },
    dominant_emotions: Object.entries(emotions)
      .filter(([, n]) => n > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([e]) => e.toLowerCase()),
  };
}

/** Full pipeline: classify -> fuse with video knowledge -> recommend -> persist. */
exports.analyze = async ({ videoIds, force = false }) => {
  const videos = await Video.find({ videoId: { $in: videoIds } }).lean();
  const missing = videoIds.filter((id) => !videos.some((v) => v.videoId === id));
  if (missing.length) {
    const err = new Error(`Unknown video(s): ${missing.join(', ')}. Create them via POST /api/videos first.`);
    err.status = 404;
    throw err;
  }

  await classifyPending(videoIds, force);

  const comments = await Comment.find({ videoId: { $in: videoIds }, analyzed: true }).lean();
  const byVideo = new Map();
  comments.forEach((c) => byVideo.set(c.videoId, [...(byVideo.get(c.videoId) || []), c]));

  const analytics_summary = summarise(comments);
  const insights = fusion.fuse(videos, byVideo);
  const actionable_recommendations = await recommendations.generate(insights, analytics_summary);

  const result = {
    analytics_summary,
    content_gaps_and_insights: insights.map(({ topic_or_timestamp, detected_issue_or_interest, supporting_evidence }) => ({
      topic_or_timestamp, detected_issue_or_interest, supporting_evidence,
    })),
    actionable_recommendations,
  };
  const saved = await FeedbackAnalysis.create({ videoIds, analyzer: analyzer.name, result });
  return { id: saved._id, analyzer: analyzer.name, ...result };
};

exports.getById = (id) => FeedbackAnalysis.findById(id).lean();
exports.latestForVideo = (videoId) => FeedbackAnalysis.findOne({ videoIds: videoId }).sort({ createdAt: -1 }).lean();
