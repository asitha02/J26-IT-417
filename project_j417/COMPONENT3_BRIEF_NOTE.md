# Component 3 – කෙටි Note

**Audience Feedback Mining and Evidence-Based Improvement Recommendations**

## 1. මොකක්ද මේක?
YouTube video එකකට එන comments (English / සිංහල / Singlish) auto කියවලා, creator ට **"මොනවා හදන්නද"** කියලා කියන system එකක්.

## 2. ප්‍රශ්නය
- Comments සිය ගණනක් කියවන්න බැහැ.
- Views, likes වලින් **ඇයි** කියලා කියන්නේ නැහැ.

## 3. අපි කරන්නේ කොහොමද? (පියවර 5)
1. YouTube URL එක දුන්නම video details, chapters, comments ගන්නවා.
2. හැම comment එකකම **sentiment, emotion, question ද** කියලා හොයනවා.
3. Comment එක video එකේ **topic එකකට** සම්බන්ධ කරනවා.
4. Topic එකේ **retention** සහ **audio** data එක්ක ගලපලා **ප්‍රශ්න / interests** හොයනවා.
5. Output දෙනවා:
   - **Creator ට:** සාක්ෂි සහිත recommendations
   - **Viewer ට:** Viewer Guide (මොන කොටස අමාරුද, මොනවා හොඳද)

## 4. Technique
| Analyzer | මොකටද |
|---|---|
| **XLM-RoBERTa** | Sentiment (multilingual) |
| **Claude** | Singlish තේරුම් ගන්න, recommendations සහ viewer guide ලියන්න |
| **Lexicon (rules)** | Offline fallback, emotions, confusion tagging |

API fail වුණොත් / key නැත්නම් auto **lexicon** එකට මාරු වෙනවා.

## 5. Novelty (අලුත් දේ)
> Sentiment score එකෙන් නවතින්නේ නැහැ. Comments + video topics + retention + audio එකතු කරලා **"මොන කොටසේද, ඇයි, මොනවා කරන්නද"** කියනවා.

- Sinhala / Singlish support
- හැම recommendation එකකටම numbers සහ real comment quotes
- Creator ට සහ Viewer ට දෙන්නටම output
- Result එක කුමන model එකෙන්ද කියලා UI එකේ පෙන්නනවා

## 6. Integration
Sentiment timeline එක **C4** (audio) component එකට යනවා, ඒකේ audio findings confirm කරන්න.

## 7. Model train කළාද?
**නැහැ.** Pre-trained models inference සඳහා පාවිච්චි කළා. Sinhala / Singlish labelled data නැති නිසා. Fine-tuning = future work.

## 8. Tech stack
React (Dashboard) · Chrome Extension · Node/Express · MongoDB · Python FastAPI (RoBERTa) · YouTube Data API · Claude API

## 9. Privacy
Public comments විතරයි. Author names SHA-256 hash කරනවා. Claude ට යවන්නේ comment text විතරයි.

## 10. Limitations (අවංකව කියන්න)
- Model fine-tune කරලා නැහැ.
- Thresholds (25%, 40%, 10 pts) අතින් තෝරපු ඒවා.
- Evaluation set එක කුඩායි, sentiment එකට විතරයි.
- Retention / audio data එන්නේ අනිත් components වලින්.

## 11. එක වාක්‍යයෙන්
> "We don't stop at sentiment. We fuse comments with the video's own topics, retention and audio to tell the creator exactly which part to fix, and why."
