# Component 3: මුළු component එකම කියන්න පුළුවන් විදියට (Speaking Note)

හැම කොටසකම **සිංහලෙන් අදහස** සහ **English එකෙන් කියන්න ඕන වාක්‍ය** තියෙනවා. කියන්න ඕන දේවල් ඒ පිළිවෙලටම කියන්න. මුළු කතාවම විනාඩි 5-6ක් විතර යනවා. (විනාඩි 2ක් විතරක් නම් කොටස් 1, 3, 5, 8 විතරක් කියන්න.)

---

## 1. Introduction

**අදහස:** මම කරන්නේ YouTube comments කියවලා creator ට උපදෙස් දෙන එක.

**Say:**
> "My component is Audience Feedback Mining. It reads the comments on a YouTube video, finds out how viewers reacted, and tells the creator what to improve, with evidence."

---

## 2. ඇයි මේක ඕන

**අදහස:** Comments දහස් ගණන් කියවන්න බෑ. Sentiment score එකෙන් මොනවා හදන්නද කියලා කියන්නේ නෑ. Sinhala / Singlish වලට හොඳ tools නෑ.

**Say:**
> "A video can have thousands of comments, and no creator can read them all. Existing tools only give a sentiment score, like 62% positive, which doesn't say what to fix. And most of them struggle with Sinhala and Singlish. My component turns comments into specific, evidence-backed recommendations."

---

## 3. System එක වැඩ කරන විදිය (Big picture)

**අදහස:** පියවර 5ක්: comments ගන්නවා → clean කරනවා → classify කරනවා → video එකේ topics එක්ක ගැලපෙනවා → recommendations දෙනවා.

**Say:**
> "The pipeline has five steps. One, fetch the comments. Two, clean and store them. Three, classify each comment. Four, match comments to the video's topics and detect problems. Five, generate recommendations."

---

## 4. පියවර එකින් එක

### පියවර 1: Comments ගැනීම
**අදහස:** User YouTube link එකක් දානවා. YouTube Data API v3 එකෙන් video title, duration, views, chapters සහ comments (replies ඇතුළුව) ගන්නවා. Description එකේ "0:00 Intro" වගේ lines තියෙනවා නම් ඒවා topics බවට හරවනවා.

**Say:**
> "The user pastes a YouTube link. I use the YouTube Data API to get the video details and the comments with their replies. If the description has chapter timestamps, I turn them into topics."

### පියවර 2: Clean කරලා save කිරීම
**අදහස:** Comment එක පිරිසිදු කරනවා, භාෂාව අඳුරගන්නවා (Sinhala / English / mixed), comment එකේ "2:30" වගේ වෙලාවක් තියෙනවා නම් ගන්නවා, author name එක hash කරනවා (privacy), duplicates ඉවත් කරනවා. MongoDB එකේ save කරනවා.

**Say:**
> "Each comment is cleaned, tagged with its language, and any timestamp mentioned in it is extracted. To protect privacy, author names are replaced with a one-way hash, and duplicates are removed before saving to MongoDB."

### පියවර 3: Classify කිරීම
**අදහස:** හැම comment එකකටම sentiment, emotions, ප්‍රශ්නයක්ද කියලා හොයනවා.
- **Sentiment:** XLM-RoBERTa (pre-trained multilingual model, මගේ laptop එකේ local service එකක් විදියට දුවනවා).
- **Emotions සහ question:** English, Sinhala, Singlish keyword rules (lexicon). Emotions 6ක්: Confusion, Curiosity, Agreement, Disagreement, Frustration, Enthusiasm.
- **Fallback:** RoBERTa service එක fail වුණොත් lexicon එකෙන් වැඩේ කරනවා. Claude API key එකක් තියෙනවා නම් Claude පාවිච්චි කරන්නත් පුළුවන් (optional).

**Say:**
> "For sentiment, I use a pre-trained multilingual XLM-RoBERTa model, running as a local service. For emotions like confusion and for detecting questions, I use a keyword lexicon covering English, Sinhala and Singlish. If the model service fails, the lexicon takes over, so the system never stops. I did not train the model; I evaluated it on 28 labelled comments and got 92.9% accuracy."

### පියවර 4: Topics එක්ක ගැලපීම සහ problems හොයා ගැනීම (මගේ core logic එක)
**අදහස:**
- Comment එකක් topic එකකට ගැලපෙන්නේ: comment එකේ timestamp එකෙන්, නැත්නම් keyword overlap එකෙන්.
- Topic එකක් අනුව මේ problems හොයනවා:
  - **Confusion:** 25%ට වඩා confused නම් → Clarification
  - **Unanswered questions:** ප්‍රශ්න 2ට වඩා → Content Expansion
  - **High interest:** curious/enthusiastic 40%ට වඩා සහ positive 50%ට වඩා → Content Expansion
  - **Negative reception:** negative 40%ට වඩා → Clarification
  - **Retention drop:** audience drop එක points 10කට වඩා → Content Structuring
  - **Audio mismatch:** audio intensity වැඩි සහ negative/confusion වැඩි → Audio Alignment
