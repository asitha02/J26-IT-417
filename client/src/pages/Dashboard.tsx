import { useCallback, useEffect, useState } from 'react';
import { ResultView } from '@/components/ResultView';
import { feedbackService } from '@/services/feedback.service';
import { videoService } from '@/services/video.service';
import type { AnalysisResponse, CommentLimit, VideoSummary } from '@/types/feedback';

const LIMITS: { label: string; value: CommentLimit }[] = [
  { label: '100 comments', value: 1 },
  { label: '500 comments', value: 5 },
  { label: '1,000 comments', value: 10 },
  { label: '5,000 comments', value: 50 },
  { label: 'All comments', value: 'all' },
];

export default function Dashboard() {
  const [url, setUrl] = useState('');
  const [limit, setLimit] = useState<CommentLimit>(5);
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const list = await videoService.list();
    setVideos(list);
    return list;
  }, []);

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, [refresh]);

  const run = async (task: () => Promise<void>) => {
    setBusy(true);
    setError('');
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setBusy(false);
      setStatus('');
    }
  };

  const analyze = (videoId: string, force = false) =>
    run(async () => {
      setSelected(videoId);
      setStatus('Analysing comments…');
      setResult(await feedbackService.analyze(videoId, force));
    });

  const importAndAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    void run(async () => {
      setStatus('Fetching video and comments from YouTube…');
      const imported = await videoService.importFromUrl(url.trim(), limit);
      const id = imported.video.videoId;
      setSelected(id);
      setStatus(`Imported ${imported.comments.inserted} new comments. Analysing…`);
      setResult(await feedbackService.analyze(id));
      await refresh();
      setUrl('');
    });
  };

  return (
    <main className="container">
      <h1>Audience Feedback Mining</h1>
      <p className="muted">Paste a YouTube link: comments are fetched automatically, analysed, and turned into recommendations.</p>

      <form className="card row" onSubmit={importAndAnalyze}>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
          aria-label="YouTube video URL"
          disabled={busy}
        />
        <select
          value={String(limit)}
          onChange={(e) => setLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
          aria-label="Number of comments to fetch"
          disabled={busy}
        >
          {LIMITS.map((l) => (
            <option key={l.label} value={String(l.value)}>{l.label}</option>
          ))}
        </select>
        <button type="submit" disabled={busy || !url.trim()}>Import &amp; analyse</button>
      </form>

      {busy && <p className="status">{status || 'Working…'}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <section className="card">
        <h2>Videos</h2>
        {videos.length === 0 && <p className="muted">No videos yet. Import one above.</p>}
        <ul className="list">
          {videos.map((v) => (
            <li key={v.videoId} className={v.videoId === selected ? 'active' : ''}>
              <div className="row between">
                <div>
                  <strong>{v.title || v.videoId}</strong>
                  <div className="muted">{v.commentCount} comments{v.topics?.length ? ` · ${v.topics.length} chapters` : ''}</div>
                </div>
                <div className="row">
                  <button type="button" onClick={() => void analyze(v.videoId)} disabled={busy}>View analysis</button>
                  <button type="button" className="secondary" onClick={() => void analyze(v.videoId, true)} disabled={busy}>
                    Re-analyse
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {result && <ResultView result={result} />}
    </main>
  );
}
