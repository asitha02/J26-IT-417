"""
Fusion rules: combine three signals into prescriptive recommendations for the creator
(CLAUDE.md section 10):
  1. audio emotion timeline   (my model: valence/arousal per window)
  2. audience sentiment       (C3, dummy for now)
  3. knowledge gaps           (knowledge graph, dummy for now)

Why rules (not another ML model)? They are transparent: every recommendation says
exactly WHICH evidence triggered it, so a creator (and the panel) can check it.

Each rule is a small separate function returning a list of recommendations.
Confidence starts at BASE_CONFIDENCE for one source of evidence and rises by
CORROBORATION_BONUS for every independent signal that agrees, capped at MAX_CONFIDENCE.
"""
from backend.config import (
    AUDIO_KEYWORDS,
    BASE_CONFIDENCE,
    COMMENT_WINDOW_S,
    CORROBORATION_BONUS,
    MAX_CONFIDENCE,
    NEGATIVE_SENTIMENT,
    R1_LOW_AROUSAL,
    R1_MIN_DURATION_S,
    R2_HIGH_AROUSAL,
    R2_LOW_VALENCE,
    R2_MIN_DURATION_S,
    R3_MIN_AROUSAL_VARIANCE,
    R4_INTENSE_AROUSAL,
)

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------- small helpers ----------

def mmss(seconds: float) -> str:
    """130 -> '02:10'"""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def confidence(corroborating_signals: int) -> float:
    """0.5 for one source of evidence, +0.2 for each independent signal that agrees, max 0.95."""
    return round(min(MAX_CONFIDENCE, BASE_CONFIDENCE + CORROBORATION_BONUS * corroborating_signals), 2)


def find_runs(segments: list[dict], condition) -> list[list[dict]]:
    """
    Group consecutive segments for which condition(segment) is True.
    Example: conditions [F, T, T, F, T] -> runs [[seg1, seg2], [seg4]]
    """
    runs, current = [], []
    for seg in segments:
        if condition(seg):
            current.append(seg)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def negative_comments_near(c3: dict, start: float, end: float) -> list[dict]:
    """C3 comments with negative sentiment inside [start - 15 s, end + 15 s]."""
    return [
        c for c in c3.get("timestamped_feedback", [])
        if c["sentiment"] < NEGATIVE_SENTIMENT and start - COMMENT_WINDOW_S <= c["t_s"] <= end + COMMENT_WINDOW_S
    ]


def audio_complaints(c3: dict) -> list[str]:
    """C3 top complaints that mention an audio/pacing keyword (music, loud, slow...)."""
    return [c for c in c3.get("top_complaints", []) if any(k in c.lower() for k in AUDIO_KEYWORDS)]


def comment_evidence(comment: dict) -> str:
    return f"Viewer comment at {mmss(comment['t_s'])}: '{comment['text']}' (sentiment {comment['sentiment']:+.1f})"


def make_rec(rule_id, rec_type, severity, start, end, title, evidence, suggestion, conf) -> dict:
    """Build one recommendation in the CLAUDE.md section 8.1 format (id is added at the end)."""
    return {"rule_id": rule_id, "type": rec_type, "severity": severity, "start_s": start, "end_s": end,
            "title": title, "evidence": evidence, "suggestion": suggestion, "confidence": conf}


# ---------- the six rules ----------

def rule_r1_low_energy(segments: list[dict], c3: dict) -> list[dict]:
    """R1: arousal < -0.3 for >= 30 s. High severity if a negative viewer comment is nearby."""
    recs = []
    for run in find_runs(segments, lambda s: s["arousal"] < R1_LOW_AROUSAL):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        if end - start < R1_MIN_DURATION_S:
            continue
        mean_arousal = sum(s["arousal"] for s in run) / len(run)
        evidence = [f"Arousal below {R1_LOW_AROUSAL} for {end - start:.0f} s (mean {mean_arousal:.2f})"]
        comments = negative_comments_near(c3, start, end)
        evidence += [comment_evidence(c) for c in comments]
        recs.append(make_rec(
            "R1_low_energy", "low_energy_segment", "high" if comments else "medium", start, end,
            f"Low-energy audio during {mmss(start)}–{mmss(end)}", evidence,
            "Raise the pace or add more dynamic background music, or shorten this section.",
            confidence(1 if comments else 0),
        ))
    return recs


def rule_r2_tense_audio(segments: list[dict], c3: dict) -> list[dict]:
    """R2: arousal > 0.6 and valence < -0.3 for >= 20 s. High if viewers complain about audio."""
    recs = []
    complaints = audio_complaints(c3)
    tense = lambda s: s["arousal"] > R2_HIGH_AROUSAL and s["valence"] < R2_LOW_VALENCE
    for run in find_runs(segments, tense):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        if end - start < R2_MIN_DURATION_S:
            continue
        mean_v = sum(s["valence"] for s in run) / len(run)
        mean_a = sum(s["arousal"] for s in run) / len(run)
        evidence = [f"Tense audio for {end - start:.0f} s (mean arousal {mean_a:+.2f}, mean valence {mean_v:+.2f})"]
        evidence += [f"Viewer complaint: '{c}'" for c in complaints]
        recs.append(make_rec(
            "R2_tense_audio", "tense_audio_segment", "high" if complaints else "medium", start, end,
            f"Tense, intense audio during {mmss(start)}–{mmss(end)}", evidence,
            "Lower the background music under narration and keep the narration clearly audible.",
            confidence(1 if complaints else 0),
        ))
    return recs


