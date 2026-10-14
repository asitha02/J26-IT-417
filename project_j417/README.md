# Transcription Component (Cross-Video Knowledge Extraction)

Input: a YouTube / podcast URL → Output: a timestamped transcript as JSON.
Scope: audio extraction + speech recognition only. NER / LLM extraction / fusion belong to the next component.

## Stack and why

| Part | Choice | Reason |
|---|---|---|
| API | FastAPI + Pydantic v2 | typed contract, async jobs |
| Audio | yt-dlp (audio-only stream) | no extra conversion pass; faster-whisper decodes it directly |
| ASR | faster-whisper `large-v3-turbo` (GPU) / `small` (CPU) | best accuracy-per-second; auto-selected |
| Speed | `BatchedInferencePipeline` + Silero VAD | parallel chunk decoding, silence skipped (also cuts hallucinations) |
| DB | MongoDB via `pymongo.AsyncMongoClient` | Motor's successor, same style |
| Frontend | React + Vite + TypeScript + Tailwind v4 + TanStack Query | job polling, transcript viewer |

## Run

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set MONGODB_URI / MONGODB_DB
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxies /api to :8000)

# tests (no GPU / Mongo / network needed - heavy parts are faked)
cd backend && pytest
```

**GPU (recommended):** install the CUDA 12 libraries faster-whisper needs
(`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`, see the faster-whisper README for `LD_LIBRARY_PATH`).
With a GPU the default is large-v3-turbo / float16 / batch 16. Without one it falls back to `small` / int8;
for better CPU accuracy set `WHISPER_MODEL=medium` (slower).

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/transcripts` `{url, language?, word_timestamps?}` | start a job → `{job_id, status}` (202) |
| GET | `/api/transcripts/{job_id}` | status + progress (`queued/downloading/transcribing/done/failed`) |
| GET | `/api/transcripts/{job_id}/result` | the transcript JSON |
| GET | `/api/transcripts/{job_id}/download` | same JSON as a file download |
| GET | `/api/transcripts` | recent jobs |
| GET | `/api/health` | model + device in use |

Repeat requests for a YouTube video already transcribed with the same model return instantly from MongoDB (`cached: true`).
Each finished transcript is also written to `data/transcripts/<source_id>.json`.

## JSON contract for the knowledge-fusion component

```json
{
  "schema_version": "1.0",
  "source_id": "dQw4w9WgXcQ",
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "…", "uploader": "…", "duration_sec": 212.0,
  "language": "en", "language_probability": 0.99,
  "asr_model": "large-v3-turbo", "device": "cuda",
  "created_at": "2026-10-14T06:00:00Z", "processing_time_sec": 14.2,
  "full_text": "…",
  "segments": [
    {"id": 0, "start": 0.0, "end": 4.2, "text": "…", "confidence": 0.93,
     "words": [{"start": 0.0, "end": 0.4, "word": "…", "probability": 0.98}]}
  ]
}
```
`words` appears only when `word_timestamps: true`. `source_id` + `start`/`end` give the traceability the project form requires.
MongoDB collections: `transcription_jobs`, `transcripts` (`_id = "<source_id>__<asr_model>"`).

## Plugging into your base project

1. Copy `backend/app/transcription/` into your backend.
2. In your `main.py`: `app.include_router(transcription_router)`, and create
   `app.state.repo = Repository(<your existing Mongo database>)` and
   `app.state.transcriber = Transcriber(settings.asr())` at startup (see `app/main.py`).
3. Delete `app/db.py` if your base already owns the Mongo connection.
4. Copy `frontend/src/features/transcription/` into your frontend (needs Tailwind + TanStack Query).

## Notes

- Keep `yt-dlp` updated; YouTube changes break old versions. If YouTube asks to sign in, set `YTDLP_COOKIES_FILE`.
- Only download media you are permitted to process (YouTube ToS / copyright apply).
- Limits: playlists and live streams are rejected; max duration `MAX_DURATION_SEC` (default 4 h); local/private URLs are blocked.
