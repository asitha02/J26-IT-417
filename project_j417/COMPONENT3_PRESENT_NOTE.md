# Component 3: Audience Feedback Mining

*Turning YouTube comments (English, Sinhala, Singlish) into clear advice for creators*

---

## 1. Problem
- A video gets hundreds of comments. A creator cannot read them all.
- Comments are in English, Sinhala and Singlish. Normal tools do not understand them.
- Views and likes show **how many** watched, not **why** viewers were confused or unhappy.

## 2. Our Solution
Read the comments automatically, find **which part of the video** has a problem or high interest, and give **evidence-based advice**.

> Example: "8 of 20 viewers are confused at 2:35. Re-explain this part."

## 3. Input and Output
| Input | Output (JSON) |
|---|---|
| YouTube video URL | Summary: sentiment %, main emotions |
| Comments (from YouTube API) | Insights: problems and interests, by topic |
| Video topics (chapters) | Recommendations: what the creator should do |
| Retention and audio data (from other components) | Viewer guide: tips for new viewers |

*JSON = a structured data format. The backend sends results as JSON and the dashboard shows them.*

## 4. How It Works
**Comments → Clean → Analyze → Fuse with video data → Insights → Recommendations**

1. **Clean:** remove duplicates, detect language, hash author names
2. **Analyze:** sentiment, emotion (6 types), question or not
3. **Fuse:** link each comment to a video topic, then add retention and audio data
4. **Recommend:** actions with proof (numbers and real comments)

## 5. Novelty
1. Supports **Sinhala, Singlish and English**
2. **Fuses** comments with the video's topics, retention and audio. It does not stop at sentiment.
3. Shows **which part** of the video has the problem
4. Every recommendation has **evidence**
5. Gives output to **creators and viewers**
6. Keeps working if an AI service fails (**fallback**)

## 6. AI Models
**No model was trained.** We use pre-trained models only.

| Model | Used for |
|---|---|
| RoBERTa (Hugging Face, multilingual) | Sentiment |
| Claude (Anthropic API) | Classify comments, write recommendations and viewer guide |
| Keyword rules (EN / සිංහල / Singlish) | Offline fallback |

- RoBERTa runs on our own Python service (`ml_service`, port 8001). The model is downloaded once and stored in the local cache.
- Claude is called through an API.

## 7. API Keys and Services
| Service | Purpose |
|---|---|
| YouTube Data API | Get comments, chapters, video details |
| Anthropic API (Claude) | Analysis, recommendations, viewer guide |
| MongoDB | Store videos, comments and results |

## 8. Evaluation
- Tested on hand-labelled comments
- Measures: accuracy, precision, recall, F1, confusion matrix
- Results: *(ඔබේ numbers මෙතනට දාන්න)*

## 9. Privacy
- Only public comments
- Author names replaced by a one-way hash

## 10. Limitations and Future Work
- Model not fine-tuned. **Future:** build a Sinhala and Singlish dataset and fine-tune.
- Thresholds (25%, 40%, 10 points) are set by hand. **Future:** tune with real data.
- Retention and audio data must come from outside.

## 11. Conclusion
> Our component turns messy multilingual comments into clear, evidence-based advice that helps creators improve their next video.

**Thank you. Questions?**

---

### ඔබට විතරයි: ඉක්මන් උත්තර
- **Train කළාද?** නැහැ, pre-trained. Sinhala data මදි. Fine-tune = future.
- **Model කොහෙද?** RoBERTa = laptop cache එකේ (`ml_service` මගින්). Claude = API.
- **Singlish?** Claude + keyword lists. RoBERTa දුර්වල විය හැකියි.
- **API නැත්නම්?** Keyword rules වලට ස්වයංක්‍රීයව මාරු වෙනවා.
- **Retention / audio කොහෙන්ද?** අනිත් components වලින් (ඔබේ team එකට confirm කරගන්න).
