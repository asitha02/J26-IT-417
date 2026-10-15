# CLAUDE.md — Component 4 (C4): Audio Emotion Analysis + Prescriptive Recommendations

## 0. How to use this file (Claude Code: read this first)

- Read this whole file at the start of every session. It is the source of truth for scope, architecture, data contracts and working rules.
- In the FIRST session: do not write code yet. Reply with a summary of what you understood (max 10 lines) and the plan for Day 1 only. Wait for my go-ahead.
- If something here is unclear or contradicts what I say in chat, ask me. Do not guess.
- Build in small steps. After each step, tell me the exact command to run and what output I should expect.

---

## 1. Who I am and how to work with me

- I'm a 4th-year BSc IT student at SLIIT. This is my FIRST AI/ML project.
- I know Python, SQL, JavaScript/React, Git/GitHub, Power BI, Azure and Figma. I have NOT trained a deep-learning model before.
- I must be able to explain every line and every design choice in a viva (oral exam) in front of a panel. So:
  - Explain each step in simple words and say WHY, not just what.
  - Prefer simple, readable, well-commented code over clever code.
  - Define ML terms the first time you use them (embedding, valence, arousal, BiLSTM, attention, ablation, etc.).
  - Never add code, libraries or features I haven't been told about.
- When I paste an error, explain what it means in plain language first, then fix it.
- Ask before: installing new packages, deleting files, changing the stack, or changing the data contracts in section 8.

---

## 2. Project background

Group research project (IT4010, SLIIT Faculty of Computing). The overall system analyzes educational YouTube videos and podcasts using AI. Evaluation domain: **science-themed content** (science-fiction breakdowns, "what if" explorations, science-mystery podcasts).

User flow: a browser extension on YouTube opens a companion web app, the viewer adds a video/podcast, and an integrated pipeline analyzes it.

Four components (one per member), merged at the end into a summary dashboard:

| # | Component | Summary |
|---|-----------|---------|
| C1 | Knowledge extraction | Audio → time-stamped transcripts → entities, facts, relationships (traceable to source + timestamp) |
| C2 | Knowledge fusion + multilingual | Fuses knowledge from many videos into one knowledge base (semantic embeddings); summaries/notes in English and Sinhala |
| C3 | Audience feedback mining | Mines comments for sentiment, complaints, requested topics → creator recommendations |
| **C4 (MINE)** | **Background music/audio analysis + prescriptive and descriptive recommendations** | See section 3 |

Research gap C4 addresses: existing tools (YouTube chapters/transcripts, AI summarizer extensions) never analyze the audio itself (music, tone, pacing), even though audio is a known driver of engagement and drop-off, and none turn analytics into prescriptive advice for creators.

---

## 3. My component (C4) — full definition

**Goal:** For a given video/podcast, (a) classify the emotional tone of its audio over time, (b) fuse that with audience sentiment (from C3) and knowledge-gap signals, and (c) produce prescriptive recommendations — not just "what happened" but "what the creator should change".

Example of the intended output: *"The segment at 02:10–02:50 has low-energy background audio, and viewer comments around that time mention it feels slow. Consider raising the pace or shortening this section."*

### Three sub-parts

1. **Audio emotion classification** — predict **valence** (negative ↔ positive) and **arousal** (calm ↔ energetic) per audio segment, using the valence-arousal (Russell circumplex) framework.
2. **Signal fusion** — combine audio emotion + C3 audience sentiment + knowledge-gap detection (against knowledge graphs).
3. **Prescriptive recommendation** — rule-based first (transparent, explainable); optional LLM rephrasing only if time allows.

### Full vision vs. what I'm building now

