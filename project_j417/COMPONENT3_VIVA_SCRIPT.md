# Viva – කතා කරන්න ඕන දේ (Component 3)

Panel එකට කතා කරන්න ලියපු සරල සිංහල. අකුරටම පාඩම් කරන්න එපා, අදහස් මතක තියාගෙන ඔයාගේ වචනවලින් කියන්න. තාක්ෂණික වචන (sentiment, API, model වගේ) English වලින්ම කියන්න.

---

## 1. ආරම්භය (තත්පර 30)

"සුභ උදෑසනක්. මම චාමොද්, Member 3. මගේ component එක **Audience Feedback Mining and Content Improvement Recommendation**.

සරලවම කිව්වොත්, YouTube video එකක comments කියවලා, ප්‍රේක්ෂකයෝ ඒ ගැන මොනවද හිතන්නේ කියලා තේරුම් අරගෙන, creator ට video එක හොඳ කරගන්න මොනවද කරන්න ඕන කියලා සාක්ෂි එක්ක කියනවා."

## 2. ගැටලුව (තත්පර 30)

"ජනප්‍රිය video එකකට comments දහස් ගණනක් එනවා. creator ට ඒ ඔක්කොම කියවන්න බැහැ.

දැනට තියෙන tools වලින් දෙන්නේ '62% positive' වගේ sentiment score එකක් විතරයි. ඒකෙන් මොනවද හදන්න ඕන කියලා කියන්නේ නැහැ.

ඒ වගේම ශ්‍රී ලංකාවේ comments ගොඩක් Sinhala වලින්, නැත්නම් Singlish වලින් තියෙන්නේ. ඒ කියන්නේ English අකුරෙන් ලියපු සිංහලෙන්. සාමාන්‍ය tools වලට මේවා හොඳට තේරෙන්නේ නැහැ."

## 3. මගේ system එක කරන දේ (විනාඩි 1)

"මේක පියවර පහකින් වැඩ කරනවා.

**එක.** YouTube Data API එකෙන් video එකේ විස්තර සහ comments, replies ඇතුළුව ගන්නවා.

**දෙක.** හැම comment එකක්ම පිරිසිදු කරලා, භාෂාව හඳුනාගෙන, author ගේ නම hash කරලා MongoDB එකේ save කරනවා.

**තුන.** හැම comment එකක්ම classify කරනවා: sentiment, emotions, ප්‍රශ්නයක්ද කියලා.

**හතර.** Comments video එකේ topics එක්ක ගැලපෙනවා, topic එකක් අනුව ගැටලු හොයනවා. උදා: එක කොටසක ගොඩක් අය confuse වෙලා නම් ඒක flag කරනවා.

**පහ.** සාක්ෂි එක්ක recommendations ලියනවා. ඒ වගේම අනාගත viewers ලට guide එකකුත් හදනවා.

මේ ඔක්කොම React dashboard එකේ පෙන්නනවා. YouTube page එකේදීම dashboard එක ඇරෙන Chrome extension එකකුත් තියෙනවා."

## 4. Demo කරන key functions දෙක (විනාඩි 1)

"මම functions දෙකක් පෙන්වනවා.

**පළමුවෙනි function: comment analysis.** video link එකක් දුන්නාම system එක හැම comment එකක්ම classify කරනවා. sentiment එකට මම **pre-trained** බහුභාෂා XLM-RoBERTa model එකක් පාවිච්චි කළා. අතින් label කරපු comments 28කින් ඒක test කළා. 26ක් හරි, ඒ කියන්නේ **accuracy 92.9%**.

**දෙවෙනි function: recommendations.** Topic එකක් අනුව රටා හයක් පරීක්ෂා කරනවා: confusion, unanswered questions, high interest, negative reception, retention drop, audio mismatch. හැම එකකටම comments ගණන, percentage, සැබෑ comment උදාහරණ සාක්ෂි විදියට තියෙනවා."

## 5. Input සහ Output (තත්පර 30)

"**Input:** YouTube video link එකක් හෝ ID එකක්, ඒකේ comments. වෙන components වලින් එන topics, retention, audio දත්තත් ඕන නම් පාවිච්චි කරනවා.

