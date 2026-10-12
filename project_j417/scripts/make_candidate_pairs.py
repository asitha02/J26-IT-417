import csv
from pathlib import Path

import numpy as np

from app.db.mongo import db
from app.models.ingest import IngestPayload
from app.services.embedding import embed_texts
from app.services.preprocess import preprocess_payload

units = []
for doc in db.raw_extractions.find({}):
    doc.pop("_id", None)
    units.extend(preprocess_payload(IngestPayload(**doc)))

emb = embed_texts([u.text for u in units])
sim = emb @ emb.T

pairs = []
for i in range(len(units)):
    for j in range(i + 1, len(units)):
        if units[i].video_id != units[j].video_id and 0.45 <= sim[i, j] <= 0.97:
            pairs.append((float(sim[i, j]), units[i].text, units[j].text))

pairs.sort(reverse=True)
step = max(1, len(pairs) // 150)          # spread across the similarity range
chosen = pairs[::step][:150]

Path("evaluation").mkdir(exist_ok=True)
with open("evaluation/candidates.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text_a", "text_b", "label"])
    for _, a, b in chosen:
        w.writerow([a, b, ""])

print(f"{len(units)} units -> wrote {len(chosen)} candidate pairs to evaluation/candidates.csv")