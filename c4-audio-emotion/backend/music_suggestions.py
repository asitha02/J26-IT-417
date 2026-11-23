"""
Background music suggestions (Part 2): recommend 3-5 free-to-use tracks that fit the video.

How it works (rule-based, like the rest of fusion, so every suggestion can be explained):

  1. Each catalog track has published MOOD TAGS (e.g. "Calming", "Bright"). A fixed table (TAG_MOOD)
     turns each tag into a point on the valence-arousal map; the track's mood = the average of its tags.
     (valence = negative <-> positive, arousal = calm <-> energetic, both in [-1, 1].)
  2. The TARGET mood for the video comes from:
       - what kind of content it is (C1 sections: hook / explanation / example / summary),
         weighted by how long each section is, and
       - the problems already found (e.g. "low energy" -> a bit livelier, "tense" -> calmer).
  3. Tracks are ranked by distance to the target mood (closest first). The top MUSIC_SUGGESTION_COUNT
     are suggested, keeping at least one track from each source (Kevin MacLeod and Pixabay).

Why several tracks and not one? Music taste is subjective: the rules narrow the choice to the
right MOOD, and the creator picks the track they like.

Why a curated catalog (not a live music API)? It needs no API key or internet at analysis time,
every track's license was checked by hand, and the results are reproducible.
"""
import json
import math

from backend.config import MUSIC_CATALOG_PATH, MUSIC_SUGGESTION_COUNT
from backend.model import quadrant_of

# Mood tag -> (valence, arousal). My own fixed mapping onto Russell's circumplex
# (e.g. "Calming" = pleasant and low-energy, "Suspenseful" = unpleasant and high-energy).
TAG_MOOD = {
    "Bright": (0.6, 0.2), "Uplifting": (0.7, 0.4), "Bouncy": (0.5, 0.6), "Grooving": (0.3, 0.4),
    "Humorous": (0.5, 0.3), "Driving": (0.1, 0.7), "Action": (0.0, 0.8), "Epic": (0.3, 0.8),
    "Intense": (-0.2, 0.8), "Calming": (0.3, -0.6), "Relaxed": (0.4, -0.5), "Mystical": (0.0, -0.3),
    "Mysterious": (-0.2, 0.0), "Eerie": (-0.5, 0.1), "Somber": (-0.5, -0.4), "Dark": (-0.6, 0.1),
    "Suspenseful": (-0.4, 0.5), "Unnerving": (-0.6, 0.4),
}

# Content type (from C1) -> the music mood that usually suits it.
CONTENT_MOOD = {
    "hook": (0.5, 0.5),          # lively and positive: grabs attention in the first seconds
    "explanation": (0.4, -0.4),  # calm and positive: lets viewers concentrate on the idea
    "example": (0.4, 0.1),       # positive with a little movement
    "summary": (0.5, -0.1),      # warm and settled
}
DEFAULT_MOOD = (0.4, -0.2)       # no C1 sections: calm-positive suits most educational science videos

# Problem type (from the recommendations) -> (change in valence, change in arousal, reason).
ADJUSTMENTS = {
    "low_energy_segment": (0.0, 0.2, "Parts of your music were flagged as low-energy, so the suggestions are a bit livelier."),
    "tense_audio_segment": (0.1, -0.2, "Parts of your music were flagged as tense, so the suggestions are calmer and brighter."),
    "intense_audio_complex_content": (0.1, -0.2, "Intense music played over hard content, so the suggestions are calmer."),
    "music_too_loud": (0.0, -0.1, "Your music was too loud under your voice, so the suggestions are a bit softer."),
}

MOOD_WORDS = {
    "energetic_positive": "lively and positive",
    "tense_negative": "tense and dark",
    "low_negative": "calm and dark",
    "calm_positive": "calm and positive",
}
SOURCE_NAMES = {"incompetech": "Kevin MacLeod (incompetech.com)", "pixabay": "Pixabay Music"}
MAX_DISTANCE = 2 * math.sqrt(2)   # largest possible distance on the [-1, 1] x [-1, 1] map


def clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


