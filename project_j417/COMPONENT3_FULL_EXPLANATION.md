# Component 3 – Audience Feedback Mining: Full Explanation Note

ප්‍රශ්න ගොඩක් එන්නේ මේ තැන් වලින්: **Idea එක, Novelty, API keys, Model train කළාද, Model එක කොහෙද පාවිච්චි වෙන්නේ**. ඒ හැම එකක්ම අදාල files එක්ක මෙතන තියෙනවා.

---

## 1. Full idea (සරලව)

**Problem:** YouTube video එකකට comments සිය ගණනක් (English / සිංහල / Singlish) එනවා. Creator ට ඒවා කියවන්න බැහැ. Views, likes වලින් "ඇයි" කියලා කියන්නේ නැහැ.

**Solution:** Comments auto කියවලා
1. හැම comment එකකම **sentiment, emotion, question ද** කියලා හොයනවා
2. Comment එක video එකේ **කුමන topic එකටද** කියලා සම්බන්ධ කරනවා
3. ඒ topic එකේ **retention** සහ **audio** data එක්ක ගලපලා **problems / interests** හොයනවා
4. Creator ට **සාක්ෂි සහිත recommendations** දෙනවා
5. අලුතෙන් බලන viewers ට **Viewer Guide** එකක් (මොන කොටස අමාරුද, මොනවා හොඳද) දෙනවා

**Output එකේ තියෙන දේවල් (4):**
- `analytics_summary`: comments ගණන, sentiment %, dominant emotions
- `content_gaps_and_insights`: topic එක, ඉස්සරවෙලා හොයාගත්ත ප්‍රශ්නය / interest, සාක්ෂි
- `actionable_recommendations`: Clarification / Content Expansion / Content Structuring / Audio Alignment
- `viewer_guide`: overview, before you watch, watch out for, highlights, common questions

---

## 2. Novelty points (මේවා අනිවාර්යයෙන් කියන්න)

| # | Novelty | සාමාන්‍ය sentiment tools වලට වඩා වෙනස |
|---|---|---|
| 1 | **Sinhala + Singlish + English** (code-mixed) comments support | බොහෝ tools English විතරයි |
| 2 | **Multimodal fusion**: comments + video topics + retention + audio emotion එකතු කිරීම | සාමාන්‍ය ඒවා comments විතරක් බලනවා |
| 3 | **Topic-level insights**: "මුළු video එකම" නෙවෙයි, **මොන කොටසේද** ප්‍රශ්නය කියලා කියනවා (timestamp / keyword මගින්) | |
| 4 | **Evidence-linked recommendations**: හැම recommendation එකකටම numbers සහ real comment quotes | "positive 60%" වගේ dashboard එකක් නෙවෙයි, **කරන්න ඕන දේ** කියනවා |
| 5 | **Creator ට + Viewer ට** දෙපාර්ශවයටම output (Recommendations සහ Viewer Guide) | |
| 6 | **Fallback chain** (RoBERTa / Claude → lexicon): API fail වුනත් නවතින්නේ නැහැ | |
| 7 | **Privacy**: author names one-way hash | |
| 8 | **Transparency**: result එකේ කුමන analyzer / model එකෙන්ද කියලා UI එකේ පෙන්නනවා | Black-box නෙවෙයි |

> Novelty එක එක වාක්‍යයෙන්: **"We don't stop at sentiment. We fuse comments with the video's own topics, retention and audio to tell the creator exactly which part to fix, and why."**

Fusion logic එක තියෙන්නේ: [fusion.service.js](backend/src/services/fusion.service.js)

---

## 3. API keys / external services (මොනවාද, මොනවටද)

[.env.example](backend/.env.example) සහ [env.js](backend/src/config/env.js) බලන්න.

| Key / Service | මොකක්ද | මොනවට පාවිච්චි කරන්නේ | Files |
|---|---|---|---|
| **`YOUTUBE_API_KEY`** | YouTube Data API v3 | Video එකේ **title, duration, views, chapters (topics)** සහ **comments (relevance order, replies සමඟ)** ගන්න | [youtube.service.js](backend/src/services/youtube.service.js) |
| **`ANTHROPIC_API_KEY`** | Claude (Anthropic API) | (a) comments classify කිරීම (sentiment / emotions / question) (b) **Recommendations** ලියන්න (c) **Viewer Guide** ලියන්න | [llm.analyzer.js](backend/src/services/analyzers/llm.analyzer.js), [recommendation.service.js](backend/src/services/recommendation.service.js), [viewerGuide.service.js](backend/src/services/viewerGuide.service.js) |
| `ANTHROPIC_MODEL` | පාවිච්චි කරන Claude model එක (default `claude-opus-5-5`) | | [env.js](backend/src/config/env.js) |
| **`MONGODB_URI`** | MongoDB Atlas database | Videos, comments, analysis results save කරන්න | [db.js](backend/src/config/db.js), [models/](backend/src/models/) |
| `BERT_SERVICE_URL` | අපේම Python service (`localhost:8001`) | RoBERTa sentiment service එකට call කරන්න | [bert.analyzer.js](backend/src/services/analyzers/bert.analyzer.js) |
| `ANALYZER` | `auto` / `llm` / `bert` / `lexicon` | මොන analyzer එකද පාවිච්චි කරන්නේ කියලා තෝරන්න | [analyzers/index.js](backend/src/services/analyzers/index.js) |

