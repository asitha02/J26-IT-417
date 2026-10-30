# Component 3 – Technology නොදන්නාට සරල Note

මේක කියවලා ඉවර වුනාම component එක ගැන දැනගන්න ඕන ඔක්කොම දැනගන්න පුළුවන්. අමාරු වචන හැම එකක්ම සරලව පැහැදිලි කරලා තියෙනවා.

---

## 1. කතාවක් විදිහට (මුලින්ම මේක කියවන්න)

හිතන්න ඔබ YouTube එකේ educational video හදන කෙනෙක්. ඔබේ video එකට comments 500ක් ආවා. ඒවා ඔක්කොම කියවන්න ඔබට වෙලාවක් නැහැ. ඒ වගේම සමහර comments සිංහලෙන්, සමහර ඒවා "mama therune na" වගේ English අකුරෙන් ලියපු සිංහල (Singlish).

**අපේ system එක කරන්නේ:**
1. ඒ comments 500ම කියවනවා.
2. "මේ පුද්ගලයා සතුටින්ද, අකමැත්තෙන්ද, අවුල් වෙලාද?" කියලා හොයනවා.
3. "මේ අවුල් ඔක්කොම video එකේ **2:35 කොටසේ** තියෙන්නේ" කියලා හොයාගන්නවා.
4. ඔබට කියනවා: **"2:35 කොටස ආයෙ පැහැදිලි කරන්න. කොමෙන්ට් 20න් 8ක්ම ඒකේ අවුල් කියලා තියෙනවා."**

ඒක තමයි component එක. **Comments → අවබෝධය → ඔබට උපදෙස්.**

---

## 2. Input සහ Output (ඇතුලට දෙන්නේ සහ එළියට එන්නේ)

**ඇතුලට දෙන්නේ:** YouTube video එකේ link එක විතරයි. (Comments system එකම YouTube එකෙන් අරගන්නවා.)

**එළියට එන්නේ (screen එකේ පෙන්නන්නේ):**
| දේ | මොකක්ද |
|---|---|
| Summary | සතුටු comments කීයද, අකමැති ඒවා කීයද, ප්‍රධාන හැඟීම් මොනවාද |
| Insights | video එකේ කොයි කොටසේ ප්‍රශ්නයක් හෝ ආසාවක් තියෙනවාද |
| Recommendations | ඔබ (creator) කරන්න ඕන දේ |
| Viewer guide | අලුතෙන් බලන කෙනෙක්ට උපදෙස් ("මේ කොටස අමාරුයි, හෙමින් බලන්න") |

---

## 3. System එකේ කොටස් (ඔක්කොම දැනගන්න ඕන නැහැ, මේ ටික ඇති)

| කොටස | සරලව | උපමාව |
|---|---|---|
| **Chrome extension** | YouTube video එක බලන ගමන් button එකක් එබුවම dashboard එක open කරනවා | කෙටි මග බොත්තමක් |
| **Dashboard (frontend)** | ඔබ screen එකේ දකින පිටුව | restaurant එකේ මේසය |
| **Backend** | පිටිපස්සේ වැඩ කරන කොටස. comments ගන්නවා, analyze කරනවා | restaurant එකේ කුස්සිය |
| **Database (MongoDB)** | Data ගබඩා කරන තැන | ගබඩාව |
| **ml_service** | RoBERTa කියන AI එක run කරන පොඩි වැඩසටහනක් | කුස්සියේ විශේෂ chef කෙනෙක් |

---

## 4. අමාරු වචන, සරලව (Glossary)

| වචනය | අර්ථය |
|---|---|
| **API** | එක වැඩසටහනක් තව වැඩසටහනකින් යමක් ඉල්ලන්න ඇති "කවුළුව". උදා: අපි YouTube API එකෙන් comments ඉල්ලනවා. |
| **API key** | ඒ කවුළුවෙන් ඉල්ලන්න ඇති රහස් password එක. |
| **Model (AI model)** | දත්ත ගොඩක් බලලා ඉගෙන ගත්ත, තීරණ ගන්න පුළුවන් "මොළයක්". |
| **Train කිරීම** | Model එකට උදාහරණ ලක්ෂ ගණනක් පෙන්නලා ඉගැන්වීම. **අපි මේක කරලා නැහැ.** |
| **Pre-trained** | වෙන කෙනෙක් (උදා: Hugging Face, Anthropic) කලින්ම ඉගැන්නුවා. අපි ඒක විතරක් **පාවිච්චි** කරනවා. |
| **Fine-tune** | Pre-trained model එකට අපේ data වලින් තව ටිකක් ඉගැන්වීම. **අපි මේකත් කරලා නැහැ.** |
| **RoBERTa** | Comment එකක් "හොඳද / නරකද / සාමාන්‍යද" කියලා කියන්න පුළුවන් AI model එකක්. භාෂා ගොඩකට වැඩ කරනවා. |
| **Claude** | Anthropic සමාගමේ AI. අපි ඒකෙන් comments තේරුම් ගන්නවා සහ උපදෙස් ලියවනවා. Internet හරහා ඉල්ලනවා. |
| **Sentiment** | Comment එකේ ස්වභාවය: හොඳ (positive), නරක (negative), සාමාන්‍ය (neutral). |
| **Retention** | Video එකේ එක එක තත්පරේ තවමත් බලන් ඉන්න අයගේ ප්‍රතිශතය. බොහෝ දෙනා අතරමග යන තැන් පෙන්නනවා. |
| **JSON** | Data පිළිවෙලට නම් දීලා ලියන format එකක්. Backend එක dashboard එකට data දෙන්නේ මේකෙන්. |
| **Keyword rules / Lexicon** | "නරක", "හොඳයි", "තේරෙන්නේ නෑ" වගේ වචන ලැයිස්තුවක් බලලා තීරණය කරන සරල ක්‍රමය. AI එකක් නෙවෙයි. |
| **Fallback** | Plan A කැඩුනොත් ස්වයංක්‍රීයව Plan B එකට මාරු වීම. |
| **Cache** | එක පාරක් download කරපු දෙයක් laptop එකේම තියාගැනීම, ආයෙ download නොකරන්න. |
| **Hash** | නමක් ආපහු කියවන්න බැරි කේතයකට හරවනවා ("Kamal" → "viewer_3fa9c1"). Privacy වලට. |

