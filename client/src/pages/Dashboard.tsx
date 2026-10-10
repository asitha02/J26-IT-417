import { useCallback, useEffect, useState } from 'react';
import { ResultView } from '@/components/ResultView';
import { feedbackService } from '@/services/feedback.service';
import { videoService } from '@/services/video.service';
import type { AnalysisResponse, VideoSummary } from '@/types/feedback';

export default function Dashboard() {
  const [url, setUrl] = useState('');
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
      const imported = await videoService.importFromUrl(url.trim());
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
