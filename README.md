# J26-IT-417 – Audience feedback mining

Analyses YouTube video comments (English, Sinhala, Singlish) for sentiment, emotions and questions.

| Folder | What it is |
|---|---|
| `client/` | React + TypeScript (Vite) dashboard |
| `server/` | Express + Mongoose API, comment ingestion and analyzers |
| `extension/` | Chrome extension that opens the dashboard for the current YouTube video |
| `training/` | Fine-tuning (`train.py`) and serving (`serve.py`) of the trained model |

## Run
Copy `server/.env.example` to `server/.env` and `client/.env.example` to `client/.env`, fill in the values, then:

```
cd server && npm install && npm run dev      # API on :5000
cd client && npm install && npm run dev      # UI on :5173
```
Load `extension/` via `chrome://extensions` → Load unpacked.

## Analyzers
`ANALYZER` in `server/.env`: `llm` (Claude), `lexicon` (offline word lists), `model` (trained model), or `auto`.

## Training the model
```
cd server && npm run export-training     # writes training/data/comments.jsonl
```
Then train `training/train.py` on a GPU (e.g. Google Colab), put the output in `training/model_out/`, run
`uvicorn serve:app --port 8001` from `training/`, and set `ANALYZER=model`.
