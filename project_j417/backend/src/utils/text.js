const SINHALA = /[\u0D80-\u0DFF]/;
const LATIN = /[A-Za-z]/;

/** Normalise raw comment text: strip HTML, URLs, zero-width chars, collapse whitespace. */
function cleanText(raw = '') {
  return String(raw)
    .normalize('NFKC')
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;|&#39;/g, "'")
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** 'si' (Sinhala script), 'en' (Latin script), 'mixed' (code-switched) or 'other'. */
function detectLanguage(text) {
  const si = SINHALA.test(text);
  const en = LATIN.test(text);
  if (si && en) return 'mixed';
  if (si) return 'si';
  if (en) return 'en';
  return 'other';
}

/** First "mm:ss" or "h:mm:ss" reference in the comment, in seconds (or null). */
function extractTimestamp(text) {
  const m = /\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b/.exec(text);
  if (!m) return null;
  const [, h, mm, ss] = m;
  if (Number(ss) > 59) return null;
  return Number(h || 0) * 3600 + Number(mm) * 60 + Number(ss);
}

/** Unicode-aware tokenizer (keeps Sinhala combining marks together). */
function tokenize(text) {
  return (String(text).toLowerCase().match(/[\p{L}\p{M}\p{N}]+/gu) || []);
}

module.exports = { cleanText, detectLanguage, extractTimestamp, tokenize };
