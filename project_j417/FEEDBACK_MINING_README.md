# Component 3 – Audience feedback mining

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions.

| Folder (inside `project_j417/`) | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite) dashboard |
| `backend/` | Express + Mongoose API, comment ingestion, analyzers, fusion and recommendations |
| `ml_service/` | FastAPI service running a multilingual RoBERTa sentiment model |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

## Run
Copy `project_j417/backend/.env.example` to `project_j417/backend/.env` and `project_j417/frontend/.env.example` to `project_j417/frontend/.env`, fill in the values, then:

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

## Analyzers
`ANALYZER` in `project_j417/backend/.env`: `bert` (pre-trained RoBERTa for sentiment, keyword rules for emotions), `llm` (Claude), `lexicon` (offline word lists), or `auto` (Claude if a key is set, else lexicon). If the sentiment service or Claude fails, the analyzer falls back to `lexicon`.

## Evaluation
`cd project_j417/backend && npm run evaluate -- --analyzer bert` (or `llm` / `lexicon`) compares sentiment against `samples/labelled-comments.json` and prints accuracy, per-class precision/recall/F1 and a confusion matrix.

## AI usage
- **At runtime:** sentiment can come from the pre-trained `cardiffnlp/twitter-xlm-roberta-base-sentiment` model (`ANALYZER=bert`), or comments can be classified and recommendations written by Claude via the Anthropic API (`ANALYZER=llm`, or `auto` with an API key). No model is trained or fine-tuned in this project. Without a key, a keyword-rule fallback (`lexicon`) is used; the UI shows which analyzer produced each result.

## Privacy
Only public comment data is used. Author handles are replaced by a one-way hash (`viewer_xxxxxxxx`) before storage.
