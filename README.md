# J26-IT-417

Research project. This repo's `project_j417/` folder holds the code.

## Component 3 – Audience feedback mining

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions.

| Folder (inside `project_j417/`) | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite) dashboard |
| `backend/` | Express + Mongoose API, comment ingestion and analyzers |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

### Run
Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`, fill in the values (never commit `.env`), then:

```
cd project_j417/backend && npm install && npm run dev      # API on :5000
cd project_j417/frontend && npm install && npm run dev      # UI on :5173
```

Load `project_j417/extension/` via `chrome://extensions` → Load unpacked.

### Analyzers
`ANALYZER` in `backend/.env`: `llm` (Claude), `lexicon` (offline word lists), or `auto`.

### Evaluation
```
cd project_j417/backend && npm run evaluate
```
Compares sentiment output against `samples/labelled-comments.json`.

### AI usage
Comments are classified (sentiment, emotions, questions) and recommendations are written by Claude via the Anthropic API (`ANALYZER=llm`, or `auto` with an API key). No model is trained in this project. Without a key, a keyword-rule fallback (`lexicon`) is used; the UI shows which analyzer produced each result.

More detail: [project_j417/FEEDBACK_MINING_README.md](project_j417/FEEDBACK_MINING_README.md)