- හැම problem එකකටම **සාක්ෂි** එකතු වෙනවා: comments ගණන, percentage, ඇත්ත comment උදාහරණ.

**Say:**
> "Each comment is linked to a video topic, first by its timestamp, otherwise by keyword overlap. Then, for each topic, I check six patterns: confusion, unanswered questions, high interest, negative reception, retention drops, and audio mismatch. Every finding comes with evidence: how many comments, what percentage, and real example comments."

### පියවර 5: Recommendations
**අදහස:** හැම problem type එකකටම action එකක් තියෙනවා. උදා: confusion → "slower pace, worked example, short recap". Rule-based, සහ evidence එක rationale එකට යනවා. Claude key තියෙනවා නම් ඒක ස්වභාවික භාෂාවෙන් ලියන්න පුළුවන්. අමතරව අනාගත viewers ලට "Guide for future viewers" එකකුත් හදනවා.

**Say:**
> "Each finding becomes a recommendation of one of four types: Clarification, Content Expansion, Content Structuring, or Audio Alignment, with the evidence as its rationale. I also generate a guide for future viewers from past comments."

---

## 5. Prototype එක (Demo)

**අදහස:** React dashboard එකේ link paste කරලා "Import & analyse" click කරනවා. Spinner එකක් එක්ක status පේනවා. ඊට පස්සේ sentiment tiles + bar, content gaps, recommendations, viewer guide පේනවා. "Analysed by …" badge එකෙන් මොන model එකද කියලා පේනවා. Chrome extension එකෙන් YouTube page එකේදීම එක click එකෙන් dashboard එක open කරන්න පුළුවන්.

**Say:**
> "In the dashboard, you paste a link and click Import and analyse. You see the sentiment breakdown, the content gaps with evidence, the recommendations, and a badge showing which analyzer produced the result. There is also a Chrome extension that opens the dashboard directly from a YouTube page."

---

## 6. Technology

**Say:**
> "The backend is Node.js with Express and MongoDB. The frontend is React with TypeScript. The sentiment model runs in a separate Python FastAPI service using Hugging Face Transformers. APIs used are the YouTube Data API, and optionally the Anthropic API."

---

## 7. Integration (වෙන components එක්ක)

**අදහස:** Video collection එකේ topics, retention, audio signals වෙන components වලින් එනවා. මම ඒවා කියවලා comments එක්ක ගැලපෙනවා. C4 ගේ audio findings තහවුරු කරන්න මගේ sentiment timeline එක පාවිච්චි වෙනවා.

**Say:**
> "My component also reads topics, retention and audio signals stored by other components, and C4 uses my sentiment timeline to confirm its audio findings."

---

## 8. Limitations (අවංකව කියන්න)

**අදහස:** අහුවෙන්න කලින් ඔයාම කියන්න.
- Labelled data 28ක් විතරයි.
- Singlish වලට model එක දුර්වලයි (evaluate එකේ වැරදුණේ Singlish දෙකයි).
- RoBERTa fine-tune කරලා නෑ.
- Thresholds (25%, 40%) tune කරලා නෑ.
- Human evaluation තවම කරලා නෑ.

**Say:**
> "The main limitations are the small labelled set of 28 comments, weaker accuracy on Singlish, and thresholds that are not tuned yet. My next steps are more labelled data, better Singlish handling, and evaluation with real creators."

---

## 9. Conclusion

**Say:**
> "In summary, my component closes the feedback loop. It captures how real viewers react to a video and turns that into evidence-backed, actionable recommendations. Without it, the system cannot tell creators what to improve."

---

## Panel ප්‍රශ්න 5ක් (ඉක්මන් උත්තර)

| ප්‍රශ්නය | උත්තරය |
|---|---|
| Model එක train කළාද? | නෑ. Pre-trained XLM-RoBERTa පාවිච්චි කරලා, labelled comments 28ක් මත evaluate කළා. |
| Model එක තියෙන්නේ කොහෙද? | මගේ laptop එකේ Hugging Face cache එකේ (`~/.cache/huggingface/hub`), local FastAPI service එකක් විදියට. |
| ඇයි lexicon ත් ඕන? | RoBERTa sentiment විතරයි දෙන්නේ. Emotions, questions වලටත්, fallback එකටත් rules ඕන. |
| Evidence කියන්නේ? | Comments ගණන, percentage, සහ ඇත්ත comment උදාහරණ. |
| Singlish වලට හොඳද? | තාම දුර්වලයි. ඒක limitation එකක් විදියට පිළිගන්නවා, ඒක next step. |
