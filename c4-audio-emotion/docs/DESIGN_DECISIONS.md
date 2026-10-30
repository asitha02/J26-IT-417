# Design Decisions — C4 (Audio Emotion Analysis + Prescriptive Recommendations)

Each decision in plain language: **what** I chose, **why**, and what I considered instead.
Progress-presentation build, October 2026 (two-part version, 21 Oct).

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

## 9. Two parts, two pages (changed 19 Oct)

The proposal describes two different jobs, so the component is split into two parts with their own endpoint and page:

| | Part 1: Affective Audio Analysis | Part 2: Content Enhancement Recommendations |
|---|---|---|
| Type of output | **descriptive**: what the background audio sounds like, where the audio problems are | **descriptive + prescriptive**: what happened in each section and what to change |
| Input | a YouTube link | Part 1 result + C1, C2, C3 outputs (dummy JSON for now) |
| Endpoint / page | `POST /audio/analyze` / "1 · Audio Analysis" | `POST /recommendations/{video_id}` / "2 · Recommendations" |
| Speed | first look ~14 s, full result ~2 min later (see 17) | < 1 s (no audio work) |

Why: Part 2 is exactly where the other components' outputs come in. Keeping it separate means that in the final
integration only the inputs change (dummy JSON → real outputs), and the audio analysis never has to be repeated.

---

## 10. Separating the narration from the background music (Demucs)

**What:** Demucs (`htdemucs`, Meta, pretrained, used frozen) splits the audio into drums, bass, other and vocals.
Speech = vocals; background = drums + bass + other. The emotion model then runs on the **background** track.

**Why:**
- The research question is about the **background** audio, not the voice.
- My model was trained on DEAM, which is **music**, so the music-only track is closer to its training data. No retraining needed.
- The separate tracks make it possible to **measure** whether the music is too loud under the voice.

**Finding (mixed vs. music-only emotion):** separation lowers the predicted energy strongly (e.g. +0.28 → −0.02):
the narrator's voice was inflating the arousal. Valence stays negative (−0.22 → −0.24), so the negative-valence bias
is **not** caused by speech. A loudness-normalisation test changed almost nothing (arousal −0.02 → −0.01), so the
difference is not a volume effect. Page 1 shows both versions (dotted lines = unseparated) so this is visible.

**Cost:** ~1.5–2 min per 3-minute clip on CPU, still inside the "≤ 2× runtime" requirement.
`USE_SOURCE_SEPARATION=false` switches it off (faster, analyses the mixed audio).

---

## 11. Measured audio problems (no AI on purpose)

For each 10 s window: loudness of the voice and of the background (RMS in dB), how much quieter the background is,
clipping (samples at maximum level) and silence. Problems: **background too loud under the narration** (less than
10 dB below the voice for ≥ 15 s; high if within 3 dB), **distortion** and **dead air** (≥ 10 s).

**Why plain measurements:** they are checkable by anyone and need no training data. They answer the functional
requirement "identify excessive loudness, distortion, or sound effects dominating speech" and the survey
(Q13: "distracting" 49 %, "too loud" 25.5 %, "poor quality" 37.3 %).
Note: Demucs puts everything that isn't voice into the background, so this also catches loud noise or sound effects
(e.g. "Me at the zoo" has no music, only outdoor noise). That is why the wording is "background sound (music or noise)".

---

## 12. Describing the music in words with CLAP (zero-shot)

CLAP was trained on audio **and text**, so it can also embed a description like "tense dramatic cinematic music".
Comparing the music's embedding with 9 such descriptions (cosine similarity → percentages with CLAP's own learned
temperature) gives "the background music sounds like: tense dramatic cinematic (29 %)".
Why: it reuses the model already loaded (no new dependency, no training) and supports the survey request
"recommend more suitable audio" (Q15, 64.7 %). Limitation: the labels are not validated against human judgements.

---

## 13. More rules, merged cards, plain language and links (Part 2)

| Rule | Uses | Fires when |
|---|---|---|
| R7 mood–content mismatch | Part 1 + C1 sections | music livelier than the video's average during an **explanation**, or calmer than average in the **hook** (survey: "mood doesn't match content", 31.4 %) |
| R8 background too loud | Part 1 measurement + C3 | measured problem; a loudness complaint or a negative comment at that moment raises severity/confidence |
| R9 audio quality | Part 1 measurement | distortion or dead air |
| R5 (extended) | C3 + Part 1 | audio complaints are now cross-checked with the **measured** loudness problem |

- **Merging:** R4 (intense music during a knowledge gap) and R7 (music too lively for an explanation) give the same advice,
  so they share a type and overlapping ones become **one card** with all the evidence (transcript, gap, comment, energy, CLAP label).
- **Plain language** (NFR usability): "energy" instead of arousal, "mood" instead of valence; numbers in brackets.
- **Links** (FR "link recommendations to the source video with the timestamp"): every card opens YouTube at its start time.
- **Descriptive section summaries:** for every C1 section: music mood + CLAP description, voice-vs-music loudness,
  negative comments, knowledge gaps and measured problems.

---

## 14. Validation against audience comments (the research gap's core claim)

The proposal asks whether flagged segments **match what real viewers react to**. Part 2 computes:
- **agreement**: share of flagged sections with a negative comment within ±15 s;
- **random baseline**: the same share for sections of the same length placed at every possible position (exact, not sampled), i.e. pure chance;
- **lift** = agreement ÷ baseline (above 1 = better than chance), plus how many negative comments a flagged section explains.

