# Component 3: සම්පූර්ණ අවබෝධ Note

**Audience Feedback Mining and Evidence-Based Improvement Recommendations**
K.W.M.C.S. Wijekoon | IIT23246928 | J26-417 | Member 3 of 4

මේ note එක කියවලා ඉවර වුණාම ඔයාට මේ component එක ගැන කිසිම panel ප්‍රශ්නයකට උත්තර දෙන්න පුළුවන් වෙන්න ඕන.

---

## 1. එක වාක්‍යයෙන්

> YouTube video එකක comments කියවලා, ප්‍රේක්ෂකයෝ මොකක්ද හිතන්නේ කියලා හොයලා, creator ට **"මොනවා වෙනස් කරන්නද" කියලා සාක්ෂි එක්ක** කියන system එක.

---

## 2. ගැටලුව සහ විසඳුම

| ගැටලුව | අපේ විසඳුම |
|---|---|
| Comments දහස් ගණන් කියවන්න බෑ | Automatic analysis |
| Sentiment score එකෙන් (62% positive) මොනවා හදන්නද කියලා කියන්නේ නෑ | Topic එකක් අනුව issue එක + සාක්ෂි comments + recommendation |
| Sinhala / Singlish comments වලට tools දුර්වලයි | Multilingual RoBERTa + Sinhala/Singlish keyword lexicon |
| Creator ට audience confused වෙන තැන් පේන්නේ නෑ | Confusion, questions, negative, retention drop detect කිරීම |

**Novelty:** Feedback loop එක වහනවා. Comments → score එකක් විතරක් නෙවෙයි, **evidence-based suggestions**.

---

## 3. System එක වැඩ කරන විදිය (Pipeline)

```
YouTube URL
   │
   ▼
[1] Fetch        youtube.service.js     → video info + chapters + comments (YouTube Data API v3)
   │
   ▼
[2] Ingest       ingestion.service.js   → clean, භාෂාව අඳුරගන්න, timestamp ගන්න,
   │                                       author hash කරන්න, duplicates ඉවත් කරන්න
   ▼                                       → MongoDB: Comment
[3] Classify     analyzers/             → sentiment, emotions, isQuestion
   │                                       → Comment එකටම ලියනවා
   ▼
[4] Fuse         fusion.service.js      → comments ↔ video topics ගැලපීම,
   │                                       topic එකක් අනුව issues හොයනවා
   ▼
[5] Recommend    recommendation.service.js, viewerGuide.service.js
   │                                    → actionable recommendations + viewer guide
   ▼
[6] Save         feedback.service.js    → MongoDB: FeedbackAnalysis
   │
   ▼
[7] Show         React dashboard + Chrome extension
```

### පියවර 1: Fetch ([youtube.service.js](backend/src/services/youtube.service.js))
- URL එකෙන් video ID එක ගන්නවා (watch / youtu.be / shorts / embed).
- `videos` endpoint එකෙන් title, duration, views ගන්නවා.
- Description එකේ "0:00 Intro" වගේ chapter lines තියෙනවා නම් ඒවා **topics** බවට හරවනවා (අඩුම තරමින් lines 2ක් ඕන).
- `commentThreads` endpoint එකෙන් comments සහ replies ගන්නවා (පිටුවකට 100, relevance order).

### පියවර 2: Ingest ([ingestion.service.js](backend/src/services/ingestion.service.js))
- `cleanText`: පිරිසිදු කරනවා.
- `detectLanguage`: si / en / mixed / other.
- `extractTimestamp`: comment එකේ "2:30" වගේ වෙලාවක් තියෙනවා නම් ගන්නවා.
- **Privacy:** author name එක `viewer_ab12cd34` වගේ hash එකක් කරනවා.
- `videoId + commentId` unique නිසා duplicate save වෙන්නේ නෑ.

### පියවර 3: Classify (analyzers/)
Analyzer තුනක් තියෙනවා. `ANALYZER` env value එකෙන් තෝරනවා.

| `ANALYZER` | Sentiment | Emotions / isQuestion |
|---|---|---|
| `bert` | XLM-RoBERTa | Lexicon rules |
| `llm` | Claude | Claude |
| `lexicon` | Rules | Rules |
| `auto` | Claude key තියෙනවා නම් Claude, නැත්නම් lexicon | එලෙසම |