| Part | Full vision (final submission) | Now (progress presentation, ~50%) |
|------|-------------------------------|-----------------------------------|
| Audio prep | yt-dlp download, Demucs music/speech separation | yt-dlp download, first 3 minutes only, no Demucs |
| Features | CLAP / VGGish / openSMILE | **CLAP embeddings** only (pretrained) |
| Emotion model | CNN-BiLSTM with attention trained on DEAM + PMEmo | **BiLSTM + attention head** on CLAP embeddings, trained on **DEAM** (PMEmo optional stretch) |
| Knowledge gaps | PyKEEN / TransE over real knowledge graph (Neo4j from C1/C2) | **Dummy JSON** |
| Audience sentiment | Real output from C3 | **Dummy JSON** |
| Recommendation | Fusion + LLM (LangChain) | **Rule-based fusion** (LLM optional) |
| Dashboard merge | Final merged dashboard with all components | Out of scope; just expose clean JSON output |
| UI | Part of the full web app | **Working Streamlit UI + FastAPI backend + MongoDB** |

Supervisor and lecturer confirmed: pretrained models are allowed **as long as I add my own customization** (my trained head, my fusion logic, my recommendation rules). Dependencies on other components use dummy data.

---

## 4. Scope for the progress presentation (deadline: ~20 Oct 2026)

Supervisor requirement: show ~50% of C4 as a **working UI (frontend + backend)**.

### In scope
- The extention we build sends the youtube video→ backend downloads audio (first 3 min) → segments → CLAP embeddings → emotion prediction → fusion with dummy C3 + dummy gaps → recommendations → saved in MongoDB → shown in UI.
- Trained BiLSTM + attention head (with a simple baseline for comparison).
- Re-opening a past analysis from MongoDB without recomputing.
- Clean JSON output that the final dashboard could later consume.

### Out of scope (do NOT build unless I ask)
- Demucs, VGGish, openSMILE, PMEmo training, CNN front-end
- PyKEEN / TransE / Neo4j
- Real integration with C1, C2, C3
- The merged summary dashboard
- Browser extension, authentication, user accounts, deployment/hosting
- Sinhala/multilingual features

### Definition of done (by 20 Oct)
- [ ] `uvicorn` backend and `streamlit` frontend run locally from README instructions
- [ ] Analyzing a real YouTube URL returns a real emotion timeline from my trained model
- [ ] Recommendations are generated from fusion rules using dummy C3 + gap data
- [ ] Results persist in MongoDB and can be reloaded
- [ ] Training notebook with logged curves, baseline vs BiLSTM+attention comparison
- [ ] README, PROGRESS.md, design-decisions doc, and a clean git history with milestone tags

---

## 5. Architecture and data flow

```
[Streamlit UI] --POST /analyze (youtube_url)--> [FastAPI backend]
                                                     |
   1. validate URL, check MongoDB cache (video_id)   |
   2. audio_utils: yt-dlp -> wav -> trim 3 min -> segment (10 s windows, 5 s hop)
   3. model.py: CLAP embeddings -> BiLSTM+attention head -> valence/arousal per segment
   4. load dummy C3 sentiment + dummy knowledge gaps (mock_data/*.json)
   5. fusion.py: apply rules -> recommendations
   6. db.py: save analysis document to MongoDB (collection: analyses)
   7. return JSON
                                                     |
[Streamlit UI] <------------ JSON ------------------+
```

Training happens separately in **Google Colab** (notebooks/). The backend only loads the saved weights file. Weights are NOT committed to git (kept on Google Drive; the README says where to download them).

---

## 6. Tech stack (do not change without asking)

- Python 3.10+, developed in VS Code, virtual environment in `venv/`
- Backend: FastAPI + Uvicorn
- Frontend: Streamlit (charts with Plotly)
- Database: MongoDB Atlas (free M0 cluster) via `pymongo`; secrets in `.env` via `python-dotenv`
- Audio: `yt-dlp` + `ffmpeg`, `librosa`, `soundfile`, `numpy`
- ML: `torch`, `transformers` (Hugging Face). Pretrained audio embedding model: CLAP (`laion/clap-htsat-unfused`, expects 48 kHz audio, produces a 512-dim embedding; verify when implementing)
- Training: Google Colab (free T4 GPU), data/checkpoints on Google Drive
- Dataset: DEAM (Database for Emotional Analysis of Music) — valence/arousal annotations. Check its documentation for annotation scale (1–9) and which time ranges of each clip are annotated; use only annotated regions.
- Tests: `pytest` (light: segmentation, fusion rules, API contract)

