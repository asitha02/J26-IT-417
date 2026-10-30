# Component 3 – විනාඩි 2 Note

## 1. මොකක්ද මේක? (15s)
YouTube video එකක comments (English / සිංහල / Singlish) auto කියවලා, creator ට **"මොනවා හදන්නද"** කියලා කියන system එකක්. Views, likes වලින් **ඇයි** කියලා කියන්නේ නැහැ, අපි ඒක කියනවා.

## 2. Flow එක (30s)
1. YouTube URL එක දෙනවා, **YouTube Data API** එකෙන් title, chapters (topics), comments ගන්නවා.
2. Comments clean කරලා, author names hash කරලා **MongoDB** එකේ save කරනවා.
3. හැම comment එකකම **sentiment, emotion, question ද** කියලා හොයනවා.
4. Comment එක video එකේ **topic එකකට** සම්බන්ධ කරලා, ඒ topic එකේ **retention** සහ **audio** data එක්ක ගලපනවා.
5. Output දෙනවා:
   - **Creator ට:** සාක්ෂි සහිත recommendations
   - **Viewer ට:** Viewer Guide

## 3. Models සහ API keys (40s)
| මොකක්ද | මොනවටද | කොහෙද run වෙන්නේ |
|---|---|---|
| **XLM-RoBERTa** | Sentiment | අපේ machine එකේ (Python FastAPI, port 8001). Key එකක් ඕන නැහැ |
| **Claude (Anthropic API)** | Singlish classify, recommendations, viewer guide ලියන්න | Cloud API, `ANTHROPIC_API_KEY` |
| **Lexicon (rules)** | Emotions, confusion tagging, offline fallback | Local, free |
| **YouTube Data API** | Comments, chapters, video details | `YOUTUBE_API_KEY` |
| **MongoDB Atlas** | Data save කරන්න | `MONGODB_URI` |

**Model train කළාද?** නැහැ. Pre-trained models inference සඳහා විතරයි. Sinhala / Singlish labelled data නැති නිසා. Fine-tuning = future work.

**Fail වුණොත්?** API fail වුණොත් / key නැත්නම් auto **lexicon** එකට මාරු වෙනවා, system එක නවතින්නේ නැහැ.

## 4. Novelty (25s)
- **Sentiment score එකෙන් නවතින්නේ නැහැ.** Comments + video topics + retention + audio එකතු කරලා "**මොන කොටසේද, ඇයි, මොනවා කරන්නද**" කියනවා.
- **Sinhala + Singlish + English** support.
- හැම recommendation එකකටම **numbers සහ real comment quotes** (evidence).
- **Creator ට සහ Viewer ට** දෙන්නටම output.

## 5. අන්තිමට කියන්න (එක වාක්‍යයක්)
> "We don't stop at sentiment. We fuse comments with the video's own topics, retention and audio to tell the creator exactly which part to fix, and why."

---
**ප්‍රශ්න ආවොත් (කෙටියෙන්):**
- *Train කළාද?* නැහැ, pre-trained inference.
- *Privacy?* Author names SHA-256 hash, Claude ට යවන්නේ comment text විතරයි.
- *Limitation?* Thresholds අතින් තෝරපු ඒවා, evaluation set එක කුඩායි, retention/audio data අනිත් components වලින් එන්නේ.
