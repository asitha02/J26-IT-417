# C1 — Transcription + Transcript Cleaning (YouTube link → JSON → cleaned JSON)
Part of **Cross-Video Knowledge Extraction**. C1 takes a **YouTube link**, turns the audio into a **timestamped
transcript (JSON)**, and then **trained models remove the duplicates and error words** from that JSON. The cleaned JSON
is the input of the next components (named-entity recognition, LLM extraction, fusion), so every segment keeps its
**video ID and its start/end timestamps**.

**Research gap:** raw speech-to-text output is full of material that is not knowledge: filler words ("um", "you
know"), words said twice, subscribe requests, sponsor reads, thank-you endings, and the same sentence repeated by the
recogniser or across videos. Feeding that straight into entity extraction pollutes every later step. C1 cleans it with
small models **trained for this job and tested on data they never saw**, instead of a pile of hand-written rules.

C1 has two parts, each with its own area in the app:

1. **Part 1, Transcription** (YouTube link → raw transcript JSON): downloads the audio, runs speech-to-text and stores a
   timestamped, confidence-scored transcript per video.
2. **Part 2, Transcript Cleaning** (raw JSON → cleaned JSON): three trained models find redundant sentences, error
   words and duplicate sentences; each model is only used if it passed its test, otherwise a hand-written rule keeps
   that job.

> Status: working end to end (link → raw JSON → cleaned JSON, per video and all videos in one file). Trained on and
> tested with 8 stored transcripts.

---

## Contents

1. [How it works](#how-it-works)
2. [Technologies used and why](#technologies-used-and-why)
3. [Key concepts explained](#key-concepts-explained)
4. [The cleaning models (my own work)](#the-cleaning-models-my-own-work)
5. [Cleaning rules](#cleaning-rules)
6. [Output format](#output-format)
7. [API reference](#api-reference)
8. [Database](#database)
9. [Project structure](#project-structure)
10. [Setup](#setup)
11. [Running](#running)
12. [Configuration (`.env`)](#configuration-env)
13. [Troubleshooting](#troubleshooting)
14. [Results](#results)
15. [Known limitations](#known-limitations)
16. [Tests](#tests)
17. [Plugging into the base project](#plugging-into-the-base-project)

---

## How it works

```
PART 1  [Add video] --POST /api/transcripts--> [FastAPI backend]
          1. validate the link (http/https only, no local or private-network addresses)
          2. same video + same speech model already transcribed?  -> return it instantly from MongoDB (cached: true)
          3. IN THE BACKGROUND:  queued -> downloading (yt-dlp, audio only)
                                 -> transcribing (faster-whisper, batched, per-segment confidence)
                                 -> done
          4. save to MongoDB "transcripts" and to data/transcripts/<source_id>.json
          the page polls GET /api/transcripts/{job_id} for status and progress

PART 2  [Train the models] --POST /api/cleaning/train--> [FastAPI backend]
          sentence model + word model + duplicate model are trained from labeled examples and real sentences of the
          stored transcripts, then each is tested on data it never saw and compared with its hand-written rule
          -> the ones that pass are used, the others stay with the rule      -> data/models/cleaning/*.json
        [Download JSON] --GET /api/videos/{id}/download | /api/cleaning/download-->
          per segment: remove redundant sentences + error words -> drop empty segments -> drop duplicates
          -> flag low-confidence segments -> cleaned JSON with a quality report and the removed examples
```

Before the models are trained, the JSON is cleaned with the hand-written rules, so the download always works.

---

## Technologies used and why

Tools marked **pretrained** are used as released (never changed). Everything marked **mine** was built and trained for
this project.

### Speech and machine learning

| Technology | What it does here | Pretrained or mine |
|---|---|---|
| **yt-dlp** | Finds the video's audio stream on YouTube and downloads it (audio only). | existing tool |
| **faster-whisper** (CTranslate2) | Runs Whisper speech-to-text quickly, with batched decoding and a confidence for each segment. | library |
| **Whisper `large-v3-turbo`** | Speech model used when an NVIDIA GPU is present (float16, batch 16, beam 5). | **pretrained** |
| **Distil-Whisper `distil-small.en`** | Speech model used on CPU (English only, int8, batch 8, beam 1). | **pretrained** |
| **PyAV (`av`)** | Decodes the downloaded audio for faster-whisper. | library |
| **numpy** | The three cleaning models are written in plain numpy, with no machine-learning library. | library |
| **Sentence model** (TF-IDF + logistic regression) | Finds redundant sentences. | **mine (trained)** |
| **Word model** (word tagger) | Finds error words: fillers and words said twice. | **mine (trained)** |
| **Duplicate model** (five similarity signals + logistic regression) | Decides whether two sentences are the same content. | **mine (trained)** |

### Application

| Technology | What it does here |
|---|---|
| **FastAPI + Uvicorn** | The backend web API (Uvicorn is the server that runs it). Gives automatic docs at `/docs`. |
| **Pydantic / pydantic-settings** | Checks every JSON response has the agreed shape and reads settings from `.env`. |
| **MongoDB + pymongo (async client)** | Stores jobs and transcripts so a repeated video returns instantly. |
| **React 18 + TypeScript** | The web UI, split by feature (transcription, videos, cleaning). |
| **Vite** | Dev server and bundler for the frontend; proxies `/api` to the backend. |
| **TanStack React Query** | Fetching, polling job status and refreshing lists. |
| **Tailwind CSS 4** | Styling. |
| **pytest + httpx** | Automatic tests; the heavy parts (download, speech model, Mongo) are faked. |

---

## Key concepts explained

- **Segment**: one timestamped piece of transcript (`start`, `end`, `text`, `confidence`). Segments are the unit that
  later components read, so cleaning never changes a timestamp or a video ID.
- **Confidence**: how sure the speech recogniser was about a segment (0–1). Below 60 % the segment is kept but flagged
  `low_confidence`.
- **Redundant sentence**: a sentence that carries no knowledge: subscribe/like requests, thank-you and goodbye,
  greetings and intros, sponsor reads, social media and links, empty filler talk.
- **Error word**: a word that should not be in the text: fillers ("um", "uh", "you know") and words said twice by
  mistake ("the the").
- **Duplicate**: the same content again, either inside one video (a common recogniser glitch) or in another video.
- **TF-IDF**: turns a sentence into numbers by counting its words, word pairs and letter groups and down-weighting
  common ones, so a simple model can work with text.
- **Logistic regression**: a simple model that turns those numbers into a probability ("how likely is this sentence
  redundant?"). Small, fast and easy to inspect.
- **Word tagger**: a model that gives every word a keep/remove decision using the word itself, the words around it,
  commas and whether it repeats the word before.
- **Cross-check (5-fold)**: the data is split into five parts; the model trains on four and is tested on the fifth, five
  times. Every score therefore comes from data the model never saw.
- **Caught / wrongly flagged**: share of really redundant sentences the model finds, and share of good sentences it
  flags by mistake. Both matter; a model that removes real content is worse than none.
- **F1**: one number that balances catching mistakes and not raising false alarms (1 = perfect).
- **Rule baseline**: the simple hand-written rule a model would replace. A model must be at least as good as it to be used.

---

## The cleaning models (my own work)

All three need **no manual labelling of the videos**: they learn from labeled example sentences and from real sentences
of the stored transcripts. They are small and plain numpy, so they train in seconds on CPU.

| Model | File | What it learns | Trained on |
|---|---|---|---|
| **Sentence model** | `app/cleaning/sentence_model.py` | TF-IDF of words, word pairs and letter groups → logistic regression. Finds redundant sentences. | 62 labeled redundant sentences (6 kinds) + 24 tricky content sentences + 800 real sentences |
| **Word model** | `app/cleaning/word_model.py` | For every word: the word, its neighbours, commas, repeat of the previous word → keep or remove. | 765 real clean sentences with mistakes added on purpose (4,590 noisy versions, 18 filler kinds), so the right answer for every word is known |
| **Duplicate model** | `app/cleaning/duplicate_model.py` | Five similarity signals of a sentence pair → logistic regression. | 3,060 pairs: a sentence vs. a noisy copy of itself, against different and look-alike sentences |

The five duplicate signals are word overlap, containment, order-aware match, length ratio and shared word triples.
Training and testing live in `app/cleaning/training.py`; the trained parameters are saved as JSON in
`data/models/cleaning/` and loaded by `Cleaner` (`app/cleaning/cleaner.py`).

### Tested before it is used

Every model is tested on data it never saw (5-fold cross-check; the sentence model also with one whole *kind* of
sentence hidden from training) **and compared with the simple hand-written rule it would replace.** A model is switched
on only if it is at least as good as the rule and rarely damages real text. Otherwise that job stays with the rule, and
the output says which is in use (`trained_models_in_use`).

### Why tests on made-up mistakes?

There is no ground-truth "perfect transcript" for YouTube videos. So the word and duplicate models are tested on real
clean sentences that get known mistakes added, which means the correct answer is known for every word. The numbers
therefore show what each model learned, not performance on every possible video.

---

## Cleaning rules

For each segment of each video (timestamps and video IDs are never changed):

| Step | What happens | Reason recorded |
|---|---|---|
| 1 | Remove redundant sentences and error words (trained model, or rule if the model did not pass). | counted as sentences / words removed |
| 2 | Drop the segment if fewer than **3** meaningful words remain. | `too_short` |
| 3 | Drop it if it repeats a segment already kept in the **same video within 120 s**. | `duplicate_in_video` |
| 4 | Drop it if it repeats a segment already kept in **another video**. | `duplicate_across_videos` |
| 5 | Flag it if the recogniser's confidence is below **60 %** (kept, not removed). | `low_confidence` |

- Segments shorter than **5 words** are never treated as duplicates: "Yes." and "Right, so…" legitimately repeat.
- Inside one video only *nearby* repeats (120 s) count, because lecturers reuse phrases later on.
- Duplicate search is indexed by word 4-grams, so a new segment is compared only with likely matches.
- Nothing is lost silently: every removal is counted by reason, kept segments carry the `id` of the raw segment, and the
  original text is stored when the text changed.
- A video where most segments are flagged `low_confidence` probably has the wrong language or no speech: delete it.

---

## Output format

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

The raw transcript (`GET /api/transcripts/{job_id}/result`) has the same segment fields before cleaning. Each finished
transcript is also written to `data/transcripts/<source_id>.json`.

---

## API reference

Interactive docs (try every endpoint): http://localhost:8000/docs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/transcripts` `{url}` | Start a job → `{job_id, status}` (202). 422 if the link is not allowed. |
| GET | `/api/transcripts/{job_id}` | Status and progress: `queued` / `downloading` / `transcribing` / `done` / `failed`. |
| GET | `/api/transcripts/{job_id}/result` | The raw transcript JSON (404 unknown job, 409 not finished). |
| GET | `/api/videos` | The transcribed videos. |
| GET | `/api/videos/{source_id}/download` | One video's cleaned JSON. |
| DELETE | `/api/videos/{source_id}` | Remove a video and its stored JSON. |
| GET | `/api/cleaning/summary` | What the cleaning did: totals, per video, examples of what was removed. |
| GET | `/api/cleaning/download` | All videos in one cleaned JSON. |
| POST | `/api/cleaning/train` | Train the three models, test each one, use the ones that pass. |
| GET | `/api/cleaning/model` | The test results and which jobs a trained model now does. |
| GET | `/api/health` | Speech model and device in use. |

Do not rename JSON fields without checking with the team: the next components read them.

---

## Database

MongoDB (the team's shared database, `MONGODB_DB`). C1 only touches its own collections:

| Collection | Holds |
|---|---|
| `transcription_jobs` | One document per job: link, status, progress, timestamps (indexed by `created_at` and `status`). |
| `transcripts` | One document per video and speech model: the full raw transcript (indexed by `source_id`). |

A repeat request for a video already transcribed with the same speech model returns instantly (`cached: true`). The
trained cleaning models are not in the database; they are JSON files in `backend/data/models/cleaning/`.

---

## Project structure

```
project_j417/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, routers, startup (model preload, Mongo indexes)
│   │   ├── config.py            settings from .env; resolves "auto" speech model/device/precision
│   │   ├── db.py                MongoDB connection (delete if the base project owns it)
│   │   ├── transcription/       Part 1
│   │   │   ├── router.py        /api/transcripts routes
│   │   │   ├── service.py       job pipeline: queued -> downloading -> transcribing -> done
│   │   │   ├── downloader.py    URL safety checks, yt-dlp audio download, limits
│   │   │   ├── transcriber.py   faster-whisper speech-to-text
│   │   │   ├── repository.py    MongoDB jobs + transcripts
│   │   │   └── schemas.py       Pydantic models
│   │   ├── cleaning/            Part 2
│   │   │   ├── router.py        /api/cleaning routes
│   │   │   ├── pipeline.py      cleans all videos, builds the quality report
│   │   │   ├── cleaner.py       uses a trained model when it passed, the rule otherwise
│   │   │   ├── rules.py         the hand-written baseline rules
│   │   │   ├── sentence_model.py, word_model.py, duplicate_model.py   the three trained models
│   │   │   ├── training.py      training, 5-fold testing, comparison with the rules
│   │   │   ├── ml.py, data.py   shared numpy helpers, example data and loading
│   │   └── videos/router.py     /api/videos routes
│   ├── data/                    transcripts/ and models/cleaning/ (audio/ is temporary)
│   ├── tests/                   test_api.py, test_cleaning.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx, main.tsx, index.css
│       ├── features/transcription/   add a link, job status, API calls
│       ├── features/videos/          list of videos, cleaned JSON, delete
│       ├── features/cleaning/        "Train the models" panel and test results
│       └── lib/request.ts            fetch helper
├── .env.example
└── README.md
```

---

## Setup

Requirements: Python 3.10+, Node.js 18+, MongoDB (local or Atlas), Git. An NVIDIA GPU is optional (much faster
transcription).

1. Backend packages (from the `backend` folder):
   ```
   python -m venv .venv
   .venv\Scripts\activate          (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
2. Copy `backend/.env.example` to `backend/.env` and set `MONGODB_URI` and `MONGODB_DB` (never commit `.env`).
3. Frontend packages (from the `frontend` folder):
   ```
   npm install
   ```
4. Check the backend with the automatic tests (no GPU, Mongo or internet needed):
   ```
   cd backend
   pytest
   ```

---

## Running

Backend (from the `backend` folder, virtual environment active):
```
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs to try the endpoints. The first start downloads the speech model and preloads it
(`PRELOAD_MODEL=true`), so the first request is not slow.

Frontend (second terminal, from the `frontend` folder, backend must be running):
```
npm run dev
```
The app opens at http://localhost:5173 and proxies `/api` to port 8000. In the page:
1. **Paste a YouTube link** and start. Progress shows `downloading` then `transcribing`; a repeat link returns instantly.
2. **See each video** with its cleaned JSON (download it, or delete the video).
3. Press **Train the models**. Each model is tested and shown with its result; the passing ones are used from then on.

Speech recognition: with an NVIDIA GPU the default is `large-v3-turbo`; without one it uses `distil-small.en` (English
only, int8, beam 1). Intel/AMD integrated graphics are not supported by faster-whisper and run on the CPU.

---

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string. A secret: never commit or print it. |
| `MONGODB_DB` | `research_project` | Database name |
| `DATA_DIR` | `data` | Where transcripts, audio and trained models are written |
| `WHISPER_MODEL` | `auto` | `auto` = `large-v3-turbo` on GPU, `distil-small.en` on CPU. For other languages on CPU use `small`. |
| `WHISPER_DEVICE` | `auto` | `auto`, `cuda` or `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto` = float16 on GPU, int8 on CPU |
| `BATCH_SIZE` / `BEAM_SIZE` | `0` (auto) | Auto = 16 / 5 on GPU, 8 / 1 on CPU |
| `MAX_DURATION_SEC` | `14400` (4 h) | Longer videos are rejected |
| `MAX_CONCURRENT_JOBS` | `1` | Jobs transcribed at the same time |
| `PRELOAD_MODEL` | `true` | Load the speech model at start |
| `KEEP_AUDIO` | `false` | Keep the downloaded audio in `data/audio/` |
| `YTDLP_COOKIES_FILE` | none | `cookies.txt` (Netscape format) if YouTube asks to sign in |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend address |

---

## Troubleshooting

| Problem | Meaning and fix |
|---|---|
| Download fails or "Sign in to confirm you're not a bot" | YouTube changed or blocked the request. Update yt-dlp (`pip install -U yt-dlp`); if it still asks to sign in, set `YTDLP_COOKIES_FILE`. |
| `Playlists are not supported` / `Live streams are not supported` | Paste a single, finished video link. |
| `Local addresses are not allowed` / `Private network addresses are not allowed` | Only public http(s) links are accepted. |
| Video rejected as too long | It is longer than `MAX_DURATION_SEC` (default 4 h). Raise it in `.env`. |
| `409 Transcript not ready` | The job is still running. Wait until the status is `done`. |
| Transcription is very slow | No NVIDIA GPU, so it runs on CPU. This is expected; a GPU is several times faster. |
| Most segments are flagged low confidence | Probably the wrong language or no speech. Delete the video, or use `WHISPER_MODEL=small` for non-English audio. |
| Page cannot reach the API | The backend is not running, or `CORS_ORIGINS` does not match the frontend address. |
| `[Errno 10048] ... only one usage of each socket address` | Port 8000 is taken by an earlier backend. Close it, or use `--port 8010` and update the Vite proxy. |
| Database errors on start | Check `MONGODB_URI` in `.env` and that MongoDB is running (or your IP is allowed in Atlas). |

---

## Results

Trained and tested on 863 real sentences from the stored transcripts (8 videos). All scores come from data the model
never saw. "Rule" is the simple hand-written rule the model would replace.

| Job | Measure | Trained model | Rule | Used? |
|---|---|---|---|---|
| **Sentence model** (redundant sentences) | Redundant sentences found | **79.0 %** | 22.6 % | Yes |
| | Good sentences wrongly flagged | 1.2 % | 0.1 % | |
| | F1 | **0.81** | 0.36 | |
| **Word model** (error words) | Damaged sentences fully repaired | **93.3 %** | 69.6 % | Yes |
| | Error words found | 97.0 % | | |
| | Clean sentences changed by mistake | 1.4 % | 0.0 % | |
| **Duplicate model** (same content) | F1 | **0.98** | 0.96 (best fixed threshold 0.57) | Yes |
| | Duplicates found | 96.9 % | 97.4 % | |
| | Different sentences wrongly flagged | 0.3 % | 1.5 % | |

- With a **whole kind of sentence hidden from training**, the sentence model still finds 38 % (0 % wrong flags), best on
  social media and links (60 %) and weakest on empty filler talk (0 %). It generalises partly; new kinds of redundancy
  need new labeled examples.
- The word model's threshold (0.8) was chosen by trying 0.5 to 0.95: lower finds slightly more error words but changes
  more clean sentences.
- On the real videos the sentence model flagged 6 of 800 sentences.
- The test data is made from the same transcripts with known mistakes added, so these numbers show what each model
  learned, not performance on every possible video.

---

## Known limitations

- Trained on 8 videos plus a small set of labeled redundant sentences; other speaking styles or topics may behave
  differently. Retrain (`Train the models`) after adding videos.
- The sentence model finds new kinds of redundancy only partly (38 % on a kind it never saw).
- The word and duplicate tests use mistakes added on purpose, not mistakes marked by a human on real transcripts.
- On CPU the default speech model is English only (`distil-small.en`); other languages need `WHISPER_MODEL=small` or a GPU.
- YouTube changes break old yt-dlp versions; some videos need cookies. Playlists and live streams are rejected.
- Only download media you are permitted to process (YouTube ToS and copyright apply).
- Out of scope for this component: named-entity recognition, LLM extraction and fusion (the next components read the
  cleaned JSON).

---

## Tests

```
cd backend
pytest
```
17 automatic tests: the API (job start, status, result, errors, cached repeats; download, Mongo and speech model are
faked) and the cleaning (rules, the three models, duplicate removal inside and across videos, low-confidence flags,
quality report).

---

## Plugging into the base project

Copy `backend/app/transcription/` (and `app/cleaning/`), include the routers in your `main.py`, create
`app.state.repo = Repository(<your Mongo database>)` and `app.state.transcriber`, and delete `app/db.py` if your base
already owns the Mongo connection.
