from app.models.ingest import IngestPayload
from app.services.preprocess import preprocess_payload
from app.services.embedding import embed_texts
from app.services.dedupe import group_units
from app.services.merge import merge_groups

payloads = [
    IngestPayload(video_id="v1", items=[
        {"type": "definition", "text": "Gradient descent minimizes a loss function.", "timestamp": "00:03:10"},
        {"type": "fact", "text": "The capital of France is Paris.", "timestamp": "00:05:00"},
    ]),
    IngestPayload(video_id="v2", items=[
        {"type": "definition", "text": "Gradient descent is an optimization algorithm used to reduce the loss.", "timestamp": "00:07:45"},
        {"type": "fact", "text": "Backpropagation computes gradients in neural networks.", "timestamp": "00:09:20"},
    ]),
    IngestPayload(video_id="v3", items=[
        {"type": "definition", "text": "Gradient descent minimizes a loss function.", "timestamp": "00:01:30"},
        {"type": "fact", "text": "Neural networks use backpropagation to compute gradients.", "timestamp": "00:02:10"},
    ]),
]

units = []
for p in payloads:
    units.extend(preprocess_payload(p))

groups = group_units(units, embed_texts([u.text for u in units]))
items = merge_groups(units, groups)

print(f"units in: {len(units)}  ->  KB items out: {len(items)}\n")
for it in items:
    print(f"[{it.type}] {it.text}")
    print(f"   merged_from={it.merged_from}  sources={[(s.video_id, s.timestamp) for s in it.sources]}")
    if it.variants:
        print(f"   variants={it.variants}")