# Component 3 – සිංහලෙන් තේරුම් ගන්න Note

## 1. ප්‍රශ්නය මොකක්ද?
- YouTube video එකකට comments සිය ගණනක් එනවා. Creator ට ඒ ඔක්කොම කියවන්න බැහැ.
- Comments English, සිංහල, Singlish වලින් තියෙනවා. සාමාන්‍ය tools වලට ඒවා තේරෙන්නේ නැහැ.
- Views සහ likes වලින් කියන්නේ කීදෙනෙක් බැලුවාද කියලා විතරයි. **ඇයි** අවුල් වුනේ කියලා කියන්නේ නැහැ.

## 2. අපි කරන්නේ මොකක්ද?
Comments ඔක්කොම අපේ system එක කියවනවා. ඊට පස්සේ video එකේ **කොයි කොටසේද** ප්‍රශ්නයක් තියෙන්නේ කියලා හොයලා, creator ට **කරන්න ඕන දේ** කියනවා.

> උදාහරණය: "20 දෙනෙක්ගෙන් 8 දෙනෙකුට 2:35 කොටස තේරුනේ නැහැ. ඒක ආයෙ පැහැදිලි කරන්න."

## 3. Input සහ Output
**Input (ඇතුලට දෙන්නේ):**
- YouTube video එකේ URL එක
- Comments (YouTube API එකෙන් auto ගන්නවා)
- Video එකේ topics (description එකේ chapters වලින්)
- Retention සහ audio data (අනිත් components වලින්)

**Output (එළියට එන්නේ):**
- **Summary:** sentiment %, ප්‍රධාන emotions
- **Insights:** මොන topic එකේ මොන ප්‍රශ්නයද, නැත්නම් ආසාවද
- **Recommendations:** creator කරන්න ඕන දේ
- **Viewer guide:** අලුතෙන් බලන කෙනෙක්ට උපදෙස්

Output එක **JSON** (data පිළිවෙලට ලියන format එකක්) විදිහට එනවා. Dashboard එක ඒක cards විදිහට පෙන්නනවා.

## 4. වැඩ කරන විදිහ (පියවර 4)
1. **පිරිසිදු කරනවා:** එක වගේ comments අයින් කරනවා, භාෂාව හඳුනාගන්නවා, නම් hash කරනවා (privacy).
2. **Analyze කරනවා:** හැම comment එකකම sentiment (හොඳ / නරක / සාමාන්‍ය), emotion, ප්‍රශ්නයක්ද කියලා බලනවා.
3. **Video එක එක්ක ගලපනවා:** Comment එක video එකේ කොයි topic එකටද කියලා සම්බන්ධ කරනවා. ඊට පස්සේ ඒ කොටසේ retention සහ audio data එකතු කරනවා.
4. **Recommendations දෙනවා:** සාක්ෂි (numbers සහ real comments) එක්ක.

**Emotions 6ක්:** ව්‍යාකූලත්වය (Confusion), කුතුහලය (Curiosity), එකඟතාව (Agreement), විරුද්ධත්වය (Disagreement), කෝපය / කලකිරීම (Frustration), උද්යෝගය (Enthusiasm).

**හොයාගන්න දේවල් 6ක්:** ව්‍යාකූලත්වය, නොදුන් උත්තර සහිත ප්‍රශ්න, ඉහළ ආසාව, නරක ප්‍රතිචාර, retention අඩු වීම, audio ගැලපෙන්නේ නැතිකම.

## 5. අලුත් දේ (Novelty)
1. **සිංහල, Singlish, English** තුනම තේරුම් ගන්නවා.
2. Sentiment විතරක් නෙවෙයි, comments **video එකේ topics, retention, audio** එක්ක එකතු කරනවා (මේක තමයි ප්‍රධානම අලුත් දේ).
3. Video එකේ **කොයි කොටසේද** ප්‍රශ්නය කියලා කියනවා.
4. හැම recommendation එකකටම **සාක්ෂි** තියෙනවා.
5. Creator ට සහ viewers ට දෙන්නටම output තියෙනවා.
6. AI service එකක් fail වුනත් system එක **නවතින්නේ නැහැ** (backup එකක් තියෙනවා).

## 6. Model train කළාද?
**නැහැ.** කලින් train කරපු models විතරයි පාවිච්චි කරන්නේ.

| Model | මොනවටද |
|---|---|
| **RoBERTa** (Hugging Face) | Sentiment හොයන්න |
| **Claude** (Anthropic API) | Comments classify කරන්න, recommendations සහ viewer guide ලියන්න |
| **Keyword rules** | Backup එක (internet නැතුව) |

**ඇයි train නොකළේ?** සිංහල සහ Singlish labelled data ප්‍රමාණවත් නැහැ. ඒක future work එකක්.

## 7. Model එක කොහෙද තියෙන්නේ?
- **RoBERTa:** project folder එකේ නැහැ. පළවෙනි වතාවට run කරද්දී download වෙලා laptop එකේ cache එකේ තියෙනවා. `ml_service` කියන Python service එකෙන් (port 8001) run කරනවා.
- **Claude:** අපේ laptop එකේ නැහැ. Internet හරහා API එකෙන් call කරනවා.

## 8. API keys
| Key / Service | මොනවටද |
|---|---|
| YouTube API | Comments, chapters, video details ගන්න |
| Anthropic API (Claude) | Analysis, recommendations, viewer guide |
| MongoDB | Data save කරන්න |

RoBERTa එකට key එකක් ඕන නැහැ.

## 9. Privacy
- Public comments විතරයි.
- Author නම් hash කරලා (`viewer_xxxxxxxx`) save කරනවා.

## 10. දුර්වලතා (Limitations) සහ future work
- Model එක fine-tune කරලා නැහැ. **Future:** සිංහල / Singlish dataset එකක් හදලා fine-tune කිරීම.
- 25%, 40%, 10 points වගේ limits අතින් දැම්මේ. **Future:** real data වලින් හරිගස්සන්න.
- Retention සහ audio data පිටින් දෙන්න ඕන.

## 11. එක වාක්‍යයෙන්
**"අපේ component එක, අවුල් සහගත සිංහල / Singlish / English comments, creator ට තේරෙන සාක්ෂි සහිත උපදෙස් බවට පත් කරනවා."**

---

## ඉක්මන් උත්තර (panel එක ඇහුවොත්)
| ප්‍රශ්නය | උත්තරය |
|---|---|
| Model එක train කළාද? | නැහැ, කලින් train කරපු ඒවා පාවිච්චි කළා. Fine-tune කිරීම future work. |
| Model එක කොහෙද? | RoBERTa = laptop cache එකේ (`ml_service` මගින්). Claude = API එකෙන්. |
| Singlish කොහොමද? | Claude සහ keyword lists වලින්. RoBERTa Singlish වලට දුර්වල විය හැකියි. |
| API නැත්නම්? | Keyword rules වලට ස්වයංක්‍රීයව මාරු වෙනවා. |
| අලුත් දේ මොකක්ද? | Comments, video එකේ topics / retention / audio එක්ක එකතු කරලා, කොයි කොටසේද ප්‍රශ්නය කියලා කියන එක. |
| Recommendations හරිද කියලා කොහොමද දන්නේ? | හැම එකකටම numbers සහ real comments සාක්ෂි විදිහට තියෙනවා. |
