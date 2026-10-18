# Design Decisions — C4 (Audio Emotion Analysis + Prescriptive Recommendations)

Each decision in plain language: **what** I chose, **why**, and what I considered instead.
Progress-presentation build, October 2026.

---

## 1. Describing emotion with valence and arousal

**What:** every 10-second window gets two numbers between -1 and +1:
- **valence**: how negative (-1) or positive (+1) the audio feels
- **arousal**: how calm (-1) or energetic (+1) the audio feels

Together they place the audio on Russell's **circumplex model of affect**, a 2-D map with four areas:
energetic/positive, tense/negative, low/negative (sad, bored) and calm/positive.

**Why:**
- Creators need **degrees** ("this part is calmer than the rest"), not just a label like "happy". Continuous values give that.
- It is the standard representation in music-emotion research, so labelled datasets (DEAM) exist for it.
- Two numbers are easy to plot over time and easy to turn into rules (e.g. "arousal drops here").

**Considered:** discrete emotion classes (happy / sad / angry...). Rejected: music rarely fits one class, and classes can't express "a bit calmer".

---

## 2. Pretrained CLAP embeddings as features

**What:** each window is passed through **CLAP** (`laion/clap-htsat-unfused`), a model pretrained by LAION on a very large set of audio + text pairs. It outputs an **embedding**: 512 numbers that summarise what the audio sounds like. CLAP is **frozen**: I never change its weights.

**Why:**
- Training an audio model from scratch needs far more data and GPU time than a student project has. DEAM has only ~1,800 songs.
- CLAP already "understands" sound (instruments, tempo, loudness, mood) because of its huge training set. My model only has to learn how to go from those 512 numbers to emotion.
- CLAP takes **48 kHz audio, at most 10 s long**, and that is exactly my window size, so nothing is cut off.
- The supervisor confirmed pretrained models are allowed **if I add my own customization** (see `CUSTOMIZATION_TABLE.md`).

**Considered:** VGGish, openSMILE (hand-crafted features). Kept as future work; CLAP was one strong, easy-to-use option for the 50% build.

---

## 3. Windows: 10 s long, a new one every 5 s, first 3 minutes only

**Why 10 s:** CLAP's maximum input length, and long enough to hear a mood.
**Why a 5 s hop (overlapping windows):** a smoother timeline, so changes are not missed if they happen at a window edge.
**Why 3 minutes:** keeps analysis fast (download + model ≈ 1–2 min) for the demo. A full video is future work.
**Same windowing in training and in the backend.** Otherwise the model would be trained on different inputs than it sees later.

---

## 4. Training data: DEAM

**What:** DEAM (Database for Emotional Analysis of Music), 1,802 songs with **dynamic** labels: listeners rated valence and arousal every 0.5 s, starting at 15 s into each clip.

