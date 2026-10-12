from app.models.ingest import IngestPayload

TYPE_MAP = {
    "concept": "concept", "concepts": "concept",
    "fact": "fact", "facts": "fact",
    "definition": "definition", "definitions": "definition",
    "entity": "entity", "entities": "entity",
    "relationship": "relationship", "relationships": "relationship", "relation": "relationship",
}
GROUP_KEYS = ("entities", "concepts", "facts", "definitions", "relationships")


def _fmt_ts(v) -> str:
    if isinstance(v, (int, float)):
        s = int(v)
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
    return str(v)


def _item(raw: dict, default_type: str | None = None) -> dict:
    t = TYPE_MAP.get(str(raw.get("type", default_type)).lower())
    if t is None:
        raise ValueError(f"Unknown item type: {raw.get('type', default_type)!r}")
    if t == "relationship" and not raw.get("text"):
        text = f"{raw['subject']} {raw['relation']} {raw['object']}"
    else:
        text = raw.get("text") or raw.get("name") or raw.get("content")
    if not text:
        raise ValueError(f"Item has no text: {raw}")
    ts = raw.get("timestamp", raw.get("start", raw.get("time", "00:00:00")))
    return {"type": t, "text": text, "timestamp": _fmt_ts(ts), "confidence": raw.get("confidence")}


def to_payloads(raw) -> list[IngestPayload]:
    videos = raw if isinstance(raw, list) else raw.get("videos", [raw])
    out = []
    for v in videos:
        vid = v.get("video_id") or v.get("videoId") or v.get("id")
        if not vid:
            raise ValueError("Video has no video_id")
        items = [_item(it) for it in v.get("items", [])]
        for key in GROUP_KEYS:
            items.extend(_item(it, key) for it in v.get(key, []))
        out.append(IngestPayload(video_id=str(vid), items=items))
    return out