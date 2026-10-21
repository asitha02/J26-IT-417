# C4 — Audio Emotion Analysis + Prescriptive Recommendations

Component 4 of the IT4010 group research project (SLIIT). Two parts, each with its own page:

1. **Part 1, Affective Audio Analysis** (descriptive): separates the narration from the background music, predicts the
   music's emotion over time (**valence**: negative ↔ positive, **arousal**: calm ↔ energetic), describes the music in
   words and measures audio problems (background too loud under the voice, distortion, dead air).
2. **Part 2, Content Enhancement Recommendations** (descriptive + prescriptive): combines Part 1 with the outputs of
   C1 (transcript sections), C2 (knowledge gaps) and C3 (audience comments), dummy data for now, into a description of
   each section, ranked recommendations with evidence and YouTube links, and a validation against viewer comments.

> Status: progress-presentation build (~50% of the full component).

## Architecture

```
PART 1  [Page 1] --POST /audio/analyze--> [FastAPI]
          download first 3 min (fast Range request) -> Demucs: voice | background
          background + mixed -> 10 s windows -> CLAP -> BiLSTM+attention -> valence/arousal per window
          voice vs. background loudness -> audio problems;  CLAP text matching -> "sounds like ..."
          -> MongoDB "audio_analyses"
PART 2  [Page 2] --POST /recommendations/{id}--> [FastAPI]
          Part 1 result + C1 sections + C2 gaps + C3 comments (dummy JSON)
          -> section summaries (descriptive) -> rules R1-R9 (prescriptive) -> validation vs. comments
          -> MongoDB "recommendation_reports"
```

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

## Running

Backend (from the `c4-audio-emotion` folder):
```
venv\Scripts\python -m uvicorn backend.main:app --reload
```
Open http://localhost:8000/docs to try the endpoints: Part 1 `POST /audio/analyze`, `GET /audio/analyses[/{video_id}]`; Part 2 `POST /recommendations/{video_id}` (see CLAUDE.md 8.6).
The first start loads Demucs (~80 MB download once) and CLAP; with `USE_SOURCE_SEPARATION=true` an analysis takes about 2 minutes.
With `USE_MOCK_MODEL=true` the emotion values are fake and marked `"mock": true`.

Frontend (second terminal, same folder, backend must be running):
```
venv\Scripts\python -m streamlit run frontend/app.py
```
The app opens at http://localhost:8501 with two pages in the sidebar:
1. **1 · Audio Analysis**: paste a YouTube link, click **Analyze audio** (about 1.5–2 minutes for a new video).
2. **2 · Recommendations**: pick the video, click **Generate recommendations** (under a second).

Good demo video: `https://www.youtube.com/watch?v=e-P5IFTqB98` (has its own dummy C1/C2/C3 data).

## Model weights

The trained head is not stored in git (model weights are large binary files).

1. Download `c4_emotion_head.pt` from Google Drive: `My Drive/C4/training/` (produced by `notebooks/02_train_emotion_head.ipynb`).
   _Shared link for the panel/teammates: TODO._
2. Put it in `c4-audio-emotion/models/c4_emotion_head.pt`.
3. In `.env` set `USE_MOCK_MODEL=false` and restart the backend.

The first start downloads the pretrained CLAP model (~600 MB) from Hugging Face; later starts take ~10 s.

## Known limitations

- Trained on DEAM (music only). Demucs separation brings the input closer to music, but the background track still contains residual voice and sound effects; valence leans negative on science videos.
- C1, C2 and C3 inputs are **dummy data** (`mock_data/`, marked `"mock": true`), so the validation numbers only demonstrate the method.
- Separation takes about 1.5–2 minutes per video on CPU; only the first 3 minutes of each video are analysed.
- Rule thresholds are starting values to tune; model results come from a single training seed.

Full explanation: [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md). Pretrained vs. own work: [`docs/CUSTOMIZATION_TABLE.md`](docs/CUSTOMIZATION_TABLE.md).

## Results (DEAM test songs, never seen in training)

| Model | Valence CCC | Arousal CCC | Mean CCC |
|---|---|---|---|
| Ridge regression (baseline) | 0.564 | 0.800 | 0.682 |
| BiLSTM | 0.589 | 0.817 | 0.703 |
| **BiLSTM + attention** | **0.625** | **0.822** | **0.723** |

## Tests

```
venv\Scripts\python -m pytest
```
77 automatic tests (URL parsing, windowing, download fallback + retries, separation helpers, loudness measurements, Part 1 pipeline and Part 2 report on synthetic audio, rules R1–R9, validation, dummy-data loader). Real-video checks: `scripts/test_separation.py`, `scripts/test_clap_embeddings.py`.
