// Measures sentiment accuracy against hand-labelled comments.
// Usage: npm run evaluate -- [--analyzer llm|lexicon|bert] [--file samples/labelled-comments.json]
// "llm" needs ANTHROPIC_API_KEY in .env and costs API credits; "lexicon" is free and offline; "bert" needs ml_service/ running.
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};

// Must be set before the analyzers load: env.js reads them once and requires a Mongo URI.
process.env.ANALYZER = opt('analyzer', 'llm');
process.env.MONGODB_URI ||= 'unused-by-this-script';

const analyzer = require('../src/services/analyzers');
const { SENTIMENTS } = require('../src/services/analyzers/constants');

const file = path.resolve(__dirname, '..', opt('file', 'samples/labelled-comments.json'));
const data = JSON.parse(fs.readFileSync(file, 'utf8')).filter((r) => SENTIMENTS.includes(r.sentiment));

(async () => {
  console.log(`Analyzer: ${analyzer.name} | file: ${path.basename(file)} | labelled comments: ${data.length}\n`);
  const items = data.map((r, i) => ({ id: String(i), text: r.text }));
  const predicted = await analyzer.analyze(items);

  const matrix = Object.fromEntries(SENTIMENTS.map((a) => [a, Object.fromEntries(SENTIMENTS.map((p) => [p, 0]))]));
  const wrong = [];
  data.forEach((row, i) => {
    const p = predicted[i].sentiment;
    matrix[row.sentiment][p] += 1;
    if (p !== row.sentiment) wrong.push({ text: row.text, actual: row.sentiment, predicted: p });
  });

  const correct = SENTIMENTS.reduce((n, s) => n + matrix[s][s], 0);
  console.log(`Accuracy: ${((correct / data.length) * 100).toFixed(1)}%  (${correct}/${data.length})\n`);

  console.log('Per class      precision  recall   F1     support');
  let f1Sum = 0;
  for (const s of SENTIMENTS) {
    const tp = matrix[s][s];
    const predictedAs = SENTIMENTS.reduce((n, a) => n + matrix[a][s], 0);
    const actual = SENTIMENTS.reduce((n, p) => n + matrix[s][p], 0);
    const precision = predictedAs ? tp / predictedAs : 0;
    const recall = actual ? tp / actual : 0;
    const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
    f1Sum += f1;
    console.log(`${s.padEnd(14)} ${precision.toFixed(2).padStart(9)} ${recall.toFixed(2).padStart(7)} ${f1.toFixed(2).padStart(6)} ${String(actual).padStart(8)}`);
  }
  console.log(`\nMacro F1: ${(f1Sum / SENTIMENTS.length).toFixed(2)}`);

  console.log('\nConfusion matrix (rows = actual, columns = predicted)');
  console.log(`${''.padEnd(10)}${SENTIMENTS.map((s) => s.padStart(10)).join('')}`);
  for (const a of SENTIMENTS) console.log(`${a.padEnd(10)}${SENTIMENTS.map((p) => String(matrix[a][p]).padStart(10)).join('')}`);

  if (wrong.length) {
    console.log(`\nMistakes (${wrong.length}):`);
    wrong.forEach((w) => console.log(`- [${w.actual} -> ${w.predicted}] ${w.text}`));
  }
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
