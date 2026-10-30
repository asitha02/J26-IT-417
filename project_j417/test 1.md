# Component 3 – Panel Q&A (කෙටි උත්තර)

## 1. මගේ component එක මොකක්ද, ඇයි ඕන?
**Audience Feedback Mining and Evidence-Based Improvement Recommendations.**
YouTube comments (English / සිංහල / Singlish) auto කියවලා, creator ට **සාක්ෂි සහිත improvement recommendations** දෙනවා.
**ඇයි ඕන:** Comments සිය ගණනක් කියවන්න බැහැ. Views / likes වලින් **ඇයි** කියලා කියන්නේ නැහැ. අපි feedback loop එක වහනවා.

## 2. PP1 එකේ පෙන්නන්න key functions 2
1. **Comment import + analysis:** YouTube URL එකක් දුන්නම comments ගෙනල්ලා, sentiment / emotion / question හොයනවා (XLM-RoBERTa, Claude, lexicon).
2. **Fusion → Recommendations + Viewer Guide:** Comments, video topics, retention, audio එකතු කරලා, "මොන කොටසේද, ඇයි, මොනවා කරන්නද" කියලා recommendations දෙනවා.

## 3. Input සහ Output
**Input:**
- YouTube URL (title, chapters/topics, comments YouTube API එකෙන්)
- Retention සහ audio signals (අනිත් components වලින් `POST /api/videos` හරහා)

**Output (JSON, කොටස් 4):**
- `analytics_summary`: comments ගණන, sentiment %, dominant emotions
- `content_gaps_and_insights`: topic, ප්‍රශ්නය / interest, සාක්ෂි
- `actionable_recommendations`: Clarification / Content Expansion / Content Structuring / Audio Alignment
- `viewer_guide`: overview, watch out for, highlights, common questions

## 4. මම ම හැදුවා කියන්න සාක්ෂි
- **Git history:** `component_3` branch එකේ commits (මගේ commits 49ක්): RoBERTa analyzer, lexicon negation fix, anonymization, evaluation script, README updates.
- **Code:** `backend/src/services/` (fusion, recommendation, viewerGuide, analyzers), `ml_service/app.py`, `frontend/` Dashboard සහ ResultView, `extension/`.
- **Evaluation:** `backend/scripts/evaluate-sentiment.js` සහ `labelled-comments.json` (අතින් label කළ data).
- Live demo එකක් පෙන්නන්න පුළුවන්, code ඕනම තැනක් පැහැදිලි කරන්න පුළුවන්.

## 5. Component එක ඉවත් කළොත් මොකක්ද නැති වෙන්නේ?
System එකට **audience feedback loop** එක නැති වෙනවා. Video එක හැදුවට (topics, audio, retention), **viewers ඒකට කොහොමද react කළේ, මොන කොටසේ ප්‍රශ්න තිබුණාද** කියලා කියන්න කෙනෙක් නැහැ. Evidence-based recommendations සහ Viewer Guide නැති වෙනවා. C4 ට audio findings confirm කරන්න sentiment timeline එකත් නැති වෙනවා.

## 6. පාවිච්චි කළ APIs සහ ඒවා කරන්නේ මොනවාද?
**External:**
| API | මොනවටද |
|---|---|
| **YouTube Data API v3** (`YOUTUBE_API_KEY`) | Title, chapters (topics), comments ගන්න |
| **Anthropic Claude API** (`ANTHROPIC_API_KEY`) | Singlish comments classify, recommendations සහ viewer guide ලියන්න |
| **MongoDB Atlas** (`MONGODB_URI`) | Videos, comments, results save කරන්න |

**අපේම (internal) REST APIs:**
- `POST /api/videos/import`: URL එකෙන් video + comments import
- `POST /api/videos`: retention / audio data ලබාදීම
- `POST /api/feedback/analyze`: analysis run කිරීම
- `GET /api/feedback/video/:videoId/latest`: අන්තිම result එක
- `POST /sentiment` (Python service, port 8001): RoBERTa sentiment

## 7. Model training තියෙනවද? ඒවා කොහෙද?
**නැහැ, අපි කිසිම model එකක් train හෝ fine-tune කළේ නැහැ.** Pre-trained models inference සඳහා විතරයි.
- **XLM-RoBERTa** (`cardiffnlp/twitter-xlm-roberta-base-sentiment`): Hugging Face එකෙන් download වෙලා local cache එකේ (`~/.cache/huggingface`), `ml_service/app.py` එකෙන් serve කරනවා.
- **Claude:** අපේ machine එකේ නැහැ, API call එකක් විතරයි.
- **Lexicon:** අතින් ලියපු word lists, train කරන්න දෙයක් නැහැ.

**ඇයි train නොකළේ?** Sinhala / Singlish labelled dataset එකක් නැති නිසා. Fine-tuning = future work.
