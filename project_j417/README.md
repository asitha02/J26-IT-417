# Transcription component: YouTube link → JSON → cleaned JSON

Part of "Cross-Video Knowledge Extraction". This component takes a **YouTube link**, turns the audio into a
**timestamped transcript (JSON)**, and then **trained models remove the duplicates and error words** from that JSON.
Named-entity recognition, LLM extraction and fusion belong to the next components, which read this cleaned JSON; every
segment therefore keeps its **video ID and its start/end timestamps**.

```
YouTube link ─► audio ─► speech-to-text ─► transcript JSON ─► trained cleaning models ─► cleaned JSON
                                                                (one per video, and all videos in one file)
```

## What is trained and what is not

| Part | What it is | Trained here? |
|---|---|---|
| Speech to text | `distil-small.en` (Distil-Whisper) via faster-whisper, int8 on CPU | No, used as released |
| **Sentence model** | finds redundant sentences (subscribe requests, sponsor reads, thank-you endings) | **Yes** |
| **Word model** | finds error words (fillers like "um", "you know", words said twice) | **Yes** |
| **Duplicate model** | decides whether two sentences are the same content | **Yes** |

The three cleaning models are small and written in plain numpy (no machine-learning library). They need **no manual
labelling**: they learn from labeled example sentences and from real sentences of the stored transcripts. "Which original
segments and words are worth keeping" is decided by the models, not by reviewing the videos.

* **Sentence model** (`app/cleaning/sentence_model.py`): TF-IDF features of words, word pairs and letter groups into a
  logistic regression. Learns from 62 labeled redundant sentences (6 kinds) plus real sentences.
* **Word model** (`word_model.py`): a word tagger. For every word it looks at the word, the words around it, commas and
  whether it repeats the word before, and decides keep or remove. Trained on real clean sentences that get mistakes
  added on purpose, so the right answer for every word is known.
* **Duplicate model** (`duplicate_model.py`): five similarity signals of a sentence pair (word overlap, containment,
  order-aware match, length ratio, shared word triples) into a logistic regression, trained on a sentence versus a noisy
  copy of it, against different or look-alike sentences.

**Every model is tested on data it never saw** (5-fold cross-check; the sentence model also with a whole kind of
sentence hidden from training) **and compared with the simple hand-written rule it would replace.** A model is used only
if it is at least as good as the rule and rarely damages real text; otherwise that job stays with the rule. On the 4
development videos all three passed: the sentence model found 85% of redundant sentences (the rule 23%), the word model
fully repaired 95% of damaged sentences (the rule 69%) while changing 1.5% of clean ones, and the duplicate model reached
F1 0.98 (the best fixed threshold 0.96). The test data is made from the same transcripts with known mistakes added, so the
numbers show what each model learned, not performance on every possible video.

## Output

`GET /api/videos/{id}/download` (one video) and `GET /api/cleaning/download` (all videos in one file):

```json
{
  "cleaning": {"trained_models_in_use": {"sentences": true, "words": true, "duplicates": true}, "model_test_results": {...}},
  "summary": {"segments_raw": 310, "segments_kept": 301, "redundant_sentences_removed": 6, "error_words_removed": 5, ...},
  "videos": [{
    "source_id": "pSHVbLPWA28", "title": "…", "source_url": "https://www.youtube.com/watch?v=pSHVbLPWA28",
    "quality": {"segments_raw": 136, "segments_kept": 136, "words_removed_pct": 0.0, ...},
    "segments": [{"id": 0, "start": 0.0, "end": 4.2, "text": "…", "confidence": 0.93, "low_confidence": false,
                  "original_text": "…only present when the text was changed"}]
  }],
  "removed_examples": [{"source_id": "…", "id": 12, "start": 31.5, "reason": "duplicate_in_video", "text": "…"}]
}
```

Segments keep the `id` of the raw segment, so every sentence traces back to the raw transcript. A segment is dropped only
if fewer than 3 meaningful words remain or it repeats a segment already kept (inside one video within 120 s, or in another
video); every removal is counted by reason. Segments the speech recogniser was unsure about (confidence below 60%) are
kept but flagged `low_confidence`. A video where most segments are flagged probably has the wrong language or no speech:
delete it.

## Run

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set MONGODB_URI / MONGODB_DB
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxies /api to :8000)

# tests (no GPU / Mongo / network needed - the heavy parts are faked)
cd backend && pytest
```

In the page: **1.** paste a link, **2.** see each video with its cleaned JSON (and delete it), **3.** press **Train the
models**. Before training, the JSON is cleaned with the hand-written rules.

Speech recognition: with an NVIDIA GPU the default is `large-v3-turbo`; without one it uses `distil-small.en` (English
only, int8, beam 1). Intel/AMD integrated graphics are not supported by faster-whisper and run on the CPU.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/transcripts` `{url}` | start a job → `{job_id, status}` (202) |
| GET | `/api/transcripts/{job_id}` | status + progress (`queued/downloading/transcribing/done/failed`) |
| GET | `/api/transcripts/{job_id}/result` | the raw transcript JSON |
| GET | `/api/videos` | the transcribed videos |
| GET | `/api/videos/{source_id}/download` | one video's cleaned JSON |
| DELETE | `/api/videos/{source_id}` | remove a video and its stored JSON |
| GET | `/api/cleaning/summary` | what the cleaning did: totals, per video, examples of what was removed |
| GET | `/api/cleaning/download` | all videos in one cleaned JSON |
| POST | `/api/cleaning/train` | train the three models, test each one, use the ones that pass |
| GET | `/api/cleaning/model` | the test results and which jobs a trained model now does |
| GET | `/api/health` | speech model + device in use |

Repeat requests for a YouTube video already transcribed with the same model return instantly from MongoDB (`cached: true`).
Each finished transcript is also written to `data/transcripts/<source_id>.json`.

## Notes

- Keep `yt-dlp` updated; YouTube changes break old versions. If YouTube asks to sign in, set `YTDLP_COOKIES_FILE`.
- Only download media you are permitted to process (YouTube ToS / copyright apply).
- Limits: playlists and live streams are rejected; max duration `MAX_DURATION_SEC` (default 4 h); local/private URLs are blocked.
- Plugging into a base project: copy `backend/app/transcription/` (and `app/cleaning/`), include the routers in your
  `main.py`, create `app.state.repo = Repository(<your Mongo database>)` and `app.state.transcriber`, and delete `app/db.py`
  if your base already owns the Mongo connection.