Why the baseline matters: with few comments and a ±15 s window, even random sections hit comments often.
Example: "How A Star Is Born" scored 100 % agreement, but chance was 97 % → lift 1.03 = **no evidence**.
"Black Holes Explained": 100 % vs. 54 % → lift 1.9.
**Honest note:** these use DUMMY comments written by me, so they only demonstrate the method. With Component 3's real
comments this becomes the actual evaluation (the "segment-level agreement" metric of the proposal).

---

## 15. Backend, frontend and database

- **FastAPI** (backend): a small, fast Python web framework. It checks request/response shapes automatically (Pydantic) and generates test docs at `/docs`.
- **Streamlit + Plotly** (frontend): two pages (`st.navigation`), written in Python, with interactive charts.
- **MongoDB Atlas** (shared team database `project_j417`): collections `audio_analyses` (Part 1) and `recommendation_reports` (Part 2). A **unique index on `video_id`** means re-analysing replaces the old result. It doubles as a **cache**: reopening a video is instant.
- **Secrets** live in `.env` (never committed). `.env.example` shows the settings without values.

---

## 16. Look and feel (21 Oct)

- A "music studio" theme in `.streamlit/config.toml` with separate **light** (soft lavender) and **dark** (night violet) colours, plus CSS in `frontend/style.py`: animated gradient headers, glowing cards with a coloured edge per severity, gradient buttons.
- Streamlit's running icons (swimmer, cyclist, runner) are replaced by animated music symbols (♪ ♫ ♬ 𝄞 🎧); waiting uses an equaliser animation.
- Page 2 starts with what a creator needs: a plain-language summary, four donut charts (what needs attention, how urgent, music mood, what viewers felt), a highlighted **top priority** card and a checklist; the technical details (sections, validation, dummy inputs) are folded away underneath.

---

## 16b. Dummy data for other components

C1 (transcript sections), C2 (knowledge gaps) and C3 (audience feedback) belong to other components that are not finished yet:
- `mock_data/` holds dummy outputs for each demo video plus a `default` for any other video.
- All format knowledge is in **one file** (`backend/mock_loader.py`). When the real outputs exist, only that file changes.
- Every dummy input is marked `"mock": true` and labelled **DUMMY DATA** in the UI.

---

## 17. Reliability decisions

- **Fast download:** only the first few MB of the audio file are requested (HTTP "Range" request) instead of streaming with ffmpeg (~90 s, because YouTube limits streaming speed). Download went from ~96 s to ~3 s; the old method is the automatic fallback.
- **Two-phase answer (changed 21 Oct):** Demucs needs ~0.9 s per second of audio on this CPU (all 8 cores already used; more threads or less overlap did not help). So Part 1 answers with a **first look in ~14 s** (model on the mixed audio, CLAP description, distortion/silence checks) and runs the separation **in the background**, reporting progress after every 30 s chunk. The page shows a progress bar and refreshes itself when the full result is ready (~2 min). Part 2 waits for the full result (409 "still separating").
- **Measured before optimising:** profiling showed the model ran twice on the same audio and PyTorch's first run is ~3× slower, so the mixed-audio result is reused, CLAP is warmed up at start-up, the fastest batch size (4) is used and one YouTube info request is shared by two steps. First look: 31 s → 14 s.
- **Completeness check + up to 3 attempts:** a dropped connection was found to crash ffmpeg or silently cut the audio short (104 s instead of 180 s).
- **Temporary audio files are deleted automatically** (NFR security/ethics); separated tracks are never stored.
- **Clear error messages:** invalid URL, unavailable/private video, live streams, failed download, database down, backend not running, Part 2 before Part 1.
- **77 automatic tests** (`pytest`): URL parsing, windowing, download retries, separation helpers, loudness measurements, the whole Part 1 pipeline and Part 2 report on synthetic audio, every rule, validation, dummy loader.

---

## 18. Known limitations (honest)

1. **Domain mismatch:** DEAM is music only; science videos mix speech + music. Separation helps, but the background track still contains residual voice and sound effects.
2. **Valence leans negative:** mean valence was negative on all test videos (−0.19 to −0.29), also after separation. Likely the quiet, ambient style of science-video music and the music-only training data. Rules therefore compare each video with its own average.
3. **Separation is slow on CPU** (~2 min per 3-minute clip; slower on battery). Hidden by the two-phase answer, not solved.
4. **Short training sequences:** most DEAM clips give ~5 windows; inference uses 35.
5. **Noisy labels** and **one random seed**: small differences between models may not be significant.
6. **Thresholds tuned on few videos** (relative delta 0.04, R3 std 0.03, loudness 10 dB) are starting values.
7. **Comment relevance isn't checked:** any negative comment near a section counts as support (topic matching is C3's job).
8. **Dummy C1, C2, C3 data:** the fusion and validation logic are real; their inputs are placeholders, so the validation numbers demonstrate the method only.
9. **CLAP music descriptions** are zero-shot and not checked against human labels.
10. **Only the first 3 minutes** of each video are analysed.

---

## 19. Future work (towards the final submission)

- Real C1/C2/C3 outputs; real validation with Component 3's comments; recommendation relevance rated by creators; SUS usability test.
- Knowledge graph with PyKEEN/TransE over Neo4j (C1/C2).
- Extra features (VGGish, openSMILE/eGeMAPS), CNN front-end, PMEmo; multi-seed training, cross-validation.
- Faster separation (GPU or a lighter model), full-length videos, batch processing.
- Optional LLM rephrasing of suggestions (rules still decide); integration into the team dashboard and browser extension.
