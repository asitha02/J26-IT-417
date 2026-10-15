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

## Day 5 — 15 Oct 2026

**Done**
- Installed ffmpeg 9.0.2 (winget), `librosa`, `soundfile`, `pytest`.
- `audio_utils.py`: `download_audio` (yt-dlp downloads ONLY the first 180 s, ffmpeg converts to WAV),
  `load_audio` (48 kHz mono via librosa), `cut_segments` (10 s windows, 5 s hop, last window padded with silence).
- `/analyze` now downloads real audio into a temporary folder that is deleted automatically.
- 22 automatic tests (`tests/`): URL parsing, window timing, padding, R1 rule. All pass.
- Real checks: 19 s video → 3 windows; 77-min documentary → only first 180 s downloaded → 35 windows of 480 000 samples.

## Day 6 — 15 Oct 2026

**Done**
- Installed `torch` 2.14.1 (CPU) and `transformers` 5.19.0.
- Verified CLAP (`laion/clap-htsat-unfused`): expects 48 kHz, max 10 s input (= our window), outputs 512 numbers per window, length-normalised to 1.
- `ClapEmbedder` in `model.py` (frozen, batches of 8, `no_grad`).
- Real check: "How A Star Is Born" → embeddings shape (35, 512), 3.9 s on CPU.

**Next (Day 7)**
- DEAM on Google Drive; notebook 01 in Colab (windowing, CLAP embeddings, labels).

**Blockers / notes**
- Downloading the first 3 minutes of a long video takes ~90 s (slow partial download). Acceptable for now; cached in MongoDB after the first time.

## Day 7 — 15 Oct 2026

**Done**
- `notebooks/01_prepare_deam_embeddings.ipynb` (Colab, T4 GPU): unzip DEAM from Drive, load dynamic annotations,
  check label scale (convert 1–9 → [-1, 1] only if needed), 10 s / 5 s windows over annotated regions only,
  CLAP embeddings, checkpoint every 200 songs, merged `deam_clap_windows.npz` + metadata JSON + overview figure.
- Windowing logic tested locally on fake annotations (45 s clip → 5 windows; partial labels; long song).

**Next**
- Run notebook 01 in Colab once DEAM is uploaded to `My Drive/C4/DEAM/`.
- Day 8: notebook 02, split by song, baseline + metrics.

**Blockers**
- DEAM must be downloaded and uploaded to Google Drive (manual step).

## Days 8–9 (prepared) — 16 Oct 2026

**Done**
- `notebooks/02_train_emotion_head.ipynb`: split by song (70/15/15, seed 42, leakage check), metrics (RMSE, MAE, Pearson, CCC),
  mean predictor, ridge baseline (closed-form, alpha chosen on validation), BiLSTM and BiLSTM+attention
  (masked MSE, Adam, early stopping), loss curves, comparison table (CSV + PNG), saves `c4_emotion_head.pt` + training log.
- Whole notebook tested locally on synthetic data: all cells run, files saved.

**Notebook 01 result (Colab, 15 Oct)**
- 1802 songs → 11 171 windows, saved to `My Drive/C4/embeddings/deam_clap_windows.npz`.
- Dynamic labels were already in [-1, 1] (valence -0.83..0.72, arousal -0.77..0.90) → no conversion applied.
  (The 1–9 scale only applies to DEAM's static per-song ratings, which are not used.)

**Notebook 02 result (Colab, 16 Oct) — test set, songs never seen in training**

| Model | Val RMSE | Val MAE | Val Pearson | Val CCC | Aro RMSE | Aro MAE | Aro Pearson | Aro CCC | Mean CCC |
|---|---|---|---|---|---|---|---|---|---|
| Mean predictor | 0.291 | 0.241 | 0.000 | 0.000 | 0.302 | 0.250 | – | 0.000 | 0.000 |
| Ridge (baseline) | 0.225 | 0.173 | 0.639 | 0.564 | 0.171 | 0.137 | 0.824 | 0.800 | 0.682 |
| BiLSTM | 0.212 | 0.167 | 0.709 | 0.589 | 0.161 | 0.132 | 0.859 | 0.817 | 0.703 |
| **BiLSTM + attention** | **0.206** | **0.164** | **0.723** | **0.625** | **0.160** | **0.130** | 0.856 | **0.822** | **0.723** |

- BiLSTM + attention is best → shipped as `c4_emotion_head.pt` (no fallback needed).
- Sequence context helps most for valence (+0.061 CCC over ridge); arousal gain from attention is small (+0.005).
- Caveat: single seed (42); multi-seed runs would show whether small differences are significant (future work).
- Fixed: mean-predictor Pearson showed NaN instead of 0 (display only).

## Day 10 — 16 Oct 2026

**Done**
- `backend/emotion_head.py`: same `EmotionHead` class as notebook 02 (needed to load the saved weights).
- `RealEmotionModel` in `model.py`: CLAP embeddings → trained head → valence/arousal per window; `"mock": false`.
- `get_model` gives a clear message if `models/c4_emotion_head.pt` is missing.
- Tested the full API path with a test checkpoint (same file format); 22 tests still pass.

**Next**
- Download the real weights, switch `USE_MOCK_MODEL=false`, check real predictions in the UI, tag `v0.2-real-model`.
- Day 11: mock C3 + gaps JSON, `mock_loader.py`, fusion rules R1–R6 + tests.
