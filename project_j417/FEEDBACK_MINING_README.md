# Component 3 – Audience feedback mining

Reads the comments on a YouTube video (English, Sinhala, Singlish), works out how viewers reacted to each part of the video, and gives the creator evidence-based recommendations plus a short guide for future viewers.

Views and likes say how many people watched, not why they liked or struggled with it. This component closes that gap by tying comments to the video's topics and showing the comments as proof.

| Folder (inside `project_j417/`) | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite) dashboard |
| `backend/` | Express + Mongoose API: ingestion, analyzers, fusion, recommendations, viewer guide |
| `ml_service/` | FastAPI service running a pre-trained multilingual RoBERTa sentiment model |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

## How it works
```
YouTube URL
  1. Fetch      youtube.service        video info, chapters (topics), comments   (YouTube Data API v3)
  2. Ingest     ingestion.service      clean text, detect language, read timestamps,
                                       hash author handles, drop duplicates      -> MongoDB
  3. Classify   analyzers/             sentiment, emotions, is-it-a-question     -> saved on each comment
  4. Fuse       fusion.service         link comments to topics, compare with retention and audio, find issues
  5. Recommend  recommendation.service + viewerGuide.service                     (Claude, or rule-based fallback)
  6. Save/Show  feedback.service       FeedbackAnalysis in MongoDB; React dashboard and Chrome extension
```

**Linking a comment to a topic:** by the timestamp inside the comment (for example "at 3:20 I got lost") if there is one, otherwise by keyword overlap with the topic name and keywords. Comments that match nothing go to "General discussion".

**What fusion detects per topic** (topics with fewer than 2 comments are ignored):

| Finding | Rule | Recommendation type |
|---|---|---|
| Confusion | at least 2 comments and at least 25% show confusion | Clarification |
| Unanswered questions | 2 or more viewer questions | Content Expansion |
| High interest | at least 40% curious or enthusiastic and at least 50% positive | Content Expansion |
| Negative reception | at least 40% negative (without confusion) | Clarification |
| Retention drop | retention falls 10 or more points inside the segment | Content Structuring |
| Audio mismatch | strong audio (intensity 0.6 or more) over a segment with 30% or more negative comments, or 2 or more confusion comments | Audio Alignment |

Every finding carries its evidence (counts, percentages and the most-liked example comments), and every recommendation cites that evidence.

Retention and audio data come from the other components through `POST /api/videos`. Without them the comment-based findings still work.

## Output
`POST /api/feedback/analyze` returns four parts:

- `analytics_summary`: comments analysed, sentiment split (%), dominant emotions
- `content_gaps_and_insights`: topic or timestamp, what was detected, supporting evidence
- `actionable_recommendations`: type (Clarification, Content Expansion, Content Structuring, Audio Alignment), action item, rationale
- `viewer_guide`: overview, before you watch, watch out for, highlights, common questions

The response also says which analyzer (and Claude model, if used) produced it.

## Run
Copy `project_j417/backend/.env.example` to `project_j417/backend/.env` and `project_j417/frontend/.env.example` to `project_j417/frontend/.env`, fill in the values (never commit `.env`), then:

```
cd project_j417/backend && npm install && npm run dev      # API on :5000
cd project_j417/frontend && npm install && npm run dev      # UI on :5173
```
For `ANALYZER=bert`, also start the sentiment service (model, about 1 GB, downloads on first run):

```
cd project_j417/ml_service
py -m pip install -r requirements.txt
py -m uvicorn app:app --port 8001                           # sentiment service on :8001
```

Load `project_j417/extension/` via `chrome://extensions` → Load unpacked.

## API
Base path `/api` (backend, port 5000).

| Method and path | Purpose |
|---|---|
| `POST /videos/import` | From a YouTube URL: save video, chapters (topics) and comments |
| `POST /videos` | Create or update a video with topics, retention and audio signals (used by the other components) |
| `GET /videos`, `GET /videos/:videoId` | List videos, get one video |
| `POST /videos/:videoId/comments` | Add comments manually |
| `POST /videos/:videoId/comments/youtube` | Fetch more comments from YouTube |
| `GET /videos/:videoId/comments` | List stored comments |
| `POST /feedback/analyze` | Run the full pipeline for one or more videos |
| `GET /feedback/analysis/:id` | Get a saved analysis |
| `GET /feedback/video/:videoId/latest` | Latest analysis for a video |
| `POST /sentiment` (`ml_service`, port 8001) | RoBERTa sentiment for a batch of comments |

## Analyzers
`ANALYZER` in `project_j417/backend/.env`:

| Value | Sentiment | Emotions and questions | Recommendations and guide |
|---|---|---|---|
| `bert` | RoBERTa (`ml_service/`) | keyword rules | rule-based |
| `llm` | Claude | Claude | Claude |
| `lexicon` | keyword rules | keyword rules | rule-based |
| `auto` | Claude if `ANTHROPIC_API_KEY` is set, else `lexicon` | same | same |

The keyword lexicon covers English, Sinhala script and romanised Sinhala, and handles negations such as "do not understand". If the sentiment service or Claude fails, the analyzer falls back to `lexicon`, and the UI shows which analyzer produced each result.

## Models, APIs and data
- **Model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment`, a pre-trained multilingual RoBERTa from Hugging Face. Not fine-tuned here; downloaded once to the local Hugging Face cache.
- **YouTube Data API v3** (`YOUTUBE_API_KEY`): video metadata, chapters and comments.
- **Anthropic API, Claude** (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`): optional; classification, recommendations and the viewer guide.
- **MongoDB Atlas** (`MONGODB_URI`): videos, comments and saved analyses.

## Evaluation
`cd project_j417/backend && npm run evaluate -- --analyzer bert` (or `llm` / `lexicon`) compares sentiment against the hand-labelled `samples/labelled-comments.json` and prints accuracy, per-class precision/recall/F1, macro F1 and a confusion matrix.

## AI usage
No model is trained or fine-tuned in this project; pre-trained models are used for inference only. Sentiment can come from the pre-trained RoBERTa model (`ANALYZER=bert`), or comments can be classified and recommendations written by Claude (`ANALYZER=llm`, or `auto` with an API key). Without a key, the keyword-rule fallback (`lexicon`) is used. The original parts of this component are the ingestion pipeline, the Sinhala/Singlish lexicon, the topic fusion rules, the recommendation and viewer-guide logic, and the evaluation script.

## Limitations
- Emotions and questions with `bert` or `lexicon` come from keyword rules, so they are weaker than Claude on Singlish and sarcasm.
- Comment-to-topic linking uses timestamps and keyword overlap, so a comment with neither lands in "General discussion".
- The thresholds in the fusion table are set by hand, not learned.
- Evaluation covers sentiment only, on a small hand-labelled set.

## Privacy
Only public comment data is used. Author handles are replaced by a one-way hash (`viewer_xxxxxxxx`) before storage, and individuals are not profiled.
