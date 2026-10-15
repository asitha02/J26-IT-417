// Offline fallback: keyword rules for English, Sinhala script and romanised Sinhala ("Singlish").
// Much weaker than the LLM analyzer, but works with no API key.
const POSITIVE = [
  'great', 'good', 'amazing', 'awesome', 'love', 'helpful', 'excellent', 'thanks', 'thank', 'best',
  'brilliant', 'nice', 'perfect', 'informative', 'well explained', 'superb',
  'ස්තූතියි', 'නියමයි', 'සුපිරි', 'ලස්සනයි', 'හොඳයි', 'වටිනවා',
  'niyamai', 'supiri', 'hodai', 'godak hodai', 'sthuthi', 'isthuti',
];
const NEGATIVE = [
  'bad', 'boring', 'confusing', 'waste', 'worst', 'terrible', 'hate', 'wrong', 'poor', 'useless',
  'annoying', 'unclear', 'too fast', 'too slow', 'not helpful',
  'නරකයි', 'අවුල්', 'එපා', 'narakai', 'awul', 'epa', 'bore',
];
const EMOTION_TERMS = {
  Confusion: ["don't understand", "didn't understand", 'confus', 'unclear', 'not clear', 'lost me', 'what do you mean',
    'තේරුණේ නැහැ', 'තේරෙන්නේ නෑ', 'තේරුනේ නෑ', 'terenne na', 'therenne na', 'terune na', 'awul'],
  Curiosity: ['how', 'why', 'what if', 'can you', 'could you', 'please explain', 'curious', 'wonder', 'any resource',
    'කොහොමද', 'ඇයි', 'මොකක්ද', 'kohomada', 'mokakda'],
  Agreement: ['agree', 'exactly', 'so true', 'correct', 'same here', 'well said', 'එකඟයි', 'ඒක ඇත්ත', 'eka aththa'],
  Disagreement: ['disagree', 'not true', 'incorrect', 'no way', 'i doubt', 'වැරදියි', 'waradi'],
  Frustration: ['frustrat', 'annoying', 'waste', 'ridiculous', 'too long', 'tired of', 'boring', 'කම්මැලි', 'bore'],
  Enthusiasm: ['love', 'amazing', 'awesome', "can't wait", 'more please', 'next part', 'excited', 'superb',
    '🔥', '❤', '😍', 'නියමයි', 'සුපිරි', 'supiri', 'niyamai'],
};
const QUESTION_START = /^(how|why|what|when|where|which|can|could|is|are|do|does|will)\b(?!')/i;

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const hit = (text, term) =>
  /^[a-z]/i.test(term) ? new RegExp(`\\b${esc(term)}`, 'i').test(text) : text.includes(term);
const count = (text, terms) => terms.filter((t) => hit(text, t)).length;

function analyzeOne(item) {
  const text = item.text.toLowerCase();
  const pos = count(text, POSITIVE);
  const neg = count(text, NEGATIVE);
  const emotions = Object.entries(EMOTION_TERMS)
    .filter(([, terms]) => count(text, terms) > 0)
    .map(([e]) => e);
  const isQuestion = /[?？]/.test(text) || QUESTION_START.test(text.trim());
  if (isQuestion && !emotions.includes('Curiosity') && !emotions.includes('Confusion')) emotions.push('Curiosity');

  let sentiment = 'neutral';
  if (pos > neg) sentiment = 'positive';
  else if (neg > pos) sentiment = 'negative';
  else if (emotions.includes('Frustration') || emotions.includes('Disagreement')) sentiment = 'negative';
  else if (emotions.includes('Enthusiasm') || emotions.includes('Agreement')) sentiment = 'positive';

  return { id: item.id, sentiment, emotions, isQuestion };
}

exports.name = 'lexicon';
exports.analyze = async (items) => items.map(analyzeOne);