---

## 7. Folder structure

```
c4-audio-emotion/
├── CLAUDE.md
├── README.md                  (setup, run, architecture, where to get model weights)
├── PROGRESS.md                (one entry per day: done / next / blockers)
├── requirements.txt
├── .env                       (NOT committed)
├── .env.example               (committed, no real values)
├── .gitignore
├── backend/
│   ├── main.py                (FastAPI app, routes)
│   ├── config.py              (env vars, constants: SEGMENT_SECONDS=10, HOP_SECONDS=5, MAX_AUDIO_SECONDS=180)
│   ├── schemas.py             (Pydantic models for the contracts in section 8)
│   ├── audio_utils.py         (download, trim, segment)
│   ├── model.py               (MockEmotionModel + RealEmotionModel, same interface)
│   ├── fusion.py              (rules -> recommendations)
│   ├── mock_loader.py         (loads dummy C3 + gaps; isolates the format so swapping in real data is easy)
│   └── db.py                  (MongoDB connection + save/get helpers)
├── frontend/
│   └── app.py
├── mock_data/
│   ├── component3_sentiment.json
│   └── knowledge_gaps.json
├── notebooks/
│   ├── 01_prepare_deam_embeddings.ipynb
│   └── 02_train_emotion_head.ipynb
├── docs/
│   ├── DESIGN_DECISIONS.md    (why each choice was made, in viva-friendly language)
│   └── CUSTOMIZATION_TABLE.md (Pretrained component -> what I changed/added -> why)
├── tests/
└── scripts/                   (db connection test, etc.)
```

---

## 8. Data contracts (JSON)

These are the interfaces with other components and the dashboard. Do not change field names without asking me. Keep all parsing of external formats inside `mock_loader.py` so the real C3 output can replace the mock later.

### 8.1 `POST /analyze`

Request:
```json
{ "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXXXXX", "force_reanalyze": false }
```

Response:
```json
{
  "video_id": "XXXXXXXXXXX",
  "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "title": "string",
  "analyzed_seconds": 180,
  "segment_seconds": 10,
  "hop_seconds": 5,
  "model_info": { "embedding_model": "clap-htsat-unfused", "head": "bilstm_attention_v1", "mock": false },
  "segments": [
    { "start_s": 0, "end_s": 10, "valence": 0.21, "arousal": -0.35, "quadrant": "calm_positive" }
  ],
  "overall": { "mean_valence": 0.1, "mean_arousal": -0.2, "dominant_quadrant": "calm_positive" },
  "c3_input": { },
  "gaps_input": { },
  "recommendations": [
    {
      "id": "rec_001",
      "rule_id": "R1_low_energy",
      "type": "low_energy_segment",
      "severity": "high",
      "start_s": 130,
      "end_s": 170,
      "title": "Low-energy audio during 02:10–02:50",
      "evidence": ["Arousal below -0.3 for 40 s", "Comment at 02:20: 'this part drags'"],
      "suggestion": "Raise the pace or add more dynamic background music, or shorten this section.",
      "confidence": 0.8
    }
  ],
  "status": "complete",
  "created_at": "ISO-8601 timestamp"
}
```

- `valence` and `arousal` are floats in **[-1, 1]**. If DEAM labels are on a 1–9 scale, convert with `(x - 5) / 4`.
- `quadrant` from the signs of valence/arousal: `(+,+) energetic_positive`, `(-,+) tense_negative`, `(-,-) low_negative` (sad/bored), `(+,-) calm_positive`.

### 8.2 Other endpoints
- `GET /health` → `{ "status": "ok" }`
- `GET /analyses` → list of past analyses (video_id, title, created_at)
- `GET /analyses/{video_id}` → the full stored document (same shape as 8.1 response)

