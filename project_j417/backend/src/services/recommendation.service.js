const Anthropic = require('@anthropic-ai/sdk');
const { anthropicApiKey, anthropicModel, analyzer } = require('../config/env');
const logger = require('../utils/logger');

const TYPES = ['Content Expansion', 'Clarification', 'Content Structuring', 'Audio Alignment'];
const useLLM = analyzer === 'llm' || (analyzer === 'auto' && Boolean(anthropicApiKey));
let client;

/** Deterministic, evidence-linked recommendations derived from the detected insights. */
function ruleBased(insights) {
  return insights.map((i) => {
    const t = i.topic_or_timestamp;
    switch (i.kind) {
      case 'confusion':
        return { recommendation_type: 'Clarification', action_item: `Re-explain "${i.topic}" at a slower pace with a worked example or on-screen summary, and add a short recap at the end of the segment.`, rationale: i.supporting_evidence };
      case 'questions':
        return { recommendation_type: 'Content Expansion', action_item: `Answer the open questions about "${i.topic}" in a pinned comment or a short Q&A segment in the next episode.`, rationale: i.supporting_evidence };
      case 'interest':
        return { recommendation_type: 'Content Expansion', action_item: `Plan a deeper follow-up episode on "${i.topic}" - the audience is asking for more.`, rationale: i.supporting_evidence };
      case 'retention':
        return { recommendation_type: 'Content Structuring', action_item: `Restructure ${t}: shorten it, split it into smaller chunks, or open with the key takeaway to stop the viewer drop-off.`, rationale: i.supporting_evidence };
      case 'audio':
        return { recommendation_type: 'Audio Alignment', action_item: `Soften or remove the background audio around ${t}, or choose a calmer track so it does not compete with the explanation.`, rationale: i.supporting_evidence };
      default:
        return { recommendation_type: 'Clarification', action_item: `Review ${t}: reception was negative - revisit the framing and address the main objections.`, rationale: i.supporting_evidence };
    }
  });
}

async function llmBased(insights, summary) {
  client ||= new Anthropic({ apiKey: anthropicApiKey });
  const response = await client.messages.create({
    model: anthropicModel,
    max_tokens: 16000,
    output_config: { effort: 'medium' },
    system: `You advise creators of educational podcasts/videos. Using ONLY the supplied findings, write concrete, actionable recommendations.
Rules: every recommendation must be grounded in one or more findings (cite the numbers in "rationale"); do not invent evidence.
"recommendation_type" must be one of: ${TYPES.join(', ')}.
Respond with ONLY JSON: {"actionable_recommendations":[{"recommendation_type":"","action_item":"","rationale":""}]}`,
    messages: [{ role: 'user', content: JSON.stringify({ summary, findings: insights.map(({ kind, ...rest }) => ({ kind, ...rest })) }) }],
  });
  if (response.stop_reason === 'refusal') throw new Error('Model refused the request');
  const text = response.content.filter((b) => b.type === 'text').map((b) => b.text).join('');
  const parsed = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1));
  const recs = (parsed.actionable_recommendations || []).filter(
    (r) => TYPES.includes(r.recommendation_type) && r.action_item && r.rationale
  );
  if (!recs.length) throw new Error('No valid recommendations returned');
  return recs;
}

exports.generate = async (insights, summary) => {
  if (!insights.length) return [];
  if (useLLM) {
    try {
      return await llmBased(insights, summary);
    } catch (err) {
      logger.warn(`LLM recommendations failed (${err.message}); using rule-based fallback`);
    }
  }
  return ruleBased(insights);
};
