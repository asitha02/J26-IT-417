"""
Part 2: segment-level validation against audience comments (the core claim of the research gap:
"flagged segments should be checked against what real viewers react to").

  agreement        share of flagged time ranges with a negative viewer comment within ±15 s
  random_baseline  the same share for time ranges of the same length placed anywhere in the
                   video, i.e. what pure chance would give (computed exactly, every 1 s position)
  lift             agreement / random_baseline: above 1 = the flags find viewer complaints more
                   often than chance; 1 = no better than chance
  comments_explained  how many negative comments fall inside at least one flagged range

Only recommendations about a specific section count as "flagged"; whole-video ones
(e.g. overall complaints) can't be checked against a moment in time.
With DUMMY C3 comments this demonstrates the METHOD only; it is not evidence yet.
"""
from backend.config import COMMENT_WINDOW_S, NEGATIVE_SENTIMENT


def _hit(start: float, end: float, times: list[float]) -> bool:
    """Is any comment time inside [start - window, end + window]?"""
    return any(start - COMMENT_WINDOW_S <= t <= end + COMMENT_WINDOW_S for t in times)


def chance_of_hit(length: float, total: float, times: list[float]) -> float:
    """Share of all 1-second start positions where a range of this length would hit a comment."""
    if length >= total:
        return 1.0 if times else 0.0
    starts = range(0, int(total - length) + 1)
    return sum(_hit(s, s + length, times) for s in starts) / len(starts)


def validate(recommendations: list[dict], c3: dict, analyzed_seconds: float) -> dict:
    negative_times = [c["t_s"] for c in c3.get("timestamped_feedback", []) if c["sentiment"] < NEGATIVE_SENTIMENT]
    flagged = [r for r in recommendations if not (r["start_s"] <= 0 and r["end_s"] >= analyzed_seconds)]

    agreeing = [r for r in flagged if _hit(r["start_s"], r["end_s"], negative_times)]
    explained = [t for t in negative_times
                 if any(r["start_s"] - COMMENT_WINDOW_S <= t <= r["end_s"] + COMMENT_WINDOW_S for r in flagged)]

    agreement = len(agreeing) / len(flagged) if flagged else None
    baseline = (sum(chance_of_hit(r["end_s"] - r["start_s"], analyzed_seconds, negative_times) for r in flagged)
                / len(flagged)) if flagged else None
    lift = agreement / baseline if agreement is not None and baseline else None

    if not flagged:
        explanation = "No section-specific recommendations to check."
    elif not negative_times:
        explanation = "There are no negative viewer comments to compare with."
    else:
        explanation = (f"{len(agreeing)} of {len(flagged)} flagged sections have a negative viewer comment within "
                       f"±{COMMENT_WINDOW_S} s ({agreement:.0%}). Sections of the same length placed at random would "
                       f"hit one {baseline:.0%} of the time, so the flags are {lift:.1f}× better than chance. "
                       f"{len(explained)} of {len(negative_times)} negative comments fall inside a flagged section.")

    return {
        "flagged_segments": len(flagged),
        "agreeing_segments": len(agreeing),
        "agreement": round(agreement, 3) if agreement is not None else None,
        "random_baseline": round(baseline, 3) if baseline is not None else None,
        "lift": round(lift, 2) if lift is not None else None,
        "negative_comments": len(negative_times),
        "comments_explained": len(explained),
        "explanation": explanation,
        "mock_data": bool(c3.get("mock", False)),
    }
