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

- Real weights downloaded, `USE_MOCK_MODEL=false`: UI shows real predictions (e.g. "How A Star Is Born":
  dominant mood tense/negative, mean valence -0.26, mean arousal +0.09). Screenshots taken.
- Fixed: ffmpeg could be interrupted by keyboard input in the server terminal → added `-nostdin`.
- UI: valence and arousal lines now use clearly different colours.

**Next**
- Tag `v0.2-real-model`.

## Day 11 — 16 Oct 2026

**Done**
- `mock_data/component3_sentiment.json`: 3 dummy C3 variants (negative → "How A Star Is Born", mixed → "The Life of Stars",
  positive → "Me at the zoo") + default for any other video. `mock_data/knowledge_gaps.json`: dummy gaps per video + default.
- `backend/mock_loader.py`: the only place that knows the dummy file formats; every input is marked `"mock": true`.
- `backend/fusion.py`: rules R1–R6, confidence scoring (0.5 + 0.2 per agreeing signal, max 0.95), merging of overlapping
  recommendations of the same type, sorting by severity then confidence. All thresholds in `config.py`.
- `/analyze` stores `c3_input` and `gaps_input` and runs all rules.
- UI: full dummy-data section (clearly labelled), "whole video" ranges, rule id on each card, only section-specific
  recommendations are shaded on the timeline.
- Reliability: downloads are checked for completeness and retried up to 3 times (a dropped connection could crash ffmpeg
  or silently cut the audio short, e.g. 104 s instead of 180 s). Correction: the earlier "-nostdin" change was not the fix.
- 44 automatic tests pass (17 new for fusion + loader, 4 for download retries).
- Real run, 3 videos, real model: all complete; R5, R3, R6 fire as expected per dummy variant.

**Finding (to discuss / tune)**
- On these speech-heavy science videos the model's predictions stay close to neutral (arousal ≈ -0.06..+0.22),
  so the absolute thresholds of R1 (-0.3), R2 (+0.6) and R4 (+0.4) never trigger, while R3 (flat profile) triggers on every video.

## Day 12 — 18 Oct 2026

