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

1. Create a virtual environment and install packages:
   ```
   py -3.13 -m venv venv
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

_To be completed (Day 10): Google Drive link for `c4_emotion_head.pt` and where to place it._

## Known limitations

_To be completed. See `docs/DESIGN_DECISIONS.md`._
