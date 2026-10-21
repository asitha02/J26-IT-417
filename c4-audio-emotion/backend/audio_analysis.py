"""
Part 1: Affective Audio Analysis (descriptive). Builds the Part 1 result for one video.

    audio (first 3 min) --separation--> speech + background music
       background music -> CLAP -> my BiLSTM+attention head -> valence/arousal per window   (main result)
       mixed audio      -> same model                       -> valence/arousal per window   (comparison)
       all three tracks -> loudness measurements            -> audio problems
       music embeddings -> CLAP text matching               -> "what the music sounds like"

No YouTube or database code here, so the whole step can be tested with synthetic audio.
"""
from datetime import datetime, timezone

from backend.audio_problems import detect_problems, loudness_db, window_metrics
from backend.audio_utils import cut_segments
from backend.config import HOP_SECONDS, SAMPLE_RATE, SEGMENT_SECONDS
from backend.model import quadrant_of, summarize


def run_audio_analysis(video_id: str, title: str, audio, emotion_model, separator,
                       mixed_preds=None, on_progress=None) -> dict:
    """
    mixed_preds: emotion of the mixed audio if already computed (phase 1), so it isn't computed twice.
    on_progress: optional function(fraction 0..1) called while the (slow) separation runs.
    """
    speech, music = separator.separate(audio, on_progress=on_progress)

    # Emotion of the background music (main result) and of the mixed audio (for comparison).
    music_preds, music_embeddings = emotion_model.analyze(cut_segments(music), video_id=video_id)
    if music is audio:                      # no separation: the "music" IS the mixed audio
        mixed_preds = music_preds
    elif mixed_preds is None:
        mixed_preds, _ = emotion_model.analyze(cut_segments(audio), video_id=video_id)
    window_labels, music_description = emotion_model.describe(music_embeddings)
    metrics = window_metrics(audio, speech, music)

    segments = []
    for i, (m, x, w) in enumerate(zip(music_preds, mixed_preds, metrics)):
        segments.append({
            **m,
            "quadrant": quadrant_of(m["valence"], m["arousal"]),
            "mixed_valence": x["valence"],
            "mixed_arousal": x["arousal"],
            **{k: w[k] for k in ("speech_db", "music_db", "music_minus_speech_db", "clipping_pct", "silent")},
            "music_label": window_labels[i] if window_labels else None,
        })
    mixed_segments = [{**x, "quadrant": quadrant_of(x["valence"], x["arousal"])} for x in mixed_preds]

    return {
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "analyzed_seconds": round(len(audio) / SAMPLE_RATE, 2),
        "segment_seconds": SEGMENT_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "model_info": emotion_model.info,
        "separation": {**separator.info,
                       "speech_db": round(loudness_db(speech), 1),
                       "music_db": round(loudness_db(music), 1)},
        "segments": segments,
        "overall": summarize(segments),
        "overall_mixed": summarize(mixed_segments),
        "music_description": music_description,
        "audio_problems": detect_problems(metrics),
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
