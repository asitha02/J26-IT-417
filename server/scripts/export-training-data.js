// Usage (from server/): npm run export-training
// Writes analyzed comments to ../training/data/comments.jsonl for model training.
const fs = require('fs');
const path = require('path');
const mongoose = require('mongoose');
const { mongoUri, mongoDb } = require('../src/config/env');

const OUT = path.join(__dirname, '..', '..', 'training', 'data', 'comments.jsonl');

(async () => {
  await mongoose.connect(mongoUri, { dbName: mongoDb, serverSelectionTimeoutMS: 8000 });
  const docs = await mongoose.connection.db
    .collection('comments')
    .find({ analyzed: true, sentiment: { $exists: true } })
    .project({ _id: 0, videoId: 1, commentId: 1, text: 1, language: 1, sentiment: 1, emotions: 1, isQuestion: 1 })
    .toArray();

  // Drop empty and exact-duplicate texts so the same comment cannot land in both train and test.
  const seen = new Set();
  const rows = [];
  for (const d of docs) {
    const text = (d.text || '').trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    rows.push({
      videoId: d.videoId,
      commentId: d.commentId,
      text,
      language: d.language || 'other',
      sentiment: d.sentiment,
      emotions: d.emotions || [],
      isQuestion: Boolean(d.isQuestion),
    });
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
  console.log(`exported ${rows.length} comments (${docs.length - rows.length} duplicates/empty skipped) -> ${OUT}`);
  await mongoose.connection.close();
})().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
