import numpy as np
from app.core.config import SIM_THRESHOLD
from app.models.unit import KnowledgeUnit


def group_units(
    units: list[KnowledgeUnit],
    embeddings: np.ndarray,
    threshold: float = SIM_THRESHOLD,
) -> list[list[int]]:
    """Group near-duplicate units. Only units of the same type are compared."""
    n = len(units)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sim = embeddings @ embeddings.T
    for i in range(n):
        for j in range(i + 1, n):
            if units[i].type == units[j].type and sim[i, j] >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())