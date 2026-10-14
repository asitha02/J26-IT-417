const { modelUrl } = require('../../config/env');
const logger = require('../../utils/logger');
const lexicon = require('./lexicon.analyzer');
const { EMOTIONS, SENTIMENTS } = require('./constants');

const BATCH_SIZE = 256;

async function predictBatch(batch) {
  const res = await fetch(`${modelUrl}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: batch.map(({ id, text }) => ({ id: String(id), text })) }),
    signal: AbortSignal.timeout(120000),
  });
  if (!res.ok) throw new Error(`model service responded ${res.status}`);
  const { results } = await res.json();
  const byId = new Map(results.map((r) => [String(r.id), r]));
  return batch.map((item) => {
    const r = byId.get(String(item.id));
    if (!r) return null;
    return {
      id: item.id,
      sentiment: SENTIMENTS.includes(r.sentiment) ? r.sentiment : 'neutral',
      emotions: (r.emotions || []).filter((e) => EMOTIONS.includes(e)),
      isQuestion: Boolean(r.isQuestion),
    };
  });
}

exports.name = 'model';

exports.analyze = async (items) => {
  const out = [];
  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    let results;
    try {
      results = await predictBatch(batch);
    } catch (err) {
      logger.warn(`Model batch failed (${err.message}); using lexicon fallback for ${batch.length} comments`);
      results = batch.map(() => null);
    }
    const missing = batch.filter((_, idx) => !results[idx]);
    const fallback = missing.length ? await lexicon.analyze(missing) : [];
    let f = 0;
    out.push(...results.map((r) => r || fallback[f++]));
  }
  return out;
};