### 8.3 Dummy C3 input — `mock_data/component3_sentiment.json`
Confirm the real format with the C3 teammate later; for now:
```json
{
  "video_id": "XXXXXXXXXXX",
  "sentiment_score": -0.35,
  "sentiment_label": "mixed_negative",
  "comment_count": 240,
  "top_complaints": ["music too loud", "slow pacing in the middle", "hard to follow explanation"],
  "requested_topics": ["black hole information paradox", "Hawking radiation"],
  "timestamped_feedback": [
    { "t_s": 140, "text": "this part drags a bit", "sentiment": -0.6 },
    { "t_s": 20,  "text": "great intro!",          "sentiment":  0.8 }
  ]
}
```
Create 3 variants (negative, mixed, positive) so the UI and rules can be demoed in different situations. If the `video_id` doesn't match any mock, fall back to a default mock.

### 8.4 Dummy knowledge gaps — `mock_data/knowledge_gaps.json`
```json
{
  "video_id": "XXXXXXXXXXX",
  "gaps": [
    { "topic": "Hawking radiation", "start_s": 120, "end_s": 165, "severity": "medium",
      "description": "Concept mentioned but not explained; related videos cover it in depth." }
  ]
}
```

### 8.5 MongoDB
- Database `research_project`, collection `analyses`. One document per analysis, same shape as the 8.1 response plus Mongo's `_id`.
- Unique index on `video_id` (re-analysis replaces the document). Serialize `_id` out of API responses.

---

## 9. Emotion model specification

### 9.1 Inference pipeline (backend)
1. Download audio with yt-dlp (audio only), convert to WAV with ffmpeg, resample to the rate CLAP expects (48 kHz, mono).
2. Trim to the first `MAX_AUDIO_SECONDS` (180).
3. Split into windows of `SEGMENT_SECONDS` (10) with hop `HOP_SECONDS` (5). Pad the final short window. Handle audio shorter than one window.
4. CLAP → one 512-dim embedding per window (frozen, no gradient).
5. Embedding sequence (T × 512) → BiLSTM → attention → two outputs (valence, arousal) per window, tanh or clipped to [-1, 1].
6. Delete temporary audio files after processing.

### 9.2 My customization (what makes this original work)
- A trained sequence head (BiLSTM + attention) on top of frozen pretrained CLAP embeddings, predicting continuous valence/arousal.
- A **baseline** for comparison: ridge regression or a small MLP on the same embeddings (per window, no sequence context).
- An **ablation**: BiLSTM without attention vs. BiLSTM with attention vs. baseline.
- My own fusion rules and recommendation logic (section 10).
- Record all of this in `docs/CUSTOMIZATION_TABLE.md`.

### 9.3 Training (Google Colab notebooks, not the backend)
- Notebook 01: load DEAM, windowing consistent with inference (10 s / 5 s hop), compute CLAP embeddings, average the dynamic annotations inside each window as the label, save embeddings + labels to Google Drive (so they are never recomputed).
- Notebook 02: train/validation/test split **by song** (never split windows of one song across sets — that leaks data), train baseline, then BiLSTM, then BiLSTM+attention.
- Metrics: RMSE, MAE, Pearson correlation and Concordance Correlation Coefficient (CCC) for valence and arousal, per model, in one comparison table.
- Save loss curves and the comparison table as images/CSV for my slides. Save weights as `c4_emotion_head.pt` to Drive.
- Fix random seeds and log hyperparameters so results are reproducible.

### 9.4 Code interface (so the mock and real models are interchangeable)
```python
class EmotionModel:
    def predict(self, segments_audio) -> list[dict]:
        """Return [{'start_s', 'end_s', 'valence', 'arousal'}, ...]"""
```
- `MockEmotionModel`: smooth random-walk values (seeded by video_id so results are stable). Used on Days 3–4 to prove the pipeline end to end.
- `RealEmotionModel`: CLAP + trained head, loaded from `MODEL_PATH`.
- Selected by env var `USE_MOCK_MODEL=true|false`.