---

## 5. AI එකෙන් වෙන්නේ මොකක්ද? (වැදගත්ම කොටස)

**අපි කිසිම AI එකක් අලුතෙන් හැදුවේ නැහැ, train කළෙත් නැහැ.** අපි හැදුවේ ඒවා **පාවිච්චි කරලා වැඩේ කරන system එක**.

| AI | කරන්නේ මොකක්ද | කොහෙද තියෙන්නේ |
|---|---|---|
| **RoBERTa** | Comment එක හොඳද නරකද කියනවා | අපේ laptop එකේ (පළවෙනි වතාවේ download වෙලා cache වෙලා) |
| **Claude** | Comments තේරුම් ගන්නවා, උපදෙස් සහ guide ලියනවා | අපේ laptop එකේ නැහැ. Internet හරහා ඉල්ලනවා |
| **Keyword rules** | Backup එක. AI සේවා නැති වෙලාවට | අපේ code එකේම |

**Backup එක (Fallback):** RoBERTa හෝ Claude වැඩ නොකළොත්, system එක නවතින්නේ නැතුව keyword rules වලට මාරු වෙනවා.

---

## 6. "අලුත් දේ" මොකක්ද? (Novelty, ප්‍රධාන වැදගත්ම කොටස)

සාමාන්‍ය tool එකක් කියන්නේ: **"60% හොඳයි, 20% නරකයි."** ඒකෙන් creator ට කරන්න දෙයක් නැහැ.

අපේ component එක කියන්නේ: **"2:35 කොටසේ 40%ක්ම අවුල් වෙලා. ඒ අතරම ඒ කොටසේදී viewers බොහෝ දෙනා video එක නවත්තනවා. ඒක ආයෙ පැහැදිලි කරන්න."**

ඒකට හේතු:
1. **Comments + video එකේ දත්ත** (topics, retention, audio) එකතු කරනවා.
2. **කොයි කොටසේද** කියලා හරියටම කියනවා.
3. **සාක්ෂි** (numbers සහ real comments) දෙනවා.
4. **සිංහල, Singlish, English** තුනම තේරුම් ගන්නවා.
5. AI fail වුනත් **නවතින්නේ නැහැ**.

---

## 7. API keys (ඔබට password තුනක් විතරයි)

| Key | මොනවටද |
|---|---|
| YouTube key | YouTube එකෙන් comments සහ video details ගන්න |
| Claude (Anthropic) key | Claude පාවිච්චි කරන්න |
| MongoDB | Data ගබඩා කරන්න |

RoBERTa එකට key එකක් ඕන නැහැ.

---

## 8. Panel එකට කියන්න ඕන ප්‍රධාන දේවල් 5 (මේක ඉගෙන ගන්න)

1. **Problem:** Comments ගොඩක්, creator ට කියවන්න බැහැ, සිංහල/Singlish tools වලට තේරෙන්නේ නැහැ.
2. **Solution:** Comments auto කියවලා, video එකේ කොයි කොටසේද ප්‍රශ්නය කියලා සාක්ෂි සහිතව උපදෙස් දෙනවා.
3. **Novelty:** Comments, video එකේ retention / audio දත්ත එක්ක එකතු කිරීම සහ සිංහල/Singlish support.
4. **AI:** අලුතෙන් train කළේ නැහැ. Pre-trained RoBERTa සහ Claude පාවිච්චි කළා. Backup keyword rules.
5. **Limitation:** Model fine-tune කරලා නැහැ (future work). Retention / audio data අනිත් components වලින් ගන්නවා.

---

## 9. අහන්න පුළුවන් ප්‍රශ්න (උත්තර සරලව)

| ප්‍රශ්නය | උත්තරය |
|---|---|
| Model එක train කළාද? | නැහැ. කලින් train කරපු ඒවා පාවිච්චි කළා. සිංහල data ප්‍රමාණවත් නැති නිසා. අනාගතයේදී කරන්න පුළුවන්. |
| Model එක කොහෙද? | RoBERTa = අපේ laptop එකේ. Claude = internet හරහා, Anthropic සමාගමේ server එකේ. |
| Singlish තේරෙනවද? | Claude සහ keyword lists වලින් තේරෙනවා. RoBERTa Singlish වලට ටිකක් දුර්වලයි. |
| AI නැත්නම් මොකද වෙන්නේ? | Keyword rules වලට ස්වයංක්‍රීයව මාරු වෙනවා. |
| ඔයාලගේ recommendations හරිද කියලා කොහොමද දන්නේ? | හැම එකකටම numbers සහ real comments සාක්ෂි විදිහට තියෙනවා. |
| Privacy? | Public comments විතරයි. නම් hash කරලා save කරනවා. |
| Accuracy කීයද? | *(Evaluation run කරලා number එක මෙතනට ලියාගන්න)* |

---

## 10. දැනගත්තේ නැති දෙයක් ඇහුවොත්
හොඳම උත්තරය අවංකව: **"ඒ ගැන මම මගේ team එකෙන් confirm කරගෙන කියන්නම්"** හෝ **"ඒක අපේ future work එකක්."** හොරෙන් හදන්න එපා.
