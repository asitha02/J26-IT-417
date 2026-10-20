const { bertServiceUrl } = require('../../config/env');
const logger = require('../../utils/logger');
const lexicon = require('./lexicon.analyzer');
const { SENTIMENTS } = require('./constants');

const BATCH_SIZE = 64;

// Sentiment comes from the RoBERTa service (ml_service/). Emotions and question detection stay rule-based,
// since the sentiment model does not output them.
async function sentimentBatch(batch) {
  const res = await fetch(`${bertServiceUrl}/sentiment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: batch.map(({ id, text }) => ({ id: String(id), text })) }),
  });
  if (!res.ok) throw new Error(`BERT service responded ${res.status}`);
  const { results } = await res.json();
  return new Map(results.map((r) => [String(r.id), r.sentiment]));
}

exports.name = 'bert';

exports.analyze = async (items) => {
  const base = await lexicon.analyze(items);
  const out = [];
  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    const part = base.slice(i, i + BATCH_SIZE);
    let sentiments = new Map();
    try {
      sentiments = await sentimentBatch(batch);
    } catch (err) {
      logger.warn(`BERT batch failed (${err.message}); using lexicon sentiment for ${batch.length} comments`);
    }
    part.forEach((r) => {
      const s = sentiments.get(String(r.id));
      out.push(SENTIMENTS.includes(s) ? { ...r, sentiment: s } : r);
    });
  }
  return out;
};