**Decisions:**
- I used the **dynamic** (per-moment) labels, not the per-song ratings, because I predict emotion **per window**.
- Only the **annotated region** of each song is used. Windows without labels can't teach anything.
- A window's label = the **average** of the ratings inside it.
- **I checked the label scale instead of assuming it.** The dynamic labels were already in [-1, 1] (valence -0.83..0.72, arousal -0.77..0.90), so no conversion was applied. (The 1–9 scale applies only to DEAM's per-song ratings.)
- Result: **11,171 windows** from **1,802 songs**. The CLAP embeddings were computed once in Colab and saved to Google Drive.

---

## 5. Splitting the data by song

**What:** 70% of **songs** for training, 15% for validation, 15% for testing (seed 42).

**Why:** windows overlap, and windows of the same song sound alike. If one song had windows in both training and test, the model would be tested on audio it has practically already heard (**data leakage**), giving falsely good scores. So each song belongs to exactly one set. The notebook checks this with an assertion.

---

## 6. The model: BiLSTM + attention (my trained head)

**What:** a small network on top of the frozen CLAP embeddings that reads a whole sequence of windows:
- **BiLSTM** (bidirectional Long Short-Term Memory): one LSTM reads the windows forwards, one backwards. Each window's prediction can use what came **before and after** it, the way the mood of a moment depends on its context.
- **Attention**: each window computes how relevant every other window is and mixes in a weighted summary. This links distant moments directly (e.g. a quiet intro and a loud climax).
- **tanh** output keeps both values in [-1, 1].
- Training: masked mean-squared error, Adam optimiser, dropout 0.3, **early stopping** on validation loss (stop when it stops improving, keep the best version).

**Why sequence context at all?** Emotion in music builds over time. A single window on its own is ambiguous.

---

## 7. Baseline and ablation: proving each part is worth it

An **ablation** removes one part at a time to see what it contributed. All models were scored on the same **test songs** they never saw.

| Model | Valence CCC | Arousal CCC | Mean CCC |
|---|---|---|---|
| Mean predictor (always predicts the average) | 0.000 | 0.000 | 0.000 |
| Ridge regression (one window, linear) | 0.564 | 0.800 | 0.682 |
| BiLSTM (sequence context) | 0.589 | 0.817 | 0.703 |
| **BiLSTM + attention (my model)** | **0.625** | **0.822** | **0.723** |

**Metrics:** RMSE/MAE = average size of the error (lower is better). Pearson r = do predictions rise and fall with the truth. **CCC** (Concordance Correlation Coefficient) = like Pearson but also penalises predictions that are shifted or squashed. It is the standard metric in emotion recognition (1 = perfect, 0 = useless).

**What it shows:**
- Each step helps: context (BiLSTM) beats one window alone, and attention helps again.
- The biggest gain is for **valence** (+0.061 over ridge). Positive/negative feeling depends more on context.
- **Arousal is easier** (CCC 0.82 vs 0.63). Energy is directly audible in loudness and tempo. This matches the literature.
- **Honest caveat:** the arousal gain from attention is small (+0.005), and the results come from one random seed. Multiple seeds would show whether small differences are significant (future work).

---

## 8. Recommendations: transparent rules (fusion)

**What:** six small rules (`backend/fusion.py`) combine three signals:
1. the audio emotion timeline (my model),
2. audience sentiment from C3 (dummy for now),
3. knowledge gaps: concepts mentioned but not explained (dummy for now).

| Rule | Fires when | Suggests |
|---|---|---|
| R1 low energy | a section is clearly calmer than the rest of the video for ≥ 30 s | raise the pace, livelier music, or shorten it |
| R2 tense audio | a section is clearly more energetic AND more negative than the rest for ≥ 20 s | lower the music under narration |
| R3 flat profile | energy barely changes over the whole clip | vary the music energy between sections |
| R4 intense audio over hard content | a knowledge gap overlaps audio more intense than the video's average | calmer audio during explanations; add a recap |
| R5 audio complaints | audience is negative overall AND complaints mention music/loud/slow... | review mixing levels and pacing |
| R6 requested topics | viewers ask for topics the video doesn't cover | consider a follow-up video |

**Why rules and not another ML model?**
- **Explainable:** every recommendation lists the exact evidence that triggered it ("arousal 0.08 below the video's average for 35 s", "viewer comment at 02:20: 'this part drags'"). A creator, or the panel, can check it.
- **No training data exists** for "good advice to video creators", so a learned model isn't possible yet.
- Easy to extend when the real C3 and knowledge-graph outputs arrive.
- An LLM could later **rephrase** the suggestions, but the rules would still decide **what** to recommend.

**Confidence (0–1):** 0.5 when one source of evidence supports a recommendation, **+0.2 for each independent signal that agrees** (e.g. a nearby negative comment, a knowledge gap), never above 0.95. More agreeing evidence means more confidence. Severity rises to **high** when a second signal agrees.

### 8.1 Why the audio rules use RELATIVE thresholds (changed 18 Oct)
The first version used fixed values (e.g. "arousal below -0.3"). On real science videos (speech + music) my model's predictions stay close to neutral (**arousal only ≈ -0.1 to +0.2**), so R1, R2 and R4 **never fired**, and R3 fired on every video.

**Change:** R1, R2 and R4 now compare each window with **that video's own average** (a section counts as low-energy when it is more than 0.04 below the video's average). Reasons:
- It matches how viewers experience pacing: "this part feels slower **than the rest**".
- Each video is judged against itself, so it works regardless of how strongly the model reacts to a type of content.
- Shown by a test: shifting a whole video up or down gives exactly the same recommendations.

