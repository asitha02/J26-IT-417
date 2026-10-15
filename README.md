# J26-IT-417 – Audience feedback mining

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions.

| Folder | What it is |
|---|---|
| `client/` | React + TypeScript (Vite) dashboard |
| `server/` | Express + Mongoose API, comment ingestion and analyzers |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |

## Run
Copy `server/.env.example` to `server/.env` and `client/.env.example` to `client/.env`, fill in the values, then:

```
cd server && npm install && npm run dev      # API on :5000
cd client && npm install && npm run dev      # UI on :5173
```
Load `extension/` via `chrome://extensions` → Load unpacked.

## Analyzers
`ANALYZER` in `server/.env`: `llm` (Claude), `lexicon` (offline word lists), or `auto`.
