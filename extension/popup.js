const DEFAULT_BASE = 'http://localhost:5173';
const $ = (id) => document.getElementById(id);

function isYouTubeVideo(raw) {
  try {
    const u = new URL(raw);
    if (u.hostname === 'youtu.be') return u.pathname.length > 1;
    const yt = u.hostname === 'youtube.com' || u.hostname.endsWith('.youtube.com');
    return yt && ((u.pathname === '/watch' && u.searchParams.has('v')) || /^\/(shorts|live|embed)\//.test(u.pathname));
  } catch {
    return false;
  }
}

async function getBase() {
  const { baseUrl } = await chrome.storage.sync.get('baseUrl');
  return (baseUrl || DEFAULT_BASE).replace(/\/+$/, '');
}

async function openDashboard(videoUrl, limit) {
  const base = await getBase();
  const query = videoUrl ? `/?url=${encodeURIComponent(videoUrl)}&limit=${encodeURIComponent(limit)}` : '/';
  await chrome.tabs.create({ url: base + query });
  window.close();
}

(async function init() {
  $('base-url').value = await getBase();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url && isYouTubeVideo(tab.url)) {
    $('on-video').hidden = false;
    $('video-title').textContent = (tab.title || tab.url).replace(/ - YouTube$/, '');
    $('analyse').addEventListener('click', () => openDashboard(tab.url, $('limit').value));
  } else {
    $('off-video').hidden = false;
    $('analyse-manual').addEventListener('click', () => {
      const value = $('manual-url').value.trim();
      if (isYouTubeVideo(value)) openDashboard(value, '5');
      else $('manual-url').style.borderColor = '#dc2626'; // not a YouTube video link
    });
  }

  $('open-dashboard').addEventListener('click', () => openDashboard());

  $('base-url').addEventListener('change', async () => {
    const value = $('base-url').value.trim();
    await chrome.storage.sync.set({ baseUrl: value || DEFAULT_BASE });
    $('saved').hidden = false;
  });
})();
