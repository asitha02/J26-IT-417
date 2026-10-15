# Component 3 – Audience feedback mining

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions.

| Folder (inside `project_j417/`) | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite) dashboard |
| `backend/` | Express + Mongoose API, comment ingestion and analyzers |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

## Run
Copy `project_j417/backend/.env.example` to `project_j417/backend/.env` and `project_j417/frontend/.env.example` to `project_j417/frontend/.env`, fill in the values, then:

```
cd project_j417/backend && npm install && npm run dev      # API on :5000
cd project_j417/frontend && npm install && npm run dev      # UI on :5173
```
Load `project_j417/extension/` via `chrome://extensions` → Load unpacked.

## Analyzers
`ANALYZER` in `project_j417/backend/.env`: `llm` (Claude), `lexicon` (offline word lists), or `auto`.