def rule_r3_flat_profile(segments: list[dict], analyzed_seconds: float) -> list[dict]:
    """R3: arousal barely changes across the whole clip (low variance) -> monotonous."""
    if len(segments) < 3:          # too short to judge variety
        return []
    arousal = [s["arousal"] for s in segments]
    mean = sum(arousal) / len(arousal)
    variance = sum((a - mean) ** 2 for a in arousal) / len(arousal)
    if variance >= R3_MIN_AROUSAL_VARIANCE:
        return []
    return [make_rec(
        "R3_flat_profile", "flat_energy_profile", "low", 0, analyzed_seconds,
        "Audio energy stays the same throughout",
        [f"Arousal variance {variance:.4f} (below {R3_MIN_AROUSAL_VARIANCE}); energy ranges only "
         f"{min(arousal):+.2f} to {max(arousal):+.2f}"],
        "Vary the music energy between sections (e.g. calmer for explanations, livelier for key moments) to hold attention.",
        confidence(0),
    )]


def rule_r4_complex_content_audio(segments: list[dict], gaps: dict, c3: dict) -> list[dict]:
    """R4: a knowledge gap (hard, unexplained content) overlaps intense audio (arousal > 0.4)."""
    recs = []
    for gap in gaps.get("gaps", []):
        overlapping = [s for s in segments
                       if s["start_s"] < gap["end_s"] and s["end_s"] > gap["start_s"] and s["arousal"] > R4_INTENSE_AROUSAL]
        if not overlapping:
            continue
        peak = max(s["arousal"] for s in overlapping)
        evidence = [
            f"Knowledge gap '{gap['topic']}' at {mmss(gap['start_s'])}–{mmss(gap['end_s'])}: {gap['description']}",
            f"Arousal up to {peak:+.2f} during this explanation ({len(overlapping)} intense window(s))",
        ]
        comments = negative_comments_near(c3, gap["start_s"], gap["end_s"])
        evidence += [comment_evidence(c) for c in comments]
        recs.append(make_rec(
            "R4_complex_content_audio", "intense_audio_complex_content",
            "high" if gap["severity"] == "high" or comments else "medium",
            gap["start_s"], gap["end_s"],
            f"Intense audio while explaining '{gap['topic']}'", evidence,
            "Use calmer audio during complex explanations, and add a short recap or visual for this concept.",
            confidence(1 + (1 if comments else 0)),   # audio + gap agree; a nearby comment adds more
        ))
    return recs


def rule_r5_audio_complaints(c3: dict, analyzed_seconds: float) -> list[dict]:
    """R5: audience is negative overall AND complaints mention audio/pacing keywords."""
    complaints = audio_complaints(c3)
    if c3.get("sentiment_score", 0) >= NEGATIVE_SENTIMENT or not complaints:
        return []
    return [make_rec(
        "R5_audio_complaints", "audio_complaints", "medium", 0, analyzed_seconds,
        "Viewers complain about the audio or pacing",
        [f"Overall comment sentiment {c3['sentiment_score']:+.2f} ({c3.get('comment_count', '?')} comments)"]
        + [f"Complaint: '{c}'" for c in complaints],
        "Review the mixing levels (music vs. narration) and the pacing across the whole video.",
        confidence(len(complaints) - 1),        # several separate complaints agree with each other
    )]


def rule_r6_requested_topics(c3: dict, gaps: dict, analyzed_seconds: float) -> list[dict]:
    """R6: topics viewers ask for that the video doesn't cover (not even as a gap). Low priority."""
    covered = [g["topic"].lower() for g in gaps.get("gaps", [])]
    missing = [t for t in c3.get("requested_topics", [])
               if not any(t.lower() in c or c in t.lower() for c in covered)]
    if not missing:
        return []
    return [make_rec(
        "R6_requested_topics", "requested_topics", "low", 0, analyzed_seconds,
        "Viewers ask for topics this video doesn't cover",
        [f"Requested topic: '{t}'" for t in missing],
        "Consider a follow-up video or a short extra section on these topics.",
        confidence(0),
    )]


# ---------- combine ----------

def merge_overlapping(recs: list[dict]) -> list[dict]:
    """Merge recommendations of the same type whose time ranges overlap into one."""
    merged = []
    for rec in sorted(recs, key=lambda r: (r["type"], r["start_s"])):
        last = merged[-1] if merged else None
        if last and last["type"] == rec["type"] and rec["start_s"] <= last["end_s"]:
            last["end_s"] = max(last["end_s"], rec["end_s"])
            last["evidence"] += [e for e in rec["evidence"] if e not in last["evidence"]]
            last["confidence"] = max(last["confidence"], rec["confidence"])
            if SEVERITY_ORDER[rec["severity"]] < SEVERITY_ORDER[last["severity"]]:
                last["severity"] = rec["severity"]
        else:
            merged.append(rec)
    return merged


def generate_recommendations(segments: list[dict], c3: dict = None, gaps: dict = None,
                             analyzed_seconds: float = None) -> list[dict]:
    """Run every rule, merge overlaps, sort (most severe first, then most confident) and number them."""
    c3, gaps = c3 or {}, gaps or {}
    if analyzed_seconds is None:
        analyzed_seconds = segments[-1]["end_s"] if segments else 0

    recs = (
        rule_r1_low_energy(segments, c3)
        + rule_r2_tense_audio(segments, c3)
        + rule_r3_flat_profile(segments, analyzed_seconds)
        + rule_r4_complex_content_audio(segments, gaps, c3)
        + rule_r5_audio_complaints(c3, analyzed_seconds)
        + rule_r6_requested_topics(c3, gaps, analyzed_seconds)
    )
    recs = merge_overlapping(recs)
    recs.sort(key=lambda r: (SEVERITY_ORDER[r["severity"]], -r["confidence"]))
    for i, rec in enumerate(recs, start=1):
        rec["id"] = f"rec_{i:03d}"
    return recs