### 9.5 Known limitations (document honestly in README and slides)
- DEAM is **music** with annotated emotion; YouTube science videos mix **speech + music**. Predictions describe the overall audio mood, not just the music. Demucs-based separation is future work.
- Training sequences are short (annotated regions of ~30–45 s clips) while inference sequences are longer; if quality drops on long inputs, run inference in chunks of at most ~9 windows.
- Valence/arousal labels are subjective and noisy (inter-annotator disagreement).

---

## 10. Fusion and recommendation specification

Implemented in `backend/fusion.py` as small, separate, unit-tested rule functions. Thresholds live in `config.py` and are **initial values to tune**, not truth. Each rule returns zero or more recommendations in the schema of section 8.1.

| Rule ID | Trigger | Evidence added | Suggestion |
|---------|---------|----------------|------------|
| R1_low_energy | Arousal < -0.3 for ≥ 30 s consecutive. Severity medium; **high** if a negative C3 comment (sentiment < -0.3) falls within ±15 s | Duration, mean arousal, matching comment text + timestamp | Raise pace / add more dynamic music / shorten the section |
| R2_tense_audio | Arousal > 0.6 and valence < -0.3 for ≥ 20 s. **High** if C3 complaints mention loud/music/audio | Duration, values, complaint | Lower background music under narration; keep narration clearly audible |
| R3_flat_profile | Variance of arousal across the whole clip below threshold | Variance value | Vary music energy across sections to hold attention |
| R4_complex_content_audio | A knowledge gap overlaps a segment with arousal > 0.4 (intense audio over hard content) | Gap topic, time range, arousal | Use calmer audio during complex explanations; add a recap or visual |
| R5_audio_complaints | C3 sentiment < -0.3 AND complaints contain audio keywords (music, loud, volume, audio, boring, slow) | The matched complaints | Review mixing levels and pacing overall |
| R6_requested_topics | C3 requested topics not covered by any detected gap/segment topic | Topic list | Consider a follow-up video or section on these topics (low priority) |

- `confidence` (0–1): start at 0.5 for audio-only evidence; add for each corroborating independent signal (C3 comment nearby, knowledge gap overlap); cap at 0.95.
- Merge overlapping recommendations of the same type; sort by severity, then confidence.
- Every recommendation must include human-readable evidence (explainable, not a black box).
- Optional later (only after everything else works): LLM rephrasing of suggestions through LangChain; the rules still decide WHAT to recommend, the LLM only improves wording.

---

## 11. UI specification (Streamlit, `frontend/app.py`)

- Sidebar: backend URL setting, list of past analyses (from `GET /analyses`) to reopen.
- Main: YouTube URL input + "Analyze" button, spinner while processing, clear error messages (invalid URL, download failed, video too long/unavailable, backend not running).
- Results:
  1. Title, video id, analyzed duration, badge showing whether the mock model was used
  2. Emotion timeline: Plotly line chart of valence and arousal over time (x-axis in mm:ss), with recommendation time-ranges highlighted
  3. Valence-arousal scatter/quadrant plot with the dominant quadrant labeled
  4. Dummy C3 input summary (sentiment, complaints) and dummy knowledge gaps, clearly labeled "dummy data"
  5. Recommendation cards sorted by severity: title, time range, evidence bullets, suggestion, confidence
  6. "Download JSON" button for the full result
- Keep it simple and readable. A working plain UI beats a broken fancy one.

---

## 12. Build order (2 weeks, starting 7 Oct 2026)

Each day ends with working code, a git commit + push, and a PROGRESS.md entry.