- **RoBERTa** ([bert.analyzer.js](backend/src/services/analyzers/bert.analyzer.js)): Python service එකට (`ml_service`, port 8001) comments 64 බැගින් යවනවා. Service එක fail වුණොත් lexicon sentiment එකට fallback වෙනවා.
- **Lexicon** ([lexicon.analyzer.js](backend/src/services/analyzers/lexicon.analyzer.js)): English, Sinhala අකුරු, සහ Singlish keyword lists. Emotions 6ක් අඳුරගන්නවා: Confusion, Curiosity, Agreement, Disagreement, Frustration, Enthusiasm. "?" හෝ how/why/what වලින් පටන් ගත්තොත් isQuestion.
- **Claude** ([llm.analyzer.js](backend/src/services/analyzers/llm.analyzer.js)): API key තියෙනවා නම් විතරයි.

### පියවර 4: Fuse ([fusion.service.js](backend/src/services/fusion.service.js)): **ඔයාගේ core logic එක**

**(a) Comment එකක් topic එකකට ගැලපීම**
1. Comment එකේ timestamp එකක් තියෙනවා නම්, ඒ වෙලාව අයිති topic එකට.
2. නැත්නම් comment එකේ වචන සහ topic නම/keywords අතර **keyword overlap** වැඩිම topic එකට.
3. කිසිවකට නොගැලපුණොත් "General discussion".

**(b) Topic එකක් අනුව issues හොයන rules** (topic එකකට අඩුම comments 2ක් ඕන):

| Insight | කොන්දේසිය | Recommendation type |
|---|---|---|
| **Confusion** | Confusion comments ≥ 2 සහ ≥ 25% | Clarification |
| **Questions** | Questions ≥ 2 | Content Expansion |
| **High interest** | (Curiosity + Enthusiasm) ≥ 40% සහ positive ≥ 50% | Content Expansion |
| **Negative** | Negative ≥ 40% (confusion නොවේ නම්) | Clarification |
| **Retention drop** | Segment එකේ retention ≥ 10 points අඩු වෙනවා | Content Structuring |
| **Audio mismatch** | Audio intensity ≥ 0.6 සහ negative ≥ 30% හෝ confusion ≥ 2 | Audio Alignment |

හැම insight එකකටම `supporting_evidence` එකක් එනවා. උදා: *"5/16 comments (31.3%) express confusion, e.g. 'I don't understand...'"*. ඒක තමයි "evidence-based" කියන්නේ.

> `retention` සහ `audioSignals` ඇවිත් තියෙන්නේ වෙන data වලින් (retention curve, Affective Audio component). ඒවා නැති වුණත් confusion/questions/interest/negative insights වැඩ කරනවා.

### පියවර 5: Recommend
- **Rule-based** ([recommendation.service.js](backend/src/services/recommendation.service.js)): insight එකකට template recommendation එකක් (උදා: confusion → "slower pace, worked example, recap").
- **Claude**: key තියෙනවා නම්, "supplied findings විතරක් පාවිච්චි කරලා, සාක්ෂි හදන්න එපා" කියලා prompt කරලා JSON ගන්නවා. Fail වුණොත් rule-based එකට fallback.
- **Viewer guide** ([viewerGuide.service.js](backend/src/services/viewerGuide.service.js)): අනාගත viewers ලට "Before you watch / Highlights / Watch out for / Questions viewers asked".

---

## 4. Output එක (JSON)

```
analytics_summary          → comments ගණන, positive/neutral/negative %, dominant emotions
content_gaps_and_insights  → topic/timestamp, issue, supporting_evidence
actionable_recommendations → type, action_item, rationale
viewer_guide               → overview, before_you_watch, highlights, watch_out_for, common_questions
```

---

## 5. Database (MongoDB)

| Collection | කාගේද | මොකට |
|---|---|---|
| **Comment** | ඔයාගේ | Comments + sentiment/emotions/isQuestion |
| **FeedbackAnalysis** | ඔයාගේ | අන්තිම output JSON |
| **Video** | බෙදාගත් | Title, duration, topics, retention, audioSignals (ඔයා කියවනවා) |
| **User** | අදාළ නෑ | Login/admin |

---

## 6. UI

- **Dashboard** ([Dashboard.tsx](frontend/src/pages/Dashboard.tsx)): link paste කරනවා, comments ගණන තෝරනවා (100 සිට All), Import & analyse. Spinner + status message. Videos sidebar (View analysis / Re-analyse).
- **ResultView** ([ResultView.tsx](frontend/src/components/ResultView.tsx)): Tiles + sentiment bar, Content gaps & insights, Recommendations (type tags), Guide for future viewers, "Analysed by …" badge.
- **Chrome extension** (`extension/`): YouTube page එකේදී එක click එකෙන් dashboard එක `?video=<link>` එක්ක open කරනවා.

