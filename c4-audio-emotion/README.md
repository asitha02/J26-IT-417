# C4 — Audio Emotion Analysis + Prescriptive Recommendations
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
