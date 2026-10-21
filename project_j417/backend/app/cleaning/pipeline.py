"""Turn the raw transcript JSONs into cleaned JSON, with a quality report.

For each segment of each video (timestamps and video ids are never changed):
  1. Remove redundant sentences (subscribe requests, sponsor reads...) and error words (fillers, stutters).
  2. Drop the segment if nothing meaningful is left.
  3. Drop it if it repeats a segment already kept - the same content again in the same video (a common
     speech-recognition glitch) or in another video.
  4. Flag it if the speech recogniser was unsure about it, so likely errors can be found.

Every removal is counted by reason, so nothing is lost silently: kept segments carry the id of the raw segment
and, when the text changed, the original text. Each of the three cleaning jobs is done by a trained model when
one has passed its test, and by hand-written rules otherwise (the output says which).
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.cleaning.cleaner import Cleaner
from app.cleaning.data import LOW_CONFIDENCE, latest_per_video
from app.cleaning.ml import words_of

SCHEMA_VERSION = "1.0"
MIN_WORDS = 3            # a segment with fewer meaningful words than this after cleaning is dropped
MIN_DUPLICATE_WORDS = 5  # shorter segments ("Yes.", "Right, so...") legitimately repeat, never treat as duplicates
SAME_VIDEO_WINDOW_SEC = 120  # within one video, only nearby repeats count (lecturers reuse phrases later on)
MAX_REMOVED_LISTED = 100

REASONS = {
    "too_short": "Nothing meaningful left after cleaning",
    "duplicate_in_video": "Repeated in the same video",
    "duplicate_across_videos": "Same content as another video",
}


def _grams(words: list[str], n: int = 4) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


class _Seen:
    """Kept segments, indexed by word 4-grams so a new segment is compared only with likely matches."""

    def __init__(self, cleaner: Cleaner):
        self.cleaner = cleaner
        self.items: list[dict] = []
        self.index: dict[tuple[str, ...], list[int]] = defaultdict(list)

    def match(self, words: list[str], source_id: str, start: float) -> dict | None:
        for i in sorted({i for g in _grams(words) for i in self.index.get(g, ())}):
            item = self.items[i]
            if item["source_id"] == source_id and abs(item["start"] - start) > SAME_VIDEO_WINDOW_SEC:
                continue
            if self.cleaner.is_duplicate(words, item["words"]):
                return item
        return None

    def add(self, words: list[str], source_id: str, seg_id: int, start: float) -> None:
        self.items.append({"source_id": source_id, "id": seg_id, "start": start, "words": words})
        for g in _grams(words):
            self.index[g].append(len(self.items) - 1)


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def clean_documents(docs: list[dict], cleaner: Cleaner | None = None, model_report: dict | None = None) -> dict:
    cleaner = cleaner or Cleaner()
    seen = _Seen(cleaner)
    videos, removed_listed = [], []
    totals = defaultdict(int)
    conf_sum, conf_n = 0.0, 0

    for doc in sorted(latest_per_video(docs), key=lambda d: (str(d.get("created_at", "")), d["source_id"])):
        sid = doc["source_id"]
        kept: list[dict] = []
        removed: defaultdict[str, int] = defaultdict(int)
        words_before = words_after = low = sentences_dropped = words_dropped = 0
        v_conf_sum, v_conf_n = 0.0, 0

        for seg in doc.get("segments", []):
            original = seg["text"].strip()
            words_before += len(original.split())
            text, s_dropped, w_dropped = cleaner.clean_text(original)
            sentences_dropped += s_dropped
            words_dropped += w_dropped
            words = words_of(text)

            reason, twin = None, None
            if len(text.split()) < MIN_WORDS:
                reason = "too_short"
            elif len(words) >= MIN_DUPLICATE_WORDS:
                twin = seen.match(words, sid, float(seg["start"]))
                if twin:
                    reason = "duplicate_in_video" if twin["source_id"] == sid else "duplicate_across_videos"

            if reason:
                removed[reason] += 1
                if len(removed_listed) < MAX_REMOVED_LISTED:
                    removed_listed.append({
                        "source_id": sid, "id": seg["id"], "start": seg["start"], "reason": reason, "text": original,
                        **({"duplicate_of": {k: twin[k] for k in ("source_id", "id", "start")}} if twin else {}),
                    })
                continue

            if len(words) >= MIN_DUPLICATE_WORDS:
                seen.add(words, sid, seg["id"], float(seg["start"]))
            conf = seg.get("confidence")
            is_low = conf is not None and conf < LOW_CONFIDENCE
            low += is_low
            if conf is not None:
                v_conf_sum, v_conf_n = v_conf_sum + conf, v_conf_n + 1
            words_after += len(text.split())
            kept.append({
                "id": seg["id"], "start": seg["start"], "end": seg["end"], "text": text, "confidence": conf,
                "low_confidence": is_low, **({"original_text": original} if text != original else {}),
            })

        raw = len(doc.get("segments", []))
        videos.append({
            "source_id": sid,
            "title": doc.get("title"),
            "source_url": doc["source_url"],
            "uploader": doc.get("uploader"),
            "duration_sec": doc.get("duration_sec"),
            "language": doc.get("language"),
            "asr_model": doc.get("asr_model"),
            "quality": {
                "segments_raw": raw,
                "segments_kept": len(kept),
                "removed": {r: removed.get(r, 0) for r in REASONS},
                "redundant_sentences_removed": sentences_dropped,
                "error_words_removed": words_dropped,
                "words_before": words_before,
                "words_after": words_after,
                "words_removed_pct": _pct(words_before - words_after, words_before),
                "avg_confidence": round(v_conf_sum / v_conf_n, 3) if v_conf_n else None,
                "low_confidence_segments": low,
            },
            "segments": kept,
        })
        conf_sum, conf_n = conf_sum + v_conf_sum, conf_n + v_conf_n
        for key, value in (("segments_raw", raw), ("segments_kept", len(kept)), ("words_before", words_before),
                           ("words_after", words_after), ("low_confidence_segments", low),
                           ("redundant_sentences_removed", sentences_dropped), ("error_words_removed", words_dropped)):
            totals[key] += value
        for r in REASONS:
            totals[f"removed_{r}"] += removed.get(r, 0)

    summary = {
        "videos": len(videos),
        "segments_raw": totals["segments_raw"],
        "segments_kept": totals["segments_kept"],
        "removed": {r: totals[f"removed_{r}"] for r in REASONS},
        "redundant_sentences_removed": totals["redundant_sentences_removed"],
        "error_words_removed": totals["error_words_removed"],
        "words_before": totals["words_before"],
        "words_after": totals["words_after"],
        "words_removed_pct": _pct(totals["words_before"] - totals["words_after"], totals["words_before"]),
        "avg_confidence": round(conf_sum / conf_n, 3) if conf_n else None,
        "low_confidence_segments": totals["low_confidence_segments"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cleaning": {
            "trained_models_in_use": cleaner.in_use,
            "min_words": MIN_WORDS,
            "min_duplicate_words": MIN_DUPLICATE_WORDS,
            "same_video_window_sec": SAME_VIDEO_WINDOW_SEC,
            "low_confidence_below": LOW_CONFIDENCE,
            "model_test_results": model_report,
        },
        "summary": summary,
        "videos": videos,
        "removed_examples": removed_listed,
    }
