# C4 — Audio Emotion Analysis + Prescriptive Recommendations

Component 4 of the IT4010 group research project (SLIIT). Given a YouTube video, C4:

1. predicts the emotional tone of the audio over time (**valence**: negative ↔ positive, **arousal**: calm ↔ energetic),
2. combines it with audience sentiment (C3) and knowledge-gap signals (dummy data for now), and
3. gives the creator **prescriptive recommendations**: what to change, where, and why.

> Status: progress-presentation build (~50% of the full component). Work in progress.

## Architecture

```
[Streamlit UI] --POST /analyze (youtube_url)--> [FastAPI backend]
                                                     |
   1. validate URL, check MongoDB cache (video_id)   |
   2. download audio -> trim to 3 min -> 10 s windows (5 s hop)
   3. CLAP embeddings -> BiLSTM + attention head -> valence/arousal per window
   4. load dummy C3 sentiment + dummy knowledge gaps
   5. fusion rules -> recommendations
   6. save to MongoDB
   7. return JSON
                                                     |
[Streamlit UI] <------------ JSON ------------------+
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
   ```

## Running

Backend (from the `c4-audio-emotion` folder):
```
venv\Scripts\python -m uvicorn backend.main:app --reload
```
Open http://localhost:8000/docs to try the endpoints (`/health`, `POST /analyze`, `/analyses`, `/analyses/{video_id}`).
With `USE_MOCK_MODEL=true` the emotion values are fake and marked `"mock": true`.

Frontend (second terminal, same folder, backend must be running):
```
venv\Scripts\python -m streamlit run frontend/app.py
```
The page opens at http://localhost:8501. Paste a YouTube link and click **Analyze**.

## Model weights

The trained head is not stored in git (model weights are large binary files).

1. Download `c4_emotion_head.pt` from Google Drive: `My Drive/C4/training/` (produced by `notebooks/02_train_emotion_head.ipynb`).
   _Shared link for the panel/teammates: TODO._
2. Put it in `c4-audio-emotion/models/c4_emotion_head.pt`.
3. In `.env` set `USE_MOCK_MODEL=false` and restart the backend.

The first start downloads the pretrained CLAP model (~600 MB) from Hugging Face; later starts take ~10 s.

## Known limitations

- Trained on DEAM (music only); YouTube science videos mix speech and music, so predictions describe the overall audio mood and stay close to neutral.
- Audience sentiment (C3) and knowledge gaps are **dummy data** (`mock_data/`, marked `"mock": true`) until those components are connected.
- Only the first 3 minutes of each video are analysed.
- Rule thresholds are starting values to tune; results come from a single training seed.

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
47 automatic tests (URL parsing, windowing, download retries, fusion rules R1–R6, dummy-data loader).
