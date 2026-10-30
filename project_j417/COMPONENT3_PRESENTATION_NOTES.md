# Component 3 – Audience Feedback Mining (Presentation Notes)

## 1. Component එක මොකක්ද? (තත්පර 30 කින් කියන්න)
YouTube video එකක comments (English, සිංහල, Singlish) කියවලා, viewers ට **මොකක්ද තේරෙන්නේ නැත්තේ, මොකක්ද ආස, මොකක්ද අප්‍රසන්න** කියලා හොයනවා. ඊට පස්සේ creator ට **ඊළඟ video එක දියුණු කරන්න කරන්න පුළුවන් දේවල්** (recommendations) දෙනවා.

> එක වාක්‍යයෙන්: "Comments වල තියෙන audience feedback එක, video එකේ topic / retention / audio data එක්ක එකතු කරලා, creator ට evidence සහිත recommendations දෙන system එකක්."

## 2. Problem එක (ඇයි මේක ඕන?)
- Video එකකට comments සිය ගණනක් එනවා. Creator ට ඒ ඔක්කොම කියවන්න බැහැ.
- Comments සිංහල, English, Singlish මිශ්‍ර. සාමාන්‍ය tools වලට Singlish තේරෙන්නේ නැහැ.
- Like count වගේ numbers වලින් **ඇයි** කියලා කියන්නේ නැහැ. (මොන කොටසේද අවුල, ඇයි අවුල කියලා)

## 3. System එක වැඩ කරන විදිය (Pipeline)
```
YouTube comments
   ↓ 1. Ingestion   : clean කරනවා, භාෂාව හඳුනාගන්නවා, duplicates අයින් කරනවා, author name hash කරනවා
   ↓ 2. Analysis    : sentiment + emotions + question detection
   ↓ 3. Fusion      : comment එක video එකේ topic එකකට සම්බන්ධ කරලා, retention / audio data එක්ක ගලපනවා
   ↓ 4. Insights    : confusion, questions, high interest, negative, retention drop, audio mismatch
   ↓ 5. Recommendations : creator ට කරන්න ඕන දේවල් (evidence එක්ක)
   ↓ Dashboard (React) + Chrome extension
```

### පියවර විස්තර
1. **Ingestion**: comment එකේ timestamp (උදා: "2:35 එකේ තේරුනේ නෑ") තිබුනොත් ඒක ගන්නවා. Author handle එක one-way hash එකකට (`viewer_xxxxxxxx`) හරවනවා, privacy වලට.
2. **Analysis**: Sentiment (positive / negative / neutral), Emotions 6ක් (Confusion, Curiosity, Agreement, Disagreement, Frustration, Enthusiasm), Question ද නැද්ද කියලා.
3. **Fusion** (අපේ main contribution එක): comment එක topic එකකට සම්බන්ධ කරන්නේ **timestamp එකෙන්, නැත්නම් keyword match එකෙන්**. ඊට පස්සේ topic එක අනුව comments එකතු කරනවා.
4. **Insights** (rules, thresholds සහිත):
   | Insight | Trigger |
   |---|---|
   | Confusion | topic එකේ comments වලින් 25%+ confused (අවම 2ක්) |
   | Questions | unanswered questions 2+ |
   | High interest | Curiosity + Enthusiasm 40%+ සහ positive 50%+ |
   | Negative reception | negative 40%+ |
   | Retention drop | segment එකේ retention එක 10 points+ අඩු වෙනවා |
   | Audio mismatch | audio intensity 0.6+ සහ negative / confusion comments තියෙනවා |
5. **Recommendations** වර්ග 4: Clarification, Content Expansion, Content Structuring, Audio Alignment. හැම recommendation එකකටම **rationale (සාක්ෂි, numbers සහිතව)** තියෙනවා.

## 4. AI / Model භාවිතය (අහන්න පුළුවන් ප්‍රශ්නයක්!)
**Model එකක් අපි train කරලා නැහැ.** Pre-trained models inference විතරයි පාවිච්චි කරන්නේ.

| Analyzer (`ANALYZER=`) | මොකක්ද | Sentiment | Emotions / Recommendations |
|---|---|---|---|
| `bert` | `cardiffnlp/twitter-xlm-roberta-base-sentiment` (multilingual RoBERTa, FastAPI service, `ml_service/`) | RoBERTa | keyword rules |
| `llm` | Claude (Anthropic API) | Claude | Claude |
| `lexicon` | keyword word lists (English / සිංහල / Singlish) | rules | rules |
| `auto` | API key තිබුනොත් Claude, නැත්නම් lexicon | | |

