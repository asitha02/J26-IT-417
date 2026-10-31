# J26-IT-417

Research project. This repo's `project_j417/` folder holds the code.

## Component 3 – Audience feedback mining evidence-based improvement recommendations​

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions, and turns them into content-improvement recommendations.

| Folder (inside `project_j417/`) | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite) dashboard |
| `backend/` | Express + Mongoose API, comment ingestion, analyzers, fusion and recommendations |
| `ml_service/` | FastAPI service running a multilingual RoBERTa sentiment model |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

### How it works
Fetch comments and chapters from YouTube, clean and anonymise them, classify each comment (sentiment, emotions, question), link comments to video topics, compare with retention and audio data from the other components, and produce evidence-based recommendations (Clarification, Content Expansion, Content Structuring, Audio Alignment) and a viewer guide. Detection rules, API list and limitations: [project_j417/FEEDBACK_MINING_README.md](project_j417/FEEDBACK_MINING_README.md)

### Run
Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`, fill in the values (never commit `.env`), then:

```
cd project_j417/backend && npm install && npm run dev      # API on :5000
cd project_j417/frontend && npm install && npm run dev      # UI on :5173
```

For `ANALYZER=bert`, also start the sentiment service (the model, about 1 GB, downloads on first run):

```
cd project_j417/ml_service
py -m pip install -r requirements.txt
py -m uvicorn app:app --port 8001                           # sentiment service on :8001
```

Load `project_j417/extension/` via `chrome://extensions` → Load unpacked.

### Analyzers
`ANALYZER` in `backend/.env`:

| Value | Sentiment | Emotions / questions | Recommendations |
|---|---|---|---|
| `bert` | RoBERTa (`ml_service/`) | keyword rules | rule-based |
| `llm` | Claude | Claude | Claude |
| `lexicon` | keyword rules | keyword rules | rule-based |
| `auto` | Claude if `ANTHROPIC_API_KEY` is set, else `lexicon` | same | same |

If the sentiment service or the Claude API fails, the analyzer falls back to the offline `lexicon`. The UI shows which analyzer produced each result.

### Evaluation
```
cd project_j417/backend
npm run evaluate -- --analyzer bert      # or llm | lexicon
```
Compares sentiment output against the hand-labelled `samples/labelled-comments.json` and prints accuracy, per-class precision/recall/F1, macro F1 and a confusion matrix.

### Models and APIs
- **Model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment`, a pre-trained multilingual RoBERTa from Hugging Face (not fine-tuned here). Downloaded once to the local Hugging Face cache.
- **YouTube Data API v3:** video metadata, chapters and comments (`YOUTUBE_API_KEY`).
- **Anthropic API (Claude):** optional; classification, recommendations and the viewer guide (`ANTHROPIC_API_KEY`).
- **MongoDB Atlas:** stores comments, videos, analyses and users (`MONGODB_URI`).

### AI usage
No model is trained in this project. Sentiment can come from a pre-trained RoBERTa model (`ANALYZER=bert`); comments can instead be classified and recommendations written by Claude via the Anthropic API (`ANALYZER=llm`, or `auto` with an API key). Without a key, a keyword-rule fallback (`lexicon`) is used.

### Privacy
Only public comment data is used. Author handles are replaced by a one-way hash (`viewer_xxxxxxxx`) before storage, and individuals are not profiled.

More detail: [project_j417/FEEDBACK_MINING_README.md](project_j417/FEEDBACK_MINING_README.md)