**Done**
- Rules R1, R2, R4 switched to **relative thresholds** (compare with the video's own average, delta 0.04);
  R3 uses arousal std < 0.03 with ≥ 6 windows. Recorded in CLAUDE.md section 10.
- 47 tests pass (new: small dip in a near-neutral video triggers R1; shifting a whole video gives the same result; R3 minimum length).
- Re-ran the rules on the saved real predictions: "The Life of Stars" and "How A Star Is Born" now each get 5 recommendations,
  including R4 (intense audio during a knowledge gap + matching viewer comment, confidence 0.9) and R1 (calmer sections).

**Known limitation**
- R1/R4 count any negative comment near a section as support, without checking what the comment is about
  (e.g. a loudness complaint can raise a low-energy recommendation). Topic matching belongs to C3 (future work).

- Drafted `docs/DESIGN_DECISIONS.md` and `docs/CUSTOMIZATION_TABLE.md`; README limitations, results and tests sections.
- **Speed fix:** an analysis took ~2 min, measured as 96 s download + 3.7 s model. New fast download requests only the first
  ~3–4 MB of the audio file (HTTP Range) and converts it with ffmpeg; the old streaming download stays as automatic fallback.
  Full analysis now **~9 s** (cached reopen 0.1 s). 49 tests pass.

## Day 13 — 18 Oct 2026

**Done**
- Tested 5 new science videos (never seen before) with the real model:
  4 analysed in 15–19 s each (incl. a 4-hour video), 1 blocked by YouTube → clear "not available" message, no crash.
- Model separates content styles sensibly: lively animated explainer arousal +0.28 … calm narration compilation −0.13.
- Error cases checked: non-YouTube link (400), random text (400), fake video id (422), missing field (422),
  unknown saved id (404); playlist-style and shorts links work; reopening a saved analysis 0.09 s.
- Finding: valence negative on all videos (−0.19 … −0.29) → added to limitations.

## Day 14 — 18 Oct 2026

**Done**
- Fresh-clone test: cloned `component4` from GitHub into an empty folder, followed only the README:
  install OK (`pip check` clean), DB check passed, yt-dlp check passed, 49 tests pass, backend analysed a video
  with the real model in 14 s, Streamlit page loads. Clone contained no `.env` and no weights (as intended).
- DESIGN_DECISIONS, CUSTOMIZATION_TABLE and README complete.

**Remaining (manual)**
- Add the Google Drive share link for `c4_emotion_head.pt` in the README.
- Final screenshots for slides; tags `v0.1`, `v0.2`, `v0.3`, `v1.0`.
- Day 11: mock C3 + gaps JSON, `mock_loader.py`, fusion rules R1–R6 + tests.

## Day 15 — 20 Oct 2026 (two-part component, branch `feature/two-part-ui`)

**Block 1: music/speech separation**
- Installed `demucs` 4.1.0 (dry run first: keeps torch 2.14.1, adds 5 small packages). `backend/separation.py`:
  speech = vocals, background = drums + bass + other; 48 kHz mono in and out. Switch `USE_SOURCE_SEPARATION`.
- Real check: 180 s separated in ~122 s on CPU (NFR ≤ 2× runtime met); "Black Holes Explained": music 11 dB under the voice overall.

**Block 2: measured audio problems + music-only emotion**
- `backend/audio_problems.py`: per window speech/music loudness (dB), music-minus-speech, clipping %, silence;
  problems "music too loud under narration" (≥ 15 s, music < 10 dB below voice; high if within 3 dB), clipping, dead air (≥ 10 s).
- 58 tests pass (6 new with synthetic tones of known loudness).
- Real results: "Black Holes Explained" → music 3 dB LOUDER than the voice in 00:00–00:20 (high); rest well mixed
  (median −15 dB). Calm narration video: no problems.
- **Finding (mixed vs. music-only emotion):** arousal drops strongly after separation (+0.28 → −0.02; −0.13 → −0.28):
  the narrator's voice was inflating the predicted energy. Valence stays negative (−0.22 → −0.24), so the
  negative-valence bias is not caused by speech. Loudness normalisation of the music track changed almost nothing
  (arousal −0.02 → −0.01), so CLAP is largely level-invariant and no normalisation step is used.

**Block 3: Part 1 endpoint + page**
- CLAP zero-shot music description (`ClapEmbedder.describe`): music embeddings compared with 9 text labels
  ("tense dramatic cinematic music", "calm ambient music", ...), softmax with CLAP's own temperature.
- `backend/audio_analysis.py` (Part 1 pipeline, testable without internet), `POST /audio/analyze`,
  `GET /audio/analyses[/{id}]`; collection `audio_analyses`. `db.py` now takes a collection name. Old `/analyze` removed.
- Frontend split into two pages (`st.navigation`): `audio_analysis.py` (Part 1) and `recommendations.py` (Part 2, next).
  Page 1: music description, music emotion timeline with unseparated audio as dotted lines, valence–arousal map,
  voice vs. music loudness chart, problem cards with "watch at" links, link to Part 2, JSON download.
- 60 tests pass. Real run "Black Holes Explained": 98 s; music sounds like "tense dramatic cinematic" (29 %);
  problem: music too loud under the narration 00:00–00:20 (high).

**Block 4: Part 2 rules with C1/C2/C3 inputs**
- Dummy C1 transcript sections (`mock_data/component1_transcript.json`: topic + content type hook/explanation/example/summary)
  and `load_c1_transcript`; knowledge gaps now attributed to C2; demo video "Black Holes Explained" got its own dummy C2/C3 data.
- New rules: R7 mood–content mismatch (lively music during an explanation / calm music in the hook, relative to the
  video's average), R8 measured "music too loud" + loudness complaints/comments, R9 distortion and dead air.
  R5 now cross-checks complaints with the measured loudness problem; R6 also counts C1 section topics as covered.
- Evidence in plain language ("energy" = arousal, "mood" = valence, numbers in brackets); every recommendation has a
  `link` that opens the video at its start time.
- 68 tests pass.
