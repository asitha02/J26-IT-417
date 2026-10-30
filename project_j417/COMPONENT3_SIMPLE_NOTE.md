# Component 3 – සරල Note

## මේක මොකක්ද?
YouTube video එකක comments (English, සිංහල, Singlish) කියවලා, viewers ට මොකක්ද තේරෙන්නේ නැත්තේ, මොකක්ද ආස කියලා හොයනවා. ඊට පස්සේ creator ට ඊළඟ video එක දියුණු කරන්න advice දෙනවා.

## කොහොමද වැඩ කරන්නේ?
1. **Comments ගන්නවා** (YouTube API)
2. **Analyze කරනවා**: sentiment (හොඳ / නරක), emotion (confusion, curiosity...), question ද කියලා
3. **Video එක එක්ක ගලපනවා**: comment එක video එකේ කොයි topic එකටද, ඒ කොටසේ retention සහ audio කොහොමද
4. **Recommendations දෙනවා**: "මේ කොටස ආයෙ පැහැදිලි කරන්න" වගේ, සාක්ෂි (numbers සහ comments) එක්ක

## අලුත් දේ (Novelty)
- **සිංහල + Singlish + English** තේරුම් ගන්නවා
- Sentiment විතරක් නෙවෙයි, **video එකේ කොයි කොටසේද ප්‍රශ්නය** කියලා කියනවා
- Recommendation එකට **සාක්ෂි** තියෙනවා
- API fail වුනත් **නවතින්නේ නැහැ** (fallback)

## Model train කළාද?
**නැහැ.** කලින් train කරපු models විතරයි පාවිච්චි කරන්නේ.

| Model | මොනවටද |
|---|---|
| **RoBERTa** (Hugging Face) | Sentiment විතරයි |
| **Claude** (API) | Comments classify කරන්න, recommendations සහ viewer guide ලියන්න |
| **Keyword rules** | Backup එක (offline) |

## Model එක කොහෙද?
- **RoBERTa:** project එකේ නැහැ. Download වෙලා laptop එකේ cache එකේ තියෙනවා (`C:\Users\chamo\.cache\huggingface\hub`). `ml_service/app.py` එකෙන් run කරනවා (port 8001).
- **Claude:** අපේ machine එකේ නැහැ. API එකෙන් call කරනවා.

## API keys
| Key | මොනවටද |
|---|---|
| YouTube API key | Comments සහ video details ගන්න |
| Anthropic API key | Claude පාවිච්චි කරන්න |
| MongoDB | Data save කරන්න |

(RoBERTa එකට key එකක් ඕන නැහැ.)

## පහසුවෙන් අහන ප්‍රශ්න
- **Train කළාද?** නැහැ, pre-trained. Sinhala data මදි නිසා. Fine-tune කිරීම future work.
- **Singlish කොහොමද?** Claude සහ keyword lists වලින්.
- **API නැත්නම්?** Keyword rules වලට ස්වයංක්‍රීයව මාරු වෙනවා.
- **Privacy?** Public comments විතරයි, නම් hash කරනවා.

## Limitations
- Model fine-tune කරලා නැහැ
- Thresholds (25%, 40%) අතින් දැම්මා
- Retention / audio data පිටින් දෙන්න ඕන

## Code එක තියෙන තැන් (ඕන වුනොත් විතරක්)
- Fusion (main logic): `backend/src/services/fusion.service.js`
- RoBERTa service: `ml_service/app.py`
- Claude analyzer: `backend/src/services/analyzers/llm.analyzer.js`
- Recommendations: `backend/src/services/recommendation.service.js`
