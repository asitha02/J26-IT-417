"""
Fusion rules: turn the emotion timeline (+ later C3 sentiment and knowledge gaps)
into prescriptive recommendations for the creator. See CLAUDE.md section 10.

Each rule is a small separate function, so it can be tested and explained on its own.
Every recommendation carries human-readable "evidence" explaining why it was made.

Day 4: R1 (audio-only part).
Day 11: R1 + C3 comments, and rules R2-R6.
"""
from backend.config import R1_LOW_AROUSAL, R1_MIN_DURATION_S


def mmss(seconds: float) -> str:
    """130 -> '02:10'"""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


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


def rule_r1_low_energy(segments: list[dict]) -> list[dict]:
    """R1: arousal stays below R1_LOW_AROUSAL for at least R1_MIN_DURATION_S seconds."""
    recommendations = []
    for run in find_runs(segments, lambda s: s["arousal"] < R1_LOW_AROUSAL):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        duration = end - start
        if duration < R1_MIN_DURATION_S:
            continue
        mean_arousal = sum(s["arousal"] for s in run) / len(run)
        recommendations.append({
            "rule_id": "R1_low_energy",
            "type": "low_energy_segment",
            "severity": "medium",   # Day 11: becomes "high" if a negative viewer comment is nearby
            "start_s": start,
            "end_s": end,
            "title": f"Low-energy audio during {mmss(start)}–{mmss(end)}",
            "evidence": [
                f"Arousal below {R1_LOW_AROUSAL} for {duration:.0f} s",
                f"Mean arousal in this section: {mean_arousal:.2f}",
            ],
            "suggestion": "Raise the pace or add more dynamic background music, or shorten this section.",
            "confidence": 0.5,      # audio-only evidence; corroborating signals add to this on Day 11
        })
    return recommendations


def generate_recommendations(segments: list[dict]) -> list[dict]:
    """Run every rule, sort by severity then confidence, and number the results."""
    recommendations = rule_r1_low_energy(segments)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: (severity_order[r["severity"]], -r["confidence"]))
    for i, rec in enumerate(recommendations, start=1):
        rec["id"] = f"rec_{i:03d}"
    return recommendations
