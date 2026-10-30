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


# C2 — Semantic Knowledge Fusion + Multilingual Content Generation (English & Sinhala)
Part of **Cross-Video Knowledge Extraction**. C2 takes the **structured knowledge JSON from C1** (concepts, definitions,
facts, relationships, entities, each with a video ID and a timestamp), **merges the repeated knowledge from many videos
into one Unified Knowledge Base (KB)**, and then **generates study content (summary, study notes, quiz) in English and
Sinhala** from that KB. Every KB item keeps all of its sources, so every sentence can be traced back to a video and a
timestamp. The KB and the generated text are the input of C4 and of the mobile app.

**Research gap:** after extraction, the same idea is still repeated and scattered across videos, each video says it in
different words, and Sinhala-speaking learners get almost no usable notes. Existing summarisers either work on one
video at a time or let an LLM write freely, so the output cannot be traced to a source. C2 fuses first, then generates
**only from the fused knowledge** with citations, and checks every Sinhala sentence against its English original.

C2 has three parts, each with its own tab in the app:

1. **Part 1, Knowledge fusion** (C1 JSON → Unified KB): reads C1's JSON, cleans it into atomic units, embeds each unit,
   groups near-duplicates by meaning and merges each group into one KB item with all of its sources.
2. **Part 2, Content generation** (KB → English text): an LLM writes a summary, study notes or a five-question quiz
   using **only** KB items and cites them as `[kb_00001]`.
3. **Part 3, Sinhala output and quality check** (English → Sinhala): NLLB-200 translates sentence by sentence and LaBSE
   checks that each Sinhala sentence still means the same as its English original.

