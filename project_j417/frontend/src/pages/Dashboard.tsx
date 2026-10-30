import { useCallback, useEffect, useRef, useState } from 'react';
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

  const importAndAnalyzeUrl = (target: string, pages: CommentLimit) =>
    run(async () => {
      setStatus('Fetching video and comments from YouTube…');
      const imported = await videoService.importFromUrl(target, pages);
      const id = imported.video.videoId;
      setSelected(id);
      setStatus(`Imported ${imported.comments.inserted} new comments. Analysing…`);
      setResult(await feedbackService.analyze(id));
      await refresh();
      setUrl('');
    });

  const importAndAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) void importAndAnalyzeUrl(url.trim(), limit);
  };

  // Opened from the browser extension: /?video=<youtube link>&limit=<pages|all>
  const autoStarted = useRef(false);
  useEffect(() => {
    if (autoStarted.current) return; // StrictMode runs effects twice in dev
    const params = new URLSearchParams(window.location.search);
    const target = params.get('video');
    if (!target) return;
    autoStarted.current = true;
    const raw = params.get('limit');
    const pages: CommentLimit = raw === 'all' ? 'all' : Number(raw) > 0 ? Number(raw) : 5;
    setUrl(target);
    setLimit(pages);
    window.history.replaceState(null, '', window.location.pathname);
    void importAndAnalyzeUrl(target, pages);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedTitle = videos.find((v) => v.videoId === selected)?.title;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <span className="logo" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              <path d="M8 9h8M8 13h5" />
            </svg>
          </span>
          <div>
            <h1>Audience Feedback Mining</h1>
            <p>Turn YouTube comments into content recommendations</p>
          </div>
        </div>
      </header>

      <main className="container">
        <form className="card analyze" onSubmit={importAndAnalyze}>
          <h2>Analyse a video</h2>
          <p className="muted">Paste a YouTube link. Comments are fetched, analysed and turned into recommendations.</p>
          <div className="row">
            <div className="field">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5" />
                <path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5" />
              </svg>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=…"
                aria-label="YouTube video URL"
                disabled={busy}
              />
            </div>
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
          </div>

          {busy && (
            <div className="status" role="status">
              <span className="spinner" aria-hidden="true" />
              {status || 'Working…'}
            </div>
          )}
          {error && <p className="error" role="alert">{error}</p>}
        </form>

        <div className="layout">
          <aside className="card sidebar">
            <div className="card-head">
              <h3 className="card-title">Videos</h3>
              <span className="badge">{videos.length}</span>
            </div>
            {videos.length === 0 && <p className="muted">No videos yet. Import one above.</p>}
            <ul className="video-list">
              {videos.map((v) => (
                <li key={v.videoId} className={`video-item ${v.videoId === selected ? 'active' : ''}`}>
                  <div className="video-title">{v.title || v.videoId}</div>
                  <div className="video-meta">
                    {v.commentCount.toLocaleString()} comments{v.topics?.length ? ` · ${v.topics.length} chapters` : ''}
                  </div>
                  <div className="video-actions">
                    <button type="button" className="small" onClick={() => void analyze(v.videoId)} disabled={busy}>
                      View analysis
                    </button>
                    <button type="button" className="small secondary" onClick={() => void analyze(v.videoId, true)} disabled={busy}>
                      Re-analyse
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </aside>

          <section className="content">
            {result ? (
              <ResultView result={result} title={selectedTitle} />
            ) : (
              <div className="card empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M3 3v18h18" />
                  <path d="M7 15l4-4 3 3 5-6" />
                </svg>
                <strong>No analysis yet</strong>
                Import a video or choose one from the list to see audience insights.
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="footer">
        Sentiment is analysed by the selected analyzer (XLM-RoBERTa, Claude or keyword rules, shown in each result); recommendations are generated by Claude when available. No custom model is trained.
      </footer>
    </>
  );
}