The 0.04 delta and the R3 limit (std < 0.03) are **starting values** chosen from the spread of predictions on three test videos (typical within-video standard deviation 0.05–0.065). They are in `config.py` to tune.

---

## 9. Backend, frontend and database

- **FastAPI** (backend): a small, fast Python web framework. It checks request/response shapes automatically (Pydantic) and generates test docs at `/docs`.
- **Streamlit + Plotly** (frontend): a working web UI written in Python, with interactive charts. Good for a research demo; the final merged dashboard is out of scope.
- **MongoDB Atlas** (shared team database `project_j417`, collection `analyses`): one JSON document per video fits the analysis result naturally. A **unique index on `video_id`** means re-analysing replaces the old result. It doubles as a **cache**: reopening a video is instant with no recomputation.
- **Secrets** live in `.env` (never committed). `.env.example` shows the settings without values.

---

## 10. Dummy data for other components

C3 (audience feedback) and the knowledge-gap detection belong to other components that are not finished yet. To build and demo the fusion now:
- `mock_data/` holds **three C3 variants** (negative, mixed, positive), each tied to a demo video, plus dummy gaps and a default for any other video.
- All format knowledge is in **one file** (`backend/mock_loader.py`). When the real outputs exist, only that file changes.
- Every dummy input is marked `"mock": true` in the JSON and labelled **DUMMY DATA** in the UI, so nobody mistakes it for real analysis.

---

## 11. Reliability decisions

- **Only the first 3 minutes are downloaded, and quickly.** Letting ffmpeg stream the first 3 minutes took ~90 s, because YouTube limits streaming speed (to about 2× playback speed). Instead, the backend asks YouTube's server for just the **first few MB of the audio file** in one normal HTTP request (a "Range" request; ~3–4 MB even for a 77-minute video), and ffmpeg converts that piece to 48 kHz mono WAV. A full analysis went from **~105 s to ~9 s**. If the fast method isn't possible (e.g. the file size is unknown), the backend falls back to the slower streaming method automatically.
- **Downloads are checked for completeness and retried (up to 3 attempts).** A dropped internet connection was found to either crash ffmpeg or silently cut the audio short (e.g. 104 s instead of 180 s). Analysing part of a video without saying so would be a hidden error, so the backend retries and otherwise returns a clear message.
- **Temporary audio files are deleted automatically** after each analysis.
- **Clear error messages** for: invalid URL, unavailable/private video, live streams, failed download, database down, backend not running.
- **49 automatic tests** (`pytest`) cover URL parsing, windowing, padding, download retries, every fusion rule and the dummy loader.

---

## 12. Known limitations (honest)

1. **Domain mismatch:** DEAM is **music only**; YouTube science videos mix **speech + music**. Predictions describe the overall audio mood, and they cluster near neutral. Separating music from speech (Demucs) is future work.
2. **Short training sequences:** most DEAM clips give ~5 windows; inference uses 35. The model still produced plausible timelines, but this mismatch was not formally evaluated.
3. **Noisy labels:** valence/arousal ratings are subjective; annotators disagree.
4. **One random seed:** small differences between models may not be significant.
5. **Thresholds tuned on few videos:** relative delta 0.04 and R3 std 0.03 are starting values.
6. **Comment relevance isn't checked:** a negative comment near a section counts as support even if it is about something else (e.g. loudness instead of pace). Topic matching is C3's job (future work).
7. **Dummy C3 and knowledge-gap data:** the fusion logic is real; its inputs are placeholders.
8. **Only the first 3 minutes** of each video are analysed.

---

## 13. Future work (towards the final submission)

- Demucs music/speech separation; extra features (VGGish, openSMILE); CNN front-end; PMEmo dataset.
- Multi-seed training and significance testing.
- Real C3 output and a real knowledge graph (PyKEEN/TransE over Neo4j from C1/C2).
- Full-length videos; optional LLM rephrasing of suggestions (rules still decide).
- Integration into the team's merged dashboard and browser extension.