**Output:** හැම comment එකකටම sentiment, emotions, ප්‍රශ්නද කියලා. සම්පූර්ණ video එකට sentiment සාරාංශයක්, content gaps, recommendations සහ viewer guide එකක්. ප්‍රතිඵල MongoDB එකේ save වෙනවා, dashboard එකේ පේනවා."

## 6. පාවිච්චි කරපු තාක්ෂණ (තත්පර 45)

"Backend එක Node.js සහ Express. Dashboard එක React සහ TypeScript. දත්ත තියෙන්නේ MongoDB එකේ.

Sentiment එකට pre-trained XLM-RoBERTa model එක දුවන්නේ පොඩි Python FastAPI service එකක, Hugging Face Transformers එක්ක. **මම ඒ model එක train කළේ නැහැ.** ඒක ඒ විදියටම ගෙන, මගේම labelled data වලින් **evaluate** කළා.

Emotions සහ ප්‍රශ්න හඳුනාගන්න English, Sinhala, Singlish keyword rules පාවිච්චි කරනවා. ඒ වගේම Anthropic API එකෙන් Claude පාවිච්චි කරන්නත් පුළුවන්, ඒක optional. model service එක හෝ API එක fail වුණොත් keyword method එකට ස්වයංක්‍රීයව මාරු වෙනවා. ඒ නිසා system එක කවදාවත් නවතින්නේ නැහැ. ප්‍රතිඵලය හැදුවේ මොන method එකෙන්ද කියලා dashboard එකේ badge එකකින් පෙන්නනවා."

## 7. වෙන components එක්ක සම්බන්ධය (තත්පර 30)

"Video collection එකේ topics, retention, audio signals වෙන components වලින් එනවා. මම ඒවා කියවලා comments එක්ක ගැලපෙනවා. Component 4 ගේ audio findings තහවුරු කරන්න මගේ sentiment timeline එක පාවිච්චි වෙනවා."

## 8. මේක මගේ ම වැඩක් කියන්නේ ඇයි (තත්පර 30)

"මගේ Git history එකේ මුල ඉඳන් මගේ commits පේනවා: backend, dashboard, Chrome extension, comments ගැනීම, analyzers, recommendation logic සහ evaluation script එක.

System එකේ කොටසක් විදියට AI tools පාවිච්චි කළා. ඒක README එකේ AI usage කොටසේ ලියලා තියෙනවා."

## 9. Ethics (තත්පර 20)

"මම පාවිච්චි කරන්නේ official YouTube API එකෙන් ගන්න public comments විතරයි. ලියපු අයගේ නම් save කරන්න කලින් one-way hash එකකට හරවනවා. පුද්ගලයන් profile කරන්නේ නැහැ."

## 10. මගේ component එක අයින් කළොත් (තත්පර 20)

"Feedback loop එක නැති වෙනවා. ප්‍රේක්ෂකයෝ video එකට ප්‍රතිචාර දැක්වූයේ කොහොමද, මොකක් වෙනස් කරන්නද කියලා creator ට කියන්න system එකට බැරි වෙනවා."

## 11. සීමාවන් සහ අවසානය (තත්පර 30)

"සීමාවන්: labelled data comments 28ක් විතරයි, Singlish වල model එක දුර්වලයි, thresholds තාම tune කරලා නැහැ, සැබෑ creators එක්ක human evaluation එකක් තාම කරලා නැහැ. ඊළඟ පියවර තමයි තව data label කිරීම, Singlish වැඩි දියුණු කිරීම, සහ creators ලා එක්ක test කිරීම.

ස්තූතියි. ප්‍රශ්න තියෙනවා නම් අහන්න."

---

# ඇහෙන්න පුළුවන් ප්‍රශ්න සහ කෙටි පිළිතුරු

**Model එක train කළාද?**
"නැහැ. Hugging Face එකෙන් pre-trained XLM-RoBERTa model එකක් ගත්තා. මගේ වැඩේ තමයි ඒක system එකට සම්බන්ධ කිරීම, මගේම labelled data වලින් evaluate කිරීම, සහ recommendation logic එක. Sinhala / Singlish labelled data ප්‍රමාණවත් නැති නිසා fine-tune කළේ නැහැ, ඒක future work."

**Model එක තියෙන්නේ කොහෙද?**
"මගේ laptop එකේ Hugging Face cache එකේ, local FastAPI service එකක් විදියට දුවනවා."

