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

_To be completed (Day 2): Python version, virtual environment, `pip install -r requirements.txt`, ffmpeg, `.env` setup._

## Running

_To be completed (Days 3–4): start the backend with `uvicorn` and the frontend with `streamlit`._

## Model weights

_To be completed (Day 10): Google Drive link for `c4_emotion_head.pt` and where to place it._

## Known limitations

_To be completed. See `docs/DESIGN_DECISIONS.md`._
