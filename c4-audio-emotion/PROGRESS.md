# Progress Log — C4

One entry per day: what was done, what's next, blockers.

## Day 1 — 7–11 Oct 2026

**Done**
- Installed Git, connected to the group repo `J26-IT-417`, working on branch `component4`.
- Created the project folder structure, `.gitignore`, `.env.example`, README skeleton and doc stubs.
- 11 Oct: the first version was removed during a group repo clean-up. Restored it into its own
  folder `c4-audio-emotion/` so C4 stays separate from the shared `project_j417/` backend.

**Next (Day 2)**
- Virtual environment + `requirements.txt`, MongoDB connection, `db.py`, DB test script, yt-dlp test.
- Decide: use the team's shared Atlas database (from `project_j417`) or my own cluster.

**Blockers**
- Behind schedule by ~3 days (planned Day 4 = 10 Oct). Need to catch up over Days 2–4.

## Day 2 — 13 Oct 2026

**Done**
- Virtual environment (Python 3.13) and `requirements.txt` (pymongo, python-dotenv, yt-dlp).
- Decided to use the team's shared Atlas database `project_j417` (collection `analyses`).
- `backend/config.py` (settings + constants) and `backend/db.py` (save / get / list / delete, unique index on `video_id`).
- `scripts/test_db_connection.py`: insert + read back + delete a test document — passes.
- `scripts/test_ytdlp.py`: reads a YouTube video's title and duration — passes.

**Next (Day 3)**
- FastAPI `/analyze` with `MockEmotionModel`, saving results to MongoDB.

**Blockers**
- ffmpeg not installed yet (needed by Day 5).
- yt-dlp warns about a missing JavaScript runtime (deno); may matter for audio downloads on Day 5.
- Confirm with the team that collection name `analyses` doesn't clash in the shared database.

## Day 3 — 14 Oct 2026

**Done**
- Installed `fastapi` + `uvicorn`.
- `schemas.py`: Pydantic models matching the CLAUDE.md section 8 JSON contracts.
- `audio_utils.py`: YouTube URL validation (watch / youtu.be / shorts), title + duration via yt-dlp, 10 s / 5 s segment timing (max 180 s).
- `model.py`: `MockEmotionModel` (seeded random walk, marked `"mock": true`), quadrant + overall summary helpers.
- `main.py`: `/health`, `POST /analyze` (with MongoDB cache), `GET /analyses`, `GET /analyses/{video_id}`; clear errors for bad URL (400), unavailable video (422), missing analysis (404), database down (503).
- Tested with curl: "Me at the zoo" → 3 mock segments saved to MongoDB; second request served from cache.

**Next (Day 4)**
- Streamlit UI connected to the backend (timeline chart, quadrant plot, results). Tag `v0.1-vertical-slice`.

**Blockers**
- `recommendations` is still an empty list; fusion rules come on Day 11 (a simple one may be added on Day 4 for the vertical slice).

## Day 4 — 14 Oct 2026

**Done**
- Installed `streamlit` + `plotly`.
- `frontend/app.py`: URL input + Analyze button, sidebar with backend URL and past analyses (click to reopen from MongoDB),
  mock-model warning badge, emotion timeline (mm:ss, recommendation ranges shaded), valence–arousal quadrant map,
  dummy-data section, recommendation cards sorted by severity, Download JSON.
- Clear UI errors: invalid URL, unavailable video, backend not running, invalid backend reply.
- `backend/fusion.py`: first rule **R1_low_energy** (audio-only: arousal < -0.3 for ≥ 30 s), wired into `/analyze`.
- Tested with Streamlit's AppTest: analyze flow, bad URL, backend down, recommendation card rendering.

**Next (Days 5–7)**
- Day 5: real audio download / trim / segment (needs ffmpeg, numpy, librosa, soundfile, pytest — awaiting approval).
- Day 6: CLAP embeddings (needs torch, transformers — awaiting approval).
- Day 7: DEAM + notebook 01 in Colab.

**Blockers**
- Package approvals for Days 5–6.