**RoBERTa model එකට API key එකක් ඕන නැහැ.** එය open model එකක්, local එකේ run වෙනවා.

**Claude call එකකට යවන data:** comment text විතරයි (author names hash කරලා, `cleanText` එක). Personal data යවන්නේ නැහැ.

---

## 4. Model train කළාද? ❌ නැහැ

> **"We did not train or fine-tune any model. We use pre-trained models for inference only."**

- RoBERTa: pre-trained, fine-tune කරලා නැහැ ([FEEDBACK_MINING_README.md](FEEDBACK_MINING_README.md) එකේත් ලියලා තියෙනවා)
- Claude: API call එකක් විතරයි
- Lexicon: අතින් ලියපු word lists, train කරන්න දෙයක් නැහැ

**"ඇයි train නොකළේ?"** → Sinhala / Singlish labelled data set එකක් නැහැ. Pre-trained multilingual model එකෙන් zero-shot ගන්න පුළුවන්. Fine-tuning = future work.

---

## 5. Model එක කොහෙද පාවිච්චි වෙන්නේ? (එක එක model එක)

### 5.1 RoBERTa (`ANALYZER=bert`)
- **Model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment` (Hugging Face, multilingual, ~1 GB)
- **ගබඩා වෙලා තියෙන්නේ:** project එකේ නෙවෙයි. පළවෙනි run එකේදී download වෙලා `C:\Users\chamo\.cache\huggingface\hub` එකේ cache වෙනවා
- **Load කරන තැන:** [ml_service/app.py](ml_service/app.py) (`pipeline("sentiment-analysis", ...)`), FastAPI, port 8001, endpoint `POST /sentiment`
- **Call කරන තැන:** [bert.analyzer.js](backend/src/services/analyzers/bert.analyzer.js) (comments 64 බැගින් batch කරලා යවනවා)
- **මොනවටද:** **Sentiment විතරයි** (positive / negative / neutral). Emotions සහ question detection = keyword rules ([lexicon.analyzer.js](backend/src/services/analyzers/lexicon.analyzer.js))
- **Fail වුනොත්:** ඒ batch එකට lexicon sentiment පාවිච්චි කරනවා

### 5.2 Claude (`ANALYZER=llm`, හෝ `auto` + API key)
- **Classification** ([llm.analyzer.js](backend/src/services/analyzers/llm.analyzer.js)): comments 40 බැගින්, batches 4ක් එකවර. Sentiment + Emotions (6) + Question. Sinhala / Singlish තේරුම් ගන්න prompt එකේ කියලා තියෙනවා
- **Recommendations** ([recommendation.service.js](backend/src/services/recommendation.service.js)): "ලැබුණු findings වලින් විතරක් ලියන්න, evidence හදන්න එපා" කියලා rule කරලා, output එක validate කරනවා
- **Viewer Guide** ([viewerGuide.service.js](backend/src/services/viewerGuide.service.js)): most-liked comments 60ක් සහ findings වලින් විතරයි
- **Fail වුනොත්:** හැම තැනම rule-based fallback එකක් තියෙනවා

### 5.3 Lexicon (`ANALYZER=lexicon`, හෝ `auto` + key නැති විට)
- English + සිංහල script + Singlish keyword lists. Offline, free
- "don't / do not / did not / can't understand", "not clear", "doesn't make sense" වගේ **negated variants** Confusion විදිහට අඳුරගන්නවා
- [lexicon.analyzer.js](backend/src/services/analyzers/lexicon.analyzer.js)

### 5.4 UI එකේ පෙන්නන්නේ (Frontend)
- හැම result එකකම **"Analysed by …"** badge එකක් තියෙනවා: `Claude` / `XLM-RoBERTa` / `Keyword rules (offline)` (+ model නම). [ResultView.tsx](frontend/src/components/ResultView.tsx)
- Dashboard footer එකේ: "Sentiment is analysed by the selected analyzer (XLM-RoBERTa, Claude or keyword rules); recommendations are generated by Claude when available. No custom model is trained." [Dashboard.tsx](frontend/src/pages/Dashboard.tsx)
- ඒ නිසා panel එකට පෙන්නන්න පුළුවන්: කුමන analyzer එකෙන්ද result එක ආවේ කියලා **transparent** විදිහට.

### සාරාංශ table
| Analyzer | Sentiment | Emotions | Question | Recommendations | Viewer Guide |
|---|---|---|---|---|---|
| `bert` | **RoBERTa** | rules | rules | rules* | rules* |
| `llm` | **Claude** | **Claude** | **Claude** | **Claude** | **Claude** |
| `lexicon` | rules | rules | rules | rules | rules |

\* `ANALYZER=bert` වුනාම recommendations / viewer guide එකට Claude පාවිච්චි කරන්නේ නැහැ ([recommendation.service.js:6](backend/src/services/recommendation.service.js#L6): `useLLM` = `llm` හෝ `auto`+key). ඒ නිසා `bert` mode එකේ ඒවා rule-based. Claude-written recommendations ඕන නම් `ANALYZER=llm` (හෝ `auto` + key) දාන්න.

---

## 6. Pipeline එක සහ Files (සම්පූර්ණ flow)

```
Chrome extension (extension/popup.js)
   ↓ YouTube URL එක dashboard එකට