> Status: working end to end (C1-format JSON → fusion → KB → English or Sinhala summary / notes / quiz → export), with a
> React web app. Tested with **stand-in data** in C1's format, because C1's final JSON was not available yet. Improving
> the Sinhala accuracy is the main goal of the next stage (see [Next stage](#next-stage-better-sinhala-accuracy)).

---

## Contents

1. [How it works](#how-it-works)
2. [Technologies used and why](#technologies-used-and-why)
3. [Key concepts explained](#key-concepts-explained)
4. [The four models and what is frozen](#the-four-models-and-what-is-frozen)
5. [My own work](#my-own-work)
6. [Thresholds](#thresholds)
7. [Data formats](#data-formats)
8. [API reference](#api-reference)
9. [Database](#database)
10. [Project structure](#project-structure)
11. [Setup](#setup)
12. [Running](#running)
13. [Configuration (`.env`)](#configuration-env)
14. [Scripts and checks](#scripts-and-checks)
15. [Troubleshooting](#troubleshooting)
16. [Results and evaluation](#results-and-evaluation)
17. [Feedback on the prototype](#feedback-on-the-prototype)
18. [Known limitations](#known-limitations)
19. [Next stage: better Sinhala accuracy](#next-stage-better-sinhala-accuracy)
20. [What was built, in order](#what-was-built-in-order)
21. [Plugging into the other components](#plugging-into-the-other-components)

---

## How it works

```
PART 1  [Upload C1 JSON] --POST /ingest/file--> [FastAPI backend]
          1. adapter.py turns C1's JSON (several shapes accepted) into one internal format
          2. saved in MongoDB "raw_extractions" (one document per video)
        [Run fusion] --POST /fusion/run-->
          3. preprocess: clean the text into atomic knowledge units (video ID + timestamp kept on every unit)
          4. embed every unit with MiniLM -> 384 numbers per unit
          5. cosine similarity between units of the SAME type; pairs >= 0.85 are the same fact
          6. union-find groups the pairs; merge: one KB item per group
             (canonical text = highest confidence, other wordings kept as variants, every source kept)
          7. saved in MongoDB "kb_items"   ->  {units_in, kb_items_out, reduction_pct}

PART 2  [Generate] --POST /generate {output_type, language}-->
          KB items (with [kb_id]) -> prompt that allows ONLY these items -> Gemini -> English text with citations
          saved in "generated_content"

PART 3  language = "si":
          English text -> split into sentences (markdown prefixes and [kb_id] citations kept out of the model)
          -> NLLB-200 (sin_Sinh, beam search 4) -> Sinhala sentences, citations put back
          -> LaBSE: English vs Sinhala vector of each pair -> consistency score, sentences below 0.70 flagged

EXPORT  GET /kb  |  GET /export/kb.txt  |  GET /export/generated.txt   -> C4 and the Flutter app
```

All four models are loaded once when the server starts (`PRELOAD`), so the first request is not slow.

---

## Technologies used and why

Tools marked **pretrained** are used as released, **frozen**, never trained or changed by me.

### AI models

| Technology | What it does here | Pretrained or mine |
|---|---|---|
| **`paraphrase-multilingual-MiniLM-L12-v2`** (sentence-transformers) | Turns each knowledge sentence into a 384-number vector so similar meanings can be found and merged. About 118M parameters, small and fast on CPU. | **pretrained** |
| **`gemini-3.5-flash-lite`** (Google AI Studio, `google-genai` SDK) | Writes the summary, study notes or quiz from KB items only. Free tier; the LLM sits behind one wrapper so it can be swapped. | **pretrained** (hosted) |
| **`facebook/nllb-200-distilled-600M`** (Meta) | English → Sinhala translation (`sin_Sinh`, beam 4). Runs locally, no per-call cost. | **pretrained** |
| **`sentence-transformers/LaBSE`** (Google) | Maps English and Sinhala sentences into one shared space (109 languages) to check that a translation kept the meaning. | **pretrained** |
| **numpy** | Cosine similarity and grouping. | library |
| **Dedupe, merge, grounded prompts, consistency check, JSON adapter** | The pipeline that connects the models. | **mine** |

### Application

| Technology | What it does here |
|---|---|
| **FastAPI + Uvicorn** | The backend web API. Automatic interactive docs at `/docs`. |
| **Pydantic** | Checks every request and response has the agreed shape (`app/models/`). |
| **python-dotenv** | Reads secrets (database address, API key) from `.env`, never from code. |
| **MongoDB Atlas + pymongo** | Shared team database for raw extractions, the KB and generated content. |
| **React + Vite** | The web app ("Knowledge Studio"): Ingest & Fuse, Knowledge Base, Generate, Translate. Vite proxies the API calls. |
| **transformers / sentencepiece / torch** | Run NLLB-200. |

---

## Key concepts explained

- **Knowledge unit**: one clean, single idea taken from C1's output (a definition, a fact, a concept…). Fusion works on units.
- **Embedding**: a list of numbers (here 384) that summarises what a sentence means. Similar meanings get similar numbers.
- **Cosine similarity**: how close two embeddings point in the same direction, from 0 to 1 for our vectors. 1 = same meaning.
- **Threshold**: the cut-off that turns a similarity score into a decision. At or above it, two units count as the same fact.
- **Union-find grouping**: if A matches B and B matches C, all three go into one group. This equals *single-linkage*
  clustering, so it can chain (A and C end up together even if they are not similar).
- **Canonical text, variants, sources**: a merged KB item shows the best wording, keeps the other wordings, and lists
  every `(video, timestamp)` where the idea appeared. Nothing unique is lost and everything is traceable.
- **Grounded generation**: the LLM may use only the KB items it is given and must cite them as `[kb_xxxxx]`.
- **Frozen / zero-shot**: a pre-trained model used as it is, with no training on my data and none of its weights changed.
- **NLLB-200**: Meta's "No Language Left Behind" translation model for 200 languages, including Sinhala.
- **LaBSE**: Google's language-agnostic sentence embedding; a sentence and its correct translation land close together.
- **Consistency score**: LaBSE cosine between an English sentence and its Sinhala translation. Low score = possible meaning drift.
- **chrF++**: a character-based translation quality score (higher is better). Better than BLEU for Sinhala.
- **Precision / recall / F1** (for duplicates): precision = of the pairs I merged, how many were really duplicates;
  recall = of the real duplicates, how many I merged; F1 balances both.

---

## The four models and what is frozen

| Model | Job | Output | Runs | What is frozen | What I control instead |
|---|---|---|---|---|---|
| MiniLM-L12 multilingual | Embeddings for dedupe | 384-dim vectors | local, CPU | all weights | similarity threshold 0.85, grouping and merge logic |
| Gemini 3.5 Flash-Lite | Generate summary / notes / quiz | text with `[kb_id]` citations | Google API | weights are hosted by Google; I fix the model name in `.env` | prompts, output formats, the swappable wrapper |
| NLLB-200 distilled 600M | English → Sinhala | Sinhala text | local | all weights; target language fixed to `sin_Sinh` | beam search 4, sentence splitting, keeping markdown and citations out of the model |
| LaBSE | Check the Sinhala keeps the meaning | 768-dim vectors, cosine score | local | all weights | pass mark 0.70 |

- No model is trained in the current version. The weights hold the knowledge from each model's original training data;
  my project only sends text through them and never updates them.
- **Licence:** NLLB-200 weights are released under a non-commercial licence (CC-BY-NC 4.0, as far as I know), so a
  commercial version would need a different translator. Gemini's free tier is rate limited and, on the free tier,
  Google may use submitted data, so do not send private content.

---

## My own work

| Part | File | What it does |
|---|---|---|
| JSON adapter | `app/services/adapter.py` | Accepts C1's JSON in several shapes (flat `items`, grouped `concepts/facts/...`, relationship triples, seconds or `HH:MM:SS`, `video_id` or `videoId`) and converts it into one internal format. When C1's final format arrives, only this file changes. |
| Preprocess | `app/services/preprocess.py` | Cleans text into atomic knowledge units and keeps video ID and timestamp on each. |
| Dedupe | `app/services/dedupe.py` | Cosine similarity and union-find grouping, comparing only units of the same type. |
| Merge | `app/services/merge.py` | One KB item per group: canonical text (highest confidence, ties to the longer text), variants, all sources, `merged_from` count. |
| Generator | `app/services/generator.py`, `llm.py` | KB-only prompts with `[kb_id]` citations for summary, notes and quiz; one wrapper so the LLM provider can be changed in `.env`. |
| Translator | `app/services/translator.py` | Sentence-by-sentence NLLB translation; markdown prefixes and `[kb_id]` citations never go through the model and are put back afterwards. |
| Consistency | `app/services/consistency.py` | LaBSE English-vs-Sinhala score per sentence, flags pairs below the threshold. |
| Export | `app/api/routes/export.py` | Plain-text and JSON outputs for C4 and the app. |
| Web app | `frontend/` | Upload and fuse, browse the KB, generate, translate and see the consistency result. |
| Evaluation tools | `scripts/` | Test scripts, stand-in data, candidate pairs for labelling, threshold sweep. |

---

## Thresholds

The thresholds belong to the pipeline, not to the models. Only two of the four models have one.

| Threshold | Applied to | Value | Meaning |
|---|---|---|---|
| `SIM_THRESHOLD` | MiniLM cosine similarity | **0.85** | At or above = same fact, merge. Strict, because a wrong merge loses information. |
| `CONSISTENCY_THRESHOLD` | LaBSE cosine similarity | **0.70** | Below = the Sinhala may have drifted, flag it. Lower, because translations are worded differently. |

Both are starting values, to be tuned on labelled data (see [Results and evaluation](#results-and-evaluation)).
NLLB-200 and Gemini have no threshold: NLLB translates everything, and Gemini is controlled by the prompt.

---

## Data formats

**Input from C1** (the adapter accepts several shapes; this is the basic one):
```json
[
  {"video_id": "ml_lecture_1",
   "items": [
     {"type": "definition", "text": "Gradient descent minimizes a loss function.", "timestamp": "00:03:10", "confidence": 0.93},
     {"type": "entity", "text": "Andrew Ng", "timestamp": "00:10:00", "confidence": 0.88}
   ]}
]
```
Item types: `concept`, `fact`, `definition`, `entity`, `relationship`. Do not rename these fields without checking with the team.

**Unified KB item** (`GET /kb`):
```json
{"kb_id": "kb_00001", "type": "definition", "text": "Gradient descent minimizes a loss function.",
 "variants": ["Gradient descent is an optimization algorithm used to reduce the loss."],
 "sources": [{"video_id": "ml_lecture_1", "timestamp": "00:03:10", "unit_id": "…"},
             {"video_id": "ml_lecture_2", "timestamp": "00:02:15", "unit_id": "…"}],
 "merged_from": 2}
```

**Generated content** (`POST /generate`): `{"output_type", "language", "content", "kb_ids"}`; for Sinhala the response also
carries the consistency report (mean score, lowest score, threshold, flagged sentences).

**Plain-text export for C4** (`GET /export/kb.txt`), one line per KB item:
```
[kb_00001] (definition) Gradient descent minimizes a loss function. | sources: ml_lecture_1@00:03:10, ml_lecture_2@00:02:15
```

---

## API reference

Interactive docs (try every endpoint): http://localhost:8000/docs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend and MongoDB status. Reports an error if MongoDB is unreachable. |
| POST | `/ingest` | Strict-format JSON for one video. |
| POST | `/ingest/raw` | C1 JSON in a flexible format, as the request body. |
| POST | `/ingest/file` | Upload a C1 JSON file (422 with a clear message if it is not valid JSON or has an unknown item type). |
| POST | `/fusion/run` `{video_ids?}` | Preprocess, embed, group and merge. Returns `{units_in, kb_items_out, reduction_pct}`. |
| GET | `/kb` `?type=&limit=&skip=` | List KB items with their sources. |
| GET | `/kb/{kb_id}` | One KB item (404 if unknown). |
| POST | `/generate` `{output_type: summary|notes|quiz, language: en|si, kb_ids?}` | Grounded generation; Sinhala adds translation and consistency check. 404 if the KB is empty. |
| POST | `/translate` `{text, source, target, check}` | Translate any text en ⇄ si and return the consistency score. |
| GET | `/export/kb.txt` | KB as plain text for C4. |
| GET | `/export/generated.txt` `?output_type=&language=` | Latest generated text. |

---

## Database

MongoDB Atlas, the team's shared database (`MONGODB_DB`, default `project_j417`). C2 uses three collections:

| Collection | Holds |
|---|---|
| `raw_extractions` | One document per video: C1's items after the adapter (replaced when the same video is uploaded again). |
| `kb_items` | The Unified KB. **Rebuilt on every fusion run** (cleared, then re-inserted). |
| `generated_content` | Every generated output: type, language, text, the `kb_ids` it used. |

---

## Project structure

```
project_j417/
├── main.py                    FastAPI app, CORS, router, startup (preloads MiniLM, LaBSE, NLLB), serves frontend/dist
├── requirements.txt
├── .env.example               template for .env (the real .env is never committed)
├── app/
│   ├── core/config.py         settings from .env (models, thresholds, keys)
│   ├── db/mongo.py            MongoDB connection and collections
│   ├── models/                Pydantic: ingest.py, unit.py, kb.py
│   ├── services/
│   │   ├── adapter.py         C1 JSON in any accepted shape -> internal format
│   │   ├── preprocess.py      clean text into knowledge units
│   │   ├── embedding.py       MiniLM (and LaBSE) embeddings
│   │   ├── dedupe.py          cosine similarity + union-find grouping
│   │   ├── merge.py           KB items with variants and sources
│   │   ├── llm.py             one wrapper for the LLM provider (Gemini)
│   │   ├── generator.py       grounded prompts: summary / notes / quiz
│   │   ├── translator.py      NLLB-200 English <-> Sinhala
│   │   └── consistency.py     LaBSE English-vs-Sinhala check
│   └── api/
│       ├── router.py
│       └── routes/            health, ingest, fusion, kb, generate, export, translate
├── scripts/                   preflight, test_*, make_standin_data, make_candidate_pairs, evaluate_dedupe
├── evaluation/                labelled pairs and results
└── frontend/                  React + Vite "Knowledge Studio"
    ├── vite.config.js         proxies /api to the backend
    └── src/
        ├── App.jsx, App.css, index.css, api.js
        └── components/        IngestFuse, KnowledgeBase, Generate, Translate, Consistency
```

---

## Setup

Requirements: Python 3.10+, Node.js 18+, a MongoDB Atlas connection, a Gemini API key, Git. A GPU is optional (NLLB is
faster with one; on CPU it works but the first Sinhala request is slow).

1. Backend packages (from the `project_j417` folder):
   ```
   py -m venv venv
   venv\Scripts\activate
   py -m pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill it in (see [Configuration](#configuration-env)). **Never commit `.env`.**
3. Atlas (team lead, one time): Network Access must allow your IP (or `0.0.0.0/0`), and the shared user needs read/write.
4. Frontend packages (from the `frontend` folder):
   ```
   npm install
   ```
5. Check everything before a demo (database, embeddings, LLM reply and a real Sinhala translation):
   ```
   py -m scripts.preflight
   ```

---

## Running

Backend (from `project_j417`, virtual environment active):
```
py -m uvicorn main:app --reload
```
Open http://localhost:8000/docs. The first start downloads the models (several GB in total) and preloads them, so
allow a few minutes once; later starts are quicker.

Frontend (second terminal, from `project_j417/frontend`, backend running):
```
npm run dev
```
The app opens at http://localhost:5173 and proxies the API to port 8000. In the page:
1. **Ingest & Fuse**: choose a C1 JSON file, press **Upload file**, then **Run fusion**. You see knowledge units in, KB items out and the redundancy removed.
2. **Knowledge Base**: browse the merged items and their sources.
3. **Generate**: choose Summary / Study notes / Quiz and English or Sinhala, then generate. Every sentence carries a `[kb_id]`.
4. **Translate**: translate any text English ⇄ Sinhala and see the consistency score and any flagged sentences.

For a single-server demo, build the frontend (`npm run build`); `main.py` then serves `frontend/dist` at `/`.

---

## Configuration (`.env`)

Each setting on its own line, no quotes, no spaces around `=`.

| Variable | Example | Meaning |
|---|---|---|
| `MONGODB_URI` | `mongodb+srv://…` | Atlas connection string. A secret: never commit or share it. |
| `MONGODB_DB` | `project_j417` | Database name |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Model used for dedupe |
| `SIM_THRESHOLD` | `0.85` | Duplicate threshold |
| `LLM_PROVIDER` | `gemini` | `gemini` (default) or `anthropic` if configured |
| `LLM_API_KEY` | (secret) | Your LLM API key. Never commit it. |
| `LLM_MODEL` | `gemini-3.5-flash-lite` | Generation model |
| `NLLB_MODEL` | `facebook/nllb-200-distilled-600M` | Translation model |
| `CONSISTENCY_MODEL` | `sentence-transformers/LaBSE` | Model for the Sinhala check |
| `CONSISTENCY_THRESHOLD` | `0.70` | Pass mark for the Sinhala check |
| `NLLB_ADAPTER_PATH` | `models/nllb-si-lora` | *Optional, next stage:* folder of a fine-tuned LoRA adapter. Empty = original NLLB. |

---

## Scripts and checks

Run all of them from `project_j417` as modules (`py -m scripts.<name>`), otherwise Python cannot find the package.

| Script | Purpose |
|---|---|
| `scripts.preflight` | One command before a demo: Mongo ping, KB count, embeddings, an LLM reply, a Sinhala translation. |
| `scripts.test_embedding` | Prints a similarity grid for sample sentences: paraphrases score high, different facts low. |
| `scripts.test_fusion` | Tiny fusion test on sample units (for example 6 units → 4 KB items). |
| `scripts.test_llm` | Checks the LLM wrapper returns a reply. |
| `scripts.test_grounding` | Checks that generated `[kb_id]` citations exist in the KB. |
| `scripts.test_translation` | Translation checks: citations preserved, matched vs mismatched pairs score clearly apart, Sinhala reads correctly. |
| `scripts.make_standin_data` | Builds stand-in data in C1's format while C1's real output is not available. |
| `scripts.make_candidate_pairs` | Lists candidate unit pairs to label as duplicate / not duplicate. |
| `scripts.evaluate_dedupe` | Sweeps thresholds on the labelled pairs and reports precision, recall and F1. |

Sample C1-format files for demos: `test_component1.json` (machine learning, 4 videos, 26 items) and
`test_component1_networks.json` (computer networking, 4 videos, 26 items).

---

## Troubleshooting

| Problem | Meaning and fix |
|---|---|
| `No module named scripts.…` or `app…` | Run from the `project_j417` folder as `py -m scripts.<name>`, and make sure `scripts/__init__.py` exists. |
| `Unknown LLM_PROVIDER: gemini, LLM_API_KEY=…` | Two `.env` lines were joined on one line. Put each setting on its own line, with no quotes. |
| `No module named anthropic` / `google` | `py -m pip install anthropic` or `py -m pip install google-genai`, then add to `requirements.txt`. |
| Pasted `LLM_*` lines into PowerShell and got errors | Those lines belong inside the `.env` file, not the terminal. |
| `/health` shows a database error | Check `MONGODB_URI`, that MongoDB is reachable, and that your IP is allowed in Atlas → Network Access. |
| Fusion numbers look too high (for example 51 units from 26 items) | Old test data is still in `raw_extractions`. Clear the collection, upload again, run fusion. |
| First Sinhala request is very slow | NLLB is loading. Models are preloaded at startup; run `scripts.preflight` or one translation before a demo. |
| Sinhala shows as boxes or `?` in PowerShell | The console cannot show Sinhala. View it in the browser (`/docs` or the app). |
| Gemini returns errors or slow replies | Free-tier rate limit. Wait a little, retry, or use a second key. |
| `[Errno 10048] … only one usage of each socket address` | Port 8000 is taken (another component's backend). Use `--port 8010` and change the proxy target in `frontend/vite.config.js`. |
| Page cannot reach the API | The backend is not running, or the Vite proxy port does not match the backend port. |
| Offline demo | Set `HF_HUB_OFFLINE=1` after the models have been downloaded once. Gemini still needs internet; keep a hotspot as a backup. |

---

## Results and evaluation

### Demo runs on stand-in data (measured)

| Run | Knowledge units in | KB items out | Redundancy removed |
|---|---|---|---|
| Small fusion test (`scripts.test_fusion`) | 6 | 4 | 33.3 % |
| Demo upload `test_component1.json` (included earlier test data in the database) | 51 | 36 | 29.4 % |

Sinhala check examples (`POST /translate`): "I am a boy." → Sinhala, consistency mean **0.902**. Translated back, it came out
as "I was a boy.", with score **0.804**, still above the 0.70 pass mark. This is a real limit: LaBSE measures meaning
similarity and can miss a small change such as tense.

### Evaluation to run and report (fill these in with your own measured numbers)

| What | How | Result |
|---|---|---|
| Duplicate detection | Label ≥ 100 candidate pairs (`make_candidate_pairs`), then `evaluate_dedupe` at thresholds 0.70 – 0.95 | precision [X], recall [X], F1 [X] at 0.85; best threshold [X] |
| Embedding model comparison | Same labelled pairs with two or three other models | [table] |
| Grouping method | Union-find vs average-linkage clustering | [table] |
| Faithfulness of generation | `test_grounding` plus manual check that every claim is in a cited KB item | [X] % of sentences supported |
| Sinhala quality | chrF++ against human reference translations, and 1–5 human ratings of meaning and fluency | chrF++ [X]; adequacy [X]; fluency [X] |

Do not quote numbers in this table until they have actually been measured.

---

## Feedback on the prototype

First tester feedback round (record the real tester names and dates):

| What the tester said | What was done |
|---|---|
| The `[kb_00001]` citation tags make the summary hard to read. | [done / planned] A show/hide citations toggle. The tags stay in the data so every claim can be traced. |
| Study notes and quiz show raw `##` and `**` symbols. | [done / planned] Render markdown as headings, bullets and bold in the Generate screen. |
| Some Sinhala letters look split (for example "යන්ත් ර" instead of "යන්ත්‍ර"), the Sinhala quiz shows `**`, and one back-translation said "I was a boy" instead of "I am a boy". | [done / planned] Strip markdown before translating; Unicode NFC clean-up of the Sinhala output; font and zero-width-joiner check. The tense error is listed as a known limit. |

---

## Known limitations

- Tested with **stand-in data** in C1's format; the real C1 JSON may differ (only `adapter.py` should need to change).
- The labelled evaluation set is small so far; the thresholds 0.85 and 0.70 are starting values, not yet proven best.
- One global threshold for all item types; short entity items (for example a person's name) behave differently from sentences.
- Union-find grouping can chain (single linkage); average-linkage clustering or HDBSCAN would be safer.
- Comparison is O(n²); fine for hundreds of units, slow for many thousands.
- The KB is rebuilt on every fusion run, not atomically, and `kb_id`s can change between runs. There are no MongoDB indexes yet.
- Generation uses a free-tier LLM (rate limits; free-tier data may be used by Google). The LLM can still add unsupported
  details, which the KB-only prompt and citations limit but cannot rule out.
- Sinhala quality is **not yet rated by humans**. LaBSE flags large meaning drift but can miss tense and negation errors.
- NLLB-200 weights are non-commercial licence.
- No authentication, and CORS is open (`*`) for development.
- Neo4j (a knowledge graph in the team's design) is future work; MongoDB is used for now.

---

## Next stage: better Sinhala accuracy

The viva panel asked for more accurate Sinhala output. The plan, in order, with real measurements at every step:

1. **Test set:** 60–100 KB-style English sentences with human reference translations from a fluent Sinhala speaker; baseline chrF++ and human ratings of today's output.
2. **Quick fixes:** Unicode NFC clean-up and zero-width-joiner check, strip markdown before translation, sentence-by-sentence translation, shorter English from the generator, a glossary of technical terms approved by a Sinhala reviewer.
3. **Compare options on the same test set:** current NLLB 600M, NLLB 1.3B (and 3.3B if hardware allows), Gemini translating directly, NLLB draft + Gemini post-edit, a commercial translation API as a reference.
4. **Stronger checks:** back-translation, number and name check, simple negation and tense rules, retry with a better model when a sentence is flagged.
5. **Optional fine-tuning:** LoRA fine-tuning of NLLB on reviewed English–Sinhala pairs from this domain. Tools prepared:
   `scripts/prepare_mt_data.py` (extract sentences → Gemini drafts → human review sheet → train/val/test),
   `train_nllb_lora.py` (Colab, reports chrF++ for original vs fine-tuned on a held-out test set) and a `translator.py`
   that loads the adapter when `NLLB_ADAPTER_PATH` is set (falls back to the original model if not). Fine-tuning is only kept if it beats the
   other options on the held-out test set and in human ratings. If NLLB is fine-tuned, it is no longer "frozen"; the other three models stay frozen.
6. **User study:** ≥ 10 Sinhala-speaking students rate the final output; report a before/after table.

Project deadline set by the supervisor: **1 January**. Other future work: atomic KB rebuild, MongoDB indexes, per-type
thresholds, a vectorised O(n²) step, connection to C4 and the Flutter app with real C1 data, and a Neo4j graph.

---

## What was built, in order

1. **Skeleton:** FastAPI app, config from `.env`, MongoDB connection, `/health`, `/ingest`.
2. **Preprocessing and embeddings:** knowledge units, MiniLM embeddings, similarity test script.
3. **Fusion:** dedupe (cosine + union-find), merge with variants and sources, `/fusion/run`, test script.
4. **Unified KB API:** `/kb` and `/kb/{kb_id}`.
5. **Real-format ingestion:** the flexible JSON adapter, `/ingest/raw` and `/ingest/file`, stand-in data generator.
6. **Generation:** LLM wrapper (Gemini), grounded prompts for summary / notes / quiz, `/generate`, grounding test.
7. **Export for C4:** `/export/kb.txt` and `/export/generated.txt`.
8. **Sinhala output:** NLLB-200 translator (markdown and citations kept out of the model), LaBSE consistency check, `/translate`, language option in `/generate`.
9. **Evaluation tooling:** candidate pair maker and threshold sweep.
10. **Web app:** React + Vite "Knowledge Studio" with Ingest & Fuse, Knowledge Base, Generate (summary / notes / quiz, English / Sinhala) and Translate.
11. **Demo readiness:** model preloading at start, `scripts.preflight`, backend serving the built frontend, offline-demo notes, sample JSON files.
12. **Progress Presentation 1:** demo, slides, viva preparation, first tester feedback.
13. **Next:** Sinhala accuracy improvement (see above).

---

## Plugging into the other components

- **From C1:** call `POST /ingest/file` (or `/ingest/raw`) with C1's JSON. If the format changes, edit `app/services/adapter.py` only.
- **To C4 (and the Flutter app):** read `GET /kb` (structured, with timestamps and sources) or `GET /export/kb.txt`
  (plain text), and `GET /export/generated.txt?output_type=summary&language=si` for generated content.
- **Sharing one backend:** other components also use ports 8000 and 5173; start C2 on another port (`--port 8010`) and
  change the Vite proxy if they run on the same machine.
- **AI usage:** the four models are all pre-trained and used frozen; nothing is trained in the current version.




## Component 3 – Audience feedback mining

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




# C4 — Background Music Analysis + Prescriptive Recommendations
Analyzes YouTube videos and podcasts with AI. C4 looks at the **audio itself**: the background music, how
loud it is under the narration, and what mood it creates, and then turns that into advice for the creator.

**Research gap:** existing tools (YouTube chapters, transcripts, AI summarisers) never analyse the audio (music, mood,
loudness), even though audio is a known driver of engagement and drop-off, and none turn analytics into
*prescriptive* advice ("change this") instead of just *descriptive* statistics ("this happened").

C4 has two parts, each with its own page in the app:

1. **Part 1, Affective Audio Analysis** (descriptive): separates the narration from the background music, predicts the
   music's emotion over time (**valence**: negative ↔ positive, **arousal**: calm ↔ energetic), describes the music in
   words and measures audio problems (background too loud under the voice, distortion, dead air).
2. **Part 2, Content Enhancement Recommendations** (descriptive + prescriptive): combines Part 1 with the outputs of
   C1 (transcript sections), C2 (knowledge gaps) and C3 (audience comments), dummy data for now, into a description of
   each section, ranked recommendations with evidence and YouTube links, and a validation against viewer comments.

> Status: progress-presentation build (~50% of the full component). C1, C2 and C3 inputs are dummy data.

---

## Contents

1. [How it works](#how-it-works)
2. [Technologies used and why](#technologies-used-and-why)
3. [Key concepts explained](#key-concepts-explained)
4. [The emotion model (my own work)](#the-emotion-model-my-own-work)
5. [Recommendation rules](#recommendation-rules)
6. [API reference](#api-reference)
7. [Database](#database)
8. [Project structure](#project-structure)
9. [Setup](#setup)
10. [Running](#running)
11. [Configuration (`.env`)](#configuration-env)
12. [Model weights](#model-weights)
13. [Troubleshooting](#troubleshooting)
14. [Results](#results)
15. [Known limitations](#known-limitations)
16. [Tests](#tests)

---

## How it works

```
PART 1  [Page 1] --POST /audio/analyze--> [FastAPI backend]
          1. validate the YouTube link, reuse the saved result if there is one
          2. download the first 3 minutes of audio (fast Range request, ffmpeg fallback)
          3. cut into 10 s windows (5 s hop)
          4. FIRST LOOK (~15 s):  mixed audio -> CLAP -> BiLSTM+attention -> valence/arousal   [status: processing]
          5. IN THE BACKGROUND (~2 min): Demucs splits voice | background music
             background -> CLAP -> BiLSTM+attention -> valence/arousal per window
             voice vs. music loudness -> audio problems;  CLAP text matching -> "sounds like ..."   [status: complete]
          -> saved in MongoDB "audio_analyses"; the page polls until the full result is ready

PART 2  [Page 2] --POST /recommendations/{video_id}--> [FastAPI backend]
          Part 1 result + C1 sections + C2 gaps + C3 comments (dummy JSON)
          -> section summaries (descriptive) -> rules R1-R9 (prescriptive) -> validation vs. comments
          -> saved in MongoDB "recommendation_reports"
```

Training of the emotion model happens separately in Google Colab (`notebooks/`). The backend only loads the saved
weights file.

---

## Technologies used and why

Tools marked **pretrained** are used as they are (frozen, never changed). Everything marked **mine** was built or
trained for this project (see [`docs/CUSTOMIZATION_TABLE.md`](docs/CUSTOMIZATION_TABLE.md)).

### Audio and machine learning

| Technology | What it does here | Pretrained or mine |
|---|---|---|
| **yt-dlp** | Reads a video's title/duration and finds its audio stream on YouTube. | existing tool |
| **ffmpeg** | Converts the downloaded audio to WAV (fallback download path). | existing tool |
| **librosa / soundfile** | Loads audio, resamples to 48 kHz, mixes to mono. | library |
| **Demucs `htdemucs`** (Meta) | Splits audio into drums, bass, other and vocals. Vocals = narration; the rest = background music and effects. | **pretrained** |
| **CLAP** `laion/clap-htsat-unfused` (LAION) | Turns a 10 s audio window into an *embedding* of 512 numbers. Its text side also lets us describe music in words. | **pretrained** |
| **PyTorch** | Runs Demucs, CLAP and my emotion head (CPU build). | library |
| **Hugging Face `transformers`** | Downloads and runs CLAP. | library |
| **BiLSTM + attention head** | Predicts valence and arousal from the CLAP embeddings. | **mine (trained)** |
| **DEAM dataset** | Songs with human valence/arousal ratings; the training data for my head. | public dataset |
| **Google Colab** | Free GPU for training (notebooks 01 and 02). | service |

### Application

| Technology | What it does here |
|---|---|
| **FastAPI + Uvicorn** | The backend web API (Uvicorn is the server that runs it). Gives automatic docs at `/docs`. |
| **Pydantic** (comes with FastAPI) | Checks that every JSON response has the agreed shape (`backend/schemas.py`). |
| **Streamlit** | The web UI, written in Python. Two pages, themed in `.streamlit/config.toml`. |
| **Plotly** | Interactive charts (emotion timeline, valence–arousal map). |
| **MongoDB Atlas + pymongo** | Stores every analysis and report so past videos reopen instantly without recomputing. |
| **python-dotenv** | Reads secrets (the database address) from `.env` so they never appear in code or git. |
| **requests** | Frontend → backend calls, and the fast partial audio download. |
| **pytest** | Automatic tests. |

---

## Key concepts explained

- **Valence** and **arousal**: the two numbers that describe an emotion in Russell's *circumplex model*. Valence is how
  negative (−1) or positive (+1) it feels; arousal is how calm (−1) or energetic (+1). Both are in the range [−1, 1].
- **Quadrants**: the signs give four named areas: `energetic_positive` (+,+), `tense_negative` (−,+),
  `low_negative` (−,−, sad/bored) and `calm_positive` (+,−).
- **Embedding**: a list of numbers (here 512) that summarises what a piece of audio sounds like. Similar sounds get
  similar numbers, so a small model can work with these instead of raw audio.
- **Window**: a 10-second slice of audio. Windows start every 5 seconds, so neighbours overlap by 5 s. Only the first
  3 minutes of each video are analysed (about 35 windows).
- **BiLSTM** (bidirectional Long Short-Term Memory): a neural network that reads a sequence forwards *and* backwards,
  so each window's prediction can use what came before and after it.
- **Attention**: lets every window look directly at the most relevant other windows instead of only its neighbours.
- **Source separation**: splitting a mix into its parts (voice vs. music). Needed because the question is about the
  *background* audio, and the model was trained on music.
- **Zero-shot description**: CLAP maps audio and text into the same space, so the music can be compared with written
  descriptions like "tense dramatic cinematic music" without training anything new.
- **CCC** (Concordance Correlation Coefficient): the main score for the emotion model. 1 = perfect agreement with the
  human ratings, 0 = none. Stricter than plain correlation because it also penalises a wrong scale or offset.
- **Baseline and ablation**: a baseline is a simple model to beat (ridge regression). An ablation removes one part of
  the model (attention) to show whether that part is worth having.
- **Loudness in dB**: measured relative to full scale (0 dB = maximum, more negative = quieter). Used to compare music
  against speech.
- **Clipping**: samples at the maximum level, heard as distortion. **Dead air**: stretches of near silence.
- **Lift over chance**: in the validation, how many times better the flagged sections match negative viewer comments
  than randomly placed sections of the same length (1× = no better than chance).
- **Mock**: fake or placeholder data. Anything dummy is marked `"mock": true` in the JSON and labelled in the UI.

---

## The emotion model (my own work)

```
10 s audio window --CLAP (frozen)--> 512-number embedding
        sequence of embeddings --> BiLSTM (128 units per direction)
                               --> self-attention + residual connection + LayerNorm
                               --> Linear --> tanh --> [valence, arousal] per window, each in [-1, 1]
```

- **Trained** on DEAM (about 1,800 songs, dynamic valence/arousal ratings). Only the annotated regions were used, with
  the same 10 s / 5 s windowing as the backend, and each window's label is the average of the ratings inside it.
- **Split by song** (never windows of one song across train/validation/test) to avoid data leakage.
- Masked MSE loss, Adam optimiser, dropout 0.3, early stopping, fixed random seed.
- **Compared** with a mean predictor, ridge regression and a BiLSTM without attention (see [Results](#results)).
- The network class in `backend/emotion_head.py` must stay identical to the one in
  `notebooks/02_train_emotion_head.ipynb`, because the weights file stores only numbers, not code.
- **Mock model:** with `USE_MOCK_MODEL=true` a seeded random walk produces fake but stable values (marked
  `"mock": true`) so the whole pipeline can run without PyTorch or the weights.

### Why separate the voice first?

The model learned from music. Running it on the music-only track brings the input closer to the training data. In
testing, the narration was inflating the predicted energy (mean arousal about +0.28 mixed vs. −0.02 on the separated
music). The mixed-audio result is kept next to the music result for comparison.

### Measured audio problems

Computed per window from the voice and music tracks, no machine learning involved, so they are checkable:

| Problem | How it is detected |
|---|---|
| Music too loud under the narration | Music less than 10 dB quieter than speech for at least 15 s (high severity if within 3 dB or louder) |
| Distortion | More than 0.1 % of samples at maximum level |
| Dead air | Whole mix quieter than −50 dB for at least 10 s |

---

## Recommendation rules

Part 2 uses transparent rules (not a black box), so every recommendation comes with plain-language evidence and a
YouTube link at the right moment. Thresholds are starting values in `backend/config.py`, to be tuned.

| Rule | Trigger | Advice |
|---|---|---|
| R1 low energy | Arousal clearly below the video's own average for ≥ 30 s (high if a negative comment is within ±15 s) | Raise pace, add dynamic music, or shorten |
| R2 tense audio | Arousal above and valence below the video's average for ≥ 20 s (high if viewers complain about loud/music) | Lower music under narration |
| R3 flat profile | Arousal barely varies across the clip | Vary music energy between sections |
| R4 complex content | A knowledge gap (C2) overlaps intense audio | Use calmer audio, add a recap or visual |
| R5 audio complaints | Negative C3 sentiment with audio keywords (music, loud, volume, boring, slow); cross-checked with measured loudness | Review mixing levels and pacing |
| R6 requested topics | C3 topics not covered by any gap or C1 section | Consider a follow-up video |
| R7 mood–content mismatch | Music livelier than average during an explanation, or calmer in the hook (uses C1 sections) | Match music mood to the content type |
| R8 music too loud | Measured in Part 1; C3 loudness complaints raise severity | Lower the music |
| R9 audio quality | Distortion or dead air measured in Part 1 | Fix the mix or remove the gap |

- **Relative thresholds:** R1, R2 and R4 compare each window with the *same video's* average, because on speech + music
  videos the model's predictions stay near neutral and fixed thresholds never triggered.
- **Confidence (0–1):** starts at 0.5 for audio-only evidence, +0.2 for each independent signal that agrees (nearby
  comment, knowledge gap), capped at 0.95.
- Overlapping recommendations of the same kind are merged into one card, then sorted by severity and confidence.

### Validation against viewer comments

Each flagged section is checked against negative C3 comments within ±15 s. The report gives the **agreement** (share of
flagged sections with a nearby negative comment), the **random baseline** (the same share for randomly placed sections
of the same length, computed exactly) and the **lift** (agreement ÷ baseline). With dummy comments this shows the
method only; it becomes evidence once real C3 data is connected.

---

## API reference

Interactive docs (try every endpoint): http://localhost:8000/docs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| POST | `/audio/analyze` | Part 1. Body: `{"youtube_url", "force_reanalyze"}`. Returns the first look immediately; status becomes `complete` when separation finishes. |
| GET | `/audio/analyses` | List saved analyses |
| GET | `/audio/analyses/{video_id}` | One saved analysis (the page polls this while separating) |
| DELETE | `/audio/analyses/{video_id}` | Delete one analysis and its recommendations |
| DELETE | `/audio/analyses` | Delete all of C4's analyses and recommendations |
| POST | `/recommendations/{video_id}` | Part 2. Needs a *complete* Part 1 result (404 if none, 409 if still separating) |
| GET | `/recommendations` | List saved reports |
| GET | `/recommendations/{video_id}` | One saved report |

Error codes: `400` not a valid YouTube link, `422` the video can't be read (private, removed, region-blocked),
`502` the audio download failed, `503` database unreachable.

The full JSON shapes (the "data contracts" other components and the final dashboard rely on) are in `CLAUDE.md`
section 8 and implemented in `backend/schemas.py`. Do not rename fields without checking with the team.

---

## Database

MongoDB Atlas, the team's shared database (`MONGODB_DB`, default `project_j417`). C4 only touches its own two
collections:

| Collection | Holds |
|---|---|
| `audio_analyses` | One document per video: Part 1 result (segments, separation info, music description, audio problems) |
| `recommendation_reports` | One document per video: Part 2 report (section summaries, recommendations, validation, inputs used) |

`video_id` is unique, so re-analysing replaces the old document. Analysed videos reopen instantly from here.

---

## Project structure

```
c4-audio-emotion/
├── backend/
│   ├── main.py              FastAPI app and all routes; two-phase Part 1 (first look + background separation)
│   ├── config.py            settings from .env and all constants/thresholds
│   ├── schemas.py           Pydantic models for the JSON contracts
│   ├── audio_utils.py       URL check, video info, download (fast + fallback), windowing
│   ├── separation.py        Demucs voice/music separation (and NoSeparation when off)
│   ├── model.py             MockEmotionModel + RealEmotionModel, CLAP embedding and text description
│   ├── emotion_head.py      my BiLSTM + attention network
│   ├── audio_analysis.py    Part 1 pipeline: separate -> predict -> describe -> measure
│   ├── audio_problems.py    loudness, clipping and silence measurements
│   ├── fusion.py            recommendation rules R1-R9, confidence, merging
│   ├── report.py            Part 2: section summaries + recommendations + validation
│   ├── validation.py        agreement, random baseline and lift against comments
│   ├── mock_loader.py       loads dummy C1/C2/C3 (the one place to swap in real data)
│   └── db.py                MongoDB save/get/list/delete
├── frontend/
│   ├── app.py               Streamlit entry point and page navigation
│   ├── audio_analysis.py    Page 1: Affective Background Audio Analysis
│   ├── recommendations.py   Page 2: Recommendations for Enhancements
│   ├── common.py, style.py  shared helpers, theme and loading animations
├── mock_data/               dummy C1 transcript, C2 gaps, C3 sentiment (JSON)
├── notebooks/               01 prepare DEAM embeddings, 02 train the emotion head (run in Colab)
├── models/                  put c4_emotion_head.pt here (not in git)
├── scripts/                 manual checks: database, yt-dlp, download, CLAP, separation
├── tests/                   automatic tests (pytest)
├── docs/                    DESIGN_DECISIONS.md, CUSTOMIZATION_TABLE.md
├── CLAUDE.md                scope, architecture and data contracts
├── PROGRESS.md              daily progress log
├── requirements.txt
└── .env.example             template for .env (the real .env is never committed)
```

---

## Setup

Requirements: Windows, Python 3.10+ (developed on 3.13), Git. All commands run from the `c4-audio-emotion` folder.

1. Create a virtual environment and install packages (CPU PyTorch first, so pip doesn't pick the large GPU build):
   ```
   py -3.13 -m venv venv
   venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
   venv\Scripts\python -m pip install -r requirements.txt
   ```
2. Install ffmpeg (needed to convert audio): `winget install Gyan.FFmpeg`, then restart the terminal and check `ffmpeg -version`.
3. Copy `.env.example` to `.env` and set `MONGODB_URI` to the team's shared Atlas connection string (ask the team lead; never commit `.env`).
4. Check everything works:
   ```
   venv\Scripts\python -m scripts.test_db_connection
   venv\Scripts\python -m scripts.test_ytdlp
   ```
   The first should end with `All database checks passed.`; the second prints a video's title and duration.
5. Optional deeper checks:
   ```
   venv\Scripts\python -m pytest                        (automatic tests, no internet needed)
   venv\Scripts\python -m scripts.test_audio_download   (real download -> windows)
   venv\Scripts\python -m scripts.test_clap_embeddings  (first run downloads the ~600 MB CLAP model)
   venv\Scripts\python -m scripts.test_separation       (Demucs voice/music separation on a real video)
   ```

---

## Running

Backend (from the `c4-audio-emotion` folder):
```
venv\Scripts\python -m uvicorn backend.main:app --reload
```
Open http://localhost:8000/docs to try the endpoints.
The first start loads Demucs (~80 MB download once) and CLAP (~20 s). A new analysis gives a first look in ~15 s and the
full result ~2 min later; analysed videos reopen instantly, so analyse demo videos once beforehand. Keep the laptop
plugged in (separation is slower on battery).
With `USE_MOCK_MODEL=true` the emotion values are fake and marked `"mock": true`.

Frontend (second terminal, same folder, backend must be running):
```
venv\Scripts\python -m streamlit run frontend/app.py
```
The app opens at http://localhost:8501 with two pages in the sidebar:
1. **Affective Background Audio Analysis**: paste a YouTube link, click **Analyze audio**. A first look appears in ~15 s; the voice/music separation then finishes in the background (~2 min, with a progress bar) and the page updates itself.
2. **Recommendations for Enhancements**: pick the video, click **Generate recommendations** (under a second).

Saved analyses are listed in the sidebar; the 🗑 next to each one deletes it (with a confirmation), and **Delete all analyses** clears the list. Only C4's own results are deleted.
The backend address is not shown on the page; to change it set `C4_BACKEND_URL` before starting Streamlit.
Light and dark themes: top-right ⋮ → Settings.

Good demo video: `https://www.youtube.com/watch?v=e-P5IFTqB98` (has its own dummy C1/C2/C3 data).

**Running without PyTorch** (mock model, no separation), e.g. on a PC that blocks PyTorch (see Troubleshooting):
```powershell
$env:USE_MOCK_MODEL='true'; $env:USE_SOURCE_SEPARATION='false'
venv\Scripts\python -m uvicorn backend.main:app --port 8010
```
Environment variables set this way override `.env` for that terminal only. If you change the port, set
`C4_BACKEND_URL=http://127.0.0.1:8010` before starting Streamlit.

---

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `MONGODB_URI` | none (required) | Atlas connection string. A secret: never commit or print it. |
| `MONGODB_DB` | `project_j417` | Database name |
| `USE_MOCK_MODEL` | `true` | `true` = fake emotion values; `false` = trained model (needs the weights file) |
| `MODEL_PATH` | `models/c4_emotion_head.pt` | Where the trained weights are |
| `USE_SOURCE_SEPARATION` | `true` | `true` = Demucs voice/music split (~2 min); `false` = analyse mixed audio (fast) |
| `C4_BACKEND_URL` | local backend | Set in the terminal that starts Streamlit, not in `.env` |

Fixed constants (window 10 s, hop 5 s, 3 minutes, 48 kHz) and all rule thresholds are in `backend/config.py`.

---

## Model weights

The trained head is not stored in git (model weights are large binary files).

1. Download `c4_emotion_head.pt` from Google Drive: `My Drive/C4/training/` (produced by `notebooks/02_train_emotion_head.ipynb`).
   _Shared link for the panel/teammates: TODO._
2. Put it in `c4-audio-emotion/models/c4_emotion_head.pt`.
3. In `.env` set `USE_MOCK_MODEL=false` and restart the backend.

The first start downloads the pretrained CLAP model (~600 MB) from Hugging Face; later starts take ~10 s.

---

## Troubleshooting

| Problem | Meaning and fix |
|---|---|
| `OSError: [WinError 4551] An Application Control policy has blocked this file ... torch_python.dll` | Windows **Smart App Control** (or a school/work policy) blocks PyTorch's unsigned DLLs. Either run the [mock mode](#running) (no PyTorch needed), turn Smart App Control off (Windows Security → App & browser control; it cannot be turned back on without resetting Windows), or run the backend on another machine / Colab. Demucs also needs PyTorch, so set `USE_SOURCE_SEPARATION=false` too. |
| `Error 422: Could not read this video ... This video is not available` | The video is private, removed or region-blocked, so yt-dlp can't read it. Open it in a browser; if it doesn't play there, use another video. This is expected behaviour, not a bug. |
| `[Errno 10048] ... only one usage of each socket address` | Port 8000 is taken (often by an earlier backend still running). Close the old terminal or start on another port with `--port 8010` and set `C4_BACKEND_URL`. |
| `503 Database unavailable` | Check `MONGODB_URI` in `.env` and that your IP is allowed in Atlas → Network Access. |
| `FileNotFoundError: Trained weights not found` | Download `c4_emotion_head.pt` into `models/` (see [Model weights](#model-weights)) or set `USE_MOCK_MODEL=true`. |
| `502 Could not download the audio` | Network dropped or YouTube blocked the request. Try again; update yt-dlp (`pip install -U yt-dlp`) if it keeps failing. |
| `409` when generating recommendations | Voice/music separation is still running for that video. Wait for the progress bar to finish. |
| Analysis stuck on "processing" after a backend restart | A result left unfinished for more than 10 minutes is treated as lost. Click Analyze again (or tick re-analyse). |
| ffmpeg not found | `winget install Gyan.FFmpeg`, then restart the terminal. |

---

## Results

DEAM test songs, never seen in training. CCC = Concordance Correlation Coefficient (higher is better, max 1).

| Model | Valence CCC | Arousal CCC | Mean CCC |
|---|---|---|---|
| Ridge regression (baseline) | 0.564 | 0.800 | 0.682 |
| BiLSTM | 0.589 | 0.817 | 0.703 |
| **BiLSTM + attention** | **0.625** | **0.822** | **0.723** |

Each addition helps: the sequence model beats the per-window baseline, and attention adds a further gain. Results come
from a single training seed.

---

## Known limitations

- Trained on DEAM (music only). Demucs separation brings the input closer to music, but the background track still contains residual voice and sound effects; valence leans negative on science videos.
- C1, C2 and C3 inputs are **dummy data** (`mock_data/`, marked `"mock": true`), so the validation numbers only demonstrate the method.
- Separation takes about 1.5–2 minutes per video on CPU; only the first 3 minutes of each video are analysed.
- Rule thresholds are starting values to tune; model results come from a single training seed.
- Valence/arousal labels are subjective and noisy (people disagree), which caps how accurate any model can be.
- Out of scope for now: the browser extension, user accounts, the merged team dashboard, Sinhala/multilingual features, and optional LLM rewording of suggestions.

Full explanation: [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md). Pretrained vs. own work: [`docs/CUSTOMIZATION_TABLE.md`](docs/CUSTOMIZATION_TABLE.md). Scope and data contracts: [`CLAUDE.md`](CLAUDE.md). Daily log: [`PROGRESS.md`](PROGRESS.md).

---

## Tests

```
venv\Scripts\python -m pytest
```
77 automatic tests (URL parsing, windowing, download fallback + retries, separation helpers, loudness measurements, Part 1 pipeline and Part 2 report on synthetic audio, rules R1–R9, validation, dummy-data loader). Real-video checks: `scripts/test_separation.py`, `scripts/test_clap_embeddings.py`.