| Day | Date | Goal | Done when |
|-----|------|------|-----------|
| 1 | Wed 7 Oct | Repo, structure, .gitignore, .env.example, README skeleton | Repo pushed to GitHub |
| 2 | Thu 8 Oct | venv, requirements, MongoDB Atlas, `db.py`, DB test script, yt-dlp test | Insert + read back a document |
| 3 | Fri 9 Oct | FastAPI `/analyze` with `MockEmotionModel`, saves to Mongo | curl/Swagger returns fake timeline |
| 4 | Sat 10 Oct | Streamlit UI connected to backend. **Tag v0.1-vertical-slice** | URL → chart + recommendation in UI |
| 5 | Sun 11 Oct | `audio_utils.py`: download, trim, segment (+ tests) | Segments produced for a real video |
| 6 | Mon 12 Oct | CLAP embeddings for segments | Embedding array shape verified |
| 7 | Tue 13 Oct | DEAM downloaded; notebook 01 (windowing, embeddings, labels) | Embeddings + labels saved to Drive |
| 8 | Wed 14 Oct | Notebook 02: split by song, baseline model + metrics | Baseline metrics recorded |
| 9 | Thu 15 Oct | BiLSTM, then BiLSTM+attention, curves, comparison table | Models trained and compared |
| 10 | Fri 16 Oct | `RealEmotionModel` in backend. **Tag v0.2-real-model** | UI shows real predictions |
| 11 | Sat 17 Oct | Mock C3 + gaps JSON, `mock_loader.py`, fusion rules R1–R6 + tests | Rules produce recommendations |
| 12 | Sun 18 Oct | Recommendations in UI, persistence/reload, error handling | Full flow works for 3 videos |
| 13 | Mon 19 Oct | Polish, test 3–5 videos, screenshots. **Tag v0.3** | No crashes on test set |
| 14 | Tue 20 Oct | Buffer, README, DESIGN_DECISIONS, CUSTOMIZATION_TABLE. **Tag v1.0-progress** | Fresh clone runs from README |

**Fallback:** if the BiLSTM is not working by Day 10, ship the baseline model as the working model, keep BiLSTM+attention as documented future work, and be honest about it. A working pipeline matters more than the fanciest model.

---

## 13. Git rules (constant commits)

- Commit small and often (2–5 times a day), each time one thing works. Push at the end of every day.
- Message format: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `wip:` + short description, e.g. `feat: add analyze endpoint with mock timeline`.
- Before every commit: run `git status`, show me what is included, propose the message, and **ask me before running `git commit` or `git push`**.
- Never commit: `.env`, `venv/`, audio files (`*.wav`, `*.mp3`), datasets, model weights (`*.pt`, `*.pth`), notebook outputs with large data.
- If a secret is ever committed, tell me immediately so I rotate it (deleting the file does not remove it from history).
- `main` always holds working code. Use `feature/<name>` branches for larger pieces and merge when they work.
- Milestone tags: `v0.1-vertical-slice`, `v0.2-real-model`, `v0.3-fusion-ui`, `v1.0-progress`.
- Clear notebook outputs before committing, except the graphs I want to keep.

---

## 14. Quality, security and don'ts

- Never hardcode secrets; use `.env` + `python-dotenv`. Never print the Mongo URI.
- Validate the YouTube URL (accept watch/short/youtu.be forms) before downloading; handle failures gracefully with useful messages.
- Limit analysis length (`MAX_AUDIO_SECONDS`); clean up temp files; cache by `video_id` in MongoDB.
- For demos/tests prefer short, openly licensed or my own videos.
- Do not silently swallow exceptions; log them and return clear errors.
- Do not add features outside section 4 "In scope". Do not refactor working code without telling me.
- Keep dependencies minimal; every new package must be justified and added to `requirements.txt`.
- Mark every dummy-data output as dummy in the UI and in the JSON (`"mock": true` where relevant) so nobody mistakes it for real analysis.

---

## 15. Documents I need to keep updated (for the panel)

- `PROGRESS.md` — daily: what was done, what's next, blockers.
- `docs/DESIGN_DECISIONS.md` — each decision in plain language (why CLAP, why valence-arousal, why BiLSTM + attention, why rule-based fusion, why MongoDB, why dummy data), plus honest limitations.
- `docs/CUSTOMIZATION_TABLE.md` — Pretrained component → what I changed/added → why.
- `README.md` — setup, run, architecture diagram, model weights download link, screenshots.
- Save training curves, the model comparison table and UI screenshots as I go (needed for the progress slides).