---

## 7. Models සහ APIs

**Models**
| Model | කොහේද | Train කළාද |
|---|---|---|
| cardiffnlp/twitter-xlm-roberta-base-sentiment | ඔයාගේ laptop (`~/.cache/huggingface/hub`) | **නෑ**, pre-trained |
| Claude | Anthropic servers | නෑ |
| Lexicon | Code එකේම | Model නෙවෙයි, rules |

**APIs:** YouTube Data API v3, Anthropic Messages API, MongoDB Atlas, ඔයාගේම REST API (Express, 5000), ඔයාගේම RoBERTa service (FastAPI, 8001), Hugging Face Hub (download විතරයි), Chrome Extension API.

---

## 8. Evaluation

- Labelled comments 28ක්, `npm run evaluate -- --analyzer bert|llm|lexicon`
- RoBERTa: **Accuracy 92.9% (26/28), Macro F1 0.93**
- වැරදුණේ Singlish දෙකක් ("supiri explanation eka, niyamai", "meka narakai, epa"), neutral කියලා.
- **ඒ නිසා:** Singlish වලට model එක දුර්වලයි කියලා කෙලින්ම පිළිගන්න.

---

## 9. ඔයාගේ ශක්තිමත් තැන් සහ දුර්වල තැන්

**ශක්තිමත්**
- Score එකක් නෙවෙයි, සාක්ෂි සහිත recommendations.
- Fallback chain: RoBERTa/Claude fail වුණත් lexicon එකෙන් system එක නතර වෙන්නේ නෑ.
- Privacy: author handles hash කරනවා.
- Sinhala + Singlish සඳහා විශේෂ lexicon.

**දුර්වල (panel එකට අහුවෙන්න පුළුවන්)**
- Labelled data 28ක් විතරයි, ඒක ඉතා කුඩා.
- Singlish accuracy අඩුයි.
- RoBERTa fine-tune කරලා නෑ.
- Emotions rules වලින් නිසා RoBERTa mode එකේ emotion accuracy අඩුයි.
- Claude key නැති නිසා Claude results තවම ගෙන නෑ.
- Insight thresholds (25%, 40%) අපි තෝරපු අගයන්. ඒවා tune කරලා නෑ.

---

## 10. බොහෝ විට අහන ප්‍රශ්න

**ඇයි RoBERTa?** Multilingual (Sinhala ඇතුළුව), free, local එකේ දුවන්න පුළුවන්, API cost නෑ.

**ඇයි lexicon ත් පාවිච්චි කරන්නේ?** RoBERTa sentiment විතරයි දෙන්නේ. Emotions (confusion, curiosity) සහ isQuestion ඕන නිසා rules පාවිච්චි කරනවා. අමතරව fallback එකක් වෙනවා.

**Evidence කියන්නේ?** හැම insight එකකම: comments ගණන, percentage, සහ ඇත්ත comment උදාහරණ 1-2ක්.

**Thresholds කොහොමද තෝරගත්තේ?** පළමු අගයන් විදියට තෝරලා. තවම tune කරලා නෑ, ඒක future work.

**C4 එක්ක සම්බන්ධය?** C4 ගේ audio findings තහවුරු කරන්න ඔයාගේ sentiment timeline එක පාවිච්චි කරනවා. Audio mismatch insight එකේදී audio intensity එකයි comments වල negative/confusion එකයි එකට බලනවා.

**Model train කළාද?** නෑ. "Pre-trained multilingual RoBERTa පාවිච්චි කරලා, labelled comments 28ක් මත evaluate කළා."

**Topics ආවේ කොහෙන්ද?** YouTube description එකේ chapter lines වලින් auto, නැත්නම් වෙන component එකකින්.

---

## 11. Viva එකට කලින් තහවුරු කරගන්න

- [ ] Slide එකේ spaCy/NLTK/Aspect-Based Sentiment තියෙනවා නම් අයින් කරන්න.
- [ ] Slide එකේ "Claude for Singlish" තියෙනවා නම් අයින් කරන්න (Claude results ගත්තේ නෑ).
- [ ] Feedback table එකේ Pavan ගෙන් ඇත්ත feedback ගන්න.
- [ ] Git commits 57න් 49ක් විතරයි ඔයාගේ. "ඔක්කොම" කියන්න එපා.
- [ ] `npm run evaluate` එක ආපහු දුවලා 92.9% තහවුරු කරගන්න.