React Dashboard (frontend/src/pages/Dashboard.tsx)
   ↓ POST /api/videos/import
video.controller.js → youtube.service.js        ← YOUTUBE_API_KEY
   ↓ title, chapters(topics), comments
ingestion.service.js   : clean, language detect, dedupe, timestamp extract, author hash → MongoDB
   ↓ POST /api/feedback/analyze
feedback.service.js    : pipeline එක පාලනය කරනවා
   ├─ analyzers/ (bert | llm | lexicon)       : sentiment, emotions, question
   ├─ fusion.service.js                        : comments ↔ topics ↔ retention ↔ audio → insights
   ├─ recommendation.service.js                : recommendations
   └─ viewerGuide.service.js                   : viewer guide
   ↓ FeedbackAnalysis (MongoDB) → ResultView.tsx එකේ පෙන්නනවා
```

| කොටස | File |
|---|---|
| Express server / routes | [server.js](backend/src/server.js), [feedback.routes.js](backend/src/routes/feedback.routes.js), [video.routes.js](backend/src/routes/video.routes.js) |
| Comment cleaning, language, timestamp | [utils/text.js](backend/src/utils/text.js) |
| Data models | [Comment.js](backend/src/models/Comment.js), [Video.js](backend/src/models/Video.js), [FeedbackAnalysis.js](backend/src/models/FeedbackAnalysis.js) |
| Emotions / sentiments constants | [constants.js](backend/src/services/analyzers/constants.js) |
| Evaluation | [evaluate-sentiment.js](backend/scripts/evaluate-sentiment.js), [labelled-comments.json](backend/samples/labelled-comments.json) |
| Frontend | [Dashboard.tsx](frontend/src/pages/Dashboard.tsx), [ResultView.tsx](frontend/src/components/ResultView.tsx) |
| Extension | [popup.js](extension/popup.js) |

**Emotions 6ක්:** Confusion, Curiosity, Agreement, Disagreement, Frustration, Enthusiasm

**Insights 6ක් (fusion.service.js):**
| Insight | Rule |
|---|---|
| Confusion | topic comments වලින් 25%+ (අවම 2) |
| Questions | questions 2+ |
| Interest | (Curiosity + Enthusiasm) 40%+ සහ positive 50%+ |
| Negative | negative 40%+ |
| Retention drop | segment එකේ retention 10 points+ අඩු වීම |
| Audio mismatch | audio intensity 0.6+ සහ (negative 30%+ හෝ confusion 2+) |

---

## 7. Topics / Retention / Audio data එන්නේ කොහෙන්ද? (පරෙස්සම් වෙන්න)

- **Topics:** YouTube video description එකේ chapters ("0:00 Intro") වලින් auto ගන්නවා. නැත්නම් **අනිත් components වලින්** ([video.controller.js:33](backend/src/controllers/video.controller.js#L33) comment එක බලන්න)
- **Retention** සහ **Audio signals:** YouTube API එකෙන් ගන්නේ නැහැ. `POST /api/videos` (Video එක create කරන API එක) හරහා **එනවා** ([video.routes.js](backend/src/routes/video.routes.js)). එනම් අනිත් components (audio emotion, knowledge / topics) හෝ YouTube Studio data එකෙන් දෙන්න ඕන.
- **Panel එකට:** "Retention සහ audio data අපේ component එකට input විදිහට එනවා, comments සමඟ fuse කරන එක තමයි අපේ කොටස." *(ඔබේ team එකේ අනිත් components වල ඇත්ත සම්බන්ධය මෙතනට ගැලපෙනවද බලන්න. නැත්නම් වෙනස් කරන්න.)*

---

## 8. Evaluation

```
cd project_j417/backend
npm run evaluate -- --analyzer bert     # හෝ llm / lexicon
```
- Data: [labelled-comments.json](backend/samples/labelled-comments.json) (අතින් label කරපු)
- Output: accuracy, precision / recall / F1, confusion matrix
- **Presentation එකට:** analyzers 3ම run කරලා numbers table එකක් දාන්න. ⚠️ Evaluation කරන්නේ **sentiment** එකට විතරයි (emotions / recommendations නෙවෙයි).

---

## 9. Panel එක අහන්න පුළුවන් ප්‍රශ්න සහ උත්තර

**Q1. ඔයාලා model එක train කළාද?**
නැහැ. Pre-trained multilingual RoBERTa (inference) සහ Claude API පාවිච්චි කළා. Sinhala / Singlish labelled data නැති නිසා. Fine-tuning = future work.

**Q2. Model එක කොහෙද තියෙන්නේ?**
Project එකේ නැහැ. RoBERTa Hugging Face එකෙන් download වෙලා local cache එකේ තියෙනවා, `ml_service` (FastAPI, port 8001) එකෙන් load කරනවා. Claude අපේ machine එකේ නැහැ, API call එකක්.

**Q3. මොන API keys පාවිච්චි කළාද?**
YouTube Data API (comments, chapters, metadata ගන්න), Anthropic API (Claude: classification, recommendations, viewer guide), MongoDB Atlas (storage). RoBERTa එකට key එකක් ඕන නැහැ.

**Q4. Novelty එක මොකක්ද?**
Sentiment analysis එකෙන් නවතින්නේ නැහැ. Comments + video topics + retention + audio fuse කරලා, "මොන කොටසේද, ඇයි, මොනවා කරන්නද" කියනවා. Sinhala / Singlish support. Evidence-linked recommendations. Creator ට සහ viewer ට දෙන්නටම output.

**Q5. Singlish කොහොමද handle කරන්නේ?**
Claude prompt එකේ "Sinhala, romanised Sinhala, code-mixed" කියලා කියලා තියෙනවා. Lexicon එකේ Singlish word lists තියෙනවා. RoBERTa Singlish වලට දුර්වල විය හැකියි, ඒ නිසා analyzers 3ම evaluate කළා.

**Q6. Claude hallucinate කරන්නේ නැද්ද?**
Prompt එකේ "supplied findings වලින් විතරක් ලියන්න, evidence හදන්න එපා" කියලා තියෙනවා. Output එක validate කරනවා (type එක වලංගුද, rationale තියෙනවද). Fail වුනොත් rule-based එකට යනවා. Rule-based recommendations හැම එකක්ම findings වලින්ම හැදෙන්නේ.

**Q7. API fail වුනොත් / key නැත්නම්?**
Auto-fallback: Claude / RoBERTa → lexicon. Dashboard එකේ analyzer එක පෙන්නනවා.

**Q8. Thresholds (25%, 40%, 10 pts) කොහොමද ගත්තේ?**
අතින් තෝරපු starting values ([fusion.service.js](backend/src/services/fusion.service.js) ඉහළ constants). Real data වලින් tune කරන්න ඕන. Limitation එකක්.

**Q9. Privacy?**
Public comments විතරයි. Author names SHA-256 hash කරලා (`viewer_xxxxxxxx`) save කරනවා. Claude ට යවන්නේ comment text විතරයි.

**Q10. Accuracy කීයද?**
*(Evaluation run කරලා numbers මෙතනට ලියාගන්න.)*

**Q11. Retention / audio data කොහෙන්ද?**
Section 7 බලන්න.

**Q12. Cost / scalability?**
Comments batch කරලා (Claude 40, RoBERTa 64) concurrency 4 සමඟ process කරනවා. Analyzed comments `analyzed` flag එකෙන් නැවත classify වෙන්නේ නැහැ (`force` දුන්නොත් විතරයි). Offline lexicon free.

**Q13. Limitations?**
Model fine-tune කරලා නැහැ. `bert` mode එකේ emotions rules. Thresholds අතින් දැමූ ඒවා. Evaluation set එක කුඩායි. Retention / audio data බාහිරින් ඕන.

---

## 10. එක බැල්මෙන් (cheat sheet)

- **Idea:** Comments → insights (topic-level) → recommendations + viewer guide
- **Novelty:** Sinhala/Singlish + **fusion with video retention/audio/topics** + evidence-linked actions
- **Keys:** YouTube Data API, Anthropic (Claude), MongoDB. RoBERTa = key නැහැ
- **Train?** ❌ නැහැ. Pre-trained inference
- **Model location:** HF cache (`C:\Users\chamo\.cache\huggingface\hub`), served by `ml_service/app.py` :8001
- **Claude කරන්නේ:** classify, recommendations, viewer guide
- **RoBERTa කරන්නේ:** sentiment විතරයි
- **Fallback:** → lexicon (rules)
