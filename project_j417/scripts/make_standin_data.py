import json
import re
from pathlib import Path

from app.services.llm import complete

PROMPT = """Extract knowledge from this lecture transcript chunk.
Return ONLY a JSON list. Each element: {{"type": "concept|fact|definition|entity|relationship", "text": "<one self-contained sentence or term>"}}.
Use only information in the chunk. Do not add outside facts. 3-8 items.

Chunk:
{chunk}"""

TS = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s*")


def fmt(sec: int) -> str:
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def chunks(lines, size=12):
    for i in range(0, len(lines), size):
        part = lines[i:i + size]
        m = TS.match(part[0])
        ts = m.group(1) if m else fmt(i * 15)        # estimated if no timestamps
        yield ts, " ".join(TS.sub("", l) for l in part)


def parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


videos = []
for path in sorted(Path("data/transcripts").glob("*.txt")):
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = []
    for ts, chunk in chunks(lines):
        try:
            for it in parse_json(complete(PROMPT.format(chunk=chunk), max_tokens=800)):
                items.append({"type": it["type"], "text": it["text"], "timestamp": ts})
        except Exception as e:
            print(f"  skipped a chunk in {path.name}: {e}")
    videos.append({"video_id": path.stem, "items": items})
    print(f"{path.name}: {len(items)} items")

Path("evaluation").mkdir(exist_ok=True)
Path("evaluation/standin_component1.json").write_text(
    json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved evaluation/standin_component1.json")