- **Fallback**: RoBERTa service එක හෝ Claude fail වුනොත් auto `lexicon` එකට මාරු වෙනවා. System එක කවදාවත් නවතින්නේ නැහැ.
- Dashboard එකේ **මොන analyzer එකෙන්ද result එක ආවේ** කියලා පෙන්නනවා (transparency).
- Recommendations වලදී Claude ට කියලා තියෙන්නේ "**දුන්න findings වලින් විතරක් ලියන්න, evidence හදන්න එපා**" කියලා. ඒකෙන් hallucination අඩු වෙනවා.

## 5. Evaluation (accuracy එක මැනපු විදිය)
- `npm run evaluate -- --analyzer bert` (හෝ `llm` / `lexicon`) command එකෙන්, `samples/labelled-comments.json` (අතින් label කරපු comments) එක්ක සසඳනවා.
- Output: accuracy, precision / recall / F1 (class එකක් එකක් අනුව), confusion matrix.
- Analyzers 3ම සසඳලා බලන්න පුළුවන්. Presentation එකට **results table එකක් දාන්න** (evaluation run කරලා numbers ගන්න).

## 6. අපේ component එකේ අලුත්/විශේෂ දේවල්
1. **Sinhala + Singlish + English** support (වෙනත් tools වල නැති).
2. Comment feedback එක **video එකේ topic / retention / audio** එක්ක fuse කිරීම. Sentiment analysis එකෙන් නවතින්නේ නැහැ.
3. Recommendations වලට **සාක්ෂි** (numbers සහ real comment quotes) ඇමුණීම.
4. **Fallback chain** එකක් නිසා offline වුනත් වැඩ කරනවා.
5. **Privacy**: public comments විතරයි, author names hash කරනවා.

## 7. Tech stack
- Frontend: React + TypeScript (Vite)
- Backend: Node.js, Express, MongoDB (Mongoose)
- ML service: Python, FastAPI, Hugging Face Transformers
- Chrome extension: YouTube video එකේදී dashboard එක open කරනවා

## 8. Demo plan (විනාඩි 2–3)
1. Chrome extension එකෙන් YouTube video එකක් open කරන්න.
2. Dashboard එකේ analyze කරන්න. Summary (sentiment %, dominant emotions) පෙන්නන්න.
3. Insights එකක් පෙන්නලා, ඒකට අදාල recommendation එකයි evidence quote එකයි පෙන්නන්න.
4. Analyzer එක මාරු කරලා (`bert` → `lexicon`) result වෙනස පෙන්නන්න (optional).

## 9. අහන්න පුළුවන් ප්‍රශ්න සහ උත්තර
| ප්‍රශ්නය | උත්තරය |
|---|---|
| ඔයාලා model එක train කළාද? | නැහැ. Pre-trained RoBERTa (inference විතරයි) සහ Claude API භාවිතා කළා. Train කරන්නේ නැතුව multilingual support ගන්න පුළුවන් නිසා. |
| Fine-tune නොකරන්නේ ඇයි? | Sinhala / Singlish labelled data ප්‍රමාණවත් නැහැ. ඒක future work එකක්. |
| Singlish accuracy එක කොහොමද? | RoBERTa Singlish වලට දුර්වල වෙන්න පුළුවන්. ඒකට lexicon එකේ Singlish word lists සහ Claude විකල්පය තියෙනවා. Evaluation numbers පෙන්නන්න. |
| Recommendations හරි කියලා කොහොමද දන්නේ? | හැම එකකටම rationale (numbers + comment quotes) තියෙනවා. Claude ට evidence හදන්න එපා කියලා කියලා තියෙනවා. |
| API fail වුනොත්? | `lexicon` fallback එකට ස්වයංක්‍රීයව මාරු වෙනවා. |
| Privacy? | Public comments විතරයි, author handle එක hash කරනවා. |
| අනිත් components එක්ක සම්බන්ධය? | Video එකේ topics (knowledge), retention, audio signals අනිත් components වලින් ගන්නවා, ඒවා එක්ක comments fuse කරනවා. *(මේක ඔබේ team එකේ අනිත් components වලට ගැලපෙන්න වෙනස් කරන්න.)* |

## 10. Limitations සහ Future work (අවංකව කියන්න)
- Model එක fine-tune කරලා නැහැ. Sinhala / Singlish data set එකක් හදලා fine-tune කරන්න පුළුවන්.
- Emotions සහ question detection `bert` mode එකේදී keyword rules. Emotion classifier එකක් අවශ්‍යයි.
- Thresholds (25%, 40%, 10 pts) අතින් තෝරපු අගයන්. Real data වලින් tune කරන්න ඕන.
- Evaluation set එක කුඩායි. විශාල labelled set එකක් ඕන.
