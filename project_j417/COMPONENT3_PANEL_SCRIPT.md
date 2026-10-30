# Component 3 – Audience Feedback Mining (විනාඩි 2 Script)

> වචන ~270ක්. සාමාන්‍ය වේගයෙන් කිව්වම විනාඩි 2ක් විතර යනවා. කිහිප සැරයක් practise කරලා time බලන්න.

---

## Script (කෙලින්ම කියන්න)

**1. Problem (තත්පර 20)**
"Good morning. I am [නම], and my component is Audience Feedback Mining. A YouTube video can get hundreds of comments in English, Sinhala and Singlish. A creator cannot read them all, and normal tools do not understand Singlish. Views and likes tell us how many people watched, but not why viewers were confused or unhappy."

**2. What it does (තත්පර 15)**
"My component reads these comments and gives the creator clear, evidence-based advice for the next video. For example: 'viewers are confused at 2:35, re-explain this part.'"

**3. How it works (තත්පර 40)**
"It works in four steps.
One, we clean the comments, detect the language, and hash author names for privacy.
Two, for each comment we find the sentiment, the emotion, and whether it is a question.
Three, and this is our main contribution, we link each comment to a topic in the video using its timestamp or keywords, and combine it with the video's retention and audio data. So we can say, for example, that confusion and a retention drop happen in the same segment.
Four, we turn these findings into recommendations. Every recommendation shows its proof: the percentages and real viewer comments."

**4. AI models (තත්පර 25)**
"We did not train a new model. We use a pre-trained multilingual RoBERTa model for sentiment, and Claude for deeper analysis and for writing recommendations. If either one fails, the system falls back to a keyword-based analyzer for English, Sinhala and Singlish, so it always works. The dashboard shows which analyzer was used."

**5. Evaluation (තත්පර 10)**
"We tested all three analyzers on hand-labelled comments, using accuracy, precision, recall and F1 score. [මෙතනට ඔබේ ඇත්ත accuracy number එක කියන්න.]"

**6. Limitations and close (තත්පර 10)**
"Our limitation is that the model is not fine-tuned. In future, we will build a Sinhala and Singlish dataset and fine-tune it. Thank you."

---

## එක බැල්මෙන් (script එක අමතක වුනොත්)
1. Problem: comments ගොඩක්, Singlish, "ඇයි" කියලා දන්නේ නැහැ
2. Result: creator ට evidence සහිත advice
3. Steps 4: clean → analyze → **fuse with video (retention, audio)** → recommend
4. Models: **train කරලා නැහැ**. Pre-trained RoBERTa + Claude + keyword fallback
5. Evaluation: accuracy / F1 number එක
6. Limitation: fine-tune කරලා නැහැ. Future: Sinhala dataset

## Q&A (ඇහුවොත් විතරක්)
- **Train කළාද?** නැහැ. Sinhala/Singlish labelled data මදි. Fine-tuning future work.
- **Singlish කොහොමද?** RoBERTa දුර්වලයි. ඒකට Singlish word lists සහ Claude තියෙනවා.
- **Recommendation හරිද?** හැම එකකටම numbers සහ real comment quotes සාක්ෂි විදිහට තියෙනවා.
- **API fail වුනොත්?** Keyword analyzer එකට ස්වයංක්‍රීයව මාරු වෙනවා.
- **අනිත් components එක්ක?** Video එකේ topics, retention, audio data ගන්නවා. *(team design එකට ගැලපෙන්න වෙනස් කරන්න.)*

## කලින් කරන්න
- [ ] Evaluation number එක ගන්න: `cd project_j417/backend && npm run evaluate -- --analyzer bert`
- [ ] Time එක practise කරන්න (විනාඩි 2 ඇතුලත)
