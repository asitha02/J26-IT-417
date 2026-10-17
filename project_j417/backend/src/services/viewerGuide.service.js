const Anthropic = require('@anthropic-ai/sdk');
const { anthropicApiKey, anthropicModel, analyzer } = require('../config/env');
const logger = require('../utils/logger');

const useLLM = analyzer === 'llm' || (analyzer === 'auto' && Boolean(anthropicApiKey));
const SAMPLE_SIZE = 60;
let client;

const clip = (text, n = 200) => (text.length > n ? `${text.slice(0, n - 1)}…` : text);
const topLiked = (comments, n) => [...comments].sort((a, b) => (b.likeCount || 0) - (a.likeCount || 0)).slice(0, n);

/** Offline guide built only from the detected insights and the most-liked questions. */
function ruleBased(insights, comments) {
  const byKind = (kind) => insights.filter((i) => i.kind === kind);
  const loved = byKind('interest');
  const hard = [...byKind('confusion'), ...byKind('retention')];

  return {
    overview: loved.length
      ? `Viewers especially enjoyed ${loved.map((i) => i.topic_or_timestamp).join(', ')}.`
      : 'Viewers have shared mixed feedback on this video.',
    before_you_watch: [
      ...(hard.length ? ['Keep a pen handy - some parts are easier to follow if you pause and take notes.'] : []),
      ...(byKind('audio').length ? ['Background audio is strong in places; headphones and a quiet room help.'] : []),
    ],
    watch_out_for: hard.map((i) => ({
      topic: i.topic_or_timestamp,
      tip: i.kind === 'confusion'
        ? 'Other viewers found this part confusing. Watch it slowly or re-watch it once.'
        : 'Many viewers stop watching here. Stay with it - or skim, then come back.',
    })),
    highlights: loved.map((i) => ({ topic: i.topic_or_timestamp, why: 'Viewers were enthusiastic and curious about this part.' })),
    common_questions: topLiked(comments.filter((c) => c.isQuestion), 5).map((c) => clip(c.cleanText)),
  };
}

async function llmBased(insights, summary, comments) {
  client ||= new Anthropic({ apiKey: anthropicApiKey });
  const sample = topLiked(comments, SAMPLE_SIZE).map((c) => ({
    text: clip(c.cleanText), sentiment: c.sentiment, likes: c.likeCount || 0, question: Boolean(c.isQuestion),
  }));
  const response = await client.messages.create({
    model: anthropicModel,
    max_tokens: 8000,
    output_config: { effort: 'low' },
    system: `You write a short guide for FUTURE VIEWERS who are about to watch an educational video/podcast, using ONLY what past viewers said in the supplied comments and findings.
Comments may be English, Sinhala, or romanised Sinhala; write the guide in English.
Rules: never invent facts about the video's content that the comments do not support; keep every item to one short sentence; skip a field (empty array) rather than guess.
Respond with ONLY JSON:
{"overview":"","before_you_watch":[""],"watch_out_for":[{"topic":"","tip":""}],"highlights":[{"topic":"","why":""}],"common_questions":[""]}`,
    messages: [{ role: 'user', content: JSON.stringify({
      summary,
      findings: insights.map(({ kind, topic_or_timestamp, detected_issue_or_interest, supporting_evidence }) => ({ kind, topic_or_timestamp, detected_issue_or_interest, supporting_evidence })),
      comments: sample,
    }) }],
  });
  if (response.stop_reason === 'refusal') throw new Error('Model refused the request');
  const text = response.content.filter((b) => b.type === 'text').map((b) => b.text).join('');
  const g = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1));
  const strs = (a) => (Array.isArray(a) ? a.filter((x) => typeof x === 'string' && x.trim()) : []);
  const pairs = (a, k1, k2) => (Array.isArray(a) ? a.filter((x) => x && x[k1] && x[k2]).map((x) => ({ [k1]: String(x[k1]), [k2]: String(x[k2]) })) : []);
  if (typeof g.overview !== 'string' || !g.overview.trim()) throw new Error('No overview returned');
  return {
    overview: g.overview,
    before_you_watch: strs(g.before_you_watch),
    watch_out_for: pairs(g.watch_out_for, 'topic', 'tip'),
    highlights: pairs(g.highlights, 'topic', 'why'),
    common_questions: strs(g.common_questions),
  };
}

exports.generate = async (insights, summary, comments) => {
  if (!comments.length) return null;
  if (useLLM) {
    try {
      return await llmBased(insights, summary, comments);
    } catch (err) {
      logger.warn(`LLM viewer guide failed (${err.message}); using rule-based fallback`);
    }
  }
  return ruleBased(insights, comments);
};
