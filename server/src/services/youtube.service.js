const { youtubeApiKey } = require('../config/env');

const API = 'https://www.googleapis.com/youtube/v3';

const fail = (message, status) => Object.assign(new Error(message), { status });

async function yt(path, params) {
  if (!youtubeApiKey) throw fail('YOUTUBE_API_KEY is not configured in server/.env', 400);
  const url = new URL(`${API}/${path}`);
  url.search = new URLSearchParams({ ...params, key: youtubeApiKey });
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const reason = body?.error?.errors?.[0]?.reason;
    if (reason === 'commentsDisabled') throw fail('Comments are disabled on this video', 400);
    throw fail(`YouTube API error ${res.status}${reason ? ` (${reason})` : ''}`, res.status === 404 ? 404 : 502);
  }
  return res.json();
}

/** Accepts a watch/share/shorts/embed URL or a bare 11-char video id. */
exports.parseVideoId = (input = '') => {
  const s = input.trim();
  if (/^[\w-]{11}$/.test(s)) return s;
  try {
    const u = new URL(s);
    if (u.hostname === 'youtu.be') return u.pathname.slice(1, 12);
    if (u.searchParams.get('v')) return u.searchParams.get('v');
    const m = u.pathname.match(/\/(?:shorts|embed|live)\/([\w-]{11})/);
    if (m) return m[1];
  } catch {
    /* not a URL */
  }
  throw fail('Could not find a YouTube video id in the given URL', 400);
};

const parseDuration = (iso = '') => {
  const m = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(iso);
  return m ? Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0) : undefined;
};

/** Chapter lines in the description ("0:00 Intro") become time-aligned topics. */
function chaptersFrom(description = '') {
  const found = [];
  for (const line of description.split('\n')) {
    const m = /^\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-–—:|]?\s*(.+?)\s*$/.exec(line);
    if (m) found.push({ name: m[4], startSec: Number(m[1] || 0) * 3600 + Number(m[2]) * 60 + Number(m[3]) });
  }
  return found.length >= 2 ? found.sort((a, b) => a.startSec - b.startSec) : [];
}

exports.fetchVideoMeta = async (videoId) => {
  const data = await yt('videos', { part: 'snippet,contentDetails,statistics', id: videoId });
  const item = data.items?.[0];
  if (!item) throw fail('Video not found on YouTube', 404);
  return {
    videoId,
    title: item.snippet.title,
    durationSec: parseDuration(item.contentDetails.duration),
    views: Number(item.statistics?.viewCount) || undefined,
    topics: chaptersFrom(item.snippet.description),
  };
};

/** Top-level comments, newest/most relevant first, up to maxPages * 100. */
exports.fetchComments = async (videoId, maxPages = 5) => {
  const comments = [];
  let pageToken;
  for (let page = 0; page < maxPages; page += 1) {
    const data = await yt('commentThreads', {
      part: 'snippet', videoId, maxResults: '100', textFormat: 'plainText', order: 'relevance',
      ...(pageToken && { pageToken }),
    });
    for (const item of data.items || []) {
      const s = item.snippet.topLevelComment.snippet;
      comments.push({
        commentId: item.snippet.topLevelComment.id,
        text: s.textDisplay,
        author: s.authorDisplayName,
        likeCount: s.likeCount,
        publishedAt: s.publishedAt,
      });
    }
    pageToken = data.nextPageToken;
    if (!pageToken) break;
  }
  return comments;
};