**ඇයි RoBERTa වගේම lexicon (keyword rules) ත් ඕන?**
"RoBERTa දෙන්නේ sentiment විතරයි. Emotions සහ ප්‍රශ්න හඳුනාගන්නත්, model එක fail වුණාම fallback එකටත් rules ඕන."

**ඇයි Claude විතරක් නෙවෙයි, RoBERTa පාවිච්චි කළේ?**
"RoBERTa නොමිලේ, offline දුවන්නත් පුළුවන්. Claude වලට key එකකුත් internet එකකුත් ඕන, ගාස්තුවකුත් තියෙනවා. ඒ නිසා දෙකම support කරලා, එකම evaluation script එකෙන් සසඳන්න පුළුවන් විදියට හැදුවා."

**නිරවද්‍යතාව කීයද?**
"අතින් label කරපු comments 28කින් 92.9%. sample එක පොඩියි, ඒ නිසා මේක මුල් ප්‍රතිඵලයක් විදියට සලකනවා."

**කොතනද වැරදෙන්නේ?**
"Singlish වල. වැරදුණු දෙක Singlish comments. Sentiment model එකට Singlish දුර්වලයි."

**Sinhala සහ Singlish ගැන කොහොමද?**
"Model එක බහුභාෂා නිසා Sinhala අකුරු හොඳටම හසුරුවනවා. Singlish වලට keyword rules එකතු කළා, Claude පාවිච්චි කරන්නත් පුළුවන්. ඒත් Singlish තමයි තාම දුර්වලම තැන."

**AI service එක down වුණොත්?**
"ස්වයංක්‍රීයව keyword method එකට මාරු වෙනවා, ඒ නිසා user ට තාමත් ප්‍රතිඵලයක් ලැබෙනවා. ප්‍රතිඵලය හැදුවේ මොන method එකෙන්ද කියලා dashboard එකේ පෙන්නනවා."

**Recommendations හැදෙන්නේ කොහොමද?**
"Comment එකක් topic එකකට ගැලපෙන්නේ timestamp එකෙන්, නැත්නම් keyword overlap එකෙන්. ඊට පස්සේ topic එකක් අනුව rules පරීක්ෂා කරනවා. උදා: confused 25%ට වඩා, unanswered questions 2ට වඩා, negative 40%ට වඩා, retention drop points 10ට වඩා. හැම rule එකකින්ම comments වලින් සාක්ෂි එක්ක recommendation එකක් හැදෙනවා. වර්ග හතර: Clarification, Content Expansion, Content Structuring, Audio Alignment."

**Evidence කියන්නේ මොකක්ද?**
"Comments ගණන, percentage, සහ ඇත්ත comment උදාහරණ."

**Privacy ආරක්ෂා කරන්නේ කොහොමද?**
"Official API එකෙන් ගන්න public data විතරයි. ලියපු අයගේ නම් save කරන්න කලින් hash කරනවා (viewer_xxxxxxxx). පුද්ගලයන් profile කරන්නේ නැහැ."

**Thresholds (25%, 40%) තෝරගත්තේ කොහොමද?**
"අතින් දැම්මා, තාම tune කරලා නැහැ. සැබෑ data එක්ක tune කරන එක ඊළඟ පියවරක්."

**ඊළඟ පියවර මොනවාද?**
"තව data label කිරීම, Singlish වැඩි දියුණු කිරීම, සැබෑ creators ලට පෙන්නලා feedback ගැනීම, සහ RoBERTa සහ Claude එකම data මත සසඳීම."

---

# උපදෙස්

- හෙමින් කතා කරන්න. වාක්‍යයකට පස්සේ පොඩි විරාමයක් දෙන්න.
- Demo එකට කලින් `ml_service` එක run කරන්න (`py -m uvicorn app:app --port 8001`) සහ backend එක `ANALYZER=bert` ද බලන්න.
- Internet නැති වුණොත් පාවිච්චි කරන්න demo එකේ screenshots හෝ video එකක් තියාගන්න.
- ප්‍රශ්නයක් තේරුණේ නැත්නම් "කරුණාකරලා ආයෙත් කියන්න පුළුවන්ද?" කියන්න.
- දන්නේ නැති දෙයක් ඇහුවොත් අවංකව කියන්න: "ඒක මම තාම test කරලා නැහැ, ඒත් මම ඒක කරන්නේ මෙහෙමයි..." කියලා.
