"""
Part 2: Content Enhancement Recommendations. Builds the full Part 2 report for one video
from the Part 1 result and the other components' outputs (dummy for now):

  descriptive   section_summaries  "what happened" in each C1 transcript section
  prescriptive  recommendations    "what to change", ranked, with evidence and a link (fusion.py)
  validation    validation         do the flagged sections match viewer complaints? (validation.py)
"""
from datetime import datetime, timezone

from backend.config import COMMENT_WINDOW_S, MUSIC_UNDER_SPEECH_LIMIT_DB, NEGATIVE_SENTIMENT
from backend.fusion import generate_recommendations, mmss
from backend.validation import validate

# Plain-language names for the four areas of the valence-arousal map.
MOOD_WORDS = {
    "energetic_positive": "lively and positive",
    "tense_negative": "tense and dark",
    "low_negative": "calm and dark (sad)",
    "calm_positive": "calm and positive",
}


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and a_end > b_start


def summarize_section(sec: dict, analysis: dict, gaps: dict, c3: dict) -> dict:
    """Descriptive summary of one transcript section: music mood, loudness, comments, gaps, problems."""
    windows = [s for s in analysis["segments"] if sec["start_s"] <= (s["start_s"] + s["end_s"]) / 2 < sec["end_s"]]

    if windows:
        quadrants = [w["quadrant"] for w in windows]
        mood = MOOD_WORDS[max(set(quadrants), key=quadrants.count)]
        labels = [w["music_label"] for w in windows if w.get("music_label")]
        if labels:
            mood += f"; sounds like {max(set(labels), key=labels.count)}"
        diffs = sorted(w["music_minus_speech_db"] for w in windows if w["music_minus_speech_db"] is not None)
    else:
        mood, diffs = "not analysed (outside the first 3 minutes)", []

    if not diffs:
        loudness = "no narration measured in this part"
    else:
        median = diffs[len(diffs) // 2]
        if median <= MUSIC_UNDER_SPEECH_LIMIT_DB:
            loudness = f"music {-median:.0f} dB below the voice (good)"
        elif median < 0:
            loudness = f"music only {-median:.0f} dB below the voice (too loud)"
        else:
            loudness = f"music {median:.0f} dB LOUDER than the voice"

    in_section = lambda t: sec["start_s"] - COMMENT_WINDOW_S <= t <= sec["end_s"] + COMMENT_WINDOW_S
    comments = [c for c in c3.get("timestamped_feedback", []) if in_section(c["t_s"])]
    gap_topics = [g["topic"] for g in gaps.get("gaps", []) if _overlaps(sec["start_s"], sec["end_s"], g["start_s"], g["end_s"])]
    problems = [p for p in analysis["audio_problems"] if _overlaps(sec["start_s"], sec["end_s"], p["start_s"], p["end_s"])]

    observations = [f"Measured: {p['description']}" for p in problems]
    observations += [f"Viewer at {mmss(c['t_s'])}: '{c['text']}' ({'negative' if c['sentiment'] < NEGATIVE_SENTIMENT else 'positive'})"
                     for c in comments]
    observations += [f"Knowledge gap: '{g}' is mentioned but not explained" for g in gap_topics]

    return {
        "start_s": sec["start_s"], "end_s": sec["end_s"], "topic": sec["topic"], "content_type": sec["content_type"],
        "music_mood": mood, "music_loudness": loudness,
        "negative_comments": sum(c["sentiment"] < NEGATIVE_SENTIMENT for c in comments),
        "knowledge_gaps": gap_topics, "observations": observations,
    }


def build_report(analysis: dict, c1: dict, c2: dict, c3: dict) -> dict:
    """The full Part 2 document (CLAUDE.md section 8.6)."""
    recommendations = generate_recommendations(
        analysis["segments"], c3, c2, analysis["analyzed_seconds"],
        c1=c1, audio_problems=analysis["audio_problems"], youtube_url=analysis["youtube_url"],
    )
    return {
        "video_id": analysis["video_id"],
        "youtube_url": analysis["youtube_url"],
        "title": analysis["title"],
        "inputs": {
            "audio_analysis_created_at": analysis["created_at"],
            "c1_input": c1,          # DUMMY ("mock": true) until Component 1 is connected
            "c2_input": c2,          # DUMMY until Component 2 is connected
            "c3_input": c3,          # DUMMY until Component 3 is connected
        },
        "section_summaries": [summarize_section(sec, analysis, c2, c3) for sec in c1.get("sections", [])],
        "recommendations": recommendations,
        "validation": validate(recommendations, c3, analysis["analyzed_seconds"]),
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
