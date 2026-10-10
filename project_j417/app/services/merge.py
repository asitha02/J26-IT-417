import numpy as np
from app.models.kb import KBItem, Source
from app.models.unit import KnowledgeUnit


def merge_groups(
    units: list[KnowledgeUnit], groups: list[list[int]]
) -> list[KBItem]:
    items: list[KBItem] = []
    for n, g in enumerate(groups):
        members = [units[i] for i in g]
        canon = max(members, key=lambda u: ((u.confidence or 0), len(u.text)))
        variants = sorted({u.text for u in members if u.norm_key != canon.norm_key})
        items.append(
            KBItem(
                kb_id=f"kb_{n:05d}",
                type=canon.type,
                text=canon.text,
                variants=variants,
                sources=[
                    Source(video_id=u.video_id, timestamp=u.timestamp, unit_id=u.unit_id)
                    for u in members
                ],
                merged_from=len(members),
            )
        )
    return items