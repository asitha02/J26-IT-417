// Usage (server must be running): npm run sample
const sample = require('../samples/sample-feedback.json');

const base = process.env.API_URL || 'http://localhost:5000/api';

async function call(method, path, body) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${JSON.stringify(json)}`);
  return json.data;
}

(async () => {
  await call('POST', '/videos', sample.video);
  console.log('comments:', await call('POST', `/videos/${sample.video.videoId}/comments`, { comments: sample.comments }));
  const result = await call('POST', '/feedback/analyze', { videoId: sample.video.videoId });
  console.log(JSON.stringify(result, null, 2));
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