def tag_mood(tags: list[str]) -> tuple[float, float]:
    """Average (valence, arousal) of a track's known mood tags."""
    points = [TAG_MOOD[t] for t in tags if t in TAG_MOOD]
    if not points:
        return 0.0, 0.0
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def load_catalog(path=MUSIC_CATALOG_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["tracks"]


def target_mood(c1: dict, recommendations: list[dict]) -> tuple[float, float, list[str]]:
    """The mood the background music should have, plus plain-language reasons."""
    sections = [s for s in (c1 or {}).get("sections", []) if s.get("content_type") in CONTENT_MOOD]
    total = sum(s["end_s"] - s["start_s"] for s in sections)
    if total > 0:
        v = sum(CONTENT_MOOD[s["content_type"]][0] * (s["end_s"] - s["start_s"]) for s in sections) / total
        a = sum(CONTENT_MOOD[s["content_type"]][1] * (s["end_s"] - s["start_s"]) for s in sections) / total
        share = {t: sum(s["end_s"] - s["start_s"] for s in sections if s["content_type"] == t) / total
                 for t in CONTENT_MOOD}
        main = max(share, key=share.get)
        reasons = [f"Most of the video is {main} ({share[main]:.0%} of the time), "
                   f"which suits {MOOD_WORDS[quadrant_of(*CONTENT_MOOD[main])]} music."]
    else:
        v, a = DEFAULT_MOOD
        reasons = ["No transcript sections available, so the default for educational videos is used (calm and positive)."]

    found = {r["type"] for r in recommendations}
    for rec_type, (dv, da, reason) in ADJUSTMENTS.items():
        if rec_type in found:
            v, a = v + dv, a + da
            reasons.append(reason)
    return round(clip(v), 2), round(clip(a), 2), reasons


def best_for(arousal: float) -> str:
    if arousal >= 0.3:
        return "the hook / intro"
    if arousal <= -0.2:
        return "explanations"
    return "examples and the recap"


def credit_line(track: dict) -> str:
    """The text the creator must paste into the video description (only for CC BY tracks)."""
    if track["license"] != "CC BY 4.0":
        return ""
    return (f'"{track["title"]}" {track["artist"]} (incompetech.com)\n'
            "Licensed under Creative Commons: By Attribution 4.0 License\n"
            "http://creativecommons.org/licenses/by/4.0/")


def rank_tracks(catalog: list[dict], v: float, a: float) -> list[dict]:
    """Every track with its mood and match score, best match first."""
    ranked = []
    for t in catalog:
        tv, ta = tag_mood(t["mood_tags"])
        match = 1 - math.dist((tv, ta), (v, a)) / MAX_DISTANCE
        ranked.append({
            "title": t["title"], "artist": t["artist"], "source": t["source"],
            "license": t["license"], "attribution_required": t["license"] == "CC BY 4.0",
            "credit": credit_line(t), "url": t["url"], "mood_tags": t["mood_tags"],
            "valence": round(tv, 2), "arousal": round(ta, 2), "match": round(match, 2),
            "best_for": best_for(ta),
            "why": (f"Tagged {', '.join(t['mood_tags'][:3]).lower()}: {MOOD_WORDS[quadrant_of(tv, ta)]}, "
                    f"{match:.0%} match to the target mood; works well for {best_for(ta)}."),
        })
    ranked.sort(key=lambda r: (-r["match"], r["title"]))
    return ranked


def pick(ranked: list[dict], count: int) -> list[dict]:
    """Top `count` tracks, swapping the last one(s) so that every source appears at least once."""
    chosen = ranked[:count]
    for source in SOURCE_NAMES:
        if not any(r["source"] == source for r in chosen):
            best_missing = next((r for r in ranked if r["source"] == source), None)
            if best_missing:
                # replace the weakest track from a source that appears more than once
                for i in range(len(chosen) - 1, -1, -1):
                    if sum(r["source"] == chosen[i]["source"] for r in chosen) > 1:
                        chosen[i] = best_missing
                        break
    return sorted(chosen, key=lambda r: (-r["match"], r["title"]))


def suggest_music(c1: dict, recommendations: list[dict], catalog: list[dict] = None,
                  count: int = MUSIC_SUGGESTION_COUNT) -> dict:
    """The `music_suggestions` field of the Part 2 report."""
    catalog = catalog if catalog is not None else load_catalog()
    v, a, reasons = target_mood(c1, recommendations)
    loud = any(r["type"] in ("music_too_loud", "audio_complaints") for r in recommendations)
    return {
        "target_valence": v,
        "target_arousal": a,
        "target_mood": MOOD_WORDS[quadrant_of(v, a)],
        "reasons": reasons,
        "tracks": pick(rank_tracks(catalog, v, a), count),
        "mixing_tip": ("Whichever track you choose, keep it more than 10 dB quieter than your voice "
                       "(your current mix was flagged as too loud)." if loud else
                       "Keep the music more than 10 dB quieter than your voice so the narration stays clear."),
        "catalog_size": len(catalog),
        "note": ("These tracks are free to use, not copyright-free: Kevin MacLeod tracks (CC BY 4.0) need the credit "
                 "line in your video description; Pixabay tracks need no credit, but check the track page for a "
                 "'Content ID' notice before monetising. Track moods are estimated from their published mood tags."),
    }
