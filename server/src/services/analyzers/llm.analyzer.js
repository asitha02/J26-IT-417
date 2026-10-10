const Anthropic = require('@anthropic-ai/sdk');
const { anthropicApiKey, anthropicModel } = require('../../config/env');
const logger = require('../../utils/logger');
const lexicon = require('./lexicon.analyzer');
const { EMOTIONS, SENTIMENTS } = require('./constants');

const BATCH_SIZE = 40;
let client;
const getClient = () => (client ||= new Anthropic({ apiKey: anthropicApiKey }));

const SYSTEM = `You classify audience comments on educational videos and podcasts.
Comments may be in English, Sinhala (script), romanised Sinhala ("Singlish"), or code-switched mixes - interpret all of them.
For every comment return:
- "id": the id you were given
- "sentiment": one of ${SENTIMENTS.join(', ')}
- "emotions": zero or more of ${EMOTIONS.join(', ')} (only those clearly expressed)
- "is_question": true if the viewer is asking something
Respond with ONLY a JSON array of objects, one per input comment, no prose or markdown.`;

function extractJson(text, open, close) {
  const start = text.indexOf(open);
  const end = text.lastIndexOf(close);
  if (start === -1 || end === -1) throw new Error('No JSON in model response');
  return JSON.parse(text.slice(start, end + 1));
}

async function classifyBatch(batch) {
  const response = await getClient().messages.create({
    model: anthropicModel,
    max_tokens: 16000,
    output_config: { effort: 'low' },
    system: SYSTEM,
    messages: [{ role: 'user', content: JSON.stringify(batch.map(({ id, text }) => ({ id, text }))) }],
  });
  if (response.stop_reason === 'refusal') throw new Error('Model refused the request');
  const text = response.content.filter((b) => b.type === 'text').map((b) => b.text).join('');
  const parsed = extractJson(text, '[', ']');
  const byId = new Map(parsed.map((r) => [String(r.id), r]));

  return batch.map((item) => {
    const r = byId.get(String(item.id));
    if (!r) return null;
    return {
      id: item.id,
      sentiment: SENTIMENTS.includes(r.sentiment) ? r.sentiment : 'neutral',
      emotions: (r.emotions || []).filter((e) => EMOTIONS.includes(e)),
      isQuestion: Boolean(r.is_question),
    };
  });
}

exports.name = 'llm';
exports.analyze = async (items) => {
  const out = [];
  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    let results;
    try {
      results = await classifyBatch(batch);
    } catch (err) {
      logger.warn(`LLM batch failed (${err.message}); using lexicon fallback for ${batch.length} comments`);
      results = batch.map(() => null);
    }
    const missing = batch.filter((_, idx) => !results[idx]);
    const fallback = missing.length ? await lexicon.analyze(missing) : [];
    let f = 0;
    results.forEach((r, idx) => out.push(r || fallback[f++]));
  }
  return out;
};
